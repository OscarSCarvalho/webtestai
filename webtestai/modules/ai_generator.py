"""
Módulo 2 — Gerador de Cenários com IA (Google Gemini REST API)
Recebe o resultado do scraper e gera um arquivo .robot completo
com casos de teste funcionais em Robot Framework.
"""

import sys
import json
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.models import PageScrapeResult
from core import logger
from config.settings import GEMINI_API_KEY, AI_MODEL, AI_MAX_TOKENS

GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent?key={key}"
)


# ── Prompt de sistema ─────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
Você é um engenheiro sênior de QA especialista em Robot Framework e Browser Library (Playwright).
Sua tarefa é analisar os elementos de uma página e gerar um arquivo Robot Framework (.robot) completo,
profissional e pronto para execução.

REGRAS OBRIGATÓRIAS:
1. Use APENAS Browser Library — NUNCA use SeleniumLibrary nem qualquer outra library
2. Gere SOMENTE o conteúdo do arquivo .robot — sem explicações, sem markdown, sem blocos de código
3. Use variáveis para todos os locators na seção *** Variables ***
4. Crie Keywords reutilizáveis na seção *** Keywords ***
5. Gere pelo menos 3 Test Cases cobrindo fluxos diferentes
6. Adicione [Documentation] em cada Test Case e Keyword
7. Use Tags para organizar os testes: smoke, functional, negative
8. Inclua Suite Setup (New Browser + New Page) e Suite Teardown (Close Browser)
9. Prefira locators por ID > data-testid > name > xpath com texto

KEYWORDS CORRETAS DA BROWSER LIBRARY (use exatamente estes nomes):
- New Browser    ${BROWSER}    headless=${HEADLESS}
- New Page    ${URL}
- Close Browser
- Wait For Load State    networkidle    (ou: load, domcontentloaded)
- Wait For Elements State    ${LOCATOR}    visible    timeout=10s
- Click    ${LOCATOR}
- Fill Text    ${LOCATOR}    ${VALOR}
- Type Text    ${LOCATOR}    ${VALOR}
- Get Text    ${LOCATOR}
- Get Title
- Get Url
- Hover    ${LOCATOR}
- Select Options By    ${LOCATOR}    value    ${VALOR}
- Keyboard Key    press    Enter
- Take Screenshot

KEYWORDS PROIBIDAS (são do SeleniumLibrary — NÃO USE):
- Click Element, Input Text, Hover Element, Wait For Page To Load
- Page Should Contain, Element Should Be Visible, Wait Until Element Is Visible
- Go To, Open Browser, Close All Browsers

ESTRUTURA OBRIGATÓRIA do arquivo:
*** Settings ***
Library    Browser

Suite Setup    Abrir Navegador
Suite Teardown    Close Browser

*** Variables ***
*** Test Cases ***
*** Keywords ***

Keyword "Abrir Navegador" deve conter:
    New Browser    ${BROWSER}    headless=${HEADLESS}
    New Page    ${URL}
    Wait For Load State    load    timeout=30s

IMPORTANTE sobre Wait For Load State:
- Use sempre "load" ou "domcontentloaded" — NUNCA "networkidle" (causa timeout em sites complexos)
- Sempre passe timeout=30s para evitar falhas em sites lentos
- Após abrir a página, use Wait For Elements State no elemento principal antes de interagir

ASSERTIONS (OBRIGATÓRIO):
- Para verificar textos de mensagens de erro ou conteúdo dinâmico, use SEMPRE Should Contain — nunca Should Be Equal
- Should Be Equal só é adequado para títulos de página exatos (Get Title)
- Exemplos corretos:
    Should Contain    ${error_text}    Username and password do not match
    Should Contain    ${url}    /inventory
- Exemplos ERRADOS:
    Should Be Equal    ${error_text}    Epic sadface: Username and password...  # evite — frágil

