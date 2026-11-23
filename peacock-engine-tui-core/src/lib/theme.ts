/**
 * Peacock Engine TUI Core — theme tokens
 * Cyber/military palette copied from the React TUI and adapted for imperative use.
 */

export interface ThemeColors {
  bgBase: string;
  bgSurface: string;
  bgRecessed: string;
  bgElevated: string;
  headerStart: string;
  headerEnd: string;
  headerText: string;
  accentGold: string;
  accentCyan: string;
  accentGoldDim: string;
  accentCyanDim: string;
  statusHealthy: string;
  statusWarning: string;
  statusCritical: string;
  statusInactive: string;
  textPrimary: string;
  textSecondary: string;
  textMuted: string;
  textInverse: string;
  borderSubtle: string;
  borderDefault: string;
  borderHighlight: string;
  connConnected: string;
  connDisconnected: string;
  connConnecting: string;
}

export const cyberTheme: ThemeColors = {
  bgBase: "#0a0b14",
  bgSurface: "#11121c",
  bgRecessed: "#070810",
  bgElevated: "#1a1b2e",
  headerStart: "#2a2b3e",
  headerEnd: "#1f2032",
  headerText: "#e8e9f0",
  accentGold: "#ffd700",
  accentCyan: "#00f0ff",
  accentGoldDim: "#b8a020",
  accentCyanDim: "#00a8b8",
  statusHealthy: "#00ff88",
  statusWarning: "#ffaa00",
  statusCritical: "#ff3366",
  statusInactive: "#555566",
  textPrimary: "#e0e1e8",
  textSecondary: "#9091a0",
  textMuted: "#606170",
  textInverse: "#0a0b14",
  borderSubtle: "#1e1f2e",
  borderDefault: "#2e2f40",
  borderHighlight: "#00f0ff",
  connConnected: "#00ff88",
  connDisconnected: "#ff3366",
  connConnecting: "#ffaa00",
};

export const militaryTheme: ThemeColors = {
  bgBase: "#0d1008",
  bgSurface: "#151a0f",
  bgRecessed: "#080a05",
  bgElevated: "#1e2418",
  headerStart: "#2a3322",
  headerEnd: "#1f2618",
  headerText: "#d8dcc8",
  accentGold: "#ccaa00",
  accentCyan: "#88aa55",
  accentGoldDim: "#887700",
  accentCyanDim: "#556633",
  statusHealthy: "#66aa44",
  statusWarning: "#cc9900",
  statusCritical: "#aa3333",
  statusInactive: "#445044",
  textPrimary: "#d8dcc8",
  textSecondary: "#889078",
  textMuted: "#556050",
  textInverse: "#0d1008",
  borderSubtle: "#1f2618",
  borderDefault: "#2e3628",
  borderHighlight: "#88aa55",
  connConnected: "#66aa44",
  connDisconnected: "#aa3333",
  connConnecting: "#cc9900",
};

export type ThemeMode = "cyber" | "military";

export function getTheme(mode: ThemeMode): ThemeColors {
  return mode === "cyber" ? cyberTheme : militaryTheme;
}
