# PEACOCK Aviary Pipeline v2.0

> Date: 2026-05-02
> Author: PEACOCK Engine
> Status: SPARK + FALCON rebuilt. EAGLE → HAWK pending.

---

## Core Theory

This pipeline is built on a single non-negotiable principle:

> **LLMs are statistical pattern matchers, not goal-following agents.**

Every prompt is a **statistical instrument**. The objective doesn't matter unless the token patterns align. Success comes from creating deep statistical grooves (few-shot examples) and locking the model into them (temperature=0, completion starters).

---

## What Was Done

### 1. SPARK — Complete Rewrite

**File:** `app/core/aviary.py` — `_phase_spark()`  
**Prompt:** `prompts/aviary/spark.md`

#### Changes:
- **System prompt stripped to 1 line.** No instructions, no "please," no "be thorough." The system prompt is just the role: *"You are a computational ontology extractor."*
- **Few-shot examples moved to the user prompt.** 3 real examples using actual DB formats:
  - RMS App Setup (start stage)
  - Android SDK Package Manager (middle stage)
  - Restaurant Phone AI (start stage)
- **DB metadata injected.** Bucket items' metadata (`technologies`, `entities`, `topics`, `decisions`, `action_items`) is extracted and passed as `[[[METADATA]]]`.
- **Gateway switching.** Payloads > 15K chars → Gemini 1.5 Pro (1M token context). Small payloads → Groq Llama 3.3 70B.
- **Temperature = 0.0.** No randomness. Locked.
- **Completion starter.** Prompt ends with `### PROJECT:` — the model cannot drift into generic text.

#### Why:
The few-shot examples CREATE the statistical path. The model sees `CHAT_LOG + METADATA → ONTOLOGY` 3 times. On the 4th instance, the highest-probability next token is the start of an ontology. Temperature=0 prevents deviation. The completion starter forces the model into the right output basin.

---

### 2. FALCON — Complete Rewrite

**File:** `app/core/aviary.py` — `_phase_falcon()`  
**Prompt:** `prompts/aviary/falcon.md`

#### Changes:
- **System prompt stripped to 1 line.** *"You are an invariant miner."*
- **Few-shot examples in user prompt.** 2 examples showing `ONTOLOGY → INVARIANTS`:
  - RMS → structural + behavioral + security invariants
  - Android SDK → structural + behavioral + integration invariants
- **Completion starter.** Prompt ends with `### STRUCTURAL INVARIANTS`.

#### Why:
Same statistical groove approach. Falcon doesn't "understand" what an invariant is — it sees the pattern of ontology-to-invariants twice and continues it.

---

### 3. Bucket Integration

**File:** `app/routes/buckets.py`

#### Changes:
- `POST /{bucket_name}/aviary` now extracts metadata from all bucket items and passes it to the pipeline as `bucket_metadata`.
- `POST /{bucket_name}/aviary/stream` does the same.

#### Why:
SPARK gets the curated payload (assembled from disk) AND the pre-extracted metadata from ChromaDB. SPARK validates and synthesizes — it doesn't mine from scratch.

---

### 4. Universal LLM Caller

**File:** `app/core/aviary.py` — `_call_llm()`

#### Changes:
- Added `gateway` parameter (`groq` | `google`).
- Supports GroqPool and GooglePool key rotation.
- Temperature locked to `0.0` for all calls.
- Verbose logging includes gateway name.

#### Why:
One function, any gateway. No code duplication. Gemini handles massive payloads. Groq handles fast, cheap calls.

---

### 5. Orchestrator Updates

**File:** `app/core/aviary.py` — `run_aviary_pipeline()` + `run_aviary_pipeline_streamed()`

#### Changes:
- Added `bucket_metadata` parameter.
- Passed through to `_phase_spark()`.

---

## What Was NOT Done

### Remaining Birds (EAGLE → HAWK)

EAGLE, CROW, OWL, RAVEN, and HAWK still use the **old conversational prompt style**:
- System prompts with paragraphs of instructions
- User prompts with `=== INPUT ===` blocks but no few-shot examples
- No completion starters
- No gateway switching

