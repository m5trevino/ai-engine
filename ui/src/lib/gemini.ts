import { GoogleGenAI } from "@google/genai";

const apiKey = process.env.GEMINI_API_KEY || "";
const ai = new GoogleGenAI({ apiKey });

export const model = "gemini-3.1-flash-lite-preview";

export async function generateResponse(prompt: string, history: { role: 'user' | 'model', parts: { text: string }[] }[] = []) {
  try {
    const response = await ai.models.generateContent({
      model: model,
      contents: [
        ...history.map(h => ({ role: h.role, parts: h.parts })),
        { role: 'user', parts: [{ text: prompt }] }
      ],
      config: {
        systemInstruction: "You are the Peacock Engine, a high-precision neural asset management system. Your tone is technical, efficient, and slightly futuristic. Use terms like 'neural pathways', 'mesh nodes', 'precision tuning', and 'deployment manifests'. Keep responses concise and structured. If asked for code or config, provide it in a clean block.",
      }
    });
    return response.text;
  } catch (error) {
    console.error("Gemini API Error:", error);
    return "ERROR: NEURAL_LINK_FAILURE. RETRY_SEQUENCE_INITIALIZED.";
  }
}
