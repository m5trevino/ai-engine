# 💀 PEACOCK ENGINE V2: OPERATIONAL MANUAL
**VERSION:** 2.1 (PYTHON REFACTOR)
**TARGET:** HIGH-STAKES ARCHITECTURAL STRIKES

---

## 1. THE MISSION
The Peacock Engine is the central nervous system for all FlintX AI operations. It is a headless, high-performance gateway built with **Python (FastAPI)** and **Pydantic AI**. It handles model orchestration, key rotation, and serves as a secure bridge to your local filesystem.

## 2. ARCHITECTURE (THE STACK)
*   **Engine:** FastAPI (Asynchronous execution).
*   **Intelligence Layer:** Pydantic AI (Type-safe agentic strikes).
*   **Ammo Box:** Local filesystem bridge (/home/flintx/ammo).
*   **The Vault:** Automated Key Rotation (Multi-key pooling).

---

## 3. SETUP & DEPLOYMENT
### **Prerequisites**
*   Python 3.11+
*   Environment variables loaded (`GROQ_KEYS`, `GOOGLE_KEYS`, etc.).

### **Ritual**
1.  **Initialize Environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```
2.  **Ignite Engine:**
    ```bash
    python3 -m app.main
    ```
    *Engine will live on `http://localhost:8888`.*

---

## 4. THE ARSENAL (KEY ROTATION)
The engine utilizes a **KeyPool** logic to prevent rate-limiting and ensure 100% uptime.
*   **Format:** Keys in `.env` should be comma-separated.
*   **Labeling:** Use `ACCOUNT_NAME:KEY` for precise tracking, or just the `KEY` for auto-labeling.
*   **Rotation:** Each strike pulls the next key in the "deck." If the end is reached, the deck is shuffled.

---

## 5. API COMMAND DECK

### **A. Intelligence Strikes**
`POST /v1/strike/`
Executes an LLM call via Pydantic AI.
*   **Payload:**
    ```json
    {
      "modelId": "llama-3.3-70b-versatile",
      "prompt": "Your directive here...",
      "temp": 0.7
    }
    ```
*   **Response:**
    ```json
    {
      "content": "Result text...",
      "keyUsed": "GROQ_DEALER_01"
    }
    ```

### **B. Registry Access**
`GET /v1/models/`
Returns the full `MODEL_REGISTRY` including tiers, gateways, and notes.

### **C. Filesystem Bridge**
*   `GET /v1/fs/ammo`: List all ammo files (.md, .txt, .json).
*   `GET /v1/fs/ammo/{file_name}`: Read specific ammo content.
*   `GET /v1/fs/prompts/{phase}`: List all prompts for a phase (e.g., SPARK, EAGLE).
*   `POST /v1/fs/prompts/{phase}`: Secure a new prompt asset to the disk.
*   `DELETE /v1/fs/prompts/{phase}/{name}`: Purge an asset from the arsenal.

---

## 6. CASINO DOCTRINE (UI INTEGRATION)
The V2 Engine is designed to feed specific data back to the Peacock HUD to trigger visual dopamine:
*   **The Strike:** Use `keyUsed` to show which "Dealer" is handling the hand.
*   **The Win:** Successful strikes should trigger the "Mechanical Click" sound in the HUD.
*   **The Jackpot:** Use the `HAWK` phase (System Certification) to trigger the full-screen visual shockwave.

---

## 7. MAINTENANCE
*   **Adding Models:** Modify `app/config.py`.
*   **Adding Gateways:** Update `app/core/striker.py` to include the new gateway logic using Pydantic AI's `OpenAIModel` or native providers.
*   **Purging:** Old TypeScript files can be safely removed once you are satisfied with the Python stability.

**[SYSTEM STATUS: OPERATIONAL]**
**[AUTHORIZATION: ARCHITECT ONLY]**