ISOLAMENTO DE TESTES (OBRIGATÓRIO):
- Cada Test Case DEVE ser independente e começar com a página no estado inicial
- Use [Setup] em cada Test Case chamando uma keyword que navega para a URL de início
- NUNCA dependa do estado deixado pelo teste anterior
- Exemplo de Test Case com [Setup]:

Exemplo De Test Case
    [Documentation]    Descrição do teste
    [Tags]    smoke
    [Setup]    Abrir Navegador
    <passos do teste>

- A keyword "Abrir Navegador" já abre um novo browser E uma nova página, garantindo estado limpo
- Se o Suite usar Suite Teardown com Close Browser, cada [Setup] abre um novo browser
- Alternativa: use "Test Setup    Abrir Navegador" na seção *** Settings *** para aplicar a todos os testes
"""


def _build_prompt(result: PageScrapeResult) -> str:
    """Monta o prompt com o contexto da página."""

    # Serializa apenas elementos de alta e média prioridade para não exceder tokens
    relevant = [
        e.to_dict() for e in result.elements
        if e.priority in ("high", "medium")
    ][:50]

    context = {
        "url":      result.url,
        "title":    result.title,
        "elements": relevant,
    }

    return f"""\
Analise a seguinte página web e gere um arquivo Robot Framework completo para testá-la.

INFORMAÇÕES DA PÁGINA:
{json.dumps(context, ensure_ascii=False, indent=2)}

CENÁRIOS QUE VOCÊ DEVE COBRIR (adapte ao que fizer sentido para esta página):
- Verificar carregamento correto da página (título, elementos visíveis)
- Testar fluxo principal (ex: login, busca, formulário, navegação)
- Testar fluxo com dados inválidos / campos vazios (se aplicável)
- Verificar links e navegação
- Testar responsividade ou comportamento de elementos interativos

