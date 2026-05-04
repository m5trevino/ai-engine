# Payload Striker System - Deep Dive Documentation

> **Version:** 1.0  
> **Created:** 2026-04-10  
> **Status:** Working / Production Ready  
> **Engine Version:** PEACOCK ENGINE V3.0.0

---

## 1. The Problem

The Payload Striker system solves the challenge of **batch AI processing** - the need to send multiple files or payloads through AI models in an organized, trackable, and recoverable way. 

### Key Problems Addressed:
- **Manual file-by-file processing is inefficient** - Operators needed a way to queue and process multiple files automatically
- **No visibility into batch progress** - Need real-time telemetry on what's being processed
- **Lost work on failures** - Need persistent state to resume interrupted batches
- **Context management** - Need to inject file contents into prompts dynamically
- **Result organization** - Need structured output with metadata for downstream use

---

## 2. User Requirements (with quotes from evolution documents)

### From Evolution Document: Feature 03 - Payload Striker

> **"Initial blueprint for a 3-column horizontal workstation for batch operations (Director, Vault, Loadout)."**

The original vision was a sophisticated UI with three distinct zones for managing batch operations.

> **"First functional version built as a 10-slot sequence manifest with a Context Vault. Introduced 'Ultra' (continuous) and 'Regular' (batched) threading modes."**

The user wanted configurable execution modes - continuous streaming vs batched processing.

> **"Evolved state management to support a Global Default Prompt that could be overridden by Custom Specific Prompts for individual assets."**

Critical requirement: flexible prompt templating with variable substitution (`{{payload}}`).

> **"Added a toggle to switch payload routing between Monolithic Mode (all assets in one strike) and Distributed Mode (one isolated strike per asset)."**

The user wanted control over how files are grouped - all at once vs one-by-one.

> **"Introduced a completely new paradigm: Strike Groups. This allows grouping multiple assets under a single primary instruction, creating a hierarchical campaign instead of a flat list."**

Advanced requirement for hierarchical organization of batch operations.

> **"The ultimate evolution. A full-screen, multi-column command center with a direct filesystem bridge."**

Vision of a sophisticated UI with filesystem integration and real-time monitoring.

---

## 3. Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PAYLOAD STRIKER ARCHITECTURE                         │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────┐     ┌──────────────────┐     ┌──────────────────────┐
│   CLIENT         │     │   FASTAPI        │     │   EXECUTION ENGINE   │
│   (UI/CLI)       │────▶│   ROUTES         │────▶│   (striker.py)       │
└──────────────────┘     └──────────────────┘     └──────────────────────┘
         │                        │                          │
         │                        │                          ▼
         │                        │               ┌──────────────────────┐
         │                        │               │   BATCH PROCESSOR    │
         │                        │               │   - File resolver    │
         │                        │               │   - Prompt builder   │
         │                        │               │   - Execute strikes  │
         │                        │               └──────────────────────┘
         │                        │                          │
         ▼                        ▼                          ▼
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────────┐
│   TELEMETRY      │◀────│   STATE MGMT     │◀────│   RESULT HANDLER     │
│   (Real-time)    │     │   (striker_      │     │   - Genesis parsing  │
│   - Progress     │     │    status.json)  │     │   - YAML welding     │
│   - RPM/TPM      │     │   - Pause/Resume │     │   - MissionVault     │
│   - Token count  │     │   - Abort        │     └──────────────────────┘
└──────────────────┘     └──────────────────┘                │
                                                             ▼
                                                  ┌──────────────────────┐
                                                  │   FORENSIC LOGGING   │
                                                  │   (HighSignalLogger) │
                                                  │   - PEA-XXXX tags    │
                                                  │   - Vault storage    │
                                                  └──────────────────────┘
```

### Data Flow

```
1. CLIENT initiates strike
   ↓
2. STRIKER ROUTE validates request
   ↓
3. STATE initialized (running, count=0, logs=[])
   ↓
4. BACKGROUND TASK starts batch processor
   ↓
