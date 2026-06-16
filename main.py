"""
Wrapper de execução para WebTestAI.
Este arquivo permite rodar `python main.py ...` a partir da raiz do workspace,
encaminhando a execução para o script real em `webtestai/main.py`.
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent
WEBTESTAI_DIR = PROJECT_ROOT / "webtestai"

# Permite importar o módulo principal do subdiretório.
sys.path.insert(0, str(WEBTESTAI_DIR))

from main import main

if __name__ == "__main__":
    main()
