import {
  CliRenderer,
  BoxRenderable,
  TextRenderable,
  ScrollBoxRenderable,
} from "@opentui/core"
import { getTheme, type ThemeColors } from "../lib/theme.js"

/* ------------------------------------------------------------------ */
/*  Types                                                               */
/* ------------------------------------------------------------------ */

export interface MainScreen {
  renderer: CliRenderer
  theme: ThemeColors
  parent: BoxRenderable
  scrollBox: ScrollBoxRenderable | null
  logText: TextRenderable | null
  statusText: TextRenderable | null
  keyboardHandler: ((key: any) => void) | null
  lines: string[]
  maxLines: number
  refreshInterval: ReturnType<typeof setInterval> | null
}

/* ------------------------------------------------------------------ */
/*  Factory                                                             */
/* ------------------------------------------------------------------ */

export function createMainScreen(renderer: CliRenderer, contentParent: BoxRenderable): MainScreen {
  const screen: MainScreen = {
    renderer,
    theme: getTheme("cyber"),
    parent: new BoxRenderable(renderer, {
      id: "main-content",
      zIndex: 10,
      width: "auto",
      height: "auto",
      flexGrow: 1,
      flexDirection: "column",
      backgroundColor: getTheme("cyber").bgBase,
    }),
    scrollBox: null,
    logText: null,
    statusText: null,
    keyboardHandler: null,
    lines: [],
    maxLines: 500,
    refreshInterval: null,
  }

  buildLayout(screen)
  bindKeys(screen)
  startAutoRefresh(screen)
  contentParent.add(screen.parent)
  return screen
}

/* ------------------------------------------------------------------ */
/*  Layout                                                              */
/* ------------------------------------------------------------------ */

function buildLayout(screen: MainScreen): void {
  const { renderer, theme, parent } = screen

  /* ---- Live logger area ------------------------------------------- */
  screen.scrollBox = new ScrollBoxRenderable(renderer, {
    id: "main-logger-scroll",
    zIndex: 0,
    width: "auto",
    height: "auto",
    flexGrow: 1,
    margin: 1,
    backgroundColor: theme.bgRecessed,
    borderStyle: "single",
    borderColor: theme.borderDefault,
    border: true,
  })

  screen.logText = new TextRenderable(renderer, {
    id: "main-logger-text",
    content: "",
    fg: theme.textSecondary,
    zIndex: 1,
    width: "auto",
    height: "auto",
    wrapMode: "word",
  })
  screen.scrollBox.add(screen.logText)
  parent.add(screen.scrollBox)

  /* ---- Footer ------------------------------------------------------ */
  const footer = new BoxRenderable(renderer, {
    id: "main-footer",
    zIndex: 0,
    width: "auto",
    height: 1,
    backgroundColor: theme.bgElevated,
    flexDirection: "row",
    alignItems: "center",
  })
  screen.statusText = new TextRenderable(renderer, {
    id: "main-status",
    content: "↑/↓: scroll log | Tab: focus nav | Q: quit",
    fg: theme.textMuted,
    zIndex: 1,
    flexGrow: 1,
  })
  footer.add(screen.statusText)
  parent.add(footer)
}

/* ------------------------------------------------------------------ */
/*  Keyboard handling                                                   */
/* ------------------------------------------------------------------ */

function bindKeys(screen: MainScreen): void {
  screen.keyboardHandler = (key: any) => {
    if (!screen.scrollBox) return
    if (key.name === "up" || key.name === "k") {
      screen.scrollBox.scrollBy(-1)
    } else if (key.name === "down" || key.name === "j") {
      screen.scrollBox.scrollBy(1)
    } else if (key.name === "pageup") {
      screen.scrollBox.scrollBy(-Math.max(1, Math.floor(screen.scrollBox.height / 2)))
    } else if (key.name === "pagedown") {
      screen.scrollBox.scrollBy(Math.max(1, Math.floor(screen.scrollBox.height / 2)))
    } else if (key.name === "home") {
      screen.scrollBox.scrollTo(0)
    } else if (key.name === "end") {
      screen.scrollBox.scrollTo(screen.scrollBox.scrollHeight)
    }
  }
  screen.renderer.keyInput.on("keypress", screen.keyboardHandler)
}

/* ------------------------------------------------------------------ */
/*  Log appending                                                       */
/* ------------------------------------------------------------------ */

export function appendLogLine(screen: MainScreen, line: string): void {
  const timestamp = new Date().toLocaleTimeString()
  screen.lines.push(`[${timestamp}] ${line}`)
  if (screen.lines.length > screen.maxLines) {
    screen.lines.shift()
  }
  if (screen.logText) {
    screen.logText.content = screen.lines.join("\n")
  }
  if (screen.scrollBox) {
    screen.scrollBox.scrollTo(screen.scrollBox.scrollHeight)
  }
}

export function appendLogDivider(screen: MainScreen, label: string): void {
  const side = "─".repeat(18)
  const divider = `${side} ${label} ${side}`
  screen.lines.push("")
  screen.lines.push(divider)
  screen.lines.push("")
  while (screen.lines.length > screen.maxLines) {
    screen.lines.shift()
  }
  if (screen.logText) {
    screen.logText.content = screen.lines.join("\n")
  }
  if (screen.scrollBox) {
    screen.scrollBox.scrollTo(screen.scrollBox.scrollHeight)
  }
}

/* ------------------------------------------------------------------ */
/*  Auto-refresh (placeholder until SSE wired)                          */
/* ------------------------------------------------------------------ */

function startAutoRefresh(screen: MainScreen): void {
  appendLogLine(screen, "Engine monitor ready. Awaiting live stream...")
  appendLogDivider(screen, "BOOT")
  appendLogLine(screen, "Connected to Peacock Engine")
  appendLogLine(screen, "Listening for API calls...")

  screen.refreshInterval = setInterval(() => {
    // Placeholder: will be replaced with real SSE log stream
  }, 3000)
}

/* ------------------------------------------------------------------ */
/*  Cleanup                                                             */
/* ------------------------------------------------------------------ */

export function destroyMainScreen(screen: MainScreen): void {
  if (screen.refreshInterval) {
    clearInterval(screen.refreshInterval)
    screen.refreshInterval = null
  }
  if (screen.keyboardHandler) {
    screen.renderer.keyInput.off("keypress", screen.keyboardHandler)
    screen.keyboardHandler = null
  }
  if (screen.parent) {
    screen.parent.parent?.remove(screen.parent.id)
    screen.parent.destroy()
  }
}
