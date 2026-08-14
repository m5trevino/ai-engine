import {
  CliRenderer,
  BoxRenderable,
  TextRenderable,
  TabSelectRenderable,
  TabSelectRenderableEvents,
  RenderableEvents,
  ScrollBoxRenderable,
  type TabSelectOption,
} from "@opentui/core"
import { getTheme, type ThemeColors } from "../lib/theme.js"
import { fetchEngineLogs, fetchStrikerStatus } from "../lib/api.js"

interface LogsScreen {
  renderer: CliRenderer
  theme: ThemeColors
  parent: BoxRenderable
  leftTabs: TabSelectRenderable | null
  scrollBox: ScrollBoxRenderable | null
  contentText: TextRenderable | null
  statusText: TextRenderable | null
  keyboardHandler: ((key: any) => void) | null
  logOptions: TabSelectOption[]
  selectedLog: string | null
  refreshInterval: ReturnType<typeof setInterval> | null
}

const STATIC_LOG_SOURCES: TabSelectOption[] = [
  { name: "Engine Log", value: "engine", description: "" },
  { name: "Striker Logs", value: "striker", description: "" },
]

export function createLogsScreen(renderer: CliRenderer, contentParent: BoxRenderable): LogsScreen {
  const screen: LogsScreen = {
    renderer,
    theme: getTheme("cyber"),
    parent: new BoxRenderable(renderer, {
      id: "logs-content",
      zIndex: 10,
      width: "auto",
      height: "auto",
      flexGrow: 1,
      flexDirection: "column",
      backgroundColor: getTheme("cyber").bgBase,
    }),
    leftTabs: null,
    scrollBox: null,
    contentText: null,
    statusText: null,
    keyboardHandler: null,
    logOptions: [...STATIC_LOG_SOURCES],
    selectedLog: "engine",
    refreshInterval: null,
  }

  buildLayout(screen)
  bindKeys(screen)
  startAutoRefresh(screen)
  loadLog(screen, "engine")
  contentParent.add(screen.parent)
  return screen
}

function buildLayout(screen: LogsScreen): void {
  const { renderer, theme, parent } = screen

  const contentRow = new BoxRenderable(renderer, {
    id: "logs-content",
    zIndex: 0,
    width: "auto",
    height: "auto",
    flexGrow: 1,
    flexDirection: "row",
    padding: 1,
    gap: 1,
  })
  parent.add(contentRow)

  const leftBox = new BoxRenderable(renderer, {
    id: "logs-left",
    zIndex: 0,
    width: 24,
    height: "auto",
    flexGrow: 0,
    flexShrink: 0,
    flexDirection: "column",
    backgroundColor: theme.bgRecessed,
    borderStyle: "single",
    borderColor: theme.borderDefault,
    border: true,
  })
  const leftLabel = new TextRenderable(renderer, {
    id: "logs-left-label",
    content: "Sources",
    fg: theme.accentCyan,
    attributes: 1,
    zIndex: 1,
  })
  leftBox.add(leftLabel)

  screen.leftTabs = new TabSelectRenderable(renderer, {
    id: "logs-tabs",
    zIndex: 1,
    width: "auto",
    flexGrow: 1,
    options: screen.logOptions,
    tabWidth: 20,
    backgroundColor: theme.bgRecessed,
    focusedBackgroundColor: theme.bgElevated,
    textColor: theme.textSecondary,
    focusedTextColor: theme.textPrimary,
    selectedBackgroundColor: theme.accentCyanDim,
    selectedTextColor: theme.textInverse,
    showDescription: false,
    showUnderline: false,
  })
  leftBox.add(screen.leftTabs)
  contentRow.add(leftBox)

  screen.scrollBox = new ScrollBoxRenderable(renderer, {
    id: "logs-scroll",
    zIndex: 0,
    width: "auto",
    height: "auto",
    flexGrow: 1,
    backgroundColor: theme.bgRecessed,
    borderStyle: "single",
    borderColor: theme.borderDefault,
    border: true,
  })
  screen.contentText = new TextRenderable(renderer, {
    id: "logs-content-text",
    content: "",
    fg: theme.textSecondary,
    zIndex: 1,
    width: "auto",
    height: "auto",
    wrapMode: "none",
  })
  screen.scrollBox.add(screen.contentText)
  contentRow.add(screen.scrollBox)

  const footer = new BoxRenderable(renderer, {
    id: "logs-footer",
    zIndex: 0,
    width: "auto",
    height: 1,
    backgroundColor: theme.bgElevated,
    flexDirection: "row",
    alignItems: "center",
  })
  screen.statusText = new TextRenderable(renderer, {
    id: "logs-status",
    content: "R: refresh | ↑/↓: scroll | Q: back",
    fg: theme.textMuted,
    zIndex: 1,
    flexGrow: 1,
  })
  footer.add(screen.statusText)
  parent.add(footer)

  renderer.root.add(parent)
  screen.leftTabs.focus()
}

async function loadLog(screen: LogsScreen, source: string): Promise<void> {
  if (!screen.contentText || !screen.scrollBox) return
  setStatus(screen, `Loading ${source}...`)
  try {
    let lines: string[] = []
    if (source === "engine") {
      const data = await fetchEngineLogs(100)
      lines = data.lines ?? []
    } else if (source === "striker") {
      const data = await fetchStrikerStatus()
      lines = data.logs ?? []
    }
    screen.contentText.content = lines.join("\n")
    screen.scrollBox.scrollTo(screen.scrollBox.scrollHeight)
    setStatus(screen, `${source}: ${lines.length} lines`)
  } catch (err) {
    screen.contentText.content = `Error loading ${source}: ${err instanceof Error ? err.message : String(err)}`
    setStatus(screen, "Load failed")
  }
}

function startAutoRefresh(screen: LogsScreen): void {
  if (screen.refreshInterval) clearInterval(screen.refreshInterval)
  screen.refreshInterval = setInterval(() => {
    if (screen.selectedLog) loadLog(screen, screen.selectedLog)
  }, 3000)
}

function bindKeys(screen: LogsScreen): void {
  screen.keyboardHandler = (key: any) => {
    if (key.name === "q" || key.name === "escape") {
      destroyLogsScreen(screen)
      return
    }
    if (key.name === "r" || key.name === "R") {
      if (screen.selectedLog) loadLog(screen, screen.selectedLog)
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
    }
  }
  screen.renderer.keyInput.on("keypress", screen.keyboardHandler)

  screen.leftTabs?.on(TabSelectRenderableEvents.ITEM_SELECTED, (_index: number, option: TabSelectOption) => {
    screen.selectedLog = option.value
    loadLog(screen, option.value)
  })

  screen.leftTabs?.on(RenderableEvents.FOCUSED, () => {
    if (screen.statusText) screen.statusText.content = "Enter: select source | R: refresh | ↑/↓: scroll | Q: back"
  })
}

function setStatus(screen: LogsScreen, text: string): void {
  if (!screen.statusText) return
  screen.statusText.content = text
}

export function destroyLogsScreen(screen: LogsScreen): void {
  if (screen.keyboardHandler) {
    screen.renderer.keyInput.off("keypress", screen.keyboardHandler)
    screen.keyboardHandler = null
  }
  if (screen.refreshInterval) {
    clearInterval(screen.refreshInterval)
    screen.refreshInterval = null
  }
  if (screen.parent) {
    screen.parent.parent?.remove(screen.parent.id)
    screen.parent.destroy()
  }
}
