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

interface DocsScreen {
  renderer: CliRenderer
  theme: ThemeColors
  parent: BoxRenderable
  leftTabs: TabSelectRenderable | null
  scrollBox: ScrollBoxRenderable | null
  contentText: TextRenderable | null
  statusText: TextRenderable | null
  keyboardHandler: ((key: any) => void) | null
  sections: Record<string, string>
  selectedSection: string | null
}

const DOC_SECTIONS: TabSelectOption[] = [
  { name: "Getting Started", value: "getting-started", description: "" },
  { name: "Overview", value: "overview", description: "" },
  { name: "Quickstart", value: "quickstart", description: "" },
  { name: "Models", value: "models", description: "" },
  { name: "Rate Limits", value: "rate-limits", description: "" },
  { name: "API Reference", value: "api-reference", description: "" },
  { name: "Core Features", value: "core-features", description: "" },
  { name: "Text Generation", value: "text-generation", description: "" },
  { name: "Tools & Integrations", value: "tools-integrations", description: "" },
  { name: "Tool Use", value: "tool-use", description: "" },
]

const DOC_CONTENT: Record<string, string> = {
  "getting-started":
    "Peacock Engine TUI Core\n\nA terminal control interface for the Peacock AI orchestration engine.\n\nUse the left tab bar to navigate sections. Press Q to return to the launcher.",
  overview:
    "Overview\n\nPeacock Engine is a multi-provider AI gateway that routes requests across Groq, OpenCode, OpenRouter, Ollama, Hetzner, and Z.ai.\n\nIt provides key rotation, rate-limit tracking, plan execution, and a unified model registry.",
  quickstart:
    "Quickstart\n\n1. Start the engine on port 3099.\n2. Launch this TUI with bun.\n3. Use Providers & Models to enable the providers you have keys for.\n4. Use the chat endpoint or striker batch to send requests.\n5. Monitor rate limits and engine health in real time.",
  models:
    "Models\n\nModels are registered in the engine registry with gateway, tier, RPM/TPM limits, context window, and pricing.\n\nModels can be active, frozen, or deprecated. Disabled providers hide their models from the registry.",
  "rate-limits":
    "Rate Limits\n\nThe engine tracks per-key, per-model RPM/RPD/TPM/TPD consumption in rolling minute and daily windows.\n\nWhen a key is exhausted, the intelligent selector routes to the next healthiest key.",
  "api-reference":
    "API Reference\n\nKey endpoints:\n- GET  /health\n- GET  /v1/admin/system\n- GET  /v1/models\n- GET  /v1/config/providers\n- POST /v1/chat\n- POST /v1/striker/execute\n- GET  /v1/admin/logs\n- GET  /v1/admin/logs/stream",
  "core-features":
    "Core Features\n\n- Multi-provider routing\n- Intelligent key rotation (deck-of-cards + headroom scoring)\n- Global pacing (RPM pacing + TPM backpressure)\n- Plan execution engine for file chunking\n- Failure classification and cooldown policy\n- Provider enable/disable gates",
  "text-generation":
    "Text Generation\n\nSend a prompt to any active model via /v1/chat or the streaming /v1/chat/stream endpoint.\n\nThe engine resolves the provider, selects a key, applies pacing, and returns the completion.",
  "tools-integrations":
    "Tools & Integrations\n\nGroq models support local tool calling through the tool engine. Tools include memory queries, project generation, and UI scaffolding.\n\nMCP servers and custom tool schemas can also be registered.",
  "tool-use":
    "Tool Use\n\nTo use tools, send a request with tool definitions. The model may return tool_calls which the engine executes locally and returns for a final answer.\n\nSee app/providers/groq/tool_schemas.py for available tool schemas.",
}

export function createDocsScreen(renderer: CliRenderer): DocsScreen {
  const screen: DocsScreen = {
    renderer,
    theme: getTheme("cyber"),
    parent: new BoxRenderable(renderer, {
      id: "docs-root",
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
    sections: DOC_CONTENT,
    selectedSection: null,
  }

  buildLayout(screen)
  bindKeys(screen)
  return screen
}

function buildLayout(screen: DocsScreen): void {
  const { renderer, theme, parent } = screen

  const header = new BoxRenderable(renderer, {
    id: "docs-header",
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
    id: "docs-header-text",
    content: "DOCS",
    fg: theme.headerText,
    attributes: 1,
    zIndex: 1,
    flexGrow: 1,
  })
  header.add(headerText)
  parent.add(header)

  const contentRow = new BoxRenderable(renderer, {
    id: "docs-content",
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
    id: "docs-left",
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
    id: "docs-left-label",
    content: "Sections",
    fg: theme.accentCyan,
    attributes: 1,
    zIndex: 1,
  })
  leftBox.add(leftLabel)

  screen.leftTabs = new TabSelectRenderable(renderer, {
    id: "docs-tabs",
    zIndex: 1,
    width: "auto",
    flexGrow: 1,
    options: DOC_SECTIONS,
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
    id: "docs-scroll",
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
    id: "docs-content-text",
    content: "",
    fg: theme.textSecondary,
    zIndex: 1,
    width: "auto",
    height: "auto",
    wrapMode: "word",
  })
  screen.scrollBox.add(screen.contentText)
  contentRow.add(screen.scrollBox)

  const footer = new BoxRenderable(renderer, {
    id: "docs-footer",
    zIndex: 0,
    width: "auto",
    height: 1,
    backgroundColor: theme.bgElevated,
    flexDirection: "row",
    alignItems: "center",
  })
  screen.statusText = new TextRenderable(renderer, {
    id: "docs-status",
    content: "↑/↓: scroll | Q: back",
    fg: theme.textMuted,
    zIndex: 1,
    flexGrow: 1,
  })
  footer.add(screen.statusText)
  parent.add(footer)

  renderer.root.add(parent)
  screen.leftTabs.focus()

  screen.selectedSection = DOC_SECTIONS[0].value
  renderContent(screen)
}

function renderContent(screen: DocsScreen): void {
  if (!screen.contentText || !screen.selectedSection) return
  const text = screen.sections[screen.selectedSection] ?? "Section content not yet written."
  screen.contentText.content = text
  if (screen.scrollBox) {
    screen.scrollBox.scrollTo(0)
  }
}

function bindKeys(screen: DocsScreen): void {
  screen.keyboardHandler = (key: any) => {
    if (key.name === "q" || key.name === "escape") {
      destroyDocsScreen(screen)
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
    screen.selectedSection = option.value
    renderContent(screen)
  })

  screen.leftTabs?.on(RenderableEvents.FOCUSED, () => {
    if (screen.statusText) screen.statusText.content = "Enter: select section | ↑/↓: scroll docs | Q: back"
  })
}

export function destroyDocsScreen(screen: DocsScreen): void {
  if (screen.keyboardHandler) {
    screen.renderer.keyInput.off("keypress", screen.keyboardHandler)
    screen.keyboardHandler = null
  }
  if (screen.parent) {
    screen.renderer.root.remove(screen.parent.id)
    screen.parent.destroy()
  }
}
