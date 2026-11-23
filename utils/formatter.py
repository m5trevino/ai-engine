"""
PEACOCK ENGINE - CLI Formatter
Fancy output formatting with gateway-specific borders and colors.
"""

import os
import random
import time
from typing import Optional, Dict, Tuple, List
from rich.console import Console
from rich.text import Text
from rich.panel import Panel

# Initialize Rich Console
console = Console()

# ANSI Color Codes
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    
    # Foreground colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    # Bright foreground
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"
    
    # Background colors
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"


# Border styles by gateway
GATEWAY_BORDERS = {
    "groq": {
        "success": ("╔══════════•⊱✦⊰•══════════╗", "╚══════════•⊱✦⊰•══════════╝"),
        "error": ("┏━━━━━━━━━☠━━━━━━━━━┓", "┗━━━━━━━━━☠━━━━━━━━━┛"),
        "info": ("┌───────────────────┐", "└───────────────────┘"),
        "color": Colors.BRIGHT_CYAN
    },
    "google": {
        "success": ("╭━─━─━─≪✠≫─━─━─━╮", "╰━─━─━─≪✠≫─━─━─━╯"),
        "error": ("┏━─━─━─☠─━─━─━┓", "┗━─━─━─☠─━─━─━┛"),
        "info": ("┌─────────────┐", "└─────────────┘"),
        "color": Colors.BRIGHT_BLUE
    },
    "deepseek": {
        "success": ("┎━─━─━─━─━─━─━─━─━┒", "┖━─━─━─━─━─━─━─━─━┚"),
        "error": ("┏━─━─━─☠━─━─━─━┓", "┗━─━─━─☠━─━─━─━┛"),
        "info": ("┌─────────────────┐", "└─────────────────┘"),
        "color": Colors.BRIGHT_GREEN
    },
    "mistral": {
        "success": ("┍──━──━──┙◆┕──━──━──┑", "┕──━──━──┑◆┍──━──━──┙"),
        "error": ("┍──━──☠──━──┑", "┕──━──☠──━──┙"),
        "info": ("┌───────────────┐", "└───────────────┘"),
        "color": Colors.BRIGHT_MAGENTA
    },
    "default": {
        "success": ("╔═══━━━─── • ───━━━═══╗", "╚═══━━━─── • ───━━━═══╝"),
        "error": ("┏━━━━━━━━━☠━━━━━━━━━┓", "┗━━━━━━━━━☠━━━━━━━━━┛"),
        "info": ("┌─────────────────────┐", "└─────────────────────┘"),
        "color": Colors.BRIGHT_WHITE
    }
}

# ARSENAL ASCII ART BLOCKS
ARSENAL_BLOCKS = {
    "groq": [
        "  ███████ ████████   ██████   ████████",
        " ███░░███░░███░░███ ███░░███ ███░░███ ",
        "░███ ░███ ░███ ░░░ ░███ ░███░███ ░███ ",
        "░███ ░███ ░███     ░███ ░███░███ ░███ ",
        "░░███████ █████    ░░██████ ░░███████ ",
        " ░░░░░███░░░░░      ░░░░░░   ░░░░░███ ",
        " ███ ░███                        ░███ ",
        "░░██████                         █████"
    ],
    "google": [
        "  #####   #####   #####   ##### ####     ######  ",
        " ###  ## ###  ## ###  ## ###  ## ###     ###  ## ",
        " ###     ###  ## ###  ## ###     ###     ###     ",
        " ### ### ###  ## ###  ## ### ### ###     #####   ",
        " ###  ## ###  ## ###  ## ###  ## ###     ###     ",
        " ###  ## ###  ## ###  ## ###  ## ###   # ###  ## ",
        "  #####   #####   #####   #####  ####### ######  "
    ],
    "deepseek": [
        " ######  ####### ####### ######   #####  ####### ####### #   # ",
        " #     # #       #       #     # #     # #       #       #  #  ",
        " #     # #       #       #     # #       #       #       # #   ",
        " #     # #####   #####   ######   #####  #####   #####   ##    ",
        " #     # #       #       #             # #       #       # #   ",
        " #     # #       #       #       #     # #       #       #  #  ",
        " ######  ####### ####### #        #####  ####### ####### #   # "
    ],
    "mistral": [
        " #     # ###  #####  ####### ######     #    #      ",
        " ##   ##  #  #     #    #    #     #   # #   #      ",
        " # # # #  #  #          #    #     #  #   #  #      ",
        " #  #  #  #   #####     #    ######  #     # #      ",
        " #     #  #        #    #    #   #   ####### #      ",
        " #     #  #  #     #    #    #    #  #     # #      ",
        " #     # ###  #####     #    #     # #     # #######"
    ]
}

