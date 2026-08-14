import {
  CliRenderer,
  BoxRenderable,
  TextRenderable,
  ScrollBoxRenderable,
  RGBA,
} from "@opentui/core"
import { getTheme, type ThemeColors } from "../lib/theme.js"

/* ------------------------------------------------------------------ */
/*  Types                                                               */
/* ------------------------------------------------------------------ */

interface ActionBlock {
  id: string
  label: string
  shortcut: string
  bg: RGBA
  hoverBg: RGBA
  pressBg: RGBA
  box: BoxRenderable
  text: TextRenderable
}

export interface MainScreen {
  renderer: CliRenderer
  theme: ThemeColors
  parent: BoxRenderable
  blocks: ActionBlock[]
  selectedBlockIndex: number
  scrollBox: ScrollBoxRenderable | null
  logText: TextRenderable | null
  statusText: TextRenderable | null
  keyboardHandler: ((key: any) => void) | null
  lines: string[]
  maxLines: number
  onOpenScreen: ((screen: string) => void) | null
  refreshInterval: ReturnType<typeof setInterval> | null
}

/* ------------------------------------------------------------------ */
/*  Action definitions                                                  */
/* ------------------------------------------------------------------ */

const ACTION_DEFS = [
  { id: "providers", label: "Providers & Models", shortcut: "P" },
  { id: "docs",      label: "Docs",               shortcut: "D" },
  { id: "logs",      label: "Logs",               shortcut: "L" },
  { id: "config",    label: "Settings",           shortcut: "S" },
  { id: "health",    label: "Health",             shortcut: "H" },
]

/* ------------------------------------------------------------------ */
/*  Factory                                                             */
/* ------------------------------------------------------------------ */

export function createMainScreen(renderer: CliRenderer): MainScreen {
  const screen: MainScreen = {
    renderer,
    theme: getTheme("cyber"),
    parent: new BoxRenderable(renderer, {
      id: "main-root",
      zIndex: 10,
      width: "auto",
      height: "auto",
      flexGrow: 1,
      flexDirection: "column",
      backgroundColor: getTheme("cyber").bgBase,
    }),
    blocks: [],
    selectedBlockIndex: 0,
    scrollBox: null,
    logText: null,
    statusText: null,
    keyboardHandler: null,
    lines: [],
    maxLines: 500,
    onOpenScreen: null,
    refreshInterval: null,
  }

  buildLayout(screen)
  bindKeys(screen)
  startAutoRefresh(screen)
  return screen
}

/* ------------------------------------------------------------------ */
/*  Layout                                                              */
/* ------------------------------------------------------------------ */

