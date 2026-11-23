import {
  CliRenderer,
  BoxRenderable,
  TextRenderable,
  SelectRenderable,
  SelectRenderableEvents,
  RGBA,
  type SelectOption,
} from "@opentui/core"
import { getTheme, type ThemeColors } from "../lib/theme.js"
import {
  fetchModels,
  fetchProviders,
  toggleProvider,
  type ProviderState,
  type ModelInfo,
} from "../lib/api.js"

/* ------------------------------------------------------------------ */
/*  Types                                                               */
/* ------------------------------------------------------------------ */

interface ProviderModelsScreen {
  renderer: CliRenderer
  theme: ThemeColors
  parent: BoxRenderable
  leftBox: BoxRenderable
  rightBox: BoxRenderable
  leftSelect: SelectRenderable | null
  rightSelect: SelectRenderable | null
  modelCardBox: BoxRenderable | null
  modelCardTexts: TextRenderable[]
  statusText: TextRenderable | null
  providers: Record<string, ProviderState>
  modelsByGateway: Record<string, ModelInfo[]>
  selectedGateway: string | null
  selectedModelId: string | null
  keyboardHandler: ((key: any) => void) | null
  focusIndex: number
  message: string | null
  messageTimeout: ReturnType<typeof setTimeout> | null
}

/* ------------------------------------------------------------------ */
/*  Factory                                                             */
/* ------------------------------------------------------------------ */

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
      flexDirection: "row",
      padding: 1,
      gap: 1,
      backgroundColor: getTheme("cyber").bgBase,
    }),
    leftBox: new BoxRenderable(renderer, {
      id: "provider-models-left-box",
      zIndex: 0,
      width: 24,
      height: "auto",
      flexGrow: 0,
      flexShrink: 0,
      flexDirection: "column",
      borderStyle: "single",
      borderColor: getTheme("cyber").borderDefault,
      focusedBorderColor: getTheme("cyber").accentCyan,
      border: true,
      backgroundColor: getTheme("cyber").bgRecessed,
    }),
    rightBox: new BoxRenderable(renderer, {
      id: "provider-models-right-box",
      zIndex: 0,
      width: "auto",
      height: "auto",
      flexGrow: 1,
      flexShrink: 1,
      flexDirection: "column",
      gap: 1,
    }),
    leftSelect: null,
    rightSelect: null,
    modelCardBox: null,
    modelCardTexts: [],
    statusText: null,
    providers: {},
    modelsByGateway: {},
    selectedGateway: null,
    selectedModelId: null,
    keyboardHandler: null,
    focusIndex: 0,
    message: null,
    messageTimeout: null,
  }

  buildLayout(screen)
  loadData(screen)
  bindKeys(screen)
  contentParent.add(screen.parent)
  return screen
}

/* ------------------------------------------------------------------ */
/*  Layout                                                              */
/* ------------------------------------------------------------------ */

