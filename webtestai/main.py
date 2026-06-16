"""
WebTestAI — Ponto de entrada principal
Uso: python main.py <URL> [opções]
"""

import sys
import argparse
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

# Garante que o projeto está no path
sys.path.insert(0, str(Path(__file__).parent))

from core import logger
from config.settings import REPORTS_DIR, DEFAULT_BROWSER, HEADLESS
from modules.scraper      import scrape
from modules.ai_generator import generate
from modules.executor     import execute
from modules.reporter     import save_elements_json, print_summary, open_report


def parse_args():
    parser = argparse.ArgumentParser(
        description="WebTestAI — Automação de testes web com IA",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python main.py https://meusite.com
  python main.py https://meusite.com --headed
  python main.py https://meusite.com --only-scrape
  python main.py https://meusite.com --no-ai --browser firefox
        """,
    )
    parser.add_argument("url",          help="URL da aplicação web a testar")
    parser.add_argument("--only-scrape",action="store_true", help="Só captura elementos, não executa testes")
    parser.add_argument("--no-ai",      action="store_true", help="Gera template padrão sem chamar a IA")
    parser.add_argument("--browser",    default=DEFAULT_BROWSER, choices=["chromium","firefox","webkit"],
                        help="Browser a usar (padrão: chromium)")
    parser.add_argument("--headed",     action="store_true", help="Mostra o browser durante execução")
    parser.add_argument("--no-report",  action="store_true", help="Não abre o relatório no browser")
    return parser.parse_args()


def make_report_dir(url: str) -> Path:
    """Cria pasta de relatório com nome: dominio_YYYYMMDD_HHMMSS"""
    domain    = urlparse(url).netloc.replace(".", "_").replace(":", "_") or "local"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_dir = REPORTS_DIR / f"{domain}_{timestamp}"
    report_dir.mkdir(parents=True, exist_ok=True)
    return report_dir


def main(
    url=None,
    browser=None,
    headed=False,
    no_ai=False,
    only_scrape=False,
    no_report=False,
):
    # Modo CLI: lê sys.argv quando chamado sem parâmetros
    if url is None:
        args = parse_args()
        url         = args.url
        headed      = args.headed
        no_ai       = args.no_ai
        browser     = args.browser
        only_scrape = args.only_scrape
        no_report   = args.no_report
    else:
        browser = browser or DEFAULT_BROWSER

    logger.header(
        "WebTestAI",
        "Automação inteligente de testes web"
    )

    report_dir = make_report_dir(url)
    logger.info(f"Pasta de saída: {report_dir}")

    # ── Módulo 1: Scraping ────────────────────────────────────────────────────
    scrape_result = scrape(
        url          = url,
        browser_name = browser,
        headless     = not headed,
    )

    # Salva JSON dos elementos
    save_elements_json(scrape_result, report_dir / "elements.json")

    if only_scrape:
        logger.success("Modo --only-scrape: concluído.")
        print_summary(scrape_result, report_dir, passed=True)
        return

    # ── Módulo 2: Geração de cenários com IA ──────────────────────────────────
    robot_file = report_dir / "scenarios.robot"

    if no_ai:
        from modules.ai_generator import _fallback_template
        _fallback_template(scrape_result, robot_file)
    else:
        generate(scrape_result, robot_file)

    # ── Módulo 3: Execução ────────────────────────────────────────────────────
    passed = execute(
        robot_file = robot_file,
        output_dir = report_dir,
        browser    = browser,
        headed     = headed,
    )

    # ── Módulo 4: Relatório ───────────────────────────────────────────────────
    print_summary(scrape_result, report_dir, passed)

    if not no_report:
        open_report(report_dir)


if __name__ == "__main__":
    main()
