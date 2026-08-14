import {
  CliRenderer,
  BoxRenderable,
  TextRenderable,
  SelectRenderable,
  SelectRenderableEvents,
  ScrollBoxRenderable,
  type SelectOption,
} from "@opentui/core"
import { getTheme, type ThemeColors } from "../lib/theme.js"

/* ------------------------------------------------------------------ */
/*  Types                                                               */
/* ------------------------------------------------------------------ */

interface DocsScreen {
  renderer: CliRenderer
  theme: ThemeColors
  parent: BoxRenderable
  leftBox: BoxRenderable
  rightBox: BoxRenderable
  leftSelect: SelectRenderable | null
  scrollBox: ScrollBoxRenderable | null
  contentText: TextRenderable | null
  statusText: TextRenderable | null
  keyboardHandler: ((key: any) => void) | null
  selectedSection: string | null
  docsDir: string
  focusMode: "left" | "right"
}

const DOC_SECTIONS: SelectOption[] = [
  { name: "Getting Started", value: "getting-started.md", description: "" },
  { name: "Overview",        value: "overview.md",        description: "" },
  { name: "Quickstart",      value: "quickstart.md",      description: "" },
  { name: "Models",          value: "models.md",          description: "" },
  { name: "Rate Limits",     value: "rate-limits.md",     description: "" },
  { name: "API Reference",   value: "api-reference.md",   description: "" },
  { name: "Core Features",   value: "core-features.md",   description: "" },
  { name: "Text Generation", value: "text-generation.md", description: "" },
  { name: "Tools & Integrations", value: "tools-integrations.md", description: "" },
  { name: "Tool Use",        value: "tool-use.md",        description: "" },
]

/* ------------------------------------------------------------------ */
/*  Factory                                                             */
/* ------------------------------------------------------------------ */

export function createDocsScreen(renderer: CliRenderer, contentParent: BoxRenderable, docsDir = "./docs"): DocsScreen {
  const screen: DocsScreen = {
    renderer,
    theme: getTheme("cyber"),
    parent: new BoxRenderable(renderer, {
      id: "docs-content",
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
      id: "docs-left-box",
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
      id: "docs-right-box",
      zIndex: 0,
      width: "auto",
      height: "auto",
      flexGrow: 1,
      flexShrink: 1,
      flexDirection: "column",
      gap: 1,
    }),
    leftSelect: null,
    scrollBox: null,
    contentText: null,
    statusText: null,
    keyboardHandler: null,
    selectedSection: null,
    docsDir,
    focusMode: "left",
  }

  buildLayout(screen)
  loadSection(screen, DOC_SECTIONS[0].value)
  bindKeys(screen)
  contentParent.add(screen.parent)
  return screen
}

/* ------------------------------------------------------------------ */
/*  Layout                                                              */
/* ------------------------------------------------------------------ */

function buildLayout(screen: DocsScreen): void {
  const { renderer, theme, parent, leftBox, rightBox } = screen

  /* Left panel: section list */
  const leftTitle = new TextRenderable(renderer, {
    id: "docs-left-title",
    content: " Sections ",
    fg: theme.accentCyan,
    attributes: 1,
    zIndex: 1,
  })
  leftBox.add(leftTitle)

  screen.leftSelect = new SelectRenderable(renderer, {
    id: "docs-select",
    zIndex: 1,
    width: "auto",
    height: "auto",
    flexGrow: 1,
    options: DOC_SECTIONS,
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

  /* Right panel: scrollable content */
  const rightTitle = new TextRenderable(renderer, {
    id: "docs-right-title",
    content: " Content ",
    fg: theme.accentCyan,
    attributes: 1,
    zIndex: 1,
  })
  rightBox.add(rightTitle)

  screen.scrollBox = new ScrollBoxRenderable(renderer, {
    id: "docs-scroll",
    zIndex: 0,
    width: "auto",
    height: "auto",
    flexGrow: 1,
    borderStyle: "single",
    borderColor: theme.borderDefault,
    border: true,
    backgroundColor: theme.bgRecessed,
  })

  screen.contentText = new TextRenderable(renderer, {
    id: "docs-content-text",
    content: "Loading...",
    fg: theme.textSecondary,
    zIndex: 1,
    width: "auto",
    height: "auto",
    wrapMode: "word",
  })
  screen.scrollBox.add(screen.contentText)
  rightBox.add(screen.scrollBox)
  parent.add(rightBox)

  /* Footer */
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
    content: "Tab: switch pane | ↑/↓: navigate | Enter: select | Q: back",
    fg: theme.textMuted,
    zIndex: 1,
    flexGrow: 1,
  })
  footer.add(screen.statusText)
  parent.add(footer)
}

/* ------------------------------------------------------------------ */
/*  Content loading (markdown files)                                    */
/* ------------------------------------------------------------------ */

async function loadSection(screen: DocsScreen, filename: string): Promise<void> {
  if (!screen.contentText || !screen.scrollBox) return
  screen.contentText.content = "Loading..."
  screen.selectedSection = filename

  try {
    const res = await fetch(`${screen.docsDir}/${filename}`)
    if (res.ok) {
      const text = await res.text()
      screen.contentText.content = text
      screen.contentText.content = text
    } else {
      screen.contentText.content = `Content not yet written: ${filename}\n\n(Place a ${filename} file in the docs directory)`
    }
  } catch {
    screen.contentText.content = `Content not yet written: ${filename}\n\n(Place a ${filename} file in the docs directory)`
  }
}

/* ------------------------------------------------------------------ */
/*  Keyboard                                                            */
/* ------------------------------------------------------------------ */

function bindKeys(screen: DocsScreen): void {
  screen.keyboardHandler = (key: any) => {
    if (key.name === "q" || key.name === "escape") {
      destroyDocsScreen(screen)
      return
    }

    /* Tab switches focus between left (sections) and right (scrolling) */
    if (key.name === "tab") {
      screen.focusMode = screen.focusMode === "left" ? "right" : "left"
      if (screen.focusMode === "left" && screen.leftSelect) {
        screen.leftSelect.focus()
        screen.leftBox.focus()
      }
      return
    }

    /* Left pane: section selection */
    if (screen.focusMode === "left" && screen.leftSelect) {
      if (key.name === "return" || key.name === "space") {
        const opt = screen.leftSelect.getSelectedOption()
        if (opt) loadSection(screen, opt.value)
      }
      /* Let the SelectRenderable handle its own arrow keys */
      return
    }

    /* Right pane: scrolling */
    if (screen.focusMode === "right" && screen.scrollBox) {
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
  }

  screen.renderer.keyInput.on("keypress", screen.keyboardHandler)

  screen.leftSelect?.on(SelectRenderableEvents.ITEM_SELECTED, (_index: number, option: SelectOption) => {
    loadSection(screen, option.value)
  })

  screen.leftSelect?.on(SelectRenderableEvents.SELECTION_CHANGED, (_index: number, option: SelectOption) => {
    screen.selectedSection = option.value
  })
}

/* ------------------------------------------------------------------ */
/*  Cleanup                                                             */
/* ------------------------------------------------------------------ */

export function destroyDocsScreen(screen: DocsScreen): void {
  if (screen.keyboardHandler) {
    screen.renderer.keyInput.off("keypress", screen.keyboardHandler)
    screen.keyboardHandler = null
  }
  if (screen.parent) {
    screen.parent.parent?.remove(screen.parent.id)
    screen.parent.destroy()
  }
}
