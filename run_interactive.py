"""
WebTestAI — Runner Interativo
Pressione F5 ou execute: python run_interactive.py
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "webtestai"))

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich import box

console = Console()


def ask_url() -> str:
    while True:
        url = Prompt.ask("\n[bold cyan]URL do site a testar[/bold cyan]").strip()
        if not url:
            console.print("[red]  URL não pode ser vazia.[/red]")
            continue
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
            console.print(f"[dim]  → Usando: {url}[/dim]")
        return url


def ask_options() -> dict:
    console.print("\n[bold]Modo de execução:[/bold]")
    console.print("  [bold green][1][/bold green] Testes completos com IA  + browser visível  [dim](recomendado)[/dim]")
    console.print("  [bold cyan] [2][/bold cyan] Testes completos com IA  + headless (sem UI)")
    console.print("  [bold yellow][3][/bold yellow] Testes sem IA (template padrão) + browser visível")
    console.print("  [bold blue] [4][/bold blue] Apenas capturar elementos da página")

    mode = Prompt.ask("\n  Escolha", choices=["1", "2", "3", "4"], default="1")

    browser = Prompt.ask(
        "  Browser",
        choices=["chromium", "firefox", "webkit"],
        default="chromium",
    )

    return {
        "headed":      mode in ("1", "3"),
        "no_ai":       mode == "3",
        "only_scrape": mode == "4",
        "browser":     browser,
    }


def main():
    console.print(Panel(
        "[bold green]WebTestAI[/bold green] — Runner Interativo\n"
        "[dim]Automação E2E com IA · insira a URL e pressione Enter[/dim]",
        border_style="bright_green",
        box=box.ROUNDED,
        padding=(0, 2),
    ))

    url  = ask_url()
    opts = ask_options()

    console.print("\n[bold]Iniciando...[/bold]")
    console.rule()

    from main import main as run_tests  # webtestai/main.py está no sys.path
    run_tests(
        url         = url,
        browser     = opts["browser"],
        headed      = opts["headed"],
        no_ai       = opts["no_ai"],
        only_scrape = opts["only_scrape"],
    )


if __name__ == "__main__":
    main()
