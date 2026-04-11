# Neural Link Bridge: WebSocket Implementation

The "Connection Lost" error and the `AssertionError` in the server logs are caused by a missing WebSocket handler in the backend. While the WebUI is designed for real-time streaming via WebSockets (`wss://`), the Python backend currently only supports REST. This plan will build the bridge.

## User Review Required

> [!IMPORTANT]
> **New Module Capability**: I am adding a full WebSocket orchestration layer to `app/routes/chat.py`. This will enable the real-time typing effect and live usage tracking in the dashboard.

## Proposed Changes

### [Backend Intelligence Bridge]

#### [MODIFY] [chat.py](file:///home/flintx/peacock-engine/app/routes/chat.py)
- **Import WebSocket Requirements**: Add `WebSocket`, `WebSocketDisconnect` from `fastapi`.
- **Implement WebSocket Route**: Add `@router.websocket("/ws/ws")` handler.
- **Protocol Orchestration**:
    - Build a listener loop for "config" and "prompt" messages.
    - Integrate the `execute_streaming_strike` generator to pipe AI tokens directly into the socket.
    - Implement the message structure expected by the UI:
        - `{"type": "content", "content": "..."}` for streaming.
        - `{"type": "metadata", "usage": "..."}` for completion.
        - `{"type": "error", "content": "..."}` for failures.

## Open Questions

- None. The UI's `api.ts` already defines the protocol; we just need to fulfill it on the backend.

## Verification Plan

### Automated Tests
- `pytest` (if available) or manual WS test script.
- Check logs for the absence of `AssertionError` during connection.

### Manual Verification
- Refresh `https://chat.save-aichats.com/`. 
- Type a prompt and verify real-time streaming tokens appear in the terminal.
- Verify "NEURAL_LINK_STABLE" status in footer.