function buildLayout(screen: ProviderModelsScreen): void {
  const { renderer, theme, parent, leftBox, rightBox } = screen

  /* ---- Left: provider list ---------------------------------------- */
  const leftTitle = new TextRenderable(renderer, {
    id: "providers-title",
    content: " Providers ",
    fg: theme.accentCyan,
    attributes: 1,
    zIndex: 1,
  })
  leftBox.add(leftTitle)

  screen.leftSelect = new SelectRenderable(renderer, {
    id: "providers-select",
    zIndex: 1,
    width: "auto",
    height: "auto",
    flexGrow: 1,
    options: [],
    backgroundColor: theme.bgRecessed,
    focusedBackgroundColor: theme.bgElevated,
    textColor: theme.textSecondary,
    focusedTextColor: theme.textPrimary,
    selectedBackgroundColor: theme.accentCyanDim,
    selectedTextColor: theme.textInverse,
    descriptionColor: theme.textMuted,
    selectedDescriptionColor: theme.textMuted,
    showScrollIndicator: true,
    wrapSelection: true,
    showDescription: false,
  })
  leftBox.add(screen.leftSelect)

  parent.add(leftBox)

  /* ---- Right top: model list -------------------------------------- */
  const modelsBox = new BoxRenderable(renderer, {
    id: "models-list-box",
    zIndex: 0,
    width: "auto",
    height: "auto",
    flexGrow: 1,
    flexShrink: 1,
    flexDirection: "column",
    borderStyle: "single",
    borderColor: theme.borderDefault,
    focusedBorderColor: getTheme("cyber").accentCyan,
    border: true,
    backgroundColor: theme.bgRecessed,
  })

  const modelsTitle = new TextRenderable(renderer, {
    id: "models-title",
    content: " Models ",
    fg: theme.accentCyan,
    attributes: 1,
    zIndex: 1,
  })
  modelsBox.add(modelsTitle)

  screen.rightSelect = new SelectRenderable(renderer, {
    id: "models-select",
    zIndex: 1,
    width: "auto",
    height: "auto",
    flexGrow: 1,
    options: [],
    backgroundColor: theme.bgRecessed,
    focusedBackgroundColor: theme.bgElevated,
    textColor: theme.textSecondary,
    focusedTextColor: theme.textPrimary,
    selectedBackgroundColor: theme.accentCyanDim,
    selectedTextColor: theme.textInverse,
    descriptionColor: theme.textMuted,
    selectedDescriptionColor: theme.textMuted,
    showScrollIndicator: true,
    wrapSelection: true,
    showDescription: true,
  })
  modelsBox.add(screen.rightSelect)
  rightBox.add(modelsBox)

  /* ---- Right bottom: model card ----------------------------------- */
  screen.modelCardBox = new BoxRenderable(renderer, {
    id: "model-card-box",
    zIndex: 0,
    width: "auto",
    height: 8,
    flexGrow: 0,
    flexShrink: 0,
    flexDirection: "column",
    gap: 0,
    padding: 1,
    borderStyle: "single",
    borderColor: theme.borderDefault,
    border: true,
    backgroundColor: theme.bgSurface,
  })

  const cardTitle = new TextRenderable(renderer, {
    id: "model-card-title",
    content: " Select a model to view details ",
    fg: theme.textMuted,
    attributes: 1,
    zIndex: 1,
  })
  screen.modelCardBox.add(cardTitle)
  screen.modelCardTexts.push(cardTitle)

  rightBox.add(screen.modelCardBox)
  parent.add(rightBox)

  /* ---- Footer ------------------------------------------------------ */
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
    content: "Tab: switch pane | ↑/↓: navigate | Enter: toggle | R: refresh",
    fg: theme.textMuted,
    zIndex: 1,
    flexGrow: 1,
  })
  footer.add(screen.statusText)
  parent.add(footer)
}

/* ------------------------------------------------------------------ */
/*  Focus management                                                    */
/* ------------------------------------------------------------------ */

function updateFocus(screen: ProviderModelsScreen): void {
  if (screen.leftSelect) {
    screen.leftSelect.blur()
  }
  if (screen.rightSelect) {
    screen.rightSelect.blur()
  }
  if (screen.leftSelect) {
    screen.leftSelect.blur()
  }
  screen.leftBox.blur()
  screen.rightBox.blur()

  if (screen.focusIndex === 0 && screen.leftSelect) {
    screen.leftSelect.focus()
    screen.leftBox.focus()
  } else if (screen.focusIndex === 1 && screen.rightSelect) {
    screen.rightSelect.focus()
    screen.rightBox.focus()
  }
}

/* ------------------------------------------------------------------ */
/*  Data loading                                                        */
/* ------------------------------------------------------------------ */

async function loadData(screen: ProviderModelsScreen): Promise<void> {
  try {
    const [modelsData, providersData] = await Promise.all([
      fetchModels(),
      fetchProviders(),
    ])

    screen.modelsByGateway = modelsData.by_gateway ?? {}
    screen.providers = providersData ?? {}

    const providerOptions: SelectOption[] = Object.entries(providersData)
      .map(([gateway, state]) => ({
        name: formatProviderName(gateway, state.label ?? gateway),
        value: gateway,
        description: state.enabled ? "enabled" : "disabled",
      }))

    if (screen.leftSelect) {
      screen.leftSelect.options = providerOptions
      if (providerOptions.length > 0 && !screen.selectedGateway) {
        screen.selectedGateway = providerOptions[0].value
        screen.leftSelect.setSelectedIndex(0)
        loadModelsForGateway(screen, providerOptions[0].value)
      }
    }

    setStatus(screen, `Loaded ${Object.keys(providersData).length} providers, ${modelsData.count} models`)
  } catch (err) {
    setStatus(screen, `Error: ${err instanceof Error ? err.message : String(err)}`)
  }
}

