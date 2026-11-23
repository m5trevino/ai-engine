import { createCliRenderer, BoxRenderable, type CliRenderer } from "@opentui/core"
import { getTheme } from "./lib/theme.js"
import { createNavBlocks, destroyNavBlocks, setActiveNav, type NavBlocks } from "./components/NavBlocks.js"
import { createMainScreen, destroyMainScreen, type MainScreen } from "./screens/MainScreen.js"
import { createProviderModelsScreen, destroyProviderModelsScreen } from "./screens/ProviderModelsScreen.js"
import { createDocsScreen, destroyDocsScreen } from "./screens/DocsScreen.js"
import { createLogsScreen, destroyLogsScreen } from "./screens/LogsScreen.js"

let renderer: CliRenderer | null = null
let nav: NavBlocks | null = null
let contentArea: BoxRenderable | null = null
let currentScreen: any = null
let screenKb: ((key: any) => void) | null = null

/* ------------------------------------------------------------------ */
/*  Switch screen                                                       */
/* ------------------------------------------------------------------ */

function switchScreen(id: string): void {
  if (!renderer || !contentArea || !nav) return

  /* destroy old screen content + its keyboard handler */
  if (currentScreen) {
    if (screenKb) {
      renderer.keyInput.off("keypress", screenKb)
      screenKb = null
    }
    if (currentScreen.kind === "main")      destroyMainScreen(currentScreen)
    if (currentScreen.kind === "providers") destroyProviderModelsScreen(currentScreen)
    if (currentScreen.kind === "docs")      destroyDocsScreen(currentScreen)
    if (currentScreen.kind === "logs")      destroyLogsScreen(currentScreen)
    currentScreen = null
  }

  /* create new screen inside contentArea */
  switch (id) {
    case "main":
      currentScreen = { ...createMainScreen(renderer, contentArea), kind: "main" }
      break
    case "providers":
      currentScreen = { ...createProviderModelsScreen(renderer, contentArea), kind: "providers" }
      break
    case "docs":
      currentScreen = { ...createDocsScreen(renderer, contentArea), kind: "docs" }
      break
    case "logs":
      currentScreen = { ...createLogsScreen(renderer, contentArea), kind: "logs" }
      break
    default:
      currentScreen = { ...createMainScreen(renderer, contentArea), kind: "main" }
  }

  /* wire screen-specific keyboard handler (only screen keys, not nav) */
  if (currentScreen && currentScreen.keyboardHandler) {
    const handler = currentScreen.keyboardHandler
    screenKb = handler
    renderer.keyInput.on("keypress", handler)
  }

  setActiveNav(nav, id)
}

/* ------------------------------------------------------------------ */
/*  Entry point                                                       */
/* ------------------------------------------------------------------ */

if (import.meta.main) {
  const theme = getTheme("cyber")
  renderer = await createCliRenderer({ exitOnCtrlC: true })
  renderer.setBackgroundColor(theme.bgBase)

  /* root layout: nav blocks + content area */
  const root = new BoxRenderable(renderer, {
    id: "app-root",
    zIndex: 0,
    width: "auto",
    height: "auto",
    flexGrow: 1,
    flexDirection: "column",
    backgroundColor: theme.bgBase,
  })
  renderer.root.add(root)

  nav = createNavBlocks(renderer)
  nav.onSwitch = (id: string) => switchScreen(id)
  root.add(nav.parent)

  contentArea = new BoxRenderable(renderer, {
    id: "content-area",
    zIndex: 0,
    width: "auto",
    height: "auto",
    flexGrow: 1,
    flexDirection: "column",
    backgroundColor: theme.bgBase,
  })
  root.add(contentArea)

  /* global quit handler */
  renderer.keyInput.on("keypress", (key: any) => {
    if (key.name === "q" || key.name === "Q") {
      renderer?.destroy()
      process.exit(0)
    }
  })

  switchScreen("main")
  renderer.start()
}