5. FOR EACH file:
   a. Read content
   b. Inject into prompt template ({{payload}})
   c. EXECUTE STRIKE via core striker
   d. PARSE response (JSON or YAML)
   e. WELD metadata + original content
   f. SAVE to MissionVault/
   g. UPDATE telemetry
   h. PERSIST state to striker_status.json
   i. SLEEP (delay/throttle)
   ↓
6. BATCH COMPLETE - state cleared
```

---

## 4. Technical Implementation

### 4.1 Core Components

| Component | File | Purpose |
|-----------|------|---------|
| Striker Router | `app/routes/striker.py` | API endpoints for batch control |
| Payload Strike | `app/routes/payload_strike.py` | Single-shot multi-file strikes |
| Core Striker | `app/core/striker.py` | Low-level AI execution |
| Key Manager | `app/core/key_manager.py` | API key rotation & cooldown |
| HighSignal Logger | `app/utils/logger.py` | Forensic logging (PEA-XXXX) |
| Token Counter | `app/utils/token_counter.py` | Unified token counting |

### 4.2 Key Data Structures

```python
# Striker Request (from client)
class StrikerRequest(BaseModel):
    files: List[str]           # Paths to files to process
    prompt: str                # Template with {{payload}} variable
    modelId: str               # Model to use
    delay: int = 5             # Seconds between strikes
    throttle: float = 1.0      # Speed multiplier

# Telemetry (real-time status)
class StrikerTelemetry(BaseModel):
    currentFile: Optional[str]
    lastResult: Optional[StrikerResult]
    nextFile: Optional[str]
    processedCount: int
    totalCount: int
    isPaused: bool
    isRunning: bool
    logs: List[str]
    totalTokens: int
    rpm: float
    tpm: float

# Result (with Genesis intel)
class StrikerResult(BaseModel):
    file: str
    title: str
    summary: str
    category: str
    priority: str
    keywords: List[str]
    genesis: Optional[GenesisIntel]  # App seed analysis
```

### 4.3 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/striker/files` | GET | List available files from chat_logs |
| `/v1/striker/status` | GET | Get current telemetry |
| `/v1/striker/execute` | POST | Start a batch strike |
| `/v1/striker/pause` | POST | Pause running batch |
| `/v1/striker/resume` | POST | Resume paused batch |
| `/v1/striker/abort` | POST | Cancel running batch |
| `/v1/striker/target/{filename}` | GET | Get processed result from MissionVault |
| `/v1/payload-strike` | POST | Single-shot multi-file strike |

### 4.4 Critical Code Snippets

**Variable Substitution (Prompt Template):**
```python
# From app/routes/striker.py:278
final_prompt = req.prompt.replace("{{payload}}", content) if "{{payload}}" in req.prompt else f"{req.prompt}\n\nPAYLOAD:\n{content}"
```

**Response Parsing (Dual Format Support):**
```python
# From app/routes/striker.py:303-324
# Try JSON first (Genesis Scout Format)
json_match = re.search(r'```json\n(.*?)\n```', raw_content, re.DOTALL)
if json_match:
    data = json.loads(json_match.group(1))

# Fallback to YAML (Legacy Refractor Format)
if not data and "---" in raw_content:
    parts = raw_content.split("---")
    clean_yaml = parts[1] if len(parts) > 1 else raw_content
    data = yaml.safe_load(clean_yaml)
```

**YAML Welding (Output Generation):**
```python
# From app/routes/striker.py:329-338
short_hash = get_short_hash(content)
data['id'] = short_hash

result_path = MISSION_VAULT_DIR / f"{path.stem}.md"
with open(result_path, 'w') as f:
    f.write("---\n")
    f.write(yaml.dump(data))
    f.write("---\n\n")
    f.write(content)  # Original file appended
```

**Throttle Control:**
```python
# From app/routes/striker.py:393-397
effective_delay = req.delay / max(req.throttle, 0.01)
await asyncio.sleep(effective_delay)
```

---

## 5. File Structure

