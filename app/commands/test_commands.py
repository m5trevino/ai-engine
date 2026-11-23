"""
Test commands for PEACOCK ENGINE CLI.
Handles validation of API keys and models.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent to path for script imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def run_test_google(args):
    """Run Google API validation."""
    console.print(Panel("🦚 Testing Google API Keys & Models", style="blue"))
    
    async def _run():
        from scripts.validate_google import GoogleValidator
        
        validator = GoogleValidator()
        results = await validator.validate_all(
            freeze_broken=not getattr(args, 'no_freeze', False),
            specific_key=getattr(args, 'key', None),
            specific_model=getattr(args, 'model', None)
        )
        
        if getattr(args, 'output', None):
            import json
            existing = {}
            output_path = Path(args.output)
            if output_path.exists():
                try:
                    existing = json.loads(output_path.read_text())
                except: pass
            
            # Merge results
            existing["google"] = results
            output_path.write_text(json.dumps(existing, indent=2, default=str))
            console.print(f"\n[green]💾 Google report merged into {args.output}[/green]")
    
    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        console.print("\n[yellow]Test interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"[red]Test failed: {e}[/red]")


def run_test_groq(args):
    """Run Groq API validation."""
    console.print(Panel("⚡ Testing Groq API Keys & Models", style="magenta"))
    
    async def _run():
        from scripts.validate_groq import GroqValidator
        
        validator = GroqValidator()
        results = await validator.validate_all(
            freeze_broken=not getattr(args, 'no_freeze', False),
            specific_key=getattr(args, 'key', None),
            specific_model=getattr(args, 'model', None)
        )
        
        if getattr(args, 'output', None):
            import json
            existing = {}
            output_path = Path(args.output)
            if output_path.exists():
                try:
                    existing = json.loads(output_path.read_text())
                except: pass
            
            # Merge results
            existing["groq"] = results
            output_path.write_text(json.dumps(existing, indent=2, default=str))
            console.print(f"\n[green]💾 Groq report merged into {args.output}[/green]")
    
    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        console.print("\n[yellow]Test interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"[red]Test failed: {e}[/red]")


def run_test_all(args):
    """Run all validations (Google + Groq)."""
    console.print(Panel("🦚⚡ Testing ALL API Keys & Models", style="bold cyan"))
    console.print()
    
    # Run Google
    console.print("[blue]═══════════════════════════════════════════════════[/blue]")
    run_test_google(args)
    console.print()
    
    # Run Groq
    console.print("[magenta]═══════════════════════════════════════════════════[/magenta]")
    run_test_groq(args)
    console.print()
    
    # Summary
    console.print(Panel("🏁 ALL TESTS COMPLETE", style="bold green"))


def add_test_subparser(subparsers):
    """Add the 'test' subcommand to the CLI."""
    test_parser = subparsers.add_parser(
        "test",
        help="Test API keys and models",
        description="Validate API keys and test model availability. Auto-freezes broken models."
    )
    
    test_subparsers = test_parser.add_subparsers(dest="test_command", help="Test commands")
    
    # Test Google
    google_parser = test_subparsers.add_parser(
        "google",
        help="Test Google API keys and models"
    )
    google_parser.add_argument("--no-freeze", action="store_true", help="Don't auto-freeze broken models")
    google_parser.add_argument("--key", help="Test specific key only")
    google_parser.add_argument("--model", help="Test specific model only")
    google_parser.add_argument("--output", "-o", help="Save report to JSON file")
    google_parser.set_defaults(func=run_test_google)
    
    # Test Groq
    groq_parser = test_subparsers.add_parser(
        "groq",
        help="Test Groq API keys and models"
    )
    groq_parser.add_argument("--no-freeze", action="store_true", help="Don't auto-freeze broken models")
    groq_parser.add_argument("--key", help="Test specific key only")
    groq_parser.add_argument("--model", help="Test specific model only")
    groq_parser.add_argument("--output", "-o", help="Save report to JSON file")
    groq_parser.set_defaults(func=run_test_groq)
    
    # Test All
    all_parser = test_subparsers.add_parser(
        "all",
        help="Test all gateways"
    )
    all_parser.add_argument("--no-freeze", action="store_true", help="Don't auto-freeze broken models")
    all_parser.add_argument("--output", "-o", help="Save report to JSON file")
    all_parser.set_defaults(func=run_test_all)
    
    return test_parser


# Token counter CLI commands
def run_tokens_count(args):
    """Count tokens for text."""
    from app.utils.gemini_token_counter import GeminiTokenCounter
    from app.utils.groq_token_counter import GroqTokenCounter
    
    text = args.text
    if args.file:
        try:
            text = Path(args.file).read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            console.print(f"[red]Error reading file: {e}[/red]")
            return
    
    if not text:
        console.print("[yellow]No text provided. Use --text or --file[/yellow]")
        return
    
    # Detect provider from model
    model = args.model
    if "gemini" in model.lower():
        counter = GeminiTokenCounter()
        tokens = counter.estimate_tokens(text)
        provider = "Google"
    else:
        # Try Groq
        try:
            counter = GroqTokenCounter()
            tokens = counter.count_tokens(text, model)
            provider = "Groq"
        except:
            # Fallback to Gemini estimation
            counter = GeminiTokenCounter()
            tokens = counter.estimate_tokens(text)
            provider = "Generic"
    
    # Get cost estimate
    from app.config import MODEL_REGISTRY
    model_cfg = next((m for m in MODEL_REGISTRY if m.id == model), None)
    if model_cfg:
        cost = (tokens / 1_000_000) * model_cfg.input_price_1m
        cost_str = f" | Est. Cost: ${cost:.6f}"
    else:
        cost_str = ""
    
    console.print(Panel(
        f"[bold]{provider} Token Count[/bold]\n"
        f"Model: {model}\n"
        f"Tokens: [cyan]{tokens}[/cyan]{cost_str}",
        title="🧮 Token Counter",
        border_style="cyan"
    ))


def add_tokens_subparser(subparsers):
    """Add the 'tokens' subcommand to the CLI."""
    tokens_parser = subparsers.add_parser(
        "tokens",
        help="Token counting utilities"
    )
    
    tokens_subparsers = tokens_parser.add_subparsers(dest="tokens_command")
    
    # Count tokens
    count_parser = tokens_subparsers.add_parser("count", help="Count tokens in text")
    count_parser.add_argument("--text", help="Text to count")
    count_parser.add_argument("--file", help="File to read and count")
    count_parser.add_argument("--model", default="gemini-2.0-flash-lite", help="Model for token counting")
    count_parser.set_defaults(func=run_tokens_count)
    
    return tokens_parser
