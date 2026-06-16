"""
Módulo 4 — Reporter
Salva o JSON de elementos, exibe resumo e abre o relatório no browser.
"""

import sys
import json
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.models import PageScrapeResult
from core import logger


def save_elements_json(result: PageScrapeResult, output_path: Path) -> None:
    """Salva o JSON completo dos elementos capturados."""
    output_path.write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.success(f"Elementos salvos: {output_path.name}")


def print_summary(result: PageScrapeResult, report_dir: Path, passed: bool) -> None:
    """Exibe o resumo final da execução."""
    high   = len(result.high_priority)
    medium = len([e for e in result.elements if e.priority == "medium"])
    low    = len([e for e in result.elements if e.priority == "low"])

    logger.step(5, "Resumo da execução")
    logger.console.print()
    logger.console.print(f"  [bold]Página:[/bold]   {result.title}")
    logger.console.print(f"  [bold]URL:[/bold]       {result.url}")
    logger.console.print()
    logger.console.print(f"  Elementos capturados:")
    logger.console.print(f"    [red]●[/red] Alta prioridade:  {high}")
    logger.console.print(f"    [yellow]●[/yellow] Média prioridade: {medium}")
    logger.console.print(f"    [dim]●[/dim] Baixa prioridade: {low}")
    logger.console.print()
    logger.console.print(f"  Relatórios em: [cyan]{report_dir}[/cyan]")
    logger.console.print(f"    → elements.json")
    logger.console.print(f"    → scenarios.robot")
    logger.console.print(f"    → report.html")
    logger.console.print(f"    → log.html")
    logger.console.print()

    status = "[bold green]PASSOU ✓[/bold green]" if passed else "[bold yellow]COM FALHAS ⚠[/bold yellow]"
    logger.console.print(f"  Status dos testes: {status}")
    logger.console.print()


def open_report(report_dir: Path) -> None:
    """Tenta abrir o report.html no browser padrão do sistema."""
    report_html = report_dir / "report.html"
    if report_html.exists():
        logger.info("Abrindo relatório no browser...")
        webbrowser.open(report_html.as_uri())
    else:
        logger.warning(f"report.html não encontrado em {report_dir}")
