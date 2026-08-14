import { createCliRenderer, type CliRenderer } from "@opentui/core"
import { getTheme } from "./lib/theme.js"
import { createMainScreen, destroyMainScreen, type MainScreen } from "./screens/MainScreen.js"
import { createProviderModelsScreen, destroyProviderModelsScreen } from "./screens/ProviderModelsScreen.js"
import { createDocsScreen, destroyDocsScreen } from "./screens/DocsScreen.js"
import { createLogsScreen, destroyLogsScreen } from "./screens/LogsScreen.js"

let renderer: CliRenderer | null = null
let mainScreen: MainScreen | null = null
let subScreen: any = null
let subKeyboardHandler: ((key: any) => void) | null = null

function showMain(): void {
  if (!renderer) return

  /* tear down any sub-screen */
  if (subScreen) {
    if (subScreen.kind === "providers") destroyProviderModelsScreen(subScreen)
    if (subScreen.kind === "docs")     destroyDocsScreen(subScreen)
    if (subScreen.kind === "logs")     destroyLogsScreen(subScreen)
    subScreen = null
  }
  if (subKeyboardHandler) {
    renderer.keyInput.off("keypress", subKeyboardHandler)
    subKeyboardHandler = null
  }

  if (!mainScreen) {
    mainScreen = createMainScreen(renderer)
    mainScreen.onOpenScreen = (id: string) => openSubScreen(id)
  }
}

function openSubScreen(id: string): void {
  if (!renderer || !mainScreen) return

  /* hide main screen without destroying it */
  if (mainScreen.parent) {
    mainScreen.parent.visible = false
  }

  /* build sub-screen */
  switch (id) {
    case "providers":
      subScreen = { ...createProviderModelsScreen(renderer), kind: "providers" }
      break
    case "docs":
      subScreen = { ...createDocsScreen(renderer), kind: "docs" }
      break
    case "logs":
      subScreen = { ...createLogsScreen(renderer), kind: "logs" }
      break
    default:
      /* unhide main for unknown ids */
      if (mainScreen.parent) mainScreen.parent.visible = true
      return
  }

  /* inject Escape / Q handler that returns to main screen */
  subKeyboardHandler = (key: any) => {
    if (key.name === "q" || key.name === "escape") {
      showMain()
    }
  }
  renderer.keyInput.on("keypress", subKeyboardHandler)
}

/* ------------------------------------------------------------------ */
/*  Entry point                                                       */
/* ------------------------------------------------------------------ */

if (import.meta.main) {
  const theme = getTheme("cyber")
  renderer = await createCliRenderer({ exitOnCtrlC: true })
  renderer.setBackgroundColor(theme.bgBase)

  showMain()
  renderer.start()
}
