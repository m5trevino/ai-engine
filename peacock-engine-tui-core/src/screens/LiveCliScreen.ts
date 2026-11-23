import {
  CliRenderer,
  BoxRenderable,
  TextRenderable,
  ScrollBoxRenderable,
  type KeyEvent,
} from "@opentui/core"
import { getTheme, type ThemeColors } from "../lib/theme.js"

interface LiveCliScreen {
  renderer: CliRenderer
  theme: ThemeColors
  parent: BoxRenderable
  scrollBox: ScrollBoxRenderable | null
  contentText: TextRenderable | null
  statusText: TextRenderable | null
  keyboardHandler: ((key: any) => void) | null
  lines: string[]
  maxLines: number
}

export function createLiveCliScreen(renderer: CliRenderer): LiveCliScreen {
  const screen: LiveCliScreen = {
    renderer,
    theme: getTheme("cyber"),
    parent: new BoxRenderable(renderer, {
      id: "live-cli-root",
      zIndex: 10,
      width: "auto",
      height: "auto",
      flexGrow: 1,
      flexDirection: "column",
      backgroundColor: getTheme("cyber").bgBase,
    }),
    scrollBox: null,
    contentText: null,
    statusText: null,
    keyboardHandler: null,
    lines: [],
    maxLines: 500,
  }

  buildLayout(screen)
  bindKeys(screen)
  // Seed with instructions until we wire a real log stream
  appendLine(screen, "Live CLI viewer ready. Awaiting engine output...")
  appendLine(screen, "[Hint] This screen will tail the engine log stream from /v1/admin/logs/stream")
  return screen
}

function buildLayout(screen: LiveCliScreen): void {
  const { renderer, theme, parent } = screen

  const header = new BoxRenderable(renderer, {
    id: "live-cli-header",
    zIndex: 0,
    width: "auto",
    height: 3,
    backgroundColor: theme.headerStart,
    borderStyle: "single",
    borderColor: theme.borderDefault,
    flexDirection: "row",
    alignItems: "center",
    border: true,
  })
  const headerText = new TextRenderable(renderer, {
    id: "live-cli-header-text",
    content: "LIVE CLI VIEWER",
    fg: theme.headerText,
    attributes: 1,
    zIndex: 1,
    flexGrow: 1,
  })
  header.add(headerText)
  parent.add(header)

  screen.scrollBox = new ScrollBoxRenderable(renderer, {
    id: "live-cli-scroll",
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

  screen.contentText = new TextRenderable(renderer, {
    id: "live-cli-content",
    content: "",
    fg: theme.textSecondary,
    zIndex: 1,
    width: "auto",
    height: "auto",
    wrapMode: "word",
  })
  screen.scrollBox.add(screen.contentText)
  parent.add(screen.scrollBox)

  const footer = new BoxRenderable(renderer, {
    id: "live-cli-footer",
    zIndex: 0,
    width: "auto",
    height: 1,
    backgroundColor: theme.bgElevated,
    flexDirection: "row",
    alignItems: "center",
  })
  screen.statusText = new TextRenderable(renderer, {
    id: "live-cli-status",
    content: "↑/↓: scroll | Q: back",
    fg: theme.textMuted,
    zIndex: 1,
    flexGrow: 1,
  })
  footer.add(screen.statusText)
  parent.add(footer)

  renderer.root.add(parent)
}

function bindKeys(screen: LiveCliScreen): void {
  screen.keyboardHandler = (key: KeyEvent) => {
    if (key.name === "q" || key.name === "escape") {
      destroyLiveCliScreen(screen)
      return
    }
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

export function appendLine(screen: LiveCliScreen, line: string): void {
  const timestamp = new Date().toLocaleTimeString()
  screen.lines.push(`[${timestamp}] ${line}`)
  if (screen.lines.length > screen.maxLines) {
    screen.lines.shift()
  }
  if (screen.contentText) {
    screen.contentText.content = screen.lines.join("\n")
  }
  if (screen.scrollBox) {
    screen.scrollBox.scrollTo(screen.scrollBox.scrollHeight)
  }
}

export function destroyLiveCliScreen(screen: LiveCliScreen): void {
  if (screen.keyboardHandler) {
    screen.renderer.keyInput.off("keypress", screen.keyboardHandler)
    screen.keyboardHandler = null
  }
  if (screen.parent) {
    screen.renderer.root.remove(screen.parent.id)
    screen.parent.destroy()
  }
}
