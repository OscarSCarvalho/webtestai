"""
Módulo 3 — Executor Robot Framework
Executa o arquivo .robot gerado e salva os relatórios HTML.
"""

import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from core import logger
from config.settings import BROWSER_CHANNEL


def execute(robot_file: Path, output_dir: Path, browser: str = "chromium", headed: bool = False) -> bool:
    """
    Executa o arquivo .robot com Robot Framework.
    Retorna True se todos os testes passaram, False caso contrário.
    """
    logger.step(4, "Executando testes com Robot Framework")
    logger.info(f"Arquivo: {robot_file.name}")
    logger.info(f"Saída:   {output_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)

    # Variáveis passadas para o Robot (override do .robot se necessário)
    variables = [
        f"BROWSER:{browser}",
        f"HEADLESS:{'False' if headed else 'True'}",
        f"CHANNEL:{BROWSER_CHANNEL}",
    ]

    cmd = [
        sys.executable, "-m", "robot",
        "--outputdir",   str(output_dir),
        "--output",      "output.xml",
        "--log",         "log.html",
        "--report",      "report.html",
        "--loglevel",    "INFO",
        "--consolewidth","120",
    ]

    for var in variables:
        cmd += ["--variable", var]

    cmd.append(str(robot_file))

    logger.info(f"Comando: {' '.join(cmd)}")
    logger.divider()

    result = subprocess.run(cmd, cwd=str(output_dir))

    logger.divider()

    passed = result.returncode == 0
    if passed:
        logger.success("Todos os testes passaram! ✓")
    else:
        logger.warning(f"Alguns testes falharam (código {result.returncode})")

    return passed
