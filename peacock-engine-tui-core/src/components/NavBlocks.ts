import {
  CliRenderer,
  BoxRenderable,
  TextRenderable,
  RGBA,
} from "@opentui/core"
import { getTheme, type ThemeColors } from "../lib/theme.js"

/* ------------------------------------------------------------------ */
/*  Nav definition                                                      */
/* ------------------------------------------------------------------ */

export interface NavAction {
  id: string
  label: string
  shortcut: string
}

export const NAV_ACTIONS: NavAction[] = [
  { id: "main",      label: "Dashboard",        shortcut: "1" },
  { id: "providers", label: "Providers & Models", shortcut: "2" },
  { id: "docs",      label: "Docs",             shortcut: "3" },
  { id: "logs",      label: "Logs",             shortcut: "4" },
  { id: "config",    label: "Settings",         shortcut: "5" },
]

/* ------------------------------------------------------------------ */
/*  Types                                                               */
/* ------------------------------------------------------------------ */

interface NavBlock {
  action: NavAction
  bg: RGBA
  hoverBg: RGBA
  pressBg: RGBA
  box: BoxRenderable
  labelText: TextRenderable
  shortcutText: TextRenderable
}

export interface NavBlocks {
  renderer: CliRenderer
  theme: ThemeColors
  parent: BoxRenderable
  blocks: NavBlock[]
  selectedIndex: number
  activeId: string
  keyboardHandler: ((key: any) => void) | null
  onSwitch: ((id: string) => void) | null
}

/* ------------------------------------------------------------------ */
/*  Factory                                                             */
/* ------------------------------------------------------------------ */

export function createNavBlocks(renderer: CliRenderer): NavBlocks {
  const nav: NavBlocks = {
    renderer,
    theme: getTheme("cyber"),
    parent: new BoxRenderable(renderer, {
      id: "nav-blocks-row",
      zIndex: 100,
      width: "auto",
      height: 5,
      flexDirection: "row",
      alignItems: "center",
      gap: 1,
      padding: 1,
      backgroundColor: getTheme("cyber").bgElevated,
    }),
    blocks: [],
    selectedIndex: 0,
    activeId: "main",
    keyboardHandler: null,
    onSwitch: null,
  }

  buildBlocks(nav)
  bindKeys(nav)
  return nav
}

/* ------------------------------------------------------------------ */
/*  Build                                                               */
/* ------------------------------------------------------------------ */

const COLORS = [
  RGBA.fromInts(60,  120, 180, 255),  // blue
  RGBA.fromInts(120, 180, 60,  255),  // green
  RGBA.fromInts(180, 120, 60,  255),  // orange
  RGBA.fromInts(180, 60,  120, 255),  // pink
  RGBA.fromInts(60,  180, 160, 255),  // teal
]

function buildBlocks(nav: NavBlocks): void {
  const { renderer, theme, parent } = nav

  NAV_ACTIONS.forEach((action, idx) => {
    const base = COLORS[idx % COLORS.length]
    const hover = RGBA.fromValues(
      Math.min(1.0, base.r * 1.3),
      Math.min(1.0, base.g * 1.3),
      Math.min(1.0, base.b * 1.3),
      base.a,
    )
    const press = RGBA.fromValues(base.r * 0.6, base.g * 0.6, base.b * 0.6, base.a)

    const box = new BoxRenderable(renderer, {
      id: `nav-block-${action.id}`,
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
      id: `nav-label-${action.id}`,
      content: action.label,
      fg: theme.textInverse,
      attributes: 1,
      zIndex: 2,
    })
    box.add(label)

    const shortcut = new TextRenderable(renderer, {
      id: `nav-shortcut-${action.id}`,
      content: `[${action.shortcut}]`,
      fg: theme.textMuted,
      zIndex: 2,
    })
    box.add(shortcut)

    parent.add(box)

    nav.blocks.push({
      action,
      bg: base,
      hoverBg: hover,
      pressBg: press,
      box,
      labelText: label,
      shortcutText: shortcut,
    })
  })

  refreshHighlight(nav)
}

/* ------------------------------------------------------------------ */
/*  Highlighting                                                        */
/* ------------------------------------------------------------------ */

export function setActiveNav(nav: NavBlocks, id: string): void {
  nav.activeId = id
  const idx = nav.blocks.findIndex(b => b.action.id === id)
  nav.selectedIndex = idx >= 0 ? idx : 0
  refreshHighlight(nav)
}

function refreshHighlight(nav: NavBlocks): void {
  nav.blocks.forEach((block, idx) => {
    const isActive = block.action.id === nav.activeId
    const isSelected = idx === nav.selectedIndex
    block.box.backgroundColor = isActive
      ? block.hoverBg
      : isSelected
        ? RGBA.fromValues(
            Math.min(1.0, block.bg.r * 1.15),
            Math.min(1.0, block.bg.g * 1.15),
            Math.min(1.0, block.bg.b * 1.15),
            block.bg.a,
          )
        : block.bg
    block.labelText.fg = isActive ? nav.theme.accentGold : nav.theme.textInverse
  })
}

/* ------------------------------------------------------------------ */
/*  Keyboard                                                            */
/* ------------------------------------------------------------------ */

function bindKeys(nav: NavBlocks): void {
  nav.keyboardHandler = (key: any) => {
    if (key.name === "left" || key.name === "h") {
      const next = nav.selectedIndex <= 0
        ? nav.blocks.length - 1
        : nav.selectedIndex - 1
      nav.selectedIndex = next
      refreshHighlight(nav)
    } else if (key.name === "right" || key.name === "l") {
      const next = nav.selectedIndex >= nav.blocks.length - 1
        ? 0
        : nav.selectedIndex + 1
      nav.selectedIndex = next
      refreshHighlight(nav)
    } else if (key.name === "return" || key.name === "space") {
      const block = nav.blocks[nav.selectedIndex]
      if (block && block.action.id !== nav.activeId && nav.onSwitch) {
        nav.onSwitch(block.action.id)
      }
    }

    /* Number shortcuts 1-5 */
    const num = parseInt(key.name, 10)
    if (!isNaN(num) && num >= 1 && num <= nav.blocks.length) {
      const block = nav.blocks[num - 1]
      if (block && block.action.id !== nav.activeId && nav.onSwitch) {
        nav.onSwitch(block.action.id)
      }
    }
  }

  nav.renderer.keyInput.on("keypress", nav.keyboardHandler)
}

/* ------------------------------------------------------------------ */
/*  Cleanup                                                             */
/* ------------------------------------------------------------------ */

export function destroyNavBlocks(nav: NavBlocks): void {
  if (nav.keyboardHandler) {
    nav.renderer.keyInput.off("keypress", nav.keyboardHandler)
    nav.keyboardHandler = null
  }
  if (nav.parent) {
    nav.renderer.root.remove(nav.parent.id)
    nav.parent.destroy()
  }
}