```
ai-engine/
├── app/
│   ├── routes/
│   │   ├── striker.py          # Main batch striker endpoints
│   │   └── payload_strike.py   # Single-shot payload endpoint
│   ├── core/
│   │   └── striker.py          # Core execution engine
│   └── utils/
│       ├── logger.py           # HighSignalLogger (PEA-XXXX)
│       └── token_counter.py    # Unified token counting
│
├── MissionVault/               # Processed output storage
│   └── {filename}.md           # YAML frontmatter + original content
│
├── chat_logs/
│   ├── washed/                 # Cleansed files
│   └── misfires/               # Failed processing outputs
│
├── vault/
│   ├── successful/             # Forensic logs (success)
│   │   └── PEA-XXXX.txt        # Individual strike records
│   └── failed/                 # Forensic logs (failure)
│       └── PEA-XXXX.txt
│
├── striker_status.json         # Persistent state file
└── success_strikes.log         # Master summary log
```

---

## 6. How It Works - Step by Step

### 6.1 Initialization Phase

1. **Client requests file list**
   ```
   GET /v1/striker/files?base_dir=/home/flintx/chat_logs
   ```
   
2. **Server scans directory**, normalizes filenames (removes `branch_of_`, `copy_of_`, date prefixes)

3. **Deduplication** - Groups by root name, selects largest file

