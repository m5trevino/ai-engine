"""
PEACOCK ENGINE - CLI Formatter
Fancy output formatting with gateway-specific borders and colors.
"""

import os
import random
import time
from typing import Optional, Dict, Tuple

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
        """Print a successful strike with fancy formatting."""
        style = CLIFormatter.get_gateway_style(gateway)
        top, bottom = style["success"]
        color = style["color"]
        
        total_tokens = prompt_tokens + completion_tokens
        duration_str = f"{duration:.2f}s" if duration else "N/A"
        format_str = format_mode or "text"
        
        # Build the output
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            f"{color}{top}{Colors.RESET}",
            f"{color}│{Colors.BRIGHT_GREEN} ✦ STRIKE SUCCESS {color}│{Colors.RESET} {f'{Colors.DIM}[{tag}]{Colors.RESET}' if tag else ''}",
            f"{color}├{'─' * (len(top) - 2)}┤{Colors.RESET}",
            f"{color}│{Colors.RESET} Time:       {Colors.DIM}{now_str}{Colors.RESET}",
            f"{color}│{Colors.RESET} Gateway:    {Colors.BOLD}{gateway.upper()}{Colors.RESET}",
            f"{color}│{Colors.RESET} Model:      {model[:35]}{Colors.RESET}",
            f"{color}│{Colors.RESET} Account:    {Colors.YELLOW}{account}{Colors.RESET}",
            f"{color}│{Colors.RESET} Temp:       {Colors.BOLD}{temp}{Colors.RESET}",
            f"{color}│{Colors.RESET} Format:     {format_str}{Colors.RESET}",
            f"{color}│{Colors.RESET} Tokens:     {Colors.CYAN}{prompt_tokens:,}{Colors.RESET} in / {Colors.CYAN}{completion_tokens:,}{Colors.RESET} out ({total_tokens:,} total){Colors.RESET}",
            f"{color}│{Colors.RESET} Cost:       {Colors.GREEN}${cost:.6f}{Colors.RESET}",
            f"{color}│{Colors.RESET} Duration:   {Colors.CYAN}{duration_str}{Colors.RESET}",
        ]
        
        if meter:
            lines.append(f"{color}│{Colors.RESET} {meter}")
            
        if rescue_note:
            lines.append(f"{color}│{Colors.RESET} {Colors.BRIGHT_YELLOW}RESCUE:     {rescue_note}{Colors.RESET}")
            
        lines.append(f"{color}{bottom}{Colors.RESET}")
        
        print("\n" + "\n".join(lines) + "\n")

    @staticmethod
    def strike_error(gateway: str, account: str, error: str, model: Optional[str] = None, temp: Optional[float] = None, tag: Optional[str] = None):
        """Print a failed strike with red error formatting."""
        style = CLIFormatter.get_gateway_style(gateway)
        top, bottom = style["error"]
        
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        # All red for errors
        lines = [
            f"{Colors.BRIGHT_RED}{top}{Colors.RESET}",
            f"{Colors.BRIGHT_RED}│ ✗ STRIKE FAILED {Colors.RESET} {f'{Colors.DIM}[{tag}]{Colors.RESET}' if tag else ''}",
            f"{Colors.BRIGHT_RED}├{'─' * (len(top) - 2)}┤{Colors.RESET}",
            f"{Colors.BRIGHT_RED}│{Colors.RESET} Time:    {Colors.DIM}{now_str}{Colors.RESET}",
            f"{Colors.BRIGHT_RED}│{Colors.RESET} Gateway: {gateway.upper()}",
        ]
        
        
        if model:
            lines.append(f"{Colors.BRIGHT_RED}│{Colors.RESET} Model:   {model}")
        if temp is not None:
            lines.append(f"{Colors.BRIGHT_RED}│{Colors.RESET} Temp:    {Colors.DIM}{temp}{Colors.RESET}")
        
        lines.extend([
            f"{Colors.BRIGHT_RED}│{Colors.RESET} Account: {account}",
            f"{Colors.BRIGHT_RED}│{Colors.RESET} Error:   {Colors.BRIGHT_RED}{error}{Colors.RESET}",
            f"{Colors.BRIGHT_RED}{bottom}{Colors.RESET}"
        ])
        
        print("\n" + "\n".join(lines) + "\n")
    
    @staticmethod
    def debug_request(model: str, gateway: str, endpoint: str = "/v1/strike"):
        """Print debug info about incoming request. (Now SILENT by default unless explicitly asked)"""
        # The user requested this to be removed. We'll make it completely silent.
        pass
    
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