Gere agora o arquivo .robot completo:
"""


# ── Gerador principal ─────────────────────────────────────────────────────────

def generate(result: PageScrapeResult, output_path: Path) -> str:
    """
    Chama a API do Google Gemini e salva o arquivo .robot gerado.
    Retorna o conteúdo do arquivo.
    """
    logger.step(3, "Gerando cenários de teste com IA")
    logger.info(f"Modelo: {AI_MODEL}")
    logger.info(f"Elementos enviados: {len([e for e in result.elements if e.priority in ('high','medium')])}")

    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY não configurada. Gerando template padrão.")
        return _fallback_template(result, output_path)

    url = GEMINI_API_URL.format(model=AI_MODEL, key=GEMINI_API_KEY)
    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"parts": [{"text": _build_prompt(result)}]}],
        "generationConfig": {"maxOutputTokens": AI_MAX_TOKENS},
    }

    with logger.console.status("[cyan]Aguardando resposta da IA...[/cyan]"):
        resp = requests.post(url, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()

    robot_content = data["candidates"][0]["content"]["parts"][0]["text"].strip()

    # Garante que começa com *** Settings *** (remove possível bloco markdown)
    if not robot_content.startswith("***"):
        parts = robot_content.split("```")
        robot_content = next((b for b in parts if "*** Settings ***" in b), parts[0])
        robot_content = robot_content.strip()

    output_path.write_text(robot_content, encoding="utf-8")
    logger.success(f"Cenários salvos: {output_path.name}")

    lines = robot_content.split("\n")
    tests = [l.strip() for l in lines if l.strip() and not l.startswith(" ") and not l.startswith("*") and not l.startswith("#")]
    logger.info(f"Test cases gerados: ~{len(tests)}")

    return robot_content


# ── Fallback sem API ──────────────────────────────────────────────────────────

def _fallback_template(result: PageScrapeResult, output_path: Path) -> str:
    """Gera um template básico quando não há chave de API."""

    high    = result.high_priority
    inputs  = result.inputs[:5]
    links   = [e for e in result.links if e.text and e.text.strip()][:5]

    _generic = {"//*", "//a", "//button", "//input", "//select", "//textarea"}

    def _unique_locator(e) -> str | None:
        if e.id:
            return f"id={e.id}"
        if e.text and e.xpath in _generic:
            txt = e.text.strip()[:60].replace("'", "\\'")
            return f"xpath=//{e.tag}[normalize-space()='{txt}']"
        if e.xpath not in _generic:
            txt = e.text.strip()[:60].replace("'", "\\'") if e.text else None
            if txt:
                return f"xpath=//{e.tag}[normalize-space()='{txt}']"
            return f"css={e.css_selector}"
        return None

    lines = [
        "*** Settings ***",
        "Library    Browser",
        "Suite Setup    Configurar Suite",
        "Suite Teardown    Close Browser",
        "",
        "*** Variables ***",
        f"${{URL}}        {result.url}",
        "${BROWSER}    chromium",
        "${HEADLESS}    True",
        "${CHANNEL}    ${EMPTY}",
    ]

    for e in high:
        if e.id:
            var = e.id.upper().replace("-", "_")[:30]
            lines.append(f"${{{var}}}    id={e.id}")

    # ── Test Cases ────────────────────────────────────────────────────────────
    lines += [
        "",
        "*** Test Cases ***",
        "",
        "Verificar Carregamento Da Página",
        "    [Documentation]    Verifica que a página carrega corretamente",
        "    [Tags]    smoke",
        "    Abrir Página",
        f"    Get Title    ==    {result.title}",
    ]

    for e in high[:8]:
        loc = _unique_locator(e)
        if loc:
            lines.append(f"    Wait For Elements State    {loc}    attached")

    lines += [
        "",
        "Verificar Elementos Interativos",
        "    [Documentation]    Verifica presença de elementos interativos na página",
        "    [Tags]    smoke    functional",
        "    Abrir Página",
    ]

    if inputs:
        for e in inputs[:3]:
            loc = _unique_locator(e)
            if loc:
                lines.append(f"    Wait For Elements State    {loc}    visible")
    elif links:
        for e in links[:4]:
            loc = _unique_locator(e)
            if loc:
                lines.append(f"    Wait For Elements State    {loc}    visible")

    if links:
        first = links[0]
        loc = _unique_locator(first)
        if loc:
            lines += [
                "",
                "Verificar Navegação Por Links",
                "    [Documentation]    Verifica que os links principais estão clicáveis",
                "    [Tags]    functional",
                "    Abrir Página",
            ]
            for e in links[:3]:
                l = _unique_locator(e)
                if l:
                    lines.append(f"    Aguardar E Clicar    {l}")
                    lines.append(f"    Abrir Página")

    # ── Keywords ──────────────────────────────────────────────────────────────
    lines += [
        "",
        "*** Keywords ***",
        "",
        "Configurar Suite",
        "    [Documentation]    Inicializa o browser com suporte a channel (ex: chrome)",
        "    IF    '${CHANNEL}' != '${EMPTY}'",
        "        New Browser    ${BROWSER}    headless=${HEADLESS}    channel=${CHANNEL}",
        "    ELSE",
        "        New Browser    ${BROWSER}    headless=${HEADLESS}",
        "    END",
        "",
        "Abrir Página",
        "    [Documentation]    Abre a URL e aguarda carregamento completo",
        "    New Page    ${URL}",
        "    Wait For Load State    networkidle",
        "",
        "Aguardar E Clicar",
        "    [Arguments]    ${locator}",
        "    [Documentation]    Aguarda elemento ficar visível e clica",
        "    Wait For Elements State    ${locator}    visible    timeout=10s",
        "    Click    ${locator}",
        "",
        "Preencher Campo",
        "    [Arguments]    ${locator}    ${valor}",
        "    [Documentation]    Aguarda campo ficar visível e preenche",
        "    Wait For Elements State    ${locator}    visible    timeout=10s",
        "    Fill Text    ${locator}    ${valor}",
    ]

    content = "\n".join(lines)
    output_path.write_text(content, encoding="utf-8")
    logger.success(f"Template padrão salvo: {output_path.name}")
    return content
