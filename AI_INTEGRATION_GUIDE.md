# 🦅 PEACOCK ENGINE: AI INTEGRATOR COMMAND DOC
**VERSION:** 5.0 (NEXUS READY)

This document is the definitive source of truth for AI agents tasked with integrating, maintaining, or expanding the Peacock Engine.

---

## 📡 1. THE BACKEND ENGINE (`ai-handler`)

The engine acts as a **Middleware Strike Center**. It abstracts variety in AI providers into a single unified protocol.

### **Core Protocol: The Strike**
- **Endpoint:** `POST http://localhost:8888/v1/strike`
- **Payload Schema:**
  ```json
  {
    "modelId": "string (e.g., 'models/gemini-2.0-flash')",
    "prompt": "string",
    "temp": "number (0-1.0)",
    "response_format": "optional (JSON schema)"
  }
  ```

### **Model Intelligence: The Registry**
- **Endpoint:** `GET http://localhost:8888/v1/models`
- **Specification:** Each model in the registry now contains tactical rate limits:
  - `rpm`: Requests Per Minute
  - `tpm`: Tokens Per Minute
  - `rpd`: Requests Per Day
  - `tier`: `free` | `cheap` | `expensive` | `custom`

---

## 🎨 2. FRONTEND PLUG-N-PLAY (`peacock`)

The `UniversalTacticalPicker` is a standalone React component designed to be dropped into any application.

### **Integration Ritual**
1.  **Source:** `/src/components/external/UniversalTacticalPicker/`
2.  **Usage:**
    ```tsx
    import { UniversalTacticalPicker } from './components/external/UniversalTacticalPicker';

    <UniversalTacticalPicker 
      engineUrl="http://localhost:8888" 
      onSelect={(modelId) => setActiveModel(modelId)}
      gatewayFilter={['google']} // Optional: restrict to specific providers
    />
    ```

### **The Nexus Doctrine**
- **Nexus Mode:** When configuring a "Nexus" stage, **always** filter for `['google']`.
- **Operation Mode:** For standard processing (SPARK -> HAWK), use `['groq', 'mistral', 'deepseek']`.

---

## ⚡ 3. OPERATIONAL RITUALS

### **The Manual Handoff (EOF Protocol)**
When generating code, the engine (via the EAGLE stage) provides skeleton structures and directives. The AI (OWL stage) then fleshes these out into **EOF Overwrite Blocks**.

**Integrator Rule:** Do not output raw code for the user to figure out. Always wrap it in shell-executable EOF blocks for precision terminal deployment.

```bash
cat << 'EOF' > path/to/target_file.ts
// [INSERT FINAL FLESHED-OUT CODE HERE]
EOF
```

---

## 💀 4. MAINTENANCE LAWS (THE BLOOD OATH)
1.  **Aesthetics Overload:** Every UI component must use glassmorphism, voltage-colored glows (#00F3FF), and CRT-style scanning effects.
2.  **Zero Scraps:** Never provide snippets. Always provide complete, executable files.
3.  **No Placeholders:** `// TODO` is a mission failure. Implement everything or ask for clarification.

**[ENGINE STATUS: FULLY_INTEGRATED]**
**[AUTHORIZATION: ARCHITECT_LEVEL_BOTS_ONLY]**
