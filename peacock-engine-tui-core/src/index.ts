import { createCliRenderer, BoxRenderable, TextRenderable, TabSelectRenderable, TabSelectRenderableEvents, type TabSelectOption, type CliRenderer } from "@opentui/core"
import { getTheme, type ThemeColors } from "./lib/theme.js"
import { createProviderModelsScreen, destroyProviderModelsScreen } from "./screens/ProviderModelsScreen.js"
import { createLiveCliScreen, destroyLiveCliScreen } from "./screens/LiveCliScreen.js"
import { createDocsScreen, destroyDocsScreen } from "./screens/DocsScreen.js"
import { createLogsScreen, destroyLogsScreen } from "./screens/LogsScreen.js"

const MENU_OPTIONS: TabSelectOption[] = [
  { name: "Providers & Models", value: "providers", description: "Enable providers and browse models" },
  { name: "Live CLI", value: "cli", description: "Verbatim engine input/output" },
  { name: "Docs", value: "docs", description: "Documentation sections" },
  { name: "Logs", value: "logs", description: "Engine and striker logs" },
]

let renderer: CliRenderer | null = null
let menuParent: BoxRenderable | null = null
let menuTabs: TabSelectRenderable | null = null
let statusText: TextRenderable | null = null
let currentScreen: any = null
let keyboardHandler: ((key: any) => void) | null = null

function setStatus(theme: ThemeColors, text: string): void {
  if (!statusText) return
  statusText.content = text
}

function launchScreen(theme: ThemeColors, choice: string): void {
  if (!renderer) return
  if (currentScreen) {
    // Currently only one screen can be alive; destroy it before switching.
    if (currentScreen.kind === "providers") destroyProviderModelsScreen(currentScreen)
    if (currentScreen.kind === "cli") destroyLiveCliScreen(currentScreen)
    if (currentScreen.kind === "docs") destroyDocsScreen(currentScreen)
    if (currentScreen.kind === "logs") destroyLogsScreen(currentScreen)
    currentScreen = null
  }

  switch (choice) {
    case "providers":
      currentScreen = { ...createProviderModelsScreen(renderer), kind: "providers" }
      break
    case "cli":
      currentScreen = { ...createLiveCliScreen(renderer), kind: "cli" }
      break
    case "docs":
      currentScreen = { ...createDocsScreen(renderer), kind: "docs" }
      break
    case "logs":
      currentScreen = { ...createLogsScreen(renderer), kind: "logs" }
      break
    default:
      setStatus(theme, "Unknown screen")
  }
}

function showLauncher(theme: ThemeColors): void {
  if (!renderer) return
  if (currentScreen) {
    if (currentScreen.kind === "providers") destroyProviderModelsScreen(currentScreen)
    if (currentScreen.kind === "cli") destroyLiveCliScreen(currentScreen)
    if (currentScreen.kind === "docs") destroyDocsScreen(currentScreen)
    if (currentScreen.kind === "logs") destroyLogsScreen(currentScreen)
    currentScreen = null
  }

  menuParent = new BoxRenderable(renderer, {
    id: "launcher-root",
    zIndex: 10,
    width: "auto",
    height: "auto",
    flexGrow: 1,
    flexDirection: "column",
    backgroundColor: theme.bgBase,
  })

  const header = new BoxRenderable(renderer, {
    id: "launcher-header",
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
    id: "launcher-header-text",
    content: "PEACOCK ENGINE TUI",
    fg: theme.headerText,
    attributes: 1,
    zIndex: 1,
    flexGrow: 1,
  })
  header.add(headerText)
  menuParent.add(header)

  const content = new BoxRenderable(renderer, {
    id: "launcher-content",
    zIndex: 0,
    width: "auto",
    height: "auto",
    flexGrow: 1,
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    padding: 2,
  })
  menuParent.add(content)

  menuTabs = new TabSelectRenderable(renderer, {
    id: "launcher-menu",
    zIndex: 1,
    width: 50,
    height: 8,
    options: MENU_OPTIONS,
    tabWidth: 46,
    backgroundColor: theme.bgRecessed,
    focusedBackgroundColor: theme.bgElevated,
    textColor: theme.textSecondary,
    focusedTextColor: theme.textPrimary,
    selectedBackgroundColor: theme.accentCyanDim,
    selectedTextColor: theme.textInverse,
    selectedDescriptionColor: theme.textMuted,
    showDescription: true,
    showUnderline: true,
    showScrollArrows: true,
  })
  content.add(menuTabs)

  const footer = new BoxRenderable(renderer, {
    id: "launcher-footer",
    zIndex: 0,
    width: "auto",
    height: 1,
    backgroundColor: theme.bgElevated,
    flexDirection: "row",
    alignItems: "center",
  })
  statusText = new TextRenderable(renderer, {
    id: "launcher-status",
    content: "↑/↓: navigate | Enter: launch | Q: quit",
    fg: theme.textMuted,
    zIndex: 1,
    flexGrow: 1,
  })
  footer.add(statusText)
  menuParent.add(footer)

  renderer.root.add(menuParent)
  menuTabs.focus()

  menuTabs.on(TabSelectRenderableEvents.ITEM_SELECTED, (_index: number, option: TabSelectOption) => {
    launchScreen(theme, option.value)
  })
}

if (import.meta.main) {
  const theme = getTheme("cyber")
  renderer = await createCliRenderer({ exitOnCtrlC: true })
  renderer.setBackgroundColor(theme.bgBase)

  keyboardHandler = (key: any) => {
    if (!currentScreen && key.name === "q") {
      renderer?.destroy()
      process.exit(0)
    }
  }
  renderer.keyInput.on("keypress", keyboardHandler)

  showLauncher(theme)
  renderer.start()
}
