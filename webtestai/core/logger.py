"""Logger colorido usando Rich."""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import print as rprint

console = Console(highlight=False, emoji=True, legacy_windows=False)


def header(title: str, subtitle: str = ""):
    console.print()
    console.print(Panel(
        f"[bold cyan]{title}[/bold cyan]\n[dim]{subtitle}[/dim]" if subtitle else f"[bold cyan]{title}[/bold cyan]",
        border_style="cyan",
        padding=(0, 2),
    ))


def step(number: int, message: str):
    console.print(f"\n[bold white][ {number} ][/bold white] [cyan]{message}[/cyan]")


def info(message: str):
    console.print(f"  [dim]→[/dim]  {message}")


def success(message: str):
    console.print(f"  [bold green]✓[/bold green]  {message}")


def warning(message: str):
    console.print(f"  [bold yellow]⚠[/bold yellow]  {message}")


def error(message: str):
    console.print(f"  [bold red]✗[/bold red]  {message}")


def element_row(priority: str, el_type: str, locator: str, extra: str = ""):
    icons = {"high": "[red]●[/red]", "medium": "[yellow]●[/yellow]", "low": "[dim]●[/dim]"}
    icon = icons.get(priority, "○")
    console.print(f"  {icon}  [dim]{el_type:10}[/dim]  {locator}  [dim]{extra}[/dim]")


def divider(label: str = ""):
    if label:
        console.rule(f"[dim]{label}[/dim]")
    else:
        console.rule()