4. **Signal intensity calculation** - Counts code blocks (```) as complexity indicator

5. **Returns file list** with status (pending/success based on MissionVault existence)

### 6.2 Execution Phase

1. **Client initiates strike**
   ```json
   POST /v1/striker/execute
   {
     "files": ["/path/to/file1.md", "/path/to/file2.md"],
     "prompt": "Analyze this chat log and extract key insights: {{payload}}",
     "modelId": "gemini-2.5-flash",
     "delay": 5,
     "throttle": 1.0
   }
   ```

2. **State initialized** in memory and saved to `striker_status.json`

3. **Background task** launched (non-blocking response to client)

4. **For each file in queue:**
   - Check if paused/aborted
   - Update `currentFile` in telemetry
   - Read file content
   - Substitute `{{payload}}` variable
   - Execute AI strike via `execute_strike()`
   - Parse response (JSON → YAML fallback)
   - Generate SHA256 hash for ID
   - Weld YAML metadata + original content
   - Save to `MissionVault/{filename}.md`
   - Update telemetry (counts, tokens, RPM/TPM)
   - Persist state to JSON
   - Sleep for `delay/throttle` seconds

5. **Completion** - State cleared, logs appended

### 6.3 Pause/Resume Flow

1. **Pause requested**
   ```
   POST /v1/striker/pause
   ```
   - Sets `is_paused = True`
   - Processor loop checks pause flag, sleeps

2. **Resume requested**
   ```
   POST /v1/striker/resume
   ```
   - Clears pause flag
   - Processing continues from `currentFile`

### 6.4 Output Format (MissionVault)

```yaml
---
id: a3f7b2d9
title: "Chat Analysis: System Architecture Discussion"
summary: "Detailed conversation about API design patterns"
primary_category: "Technical Discussion"
stage: "MVP_Complete"
priority: "Winner"
isAppSeed: true
completeness: 85
contextType: "architecture"
buildStatus: "functional"
search_keywords: ["api", "architecture", "design patterns"]
---

[ORIGINAL FILE CONTENT PRESERVED HERE]
```

---

## 7. Decision Points

### Decision: Simplified vs Hierarchical Campaign Mode

**Context:** Evolution document described "Strike Groups" for hierarchical organization.

**Decision:** **IMPLEMENTED AS FLAT LIST**
- Hierarchical grouping added complexity without clear use case
- Current implementation processes files sequentially
- MissionVault output is flat (no group nesting)

**Trade-off:** Lost organizational flexibility, gained simplicity and reliability.

---

### Decision: Monolithic vs Distributed Mode

**Context:** User wanted toggle between "all assets in one strike" vs "one strike per asset".

**Decision:** **DISTRIBUTED MODE ONLY**
- `payload_strike.py` supports monolithic (all files in one prompt)
- `striker.py` (batch) uses distributed (one file at a time)
- No runtime toggle - separate endpoints for different use cases

**Trade-off:** Less runtime flexibility, clearer API contract.

---

### Decision: Prompt Template Variable

**Context:** Need way to inject file content into prompts.

**Decision:** **{{payload}} VARIABLE**
- If present in prompt, content replaces the variable
- If absent, content appended after "PAYLOAD:" header
- Backward compatible with prompts not using variable

**Trade-off:** Simple, explicit, but requires users to know syntax.

---

### Decision: Dual Format Response Parsing

**Context:** AI responses could be JSON or YAML.

**Decision:** **TRY JSON FIRST, FALLBACK TO YAML**
```python
# Try JSON first (Genesis Scout Format)
json_match = re.search(r'```json\n(.*?)\n```', raw_content, re.DOTALL)

# Fallback to YAML (Legacy Refractor Format)
if not data and "---" in raw_content:
    data = yaml.safe_load(clean_yaml)
```

**Trade-off:** Supports both formats but parsing is fragile (regex-based).

---

### Decision: YAML Welding for Output

**Context:** Need to preserve original file + add metadata.

**Decision:** **YAML FRONTMATTER + CONTENT APPEND**
```yaml
---
metadata: here
---

[original content preserved]
```

**Trade-off:** Human-readable, but requires YAML parser to extract metadata.

---

## 8. Current Status

### ✅ Working

| Feature | Status | Notes |
|---------|--------|-------|
| Batch file processing | ✅ | Sequential processing with telemetry |
| Real-time status | ✅ | WebSocket/polling via `/status` endpoint |
| Pause/Resume | ✅ | State persisted to `striker_status.json` |
| Abort | ✅ | Immediate termination |
| Variable substitution | ✅ | `{{payload}}` support |
| Genesis parsing | ✅ | JSON and YAML format support |
| MissionVault output | ✅ | YAML-welded files with metadata |
| Misfire handling | ✅ | Failed outputs saved to `chat_logs/misfires/` |
| Token tracking | ✅ | Per-batch and cumulative |
| RPM/TPM calculation | ✅ | Session-based rate metrics |
| Throttle control | ✅ | `delay/throttle` formula |

### ⚠️ Partial / Evolved

| Feature | Status | Notes |
|---------|--------|-------|
| 10-slot manifest | ❌ | Not implemented - unlimited queue |
| Ultra/Regular modes | ⚠️ | WebSocket streaming exists, but not in batch striker |
| Global vs Custom prompts | ⚠️ | Single prompt per batch, no per-file override |
| 4-Zone LIM UI | ❌ | Backend exists, no dedicated UI screen |

### ❌ Not Implemented (from evolution)

| Feature | Status | Notes |
|---------|--------|-------|
| Strike Groups | ❌ | Flat list only |
| Monolithic/Distributed toggle | ❌ | Separate endpoints instead |
| Full-screen command center | ❌ | API-only, no dedicated UI |
| Filesystem bridge UI | ❌ | API exists (`/v1/fs/browse`) |

### 🐛 Known Issues

1. **Fragile response parsing** - Regex-based JSON/YAML extraction can fail on malformed AI output
2. **No retry logic** - Failed files go to misfires, no automatic retry
3. **Memory usage** - All file contents loaded into memory for payload_strike
4. **No progress streaming** - Client must poll `/status`, no WebSocket push
5. **Path traversal risk** - File paths not fully validated (relies on OS permissions)

---

## 9. Troubleshooting

### Issue: Batch stops unexpectedly

**Symptoms:** Status shows `isRunning: false` but not all files processed

**Check:**
```bash
# View status file
cat striker_status.json

# Check logs
tail -f success_strikes.log
tail -f failed_strikes.log
```

**Causes:**
- Abort was called
- Exception in processor (check console logs)
- All keys on cooldown (rate limited)

**Fix:** Restart the batch (will re-process from beginning, but MissionVault prevents duplicates)

---

### Issue: Files showing "pending" but already processed

**Symptoms:** `/files` endpoint returns `status: "pending"` for files in MissionVault

**Check:**
```bash
ls MissionVault/
```

**Cause:** Filename normalization mismatch (e.g., `copy_of_file.md` vs `file.md`)

**Fix:** Clean up `chat_logs/` directory, remove duplicate files

---

### Issue: All strikes failing (misfires)

**Symptoms:** All files go to `chat_logs/misfires/`

**Check:**
```bash
# Check misfire content
cat chat_logs/misfires/{filename}.failed.txt

# Verify model availability
./ai-engine.py models

# Check key health
./ai-engine.py audit
```

**Causes:**
- Model frozen or deprecated
- All API keys on cooldown
- Invalid prompt template
- AI returning unexpected format

**Fix:** 
- Unfreeze model: `./ai-engine.py unfreeze {model_id}`
- Wait for key cooldown (60s)
- Check prompt syntax (must include `{{payload}}` or expect appended content)

---

### Issue: High token usage / slow processing

**Symptoms:** TPM exceeding limits, long delays between files

**Check telemetry:**
```json
{
  "rpm": 12.5,
  "tpm": 45000,
  "totalTokens": 150000
}
```

**Causes:**
- Large files being processed
- Low throttle setting (e.g., `throttle: 0.1` = 10x faster but riskier)
- High delay setting

**Fix:**
- Increase delay: `"delay": 10`
- Reduce throttle: `"throttle": 2.0` (2x slower = safer)
- Filter large files before sending

---

### Issue: Cannot resume after restart

**Symptoms:** After engine restart, batch doesn't resume

**Cause:** By design - `isRunning` reset to `false` on boot for safety

**Fix:** Re-initiate the batch (files already in MissionVault will be skipped if deduplication works)

---

## 10. Usage Examples

### Basic Batch Strike (CLI)

```bash
curl -X POST http://localhost:3099/v1/striker/execute \
  -H "Content-Type: application/json" \
  -d '{
    "files": ["/home/flintx/chat_logs/session1.md", "/home/flintx/chat_logs/session2.md"],
    "prompt": "Extract the main technical decisions from this chat log: {{payload}}",
    "modelId": "gemini-2.5-flash",
    "delay": 5,
    "throttle": 1.0
  }'
