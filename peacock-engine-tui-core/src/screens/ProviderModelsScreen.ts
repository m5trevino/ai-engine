import {
  CliRenderer,
  BoxRenderable,
  TextRenderable,
  TabSelectRenderable,
  TabSelectRenderableEvents,
  RenderableEvents,
  type TabSelectOption,
} from "@opentui/core"
import { getTheme, type ThemeColors } from "../lib/theme.js"
import {
  fetchModels,
  fetchProviders,
  toggleProvider,
  type ProviderState,
  type ModelInfo,
} from "../lib/api.js"

interface ProviderModelsScreen {
  renderer: CliRenderer
  theme: ThemeColors
  parent: BoxRenderable
  leftTabs: TabSelectRenderable | null
  rightBox: BoxRenderable | null
  rightTitle: TextRenderable | null
  rightContent: TextRenderable | null
  statusText: TextRenderable | null
  providers: Record<string, ProviderState>
  modelsByGateway: Record<string, ModelInfo[]>
  selectedGateway: string | null
  keyboardHandler: ((key: any) => void) | null
  message: string | null
  messageTimeout: ReturnType<typeof setInterval> | null
}

export function createProviderModelsScreen(renderer: CliRenderer, contentParent: BoxRenderable): ProviderModelsScreen {
  const screen: ProviderModelsScreen = {
    renderer,
    theme: getTheme("cyber"),
    parent: new BoxRenderable(renderer, {
      id: "provider-models-content",
      zIndex: 10,
      width: "auto",
      height: "auto",
      flexGrow: 1,
      flexDirection: "column",
      backgroundColor: getTheme("cyber").bgBase,
    }),
    leftTabs: null,
    rightBox: null,
    rightTitle: null,
    rightContent: null,
    statusText: null,
    providers: {},
    modelsByGateway: {},
    selectedGateway: null,
    keyboardHandler: null,
    message: null,
    messageTimeout: null,
  }

  buildLayout(screen)
  loadData(screen)
  bindKeys(screen)
  contentParent.add(screen.parent)
  return screen
}