function buildLayout(screen: MainScreen): void {
  const { renderer, theme, parent } = screen

  /* ---- Header ------------------------------------------------------ */
  const header = new BoxRenderable(renderer, {
    id: "main-header",
    zIndex: 0,
    width: "auto",
    height: 1,
    backgroundColor: theme.headerStart,
    flexDirection: "row",
    alignItems: "center",
  })
  const headerText = new TextRenderable(renderer, {
    id: "main-header-text",
    content: " PEACOCK ENGINE ",
    fg: theme.headerText,
    attributes: 1,
    zIndex: 1,
  })
  header.add(headerText)
  parent.add(header)

  /* ---- Action blocks row ------------------------------------------ */
  const blocksRow = new BoxRenderable(renderer, {
    id: "main-blocks-row",
    zIndex: 0,
    width: "auto",
    height: 5,
    flexDirection: "row",
    alignItems: "center",
    gap: 1,
    padding: 1,
    backgroundColor: theme.bgElevated,
  })
  parent.add(blocksRow)

  const colors = [
    RGBA.fromInts(60,  120, 180, 255),  // blue
    RGBA.fromInts(120, 180, 60,  255),  // green
    RGBA.fromInts(180, 120, 60,  255),  // orange
    RGBA.fromInts(180, 60,  120, 255),  // pink
    RGBA.fromInts(60,  180, 160, 255),  // teal
  ]

  ACTION_DEFS.forEach((def, idx) => {
    const base = colors[idx % colors.length]
    const hover = RGBA.fromValues(
      Math.min(1.0, base.r * 1.3),
      Math.min(1.0, base.g * 1.3),
      Math.min(1.0, base.b * 1.3),
      base.a,
    )
    const press = RGBA.fromValues(base.r * 0.6, base.g * 0.6, base.b * 0.6, base.a)

    const box = new BoxRenderable(renderer, {
      id: `main-block-${def.id}`,
      zIndex: 1,
      flexGrow: 1,
      height: 3,
      backgroundColor: base,
      borderStyle: "single",
      borderColor: theme.borderDefault,
      border: true,
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
    })

    const label = new TextRenderable(renderer, {
      id: `main-block-label-${def.id}`,
      content: def.label,
      fg: theme.textInverse,
      attributes: 1,
      zIndex: 2,
    })
    box.add(label)

    const shortcut = new TextRenderable(renderer, {
      id: `main-block-shortcut-${def.id}`,
      content: `[${def.shortcut}]`,
      fg: theme.textMuted,
      zIndex: 2,
    })
    box.add(shortcut)

    blocksRow.add(box)

    screen.blocks.push({
      id: def.id,
      label: def.label,
      shortcut: def.shortcut,
      bg: base,
      hoverBg: hover,
      pressBg: press,
      box,
      text: label,
    })
  })

  highlightBlock(screen, 0)

  /* ---- Live logger area ------------------------------------------- */
  screen.scrollBox = new ScrollBoxRenderable(renderer, {
    id: "main-logger-scroll",
    zIndex: 0,
    width: "auto",
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
    content: "←/→: select | Enter: open | ↑/↓: scroll log | Q: quit",
    fg: theme.textMuted,
    zIndex: 1,
    flexGrow: 1,
  })
  footer.add(screen.statusText)
  parent.add(footer)

  renderer.root.add(parent)
}

/* ------------------------------------------------------------------ */
/*  Block highlighting                                                  */
/* ------------------------------------------------------------------ */

function highlightBlock(screen: MainScreen, index: number): void {
  screen.blocks.forEach((block, idx) => {
    block.box.backgroundColor = idx === index ? block.hoverBg : block.bg
  })
  screen.selectedBlockIndex = index
}

/* ------------------------------------------------------------------ */
/*  Keyboard handling                                                   */
/* ------------------------------------------------------------------ */

function bindKeys(screen: MainScreen): void {
  let focusMode: "blocks" | "log" = "blocks"

  screen.keyboardHandler = (key: any) => {
    if (key.name === "q" || key.name === "escape") {
      destroyMainScreen(screen)
      process.exit(0)
    }

    /* -- Switch focus mode -- */
    if (key.name === "tab") {
      focusMode = focusMode === "blocks" ? "log" : "blocks"
      if (screen.statusText) {
        screen.statusText.content = focusMode === "blocks"
          ? "←/→: select | Enter: open | Tab: focus log | Q: quit"
          : "↑/↓: scroll | Tab: focus blocks | Q: quit"
      }
      return
    }

    /* -- Block navigation -- */
    if (focusMode === "blocks") {
      if (key.name === "left" || key.name === "h") {
        const next = screen.selectedBlockIndex <= 0
          ? screen.blocks.length - 1
          : screen.selectedBlockIndex - 1
        highlightBlock(screen, next)
      } else if (key.name === "right" || key.name === "l") {
        const next = screen.selectedBlockIndex >= screen.blocks.length - 1
          ? 0
          : screen.selectedBlockIndex + 1
        highlightBlock(screen, next)
      } else if (key.name === "return" || key.name === "space") {
        const block = screen.blocks[screen.selectedBlockIndex]
        if (block && screen.onOpenScreen) {
          screen.onOpenScreen(block.id)
        }
      }

      /* Shortcut keys */
      const shortcutMap: Record<string, string> = {
        p: "providers", d: "docs", l: "logs",
        s: "config",    h: "health",
      }
      const shortcut = shortcutMap[key.name]
      if (shortcut && screen.onOpenScreen) {
        screen.onOpenScreen(shortcut)
      }
      return
    }

    /* -- Log scrolling -- */
    if (focusMode === "log" && screen.scrollBox) {
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
  const width = 40
  const side = "─".repeat(Math.floor((width - label.length - 2) / 2))
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
    screen.renderer.root.remove(screen.parent.id)
    screen.parent.destroy()
  }
}