```

### Single-Shot Multi-File (Payload Strike)

```bash
curl -X POST http://localhost:3099/v1/payload-strike \
  -H "Content-Type: application/json" \
  -d '{
    "modelId": "gemini-2.5-flash",
    "prompt": "Compare these code files and identify patterns:",
    "files": ["/path/to/file1.py", "/path/to/file2.py"],
    "temp": 0.7
  }'
```

### Monitor Progress

```bash
# Watch status in real-time
while true; do
  curl -s http://localhost:3099/v1/striker/status | jq .
  sleep 2
done
```

### Pause/Resume

```bash
# Pause
curl -X POST http://localhost:3099/v1/striker/pause

# Resume
curl -X POST http://localhost:3099/v1/striker/resume

# Abort
curl -X POST http://localhost:3099/v1/striker/abort
```

---

## 11. Integration with Other Systems

### Key Manager Integration
- Uses `GroqPool`, `GooglePool`, etc. from `key_manager.py`
- Automatic key rotation on 429 errors
- Cooldown tracking prevents rate limit violations

### HighSignal Logger Integration
- Every strike generates a `PEA-XXXX` tag
- Verbatim logs saved to `vault/successful/` or `vault/failed/`
- Master logs (`success_strikes.log`) for quick auditing

### Database Integration
- `KeyUsageDB` tracks per-key token consumption
- `ConversationDB` not used by striker (batch is stateless)

### File System Integration
- `app/routes/fs.py` provides `/v1/fs/browse` for file discovery
- `payload_strike.py` supports recursive directory traversal

---

## 12. Future Enhancements (from evolution documents)

Based on the evolution documents, potential future improvements:

1. **Strike Groups** - Hierarchical organization of files into campaigns
2. **WebSocket Streaming** - Real-time progress push instead of polling
3. **Per-File Prompt Override** - Custom prompts for individual assets
4. **Monolithic Mode Toggle** - All files in single context window
5. **Dedicated UI Screen** - 4-zone command center interface
6. **Retry Logic** - Automatic retry for failed files with backoff
7. **Parallel Processing** - Concurrent strikes (currently sequential)
8. **Progress Persistence** - Resume from exact file after restart

---

**END OF DOCUMENTATION**