function buildLayout(screen: ProviderModelsScreen): void {
  const { renderer, theme, parent } = screen

  // Content row
  const contentRow = new BoxRenderable(renderer, {
    id: "provider-models-content",
    zIndex: 0,
    width: "auto",
    height: "auto",
    flexGrow: 1,
    flexDirection: "row",
    padding: 1,
    gap: 1,
  })
  parent.add(contentRow)

  // Left: provider tabs
  const leftBox = new BoxRenderable(renderer, {
    id: "provider-models-left",
    zIndex: 0,
    width: 22,
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
    id: "provider-models-left-label",
    content: "Providers",
    fg: theme.accentCyan,
    attributes: 1,
    zIndex: 1,
  })
  leftBox.add(leftLabel)

  screen.leftTabs = new TabSelectRenderable(renderer, {
    id: "provider-models-tabs",
    zIndex: 1,
    width: "auto",
    flexGrow: 1,
    options: [],
    tabWidth: 18,
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

  const hint = new TextRenderable(renderer, {
    id: "provider-models-left-hint",
    content: "←/→: nav | Enter: toggle",
    fg: theme.textMuted,
    zIndex: 1,
  })
  leftBox.add(hint)
  contentRow.add(leftBox)

  // Right: model list for selected provider
  screen.rightBox = new BoxRenderable(renderer, {
    id: "provider-models-right",
    zIndex: 0,
    width: "auto",
    height: "auto",
    flexGrow: 1,
    flexDirection: "column",
    backgroundColor: theme.bgRecessed,
    borderStyle: "single",
    borderColor: theme.borderDefault,
    border: true,
  })
  screen.rightTitle = new TextRenderable(renderer, {
    id: "provider-models-right-title",
    content: "Select a provider",
    fg: theme.accentGold,
    attributes: 1,
    zIndex: 1,
  })
  screen.rightBox.add(screen.rightTitle)
  screen.rightContent = new TextRenderable(renderer, {
    id: "provider-models-right-content",
    content: "",
    fg: theme.textSecondary,
    zIndex: 1,
    flexGrow: 1,
    height: "auto",
    width: "auto",
    wrapMode: "word",
  })
  screen.rightBox.add(screen.rightContent)
  contentRow.add(screen.rightBox)

  // Footer status bar
  const footer = new BoxRenderable(renderer, {
    id: "provider-models-footer",
    zIndex: 0,
    width: "auto",
    height: 1,
    backgroundColor: theme.bgElevated,
    flexDirection: "row",
    alignItems: "center",
  })
  screen.statusText = new TextRenderable(renderer, {
    id: "provider-models-status",
    content: "R: refresh | Q: back",
    fg: theme.textMuted,
    zIndex: 1,
    flexGrow: 1,
  })
  footer.add(screen.statusText)
  parent.add(footer)

  renderer.root.add(parent)
  screen.leftTabs.focus()
}

async function loadData(screen: ProviderModelsScreen): Promise<void> {
  setStatus(screen, "Loading providers and models...")
  try {
    const [modelsData, providersData] = await Promise.all([
      fetchModels(),
      fetchProviders(),
    ])
    screen.providers = providersData
    screen.modelsByGateway = modelsData.by_gateway

    const providerOptions: TabSelectOption[] = Object.entries(providersData)
      .filter(([, state]) => state.visible)
      .map(([gateway, state]) => ({
        name: formatProviderName(gateway, state.label),
        value: gateway,
        description: state.enabled ? "enabled" : "disabled",
      }))

    if (screen.leftTabs) {
      screen.leftTabs.options = providerOptions
      if (providerOptions.length > 0 && !screen.selectedGateway) {
        screen.selectedGateway = providerOptions[0].value
        screen.leftTabs.setSelectedIndex(0)
      }
    }

    renderRightPane(screen)
    setStatus(screen, `Loaded ${Object.keys(providersData).length} providers, ${modelsData.count} models`)
  } catch (err) {
    setStatus(screen, `Error: ${err instanceof Error ? err.message : String(err)}`)
  }
}

function formatProviderName(gateway: string, label: string): string {
  return `${label} (${gateway})`.substring(0, 22)
}

function renderRightPane(screen: ProviderModelsScreen): void {
  if (!screen.rightTitle || !screen.rightContent) return
  const { selectedGateway, modelsByGateway, providers, theme } = screen

  if (!selectedGateway) {
    screen.rightTitle.content = "No provider selected"
    screen.rightContent.content = ""
    return
  }

  const state = providers[selectedGateway]
  const models = modelsByGateway[selectedGateway] ?? []
  const enabledTag = state?.enabled ? "[enabled]" : "[disabled]"

  screen.rightTitle.content = `${state?.label ?? selectedGateway} ${enabledTag}`

  if (models.length === 0) {
    screen.rightContent.content = "No models loaded for this provider."
    return
  }

  const header = [
    "Model".padEnd(34),
    "Tier".padEnd(8),
    "Status".padEnd(8),
    "RPM".padEnd(6),
    "TPM".padEnd(8),
  ].join(" ")
  const lines: string[] = [header, ""]

  for (const m of models) {
    const name = m.display_name ?? m.id
    const shortName = name.length > 34 ? name.substring(0, 32) + ".." : name.padEnd(34)
    const tier = m.tier.padEnd(8)
    const status = m.status.padEnd(8)
    const rpm = String(m.rpm ?? "-").padEnd(6)
    const tpm = String(m.tpm ?? "-").padEnd(8)
    lines.push(`${shortName} ${tier} ${status} ${rpm} ${tpm}`)
    if (m.note) {
      lines.push(`  ${m.note}`)
    }
  }

  screen.rightContent.content = lines.join("\n")
  screen.rightContent.fg = theme.textSecondary
}

async function toggleSelectedProvider(screen: ProviderModelsScreen): Promise<void> {
  if (!screen.selectedGateway) return
  const gateway = screen.selectedGateway
  try {
    const updated = await toggleProvider(gateway)
    screen.providers[gateway] = updated
    renderRightPane(screen)
    setStatus(screen, `${updated.label ?? gateway} is now ${updated.enabled ? "enabled" : "disabled"}`)
  } catch (err) {
    setStatus(screen, `Toggle failed: ${err instanceof Error ? err.message : String(err)}`)
  }
}

function bindKeys(screen: ProviderModelsScreen): void {
  screen.keyboardHandler = (key: any) => {
    if (key.name === "r" || key.name === "R") {
      loadData(screen)
      return
    }
    if (key.name === "q" || key.name === "escape") {
      destroyProviderModelsScreen(screen)
      return
    }
  }
  screen.renderer.keyInput.on("keypress", screen.keyboardHandler)

  screen.leftTabs?.on(TabSelectRenderableEvents.SELECTION_CHANGED, (index: number, option: TabSelectOption) => {
    screen.selectedGateway = option.value
    renderRightPane(screen)
  })

  screen.leftTabs?.on(TabSelectRenderableEvents.ITEM_SELECTED, async (_index: number, option: TabSelectOption) => {
    screen.selectedGateway = option.value
    await toggleSelectedProvider(screen)
  })

  screen.leftTabs?.on(RenderableEvents.FOCUSED, () => {
    setStatus(screen, "←/→: select provider | Enter: toggle enabled | R: refresh | Q: back")
  })
}

function setStatus(screen: ProviderModelsScreen, text: string): void {
  if (!screen.statusText) return
  const base = "R: refresh | Q: back"
  screen.statusText.content = text ? `${text}  |  ${base}` : base
  screen.statusText.fg = screen.theme.textMuted
}

export function destroyProviderModelsScreen(screen: ProviderModelsScreen): void {
  if (screen.keyboardHandler) {
    screen.renderer.keyInput.off("keypress", screen.keyboardHandler)
    screen.keyboardHandler = null
  }
  if (screen.messageTimeout) {
    clearTimeout(screen.messageTimeout)
    screen.messageTimeout = null
  }
  if (screen.parent) {
    screen.parent.parent?.remove(screen.parent.id)
    screen.parent.destroy()
  }
}