function loadModelsForGateway(screen: ProviderModelsScreen, gateway: string): void {
  const models = screen.modelsByGateway[gateway] ?? []
  const options: SelectOption[] = models.map((m) => ({
    name: m.id.replace(/^models\//, "").substring(0, 40),
    value: m.id,
    description: `${m.status} | ctx:${m.context_window}`,
  }))

  if (screen.rightSelect) {
    screen.rightSelect.options = options
    if (options.length > 0) {
      screen.rightSelect.setSelectedIndex(0)
      screen.selectedModelId = options[0].value
      renderModelCard(screen, models[0])
    } else {
      screen.selectedModelId = null
      clearModelCard(screen)
    }
  }
}

/* ------------------------------------------------------------------ */
/*  Model card — live-state-demo style stat blocks                      */
/* ------------------------------------------------------------------ */

const STATUS_COLORS: Record<string, RGBA> = {
  active:    RGBA.fromInts(144, 238, 144, 255), // green
  frozen:    RGBA.fromInts(255, 170, 0, 255),   // orange
  deprecated: RGBA.fromInts(255, 50, 102, 255),  // red
}

function renderModelCard(screen: ProviderModelsScreen, model: ModelInfo | null): void {
  if (!screen.modelCardBox) return

  /* remove old text nodes */
  screen.modelCardTexts.forEach((t) => {
    screen.modelCardBox?.remove(t.id)
  })
  screen.modelCardTexts = []

  if (!model) {
    const empty = new TextRenderable(screen.renderer, {
      id: "model-card-empty",
      content: " No model selected ",
      fg: screen.theme.textMuted,
      zIndex: 1,
    })
    screen.modelCardBox.add(empty)
    screen.modelCardTexts.push(empty)
    return
  }

  const statusColor = STATUS_COLORS[model.status] ?? screen.theme.textMuted
  const isFrozen = model.status === "frozen"
  const isDeprecated = model.status === "deprecated"

  /* Title row */
  const title = new TextRenderable(screen.renderer, {
    id: "model-card-title",
    content: ` ${model.id.replace(/^models\//, "")} `,
    fg: screen.theme.accentGold,
    attributes: 1,
    zIndex: 1,
  })
  screen.modelCardBox.add(title)
  screen.modelCardTexts.push(title)

  /* Row 1: gateway + tier */
  const row1 = new TextRenderable(screen.renderer, {
    id: "model-card-row1",
    content: `  Gateway: ${model.gateway}   Tier: ${model.tier}  `,
    fg: screen.theme.textSecondary,
    zIndex: 1,
  })
  screen.modelCardBox.add(row1)
  screen.modelCardTexts.push(row1)

  /* Row 2: RPM + TPM + RPD */
  const rpmStr = model.rpm ?? "N/A"
  const tpmStr = model.tpm ?? "N/A"
  const rpdStr = model.rpd ?? "N/A"
  const row2 = new TextRenderable(screen.renderer, {
    id: "model-card-row2",
    content: `  RPM: ${rpmStr}   TPM: ${tpmStr}   RPD: ${rpdStr}  `,
    fg: screen.theme.textSecondary,
    zIndex: 1,
  })
  screen.modelCardBox.add(row2)
  screen.modelCardTexts.push(row2)

  /* Row 3: context window + status indicator */
  const ctxStr = model.context_window ? `${model.context_window.toLocaleString()} tokens` : "N/A"
  const statusInd = isFrozen
    ? `[◐ ${model.status.toUpperCase()}]`
    : isDeprecated
      ? `[○ ${model.status.toUpperCase()}]`
      : `[● ${model.status.toUpperCase()}]`
  const row3 = new TextRenderable(screen.renderer, {
    id: "model-card-row3",
    content: `  Context: ${ctxStr}   Status: ${statusInd}  `,
    fg: statusColor,
    zIndex: 1,
  })
  screen.modelCardBox.add(row3)
  screen.modelCardTexts.push(row3)

  /* Row 4: pricing */
  const hasPrice = model.input_price_1m > 0 || model.output_price_1m > 0
  const row4 = new TextRenderable(screen.renderer, {
    id: "model-card-row4",
    content: hasPrice
      ? `  Price: $${model.input_price_1m}/1M in $${model.output_price_1m}/1M out  `
      : "  No pricing data  ",
    fg: hasPrice ? screen.theme.textSecondary : screen.theme.textMuted,
    zIndex: 1,
  })
  screen.modelCardBox.add(row4)
  screen.modelCardTexts.push(row4)

  /* Row 5: tools + base_url */
  const toolsStr = model.tools_supported ? "tools" : "no tools"
  const urlStr = model.base_url ? model.base_url.replace(/^https?:\/\//, "") : "N/A"
  const row5 = new TextRenderable(screen.renderer, {
    id: "model-card-row5",
    content: `  Tools: ${toolsStr}   URL: ${urlStr}  `,
    fg: screen.theme.textMuted,
    zIndex: 1,
  })
  screen.modelCardBox.add(row5)
  screen.modelCardTexts.push(row5)
}

function clearModelCard(screen: ProviderModelsScreen): void {
  screen.modelCardTexts.forEach((t) => {
    screen.modelCardBox?.remove(t.id)
  })
  screen.modelCardTexts = []
  const empty = new TextRenderable(screen.renderer, {
    id: "model-card-empty",
    content: " No models for this provider ",
    fg: screen.theme.textMuted,
    zIndex: 1,
  })
  screen.modelCardBox?.add(empty)
  screen.modelCardTexts.push(empty)
}

/* ------------------------------------------------------------------ */
/*  Keyboard                                                            */
/* ------------------------------------------------------------------ */

function bindKeys(screen: ProviderModelsScreen): void {
  screen.keyboardHandler = (key: any) => {
    if (key.name === "tab") {
      screen.focusIndex = (screen.focusIndex + 1) % 2
      updateFocus(screen)
      return
    }
    if (key.name === "r" || key.name === "R") {
      loadData(screen)
      return
    }
    if (key.name === "q" || key.name === "escape") {
      destroyProviderModelsScreen(screen)
      return
    }

    /* Let the focused SelectRenderable handle arrow keys via its own
       internal key handler. We only intercept Enter for actions. */
    if (key.name === "return" || key.name === "space") {
      if (screen.focusIndex === 0 && screen.leftSelect) {
        const opt = screen.leftSelect.getSelectedOption()
        if (opt) {
          screen.selectedGateway = opt.value
          loadModelsForGateway(screen, opt.value)
        }
      } else if (screen.focusIndex === 1 && screen.rightSelect) {
        const opt = screen.rightSelect.getSelectedOption()
        if (opt) {
          toggleSelectedModel(screen, opt.value)
        }
      }
    }
  }
  screen.renderer.keyInput.on("keypress", screen.keyboardHandler)

  /* Selection change listeners */
  screen.leftSelect?.on(SelectRenderableEvents.SELECTION_CHANGED, (_idx: number, option: SelectOption) => {
    screen.selectedGateway = option.value
    loadModelsForGateway(screen, option.value)
  })

  screen.rightSelect?.on(SelectRenderableEvents.SELECTION_CHANGED, (_idx: number, option: SelectOption) => {
    screen.selectedModelId = option.value
    const model = screen.modelsByGateway[screen.selectedGateway ?? ""]?.find(
      (m) => m.id === option.value,
    )
    renderModelCard(screen, model ?? null)
  })

  screen.leftSelect?.on(SelectRenderableEvents.ITEM_SELECTED, (_idx: number, option: SelectOption) => {
    screen.selectedGateway = option.value
    loadModelsForGateway(screen, option.value)
  })
}

/* ------------------------------------------------------------------ */
/*  Actions                                                             */
/* ------------------------------------------------------------------ */

async function toggleSelectedModel(screen: ProviderModelsScreen, modelId: string): Promise<void> {
  const gateway = screen.selectedGateway
  if (!gateway) return

  setMessage(screen, "Toggling...")
  try {
    const result = await toggleProvider(gateway)
    setMessage(screen, result.enabled ? "Provider enabled" : "Provider disabled")
    /* Refresh data to show updated state */
    await loadData(screen)
  } catch (err) {
    setMessage(screen, `Error: ${err instanceof Error ? err.message : String(err)}`)
  }
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                             */
/* ------------------------------------------------------------------ */

function formatProviderName(gateway: string, label: string): string {
  return `${label} (${gateway})`.substring(0, 22)
}

function setStatus(screen: ProviderModelsScreen, text: string): void {
  if (!screen.statusText) return
  screen.statusText.content = text
}

function setMessage(screen: ProviderModelsScreen, text: string): void {
  if (screen.messageTimeout) clearTimeout(screen.messageTimeout)
  screen.message = text
  setStatus(screen, text)
  screen.messageTimeout = setTimeout(() => {
    screen.message = null
    setStatus(screen, "Tab: switch pane | ↑/↓: navigate | Enter: toggle | R: refresh")
  }, 3000)
}

/* ------------------------------------------------------------------ */
/*  Cleanup                                                             */
/* ------------------------------------------------------------------ */

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
