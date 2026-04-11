# Plan: Fix Peacock Engine Audit and Token Counter

The user reported that the `audit` command and the `token counter` are broken. Investigation reveals several architectural mismatches and potential runtime failures.

## Objective
Fix the `AttributeError` in token counting, ensure the `audit` command works by correcting `pydantic-ai` integration, and prevent crashes in the logging system.

## Key Files & Context
- `app/core/striker.py`: Core execution logic, currently calling non-existent methods on token counters and using potentially incorrect `pydantic-ai` imports.
- `app/utils/gemini_token_counter.py` & `app/utils/groq_token_counter.py`: Token counting implementations with method name mismatches.
- `app/utils/token_counter.py`: Unified token counter with static method call mismatches.
- `app/utils/logger.py`: High-signal logger that may fail if vault directories are missing.
- `ai-engine.py`: CLI tool where the `audit` command resides.

## Implementation Steps

### 1. Fix Token Counter Mismatches
- **`app/utils/gemini_token_counter.py`**:
    - Add an alias method `count_tokens_offline` that points to `estimate_tokens`.
    - Add a static method `count_tokens` for compatibility with `PeacockTokenCounter`.
- **`app/utils/groq_token_counter.py`**:
    - Add an alias method `count_tokens_in_prompt` that points to `count_tokens`.
    - Add a static method `count_messages` for compatibility with `PeacockTokenCounter`.
- **`app/core/striker.py`**:
    - Update `count_tokens_for_strike` to use the correct method names if aliases aren't preferred, but aliases are safer for backward compatibility.

### 2. Fix Logging System Crashes
- **`app/utils/logger.py`**:
    - Add directory creation logic in `log_strike` to ensure `vault/successful` and `vault/failed` exist before writing.

### 3. Correct `pydantic-ai` Integration
- **`app/core/striker.py`**:
    - Verify `pydantic_ai` imports. `GroqProvider`, `OpenAIProvider`, and `GoogleProvider` from `pydantic_ai.providers` are likely incorrect.
    - Switch to using the correct model initialization for each gateway (e.g., `GroqModel(..., api_key=...)` or `OpenAIModel(base_url=..., api_key=...)`).

### 4. Verify and Test
- Create a test script `verify_fixes.py` that:
    - Tests `GeminiTokenCounter` and `GroqTokenCounter` with the expected calling patterns.
    - Tests `HighSignalLogger` by logging a dummy strike and checking if directories are created.
    - Attempts to initialize the models used in `execute_strike` to verify imports.

## Verification & Testing
- Run `python3 verify_fixes.py`.
- Run `python3 ai-engine.py audit` to ensure it now correctly reports model status.
- Run `python3 ai-engine.py strike "test"` to verify end-to-end execution.