class CLIFormatter:
    """Format CLI output with fancy borders and colors."""
    
    @staticmethod
    def get_gateway_style(gateway: str) -> Dict:
        """Get border style for a gateway."""
        return GATEWAY_BORDERS.get(gateway.lower(), GATEWAY_BORDERS["default"])
    
    @staticmethod
    def strike_success(gateway: str, account: str, model: str, 
                       prompt_tokens: int = 0, completion_tokens: int = 0,
                       duration: Optional[float] = None, format_mode: Optional[str] = None,
                       temp: Optional[float] = None, tag: Optional[str] = None, cost: float = 0.0,
                       rescue_note: Optional[str] = None, meter: Optional[str] = None):
        """Print a successful strike with the NEBULA-SUCCESS industrial frame."""
        style = CLIFormatter.get_gateway_style(gateway)
        gw_color = style["color"].replace("\033[", "").replace("m", "") # Strip to basic for rich if needed
        # Mapping ANSI to Rich colors roughly
        color_map = {"96": "cyan", "94": "blue", "92": "green", "95": "magenta", "97": "white"}
        base_color = color_map.get(gw_color, "white")
        
        total_tokens = prompt_tokens + completion_tokens
        duration_str = f"{duration:.2f}s" if duration else "N/A"
        format_str = format_mode or "text"
        tag_str = tag if tag else "PEA-XXXX"
        
        # NEBULA-SUCCESS Frame with Gradient Logic
        # 1. ░█▀▀░▀█▀░█▀▄░▀█▀░█░█░█▀▀
        # 2. ░▀▀█░░█░░█▀▄░░█░░█▀▄░█▀▀
        # 3. ░▀▀▀░░▀░░▀░▀░▀▀▀░▀░▀░▀▀▀
        
        success_block = [
            f"  ░█▀▀░▀█▀░█▀▄░▀█▀░█░█░█▀▀     ___ _   _  ___ ___ ___  ___ ___ ",
            f"  ░▀▀█░░█░░█▀▄░░█░░█▀▄░█▀▀    / __| | | |/ __/ __/ _ \\/ __/ __|",
            f"  ░▀▀▀░░▀░░▀░▀░▀▀▀░▀░▀░▀▀▀    \\__ \\ |_| | (_| (_|  __/\\__ \\__ \\",
            f"                                      |___/\\__,_|\\___\\___\\___||___/___/"
        ]

        # Build Frame
        console.print()
        console.print(Text(".:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::.", style=f"dim {base_color}"))
        console.print(Text(f":: [ SUCCESS ] :::::::::::::::::::::::::::::::::::::::::::::::: [{tag_str}] ::", style=f"bold {base_color}"))
        console.print(Text(":::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::", style=f"dim {base_color}"))
        
        # Success Alpha Block (Greenish Gradient)
        colors = ["green3", "spring_green3", "spring_green2", "spring_green1"]
        for i, line in enumerate(success_block):
            console.print(Text(line, style=colors[i % len(colors)]))
            
        console.print(Text(":::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::", style=f"dim {base_color}"))
        console.print(Text(f"  ::  GATEWAY : {gateway.upper():<58} ::", style=f"bold {base_color}"))
        console.print(Text(f"  ::  MODEL   : {model[:59]:<58} ::", style=f"bold {base_color}"))
        
        stats_line = f"TOKENS  : {prompt_tokens} in / {completion_tokens} out ({total_tokens} total) | DURATION: {duration_str}"
        console.print(Text(f"  ::  {stats_line:<70} ::", style=f"{base_color}"))
        
        if meter:
             console.print(Text(f"  ::  METER   : {meter:<58} ::", style="dim cyan"))
        if rescue_note:
             console.print(Text(f"  ::  RESCUE  : {rescue_note:<58} ::", style="bold yellow"))
             
        console.print(Text("':::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::'", style=f"dim {base_color}"))
        console.print()

    @staticmethod
    def strike_error(gateway: str, account: str, error: str, model: Optional[str] = None, temp: Optional[float] = None, tag: Optional[str] = None):
        """Print a failed strike with the VAULT-FAILURE industrial frame."""
        tag_str = tag if tag else "PEA-XXXX"
        
        # VAULT-FAILURE Frame with Gradient Logic
        error_block = [
            f"  ░█▀▀░▀█▀░█▀▄░▀█▀░█░█░█▀▀      ░█▀▀░█▀█░▀█▀░█░░░█▀▀░█▀▄",
            f"  ░▀▀█░░█░░█▀▄░░█░░█▀▄░█▀▀      ░█▀▀░█▀█░░█░░█░░░█▀▀░█░█",
            f"  ░▀▀▀░░▀░░▀░▀░▀▀▀░▀░▀░▀▀▀      ░▀░░░▀░▀░▀▀▀░▀▀▀░▀▀▀░▀▀░"
        ]

        console.print()
        console.print(Text("/#############################################################################\\", style="bold red"))
        console.print(Text(f"|# [!] CRITICAL STRIKE FAILURE                                   [{tag_str}]  #|", style="bold white on red"))
        console.print(Text("|#############################################################################|", style="bold red"))
        console.print(Text("|                                                                             |", style="red"))
        
        # Error Block (Reddish Gradient)
        colors = ["red", "bright_red", "orange_red1"]
        for i, line in enumerate(error_block):
            console.print(Text("|" + line.ljust(77) + "|", style=colors[i % len(colors)]))
            
        console.print(Text("|                                                                             |", style="red"))
        console.print(Text("|#############################################################################|", style="bold red"))
        console.print(Text(f"|  GATEWAY :: {gateway.upper():<64} |", style="bold white"))
        console.print(Text(f"|  ERROR   :: {account:<66} |", style="yellow"))
        
        # Handle multi-line error details
        detail = error
        if len(detail) > 63:
            detail = detail[:60] + "..."
        console.print(Text(f"|  DETAIL  :: {detail:<64} |", style="dim white"))
        
        if model:
            console.print(Text(f"|  MODEL   :: {model:<64} |", style="dim cyan"))
            
        console.print(Text("\\#############################################################################/", style="bold red"))
        console.print()
    
    @staticmethod
    def debug_request(model: str, gateway: str, endpoint: str = "/v1/strike"):
        """Print debug info about incoming request. (Now SILENT by default unless explicitly asked)"""
        # The user requested this to be removed. We'll make it completely silent.
        pass
    
    @staticmethod
    def display_key_arsenal(gateway: str, keys: List[any]):
        """Render a high-fidelity 'Arsenal' key display for a gateway."""
        style = CLIFormatter.get_gateway_style(gateway)
        gw_color = style["color"].replace("\033[", "").replace("m", "") 
        color_map = {"96": "cyan", "94": "blue", "92": "green", "95": "magenta", "97": "white"}
        base_color = color_map.get(gw_color, "white")
        
        # 1. Header ASCII (Arsenal Block)
        block = ARSENAL_BLOCKS.get(gateway.lower(), [])
        if block:
            console.print()
            # Success Alpha Block Gradient (Matching gateway)
            step = max(1, len(block) // 3)
            # Use gateway color for most, but keep it punchy
            for i, line in enumerate(block):
                console.print(Text(line, style=f"bold {base_color}"))
        
        # 2. Key Table (Hardened Box Drawing)
        if not keys:
            console.print(Text(f"    [!] NO {gateway.upper()} KEYS ENROLLED.", style="bold red"))
            return

        console.print(Text("    ╔═══╦══════════════╦═════════════╗", style=f"dim {base_color}"))
        
        for i, asset in enumerate(keys):
            idx = str(i + 1).zfill(1)
            account = asset.account[:12]
            masked = f"{asset.key[:8]}..."
            
            console.print(Text(f"    ║ {idx:>1} ║ {account:<12} ║ {masked:<11} ║", style=f"bold {base_color}"))
            
            if i < len(keys) - 1:
                # Spacer
                if (i + 1) % 3 == 0:
                     console.print(Text("    ║═══╣══════════════╣═════════════║", style=f"dim {base_color}"))
                else:
                     console.print(Text("    ╠═══╬══════════════╬═════════════╣", style=f"dim {base_color}"))
        
        console.print(Text("    ╚═══╩══════════════╩═════════════╝", style=f"dim {base_color}"))
        console.print()

    @staticmethod
    def key_usage_header(gateway: str):
        """Print header for key usage display."""
        style = CLIFormatter.get_gateway_style(gateway)
        color = style["color"]
        
        print(f"\n{color}═══ {gateway.upper()} KEYS {'═' * (40 - len(gateway))}{Colors.RESET}")
        print(f"{color}Account{'':<20} Last Used{'':<20} Count{'':>10} Tokens{Colors.RESET}")
        print(f"{color}{'─' * 80}{Colors.RESET}")
    
    @staticmethod
    def key_usage_row(account: str, last_used: Optional[str], count: int, tokens: int, gateway: str):
        """Print a key usage row."""
        style = CLIFormatter.get_gateway_style(gateway)
        color = style["color"]
        
        last_used_str = last_used if last_used else "Never"
        if len(last_used_str) > 19:
            last_used_str = last_used_str[:16] + "..."
        
        print(f"{color}│{Colors.RESET} {Colors.YELLOW}{account:<20}{Colors.RESET} {last_used_str:<20} {count:>10} {tokens:>10,}")
    
    @staticmethod
    def section_header(title: str):
        """Print a section header."""
        width = 60
        padding = (width - len(title) - 4) // 2
        print(f"\n{Colors.BOLD}{Colors.BRIGHT_CYAN}{'═' * padding} ✦ {title} ✦ {'═' * padding}{Colors.RESET}\n")
    
    @staticmethod
    def info(message: str):
        """Print an info message."""
        print(f"{Colors.BLUE}[ℹ]{Colors.RESET} {message}")
    
    @staticmethod
    def success(message: str):
        """Print a success message."""
        print(f"{Colors.GREEN}[✓]{Colors.RESET} {message}")
    
    @staticmethod
    def warning(message: str):
        """Print a warning message."""
        print(f"{Colors.YELLOW}[⚠]{Colors.RESET} {message}")
    
    @staticmethod
    def error(message: str):
        """Print an error message."""
        print(f"{Colors.RED}[✗]{Colors.RESET} {message}")


# Convenience instance
formatter = CLIFormatter()