**They need the same treatment SPARK and FALCON received:**
1. Strip system prompts to 1-line roles
2. Move instructions to few-shot examples in user prompts
3. Add completion starters
4. Ensure temperature=0

### Testing

No end-to-end pipeline test has been run with the new prompts. Recommended test:
1. Add 1-2 real chat logs to bucket `aviary_payload`
2. Call `POST /v1/buckets/aviary_payload/aviary/stream`
3. Verify SPARK output: consistent ontology structure across 5 runs
4. Verify FALCON output: consistent invariant structure across 5 runs
5. Check gateway switching: large payloads route to Gemini, small to Groq

### Token Counting Integration

The pipeline does not yet verify token count before sending. A pre-flight check should:
1. Count tokens in payload + examples
2. Route to Gemini if > 120K tokens
3. Error if > 1M tokens (Gemini's limit)

### Output Validation

No JSON schema or regex validation on SPARK/FALCON outputs. The pipeline assumes the model follows the pattern. If it doesn't, downstream birds receive garbage.

**Recommended:** Add a validator that checks for required sections (`### PROJECT:`, `### STAGE:`, etc.) and retries if missing.

---

## Architecture Diagram

```
BUCKET (user-curated docs)
    │
    ├──> Assembly Endpoint (full docs from disk)
    │
    ├──> Metadata Extraction (ChromaDB fields)
    │
    ▼
SPARK (Gemini if large, Groq if small)
    ├──> Few-shot examples (statistical groove)
    ├──> Temperature=0 (locked)
    ├──> Completion starter (### PROJECT:)
    └──> Output: Structured Ontology
    │
    ▼
FALCON (Groq)
    ├──> Few-shot examples (ONTOLOGY → INVARIANTS)
    ├──> Temperature=0 (locked)
    ├──> Completion starter (### STRUCTURAL INVARIANTS)
    └──> Output: Invariant Set
    │
    ▼
EAGLE → CROW → OWL → RAVEN → HAWK
    └──> STILL USE OLD PROMPT STYLE (needs rebuild)
```

---

## Key Design Decisions

| Decision | Old Way | New Way | Why |
|----------|---------|---------|-----|
| System prompt | 40-line instruction block | 1-line role | Instructions are noise. Patterns are signal. |
| Few-shot | None | 3 examples hardcoded | Examples ARE the prompt. They create the statistical groove. |
| Temperature | 0.3 | 0.0 | Any randomness breaks pattern consistency. |
| Completion starter | None | `### PROJECT:` / `### STRUCTURAL INVARIANTS` | Forces model into the right output basin. Prevents drift. |
| Gateway | Groq only | Groq + Gemini | Gemini handles 1M context for large payloads. Groq is fast for small ones. |
| Metadata | Ignored | Injected as `[[[METADATA]]]` | ChromaDB already extracted entities, tech, topics. SPARK validates, doesn't re-mine. |

---

## Next Steps

1. **Test SPARK + FALCON** with real bucket contents. Verify consistency across 5 runs.
2. **Rebuild EAGLE** — implementation planner needs ontology → plan few-shot examples.
3. **Rebuild CROW** — UI scaffold designer needs plan → scaffold few-shot examples.
4. **Rebuild OWL** — code generator needs scaffold → code few-shot examples.
5. **Add output validators** — regex/schema check after each phase. Retry on failure.
6. **Add token pre-flight** — count tokens, route to correct gateway, error if > 1M.

---

## Files Changed

| File | Change |
|------|--------|
| `app/core/aviary.py` | `_call_llm()` universal gateway, `_phase_spark()` rebuilt, `_phase_falcon()` rebuilt, orchestrator updated |
| `app/routes/buckets.py` | `aviary` and `aviary/stream` endpoints pass metadata |
| `prompts/aviary/spark.md` | Stripped to 1-line role |
| `prompts/aviary/falcon.md` | Stripped to 1-line role |
| `docs/AVIARY_PIPELINE_V2.md` | This document |
