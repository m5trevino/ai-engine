"""
PEACOCK ENGINE — Plan Queue & Sequential Runner (TB-017)
In-memory queue for multiple plans with sequential execution.

Scope:
  • Maintain an ordered queue of plan IDs awaiting execution
  • Provide manual enqueue/dequeue/list/clear operations
  • Run plans sequentially via PlanExecutor (TB-016)
  • Track runner state (idle / running / stopping)
  • Persist plan status transitions through PlanManager (TB-014)

References:
  • app.core.plan_manager       (TB-014)
  • app.core.plan_executor      (TB-016)
"""

import asyncio
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Any, Literal

from app.core.plan_manager import PlanManager
from app.core.plan_executor import PlanExecutor, PlanExecutionResult
from app.monitoring.metrics import global_metrics


# ═══════════════════════════════════════════════════════════════════════════════
# RESULT TYPES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class QueueItem:
    plan_id: str
    enqueued_at: float
    position: int


@dataclass
class QueueSnapshot:
    state: Literal["idle", "running", "stopping"]
    length: int
    current_plan_id: Optional[str]
    completed_count: int
    failed_count: int
    items: List[QueueItem]


# ═══════════════════════════════════════════════════════════════════════════════
# QUEUE
# ═══════════════════════════════════════════════════════════════════════════════

class PlanQueue:
    """
    Ordered in-memory queue of plan IDs.

    Thread-safe via asyncio.Lock. Plans are referenced by ID only;
    full plan metadata lives in PlanManager storage.
    """

    def __init__(self):
        self._queue: List[str] = []
        self._lock = asyncio.Lock()

    async def enqueue(self, plan_id: str) -> int:
        """Add a plan to the tail of the queue. Returns position (1-based)."""
        async with self._lock:
            if plan_id in self._queue:
                return self._queue.index(plan_id) + 1
            self._queue.append(plan_id)
            return len(self._queue)

    async def dequeue(self) -> Optional[str]:
        """Remove and return the plan at the head of the queue."""
        async with self._lock:
            if not self._queue:
                return None
            return self._queue.pop(0)

    async def peek(self) -> Optional[str]:
        """Return the plan at the head without removing it."""
        async with self._lock:
            return self._queue[0] if self._queue else None

    async def remove(self, plan_id: str) -> bool:
        """Remove a specific plan from the queue."""
        async with self._lock:
            if plan_id in self._queue:
                self._queue.remove(plan_id)
                return True
            return False

    async def clear(self) -> int:
        """Empty the queue. Returns number of items removed."""
        async with self._lock:
            removed = len(self._queue)
            self._queue.clear()
            return removed

    async def list(self) -> List[str]:
        """Return a snapshot of queued plan IDs in order."""
        async with self._lock:
            return list(self._queue)

    async def contains(self, plan_id: str) -> bool:
        async with self._lock:
            return plan_id in self._queue

    async def __len__(self) -> int:
        async with self._lock:
            return len(self._queue)


# ═══════════════════════════════════════════════════════════════════════════════
# RUNNER
# ═══════════════════════════════════════════════════════════════════════════════

class PlanRunner:
    """
    Sequential runner that drains a PlanQueue through PlanExecutor.

    Usage:
        queue = PlanQueue()
        runner = PlanRunner(queue)
        await queue.enqueue("plan_a")
        await queue.enqueue("plan_b")
        await runner.start()   # blocks until queue is empty or stop() is called
    """

    def __init__(
        self,
        queue: PlanQueue,
        executor: Optional[PlanExecutor] = None,
        on_plan_complete: Optional[Callable[[str, PlanExecutionResult], Any]] = None,
        on_plan_error: Optional[Callable[[str, Exception], Any]] = None,
    ):
        self.queue = queue
        self.executor = executor or PlanExecutor()
        self.on_plan_complete = on_plan_complete
        self.on_plan_error = on_plan_error
        self._state: Literal["idle", "running", "stopping"] = "idle"
        self._state_lock = asyncio.Lock()
        self._task: Optional[asyncio.Task] = None
        self._completed_count = 0
        self._failed_count = 0
        self._current_plan_id: Optional[str] = None

    @property
    def state(self) -> Literal["idle", "running", "stopping"]:
        return self._state

    async def start(self, **executor_kwargs) -> None:
        """Begin processing the queue. Safe to call multiple times."""
        async with self._state_lock:
            if self._state == "running":
                return
            self._state = "running"

        global_metrics.update_queue_state(len(await self.queue.list()), self._state)
        self._task = asyncio.create_task(self._run_loop(**executor_kwargs))

    async def stop(self) -> None:
        """Signal the runner to stop after the current plan finishes."""
        async with self._state_lock:
            if self._state != "running":
                return
            self._state = "stopping"

        global_metrics.update_queue_state(len(await self.queue.list()), self._state)
        if self._task:
            try:
                await self._task
            except Exception:
                pass
            self._task = None

    async def _run_loop(self, **executor_kwargs) -> None:
        """Internal loop that drains the queue sequentially."""
        while True:
            async with self._state_lock:
                if self._state == "stopping":
                    self._state = "idle"
                    break

            plan_id = await self.queue.dequeue()
            if plan_id is None:
                async with self._state_lock:
                    self._state = "idle"
                global_metrics.update_queue_state(0, "idle")
                break

            global_metrics.update_queue_state(len(await self.queue.list()), "running")

            self._current_plan_id = plan_id
            try:
                result = await self.executor.execute_plan(plan_id, **executor_kwargs)

                if result.status == "completed":
                    self._completed_count += 1
                else:
                    self._failed_count += 1

                if self.on_plan_complete:
                    try:
                        self.on_plan_complete(plan_id, result)
                    except Exception:
                        pass

            except Exception as e:
                self._failed_count += 1
                try:
                    PlanManager.update_plan_status(plan_id, "failed")
                except Exception:
                    pass
                if self.on_plan_error:
                    try:
                        self.on_plan_error(plan_id, e)
                    except Exception:
                        pass
            finally:
                self._current_plan_id = None

    async def snapshot(self) -> QueueSnapshot:
        """Current runner + queue snapshot."""
        items = await self.queue.list()
        now = asyncio.get_event_loop().time()
        return QueueSnapshot(
            state=self._state,
            length=len(items),
            current_plan_id=self._current_plan_id,
            completed_count=self._completed_count,
            failed_count=self._failed_count,
            items=[QueueItem(plan_id=p, enqueued_at=now, position=i + 1) for i, p in enumerate(items)],
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

PlanQueueSingleton = PlanQueue()
PlanRunnerSingleton = PlanRunner(PlanQueueSingleton)
