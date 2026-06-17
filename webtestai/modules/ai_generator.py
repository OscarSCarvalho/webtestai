"""
Módulo 2 — Gerador de Cenários com IA (Google Gemini REST API)
Recebe o resultado do scraper e gera um arquivo .robot completo
com casos de teste funcionais em Robot Framework / Browser Library.
"""

import sys
import json
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.models import PageScrapeResult, ElementType
from core import logger
from config.settings import GEMINI_API_KEY, AI_MODEL, AI_MAX_TOKENS

GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent?key={key}"
)


# ── Prompt de sistema ─────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
Você é um Engenheiro Sênior de QA especialista em Robot Framework e Browser Library (Playwright).
Sua missão é analisar os elementos de uma página web e gerar um arquivo .robot COMPLETO, profissional
e pronto para execução, com alta cobertura funcional de navegação e interação.

══════════════════════════════════════════════════════════════════
REGRAS ABSOLUTAS
══════════════════════════════════════════════════════════════════
1. Use APENAS Browser Library — NUNCA use SeleniumLibrary
2. Gere SOMENTE o conteúdo do arquivo .robot — sem markdown, sem ```robot, sem explicações
3. Declare TODOS os locators como variáveis na seção *** Variables ***
4. Crie Keywords reutilizáveis na seção *** Keywords ***
5. Gere no mínimo 5 Test Cases cobrindo fluxos diferentes
6. Adicione [Documentation] em cada Test Case e Keyword
7. Use Tags: smoke, navigation, functional, forms, negative
8. Use "Test Setup    Abrir Navegador" na seção *** Settings *** (NUNCA Suite Setup)
9. A Keyword "Abrir Navegador": New Browser + New Page + Wait For Load State

══════════════════════════════════════════════════════════════════
ESTRATÉGIAS DE LOCATOR — ORDEM DE PRIORIDADE
══════════════════════════════════════════════════════════════════
Use esta ordem. Role selectors são os mais robustos para apps React/Vue/Angular
porque funcionam independente da tag HTML usada pelo framework.

1. ROLE SELECTOR (funciona para qualquer tag com o role correto — PREFIRA ESTE):
   role=button[name="Login"]
   role=link[name="Home"]
   role=navigation
   role=menuitem[name="Produtos"]
   role=tab[name="Detalhes"]
   role=checkbox[name="Aceitar termos"]
   role=textbox[name="Email"]
   role=combobox[name="País"]

2. TEXT SELECTOR (texto visível exato):
   text=Login
   text=Enviar pedido
   text=Cancelar

3. ID:
   id=login-button

4. DATA-TESTID:
   [data-testid="login-btn"]

5. ARIA-LABEL:
   [aria-label="Fechar menu"]

6. CSS:
   css=nav .nav-link
   css=.btn-primary

7. XPATH (último recurso):
   xpath=//nav//a[normalize-space()='Home']

══════════════════════════════════════════════════════════════════
PREVENÇÃO DE STRICT MODE VIOLATION — CRÍTICO
══════════════════════════════════════════════════════════════════
Strict mode violation ocorre quando um seletor resolve para MÚLTIPLOS elementos.
Isso faz o teste falhar. Evite assim:

PROBLEMA:  text=Books              → pode resolver para "Books" e "Books to Scrape"
SOLUÇÃO 1: role=link[name="Books"] → exact match pelo nome (preferido)
SOLUÇÃO 2: text=Books >> nth=0     → seleciona explicitamente o primeiro elemento
SOLUÇÃO 3: xpath=(//a[.='Books'])[1] → XPath com posição explícita

PROBLEMA:  css=.product_pod h3 a   → resolve para TODOS os produtos da lista
SOLUÇÃO 1: css=.product_pod:first-child h3 a  → primeiro produto
SOLUÇÃO 2: css=.product_pod h3 a >> nth=0     → primeiro da lista

REGRA GERAL:
- Para LISTAS de elementos (cards, linhas de tabela, itens repetidos): SEMPRE use `>> nth=0` ou `:first-child`
- Para textos que aparecem mais de uma vez: SEMPRE use `role=link[name="texto"]` (exact match)
- O seletor `text=X` faz match PARCIAL — "Books to Scrape" também é matched por `text=Books`
- O seletor `role=link[name="X"]` faz match EXATO — "Books to Scrape" NÃO é matched por `role=link[name="Books"]`

══════════════════════════════════════════════════════════════════
FUNDAMENTAL: ELEMENTOS CLICÁVEIS ALÉM DE <a> E <button>
══════════════════════════════════════════════════════════════════
NUNCA assuma que apenas <a> e <button> são clicáveis.
Elementos com element_type "nav_item", "menu_item" ou "interactive" são componentes
customizados que podem ser <div>, <span>, <li>, <svg> — mas são 100% clicáveis.

Para esses elementos, use:
  role=link[name="Texto"]          (se o elemento for de navegação — EXACT MATCH)
  role=button[name="Texto"]        (se o elemento tiver role=button — EXACT MATCH)
  text=Texto do elemento           (SOMENTE se o texto for ÚNICO na página)
  css=.classe-especifica           (se tiver classe identificável)
  xpath=//*[normalize-space()='Texto']   (fallback — exact match)

══════════════════════════════════════════════════════════════════
REGRAS PARA NAVBAR E NAVEGAÇÃO — OBRIGATÓRIO
══════════════════════════════════════════════════════════════════
Ao receber elementos com in_nav=true ou element_type nav_item/menu_item:
- SEMPRE crie um Test Case dedicado "Testar Navegação Principal"
- Teste no máximo 5 itens de menu por Test Case
- Padrão para item de navbar:
    ${url_antes}=    Get Url
    Click    text=Home
    Wait For Load State    load    timeout=30s
    ${url_depois}=    Get Url
    Should Not Be Equal    ${url_antes}    ${url_depois}
- Para submenu (requer hover no pai):
    Hover    text=Produtos
    Wait For Elements State    text=Categoria X    visible    timeout=5s
    Click    text=Categoria X

══════════════════════════════════════════════════════════════════
PADRÕES PARA TIPOS ESPECIAIS
══════════════════════════════════════════════════════════════════

DROPDOWN (combobox customizado, não <select>):
    Click    ${DROPDOWN_TRIGGER}
    Wait For Elements State    ${DROPDOWN_MENU}    visible    timeout=5s
    Click    ${DROPDOWN_OPCAO}

MODAL / DIALOG:
    Click    ${MODAL_TRIGGER}
    Wait For Elements State    role=dialog    visible    timeout=5s
    Click    role=button[name="Fechar"]
    Wait For Elements State    role=dialog    hidden    timeout=5s

TABS:
    Click    role=tab[name="Detalhes"]
    Wait For Elements State    role=tabpanel    visible    timeout=5s

LINK QUE ABRE NOVA ABA (opens_new_tab=true):
    Click    ${LINK_NOVA_ABA}
    Switch Page    NEW
    Wait For Load State    load    timeout=15s
    ${nova_url}=    Get Url
    Should Not Be Equal    ${nova_url}    about:blank
    Close Page
    Switch Page    FIRST

SPA — Navegação sem reload (Single Page Application):
    ${url_antes}=    Get Url
    Click    ${LINK_SPA}
    Wait For Navigation    url=**${PATH_ESPERADO}**    timeout=10s
    # OU: espera elemento da nova rota aparecer:
    Wait For Elements State    ${EL_DA_NOVA_ROTA}    visible    timeout=10s

══════════════════════════════════════════════════════════════════
KEYWORDS CORRETAS DA BROWSER LIBRARY
══════════════════════════════════════════════════════════════════
New Browser    ${BROWSER}    headless=${HEADLESS}
New Page    ${URL}
Close Browser / Close Page
Wait For Load State    load    timeout=30s
Wait For Elements State    ${LOCATOR}    visible    timeout=10s
Wait For Elements State    ${LOCATOR}    hidden     timeout=10s
Wait For Navigation    url=**padrão**    timeout=10s
Click    ${LOCATOR}
Hover    ${LOCATOR}
Fill Text    ${LOCATOR}    ${VALOR}
Type Text    ${LOCATOR}    ${VALOR}
Clear Text   ${LOCATOR}
Get Text    ${LOCATOR}
Get Title
Get Url
Select Options By    ${LOCATOR}    value    ${VALOR}
Select Options By    ${LOCATOR}    label    ${TEXTO}
Keyboard Key    press    Enter
Keyboard Key    press    Escape
Take Screenshot
Scroll To Element    ${LOCATOR}
Switch Page    NEW / Switch Page    FIRST

══════════════════════════════════════════════════════════════════
KEYWORDS PROIBIDAS (SeleniumLibrary — NUNCA USE)
══════════════════════════════════════════════════════════════════
Click Element, Input Text, Hover Element, Wait For Page To Load,
Page Should Contain, Element Should Be Visible, Wait Until Element Is Visible,
Go To, Open Browser, Close All Browsers, Switch Window, Get Location

══════════════════════════════════════════════════════════════════
ASSERTIONS CORRETAS
══════════════════════════════════════════════════════════════════
URL parcial:  ${url}=    Get Url    THEN    Should Contain    ${url}    /inventory
Título:       Get Title    ==    Swag Labs
Texto:        Get Text    ${locator}    *=    texto esperado
Presença:     Wait For Elements State    ${locator}    attached
Visível:      Wait For Elements State    ${locator}    visible
URL padrão:   Wait For Navigation    url=**/pagina**    timeout=10s
ERRADO:       Should Be Equal    ${url}    https://site.com  (falha em qualquer diferença mínima)

══════════════════════════════════════════════════════════════════
WAIT FOR LOAD STATE — REGRA CRÍTICA
══════════════════════════════════════════════════════════════════
- Use SEMPRE "load" ou "domcontentloaded" — NUNCA "networkidle" nos test cases
  (networkidle causa timeout em sites com analytics, websockets, polling)
- Em SPAs: após clicar em link interno, use Wait For Navigation ou Wait For Elements State
  em vez de Wait For Load State (não há reload real de página)
  Exemplo: Wait For Navigation    url=**/produtos**    timeout=10s

══════════════════════════════════════════════════════════════════
ESTRUTURA OBRIGATÓRIA
══════════════════════════════════════════════════════════════════
*** Settings ***
Library    Browser

Test Setup     Abrir Navegador
Suite Teardown    Close Browser

*** Variables ***
${URL}         https://...
${BROWSER}     chromium
${HEADLESS}    True
# TODOS os locators declarados aqui como variáveis

*** Test Cases ***
# Mínimo 5 test cases: smoke, navigation, functional, forms, negative

*** Keywords ***
Abrir Navegador
    [Documentation]    Abre o browser e carrega a URL configurada
    New Browser    ${BROWSER}    headless=${HEADLESS}
    New Page    ${URL}
    Wait For Load State    load    timeout=30s

Preencher Campo
    [Arguments]    ${locator}    ${valor}
    [Documentation]    Aguarda campo visível e preenche
    Wait For Elements State    ${locator}    visible    timeout=10s
    Fill Text    ${locator}    ${valor}

Aguardar E Clicar
    [Arguments]    ${locator}
    [Documentation]    Aguarda elemento visível e clica
    Wait For Elements State    ${locator}    visible    timeout=10s
    Click    ${locator}

"""


def _build_prompt(result: PageScrapeResult) -> str:
    """
    Monta o prompt com contexto completo da página, organizado por seção.
    Inclui metadados adicionais para guiar a IA na geração de testes mais precisos.
    """
    all_els = result.elements

    nav_elements  = [e for e in all_els if e.in_nav or e.element_type in (ElementType.NAV_ITEM, ElementType.MENU_ITEM)]
    header_els    = [e for e in all_els if e.in_header and not e.in_nav]
    form_inputs   = [e for e in all_els if e.element_type in (ElementType.INPUT, ElementType.SELECT, ElementType.TEXTAREA)]
    buttons       = [e for e in all_els if e.element_type == ElementType.BUTTON]
    links         = [e for e in all_els if e.element_type == ElementType.LINK and not e.in_nav]
    tabs          = [e for e in all_els if e.element_type == ElementType.TAB]
    checkboxes    = [e for e in all_els if e.element_type in (ElementType.CHECKBOX, ElementType.RADIO, ElementType.SWITCH)]
    footer_els    = [e for e in all_els if e.in_footer]
    interactive   = [e for e in all_els if e.element_type == ElementType.INTERACTIVE]
    new_tab_links = [e for e in all_els if e.opens_new_tab]
    js_elements   = [e for e in all_els if e.has_js_event and e.element_type not in (ElementType.LINK, ElementType.BUTTON)]

    def to_list(items, limit):
        return [e.to_dict() for e in items[:limit]]

    context = {
        "url":   result.url,
        "title": result.title,
        "page_summary": {
            "total_interactive_elements": len(all_els),
            "has_navigation":      len(nav_elements) > 0,
            "has_forms":           len(form_inputs) > 0,
            "has_tabs":            len(tabs) > 0,
            "has_checkboxes":      len(checkboxes) > 0,
            "has_new_tab_links":   len(new_tab_links) > 0,
            "has_js_elements":     len(js_elements) > 0,
            "nav_items_count":     len(nav_elements),
            "form_inputs_count":   len(form_inputs),
            "buttons_count":       len(buttons),
            "links_count":         len(links),
            "interactive_count":   len(interactive),
        },
        "elements_by_section": {
            "navigation_navbar_menus": to_list(nav_elements, 25),
            "header_elements":         to_list(header_els, 10),
            "form_inputs_selects":     to_list(form_inputs, 25),
            "buttons":                 to_list(buttons, 20),
            "content_links":           to_list(links, 20),
            "tabs":                    to_list(tabs, 10),
            "checkboxes_radios":       to_list(checkboxes, 10),
            "footer_elements":         to_list(footer_els, 10),
            "custom_interactive":      to_list(interactive, 15),
            "opens_new_tab":           to_list(new_tab_links, 5),
            "js_event_only":           to_list(js_elements, 10),
        },
    }

    nav_note = ""
    if nav_elements:
        nav_texts = [e.text or e.aria_label or e.href or "" for e in nav_elements[:8] if e.text or e.aria_label]
        nav_note = (
            f"\nATENÇÃO — {len(nav_elements)} elementos de NAVEGAÇÃO detectados. "
            f"Textos: {nav_texts}. "
            "Crie obrigatoriamente o Test Case 'Testar Itens De Navegação'.\n"
        )

    forms_note = ""
    if form_inputs:
        field_hints = [e.placeholder or e.aria_label or e.name or "" for e in form_inputs[:6] if any([e.placeholder, e.aria_label, e.name])]
        forms_note = (
            f"\nATENÇÃO — {len(form_inputs)} campos de formulário detectados: {field_hints}. "
            "Crie Test Cases para preenchimento válido e inválido.\n"
        )

    new_tab_note = ""
    if new_tab_links:
        new_tab_note = (
            f"\nATENÇÃO — {len(new_tab_links)} links com target=_blank (abrem nova aba). "
            "Use Switch Page    NEW após o clique.\n"
        )

    return f"""\
Analise a seguinte página web e gere um arquivo Robot Framework (.robot) COMPLETO.

═══════════════════════════════════════════
DADOS DA PÁGINA
═══════════════════════════════════════════
URL:    {result.url}
Título: {result.title}
{nav_note}{forms_note}{new_tab_note}
═══════════════════════════════════════════
ELEMENTOS DA PÁGINA (organizados por seção)
═══════════════════════════════════════════
{json.dumps(context, ensure_ascii=False, indent=2)}

═══════════════════════════════════════════
CENÁRIOS OBRIGATÓRIOS
═══════════════════════════════════════════
1. [smoke]      Verificar carregamento — título, elementos essenciais visíveis
2. [navigation] Testar navegação — navbar, menus, links{"  ← OBRIGATÓRIO (" + str(len(nav_elements)) + " nav_items)" if nav_elements else ""}
3. [functional] Testar funcionalidade principal da página
4. [forms]      Testar formulário — preenchimento válido e envio{"  ← OBRIGATÓRIO (" + str(len(form_inputs)) + " campos)" if form_inputs else ""}
5. [negative]   Testar validação — dados inválidos, campos obrigatórios
{"6. [navigation] Testar links que abrem nova aba  ← OBRIGATÓRIO (" + str(len(new_tab_links)) + " links)" if new_tab_links else ""}
{"7. [functional] Testar tabs e abas  ← OBRIGATÓRIO (" + str(len(tabs)) + " tabs)" if tabs else ""}

LEMBRETE CRÍTICO:
- Elementos com element_type "nav_item", "menu_item" ou "interactive" SÃO clicáveis mesmo sendo <div>/<span>/<li>
  Use: text=Texto, role=button[name="Texto"], role=link[name="Texto"]
- Elementos com has_js_event=true: Click + Wait For Url OU Wait For Elements State
- Elementos com opens_new_tab=true: Click → Switch Page    NEW → validate → Close Page → Switch Page    FIRST

Gere agora o arquivo .robot completo:
"""


# ── Gerador principal ─────────────────────────────────────────────────────────

def generate(result: PageScrapeResult, output_path: Path) -> str:
    """
    Chama a API do Google Gemini com retry automático.
    Implementa backoff exponencial para erros 503 (Service Unavailable).
    Retorna o conteúdo do arquivo.
    """
    logger.step(3, "Gerando cenários de teste com IA")
    logger.info(f"Modelo: {AI_MODEL}")
    nav_count  = len([e for e in result.elements if e.in_nav or e.element_type in ("nav_item", "menu_item")])
    form_count = len([e for e in result.elements if e.element_type in ("input", "select", "textarea")])
    logger.info(f"Elementos: {len(result.elements)} total | {nav_count} navegação | {form_count} formulário")

    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY não configurada. Gerando template padrão.")
        return _fallback_template(result, output_path)

    url = GEMINI_API_URL.format(model=AI_MODEL, key=GEMINI_API_KEY)
    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"parts": [{"text": _build_prompt(result)}]}],
        "generationConfig": {"maxOutputTokens": AI_MAX_TOKENS},
    }

    # ── Retry com backoff exponencial ────────────────────────────────────────
    max_retries = 5
    retry_delay = 2  # segundos
    
    for attempt in range(1, max_retries + 1):
        try:
            with logger.console.status("[cyan]Aguardando resposta da IA...[/cyan]"):
                resp = requests.post(url, json=payload, timeout=120)
                resp.raise_for_status()
                data = resp.json()
            break  # Sucesso, sai do loop
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 503 and attempt < max_retries:
                wait_time = retry_delay * (2 ** (attempt - 1))  # 2, 4, 8, 16, 32 segundos
                logger.warning(
                    f"⚠ Serviço indisponível (503). Tentativa {attempt}/{max_retries}. "
                    f"Aguardando {wait_time}s antes de tentar novamente..."
                )
                time.sleep(wait_time)
                continue
            else:
                logger.error(f"❌ Erro HTTP {e.response.status_code}: {e.response.reason}")
                if e.response.status_code == 429:
                    logger.error("Quota de requisições excedida. Verifique sua chave API no Google Cloud.")
                elif e.response.status_code == 403:
                    logger.error("Acesso negado. Verifique sua chave API e permissões.")
                raise
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Erro de conexão: {e}")
            raise

    candidate = data["candidates"][0]
    finish_reason = candidate.get("finishReason", "STOP")
    if finish_reason == "MAX_TOKENS":
        logger.warning(
            f"⚠ Resposta truncada pelo limite de tokens ({AI_MAX_TOKENS}). "
            "O arquivo .robot pode estar incompleto e não gerar report.html. "
            "Aumente AI_MAX_TOKENS em config/settings.py ou simplifique o prompt."
        )

    robot_content = candidate["content"]["parts"][0]["text"].strip()

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
    nav     = result.nav_items[:5]

    _generic = {"//*", "//a", "//button", "//input", "//select", "//textarea", "//div", "//span", "//li"}

    def _locator(e) -> str | None:
        if e.id:
            return f"id={e.id}"
        if e.data_testid:
            return f"[data-testid='{e.data_testid}']"
        if e.aria_label and len(e.aria_label) < 60:
            return f"[aria-label='{e.aria_label}']"
        if e.text and len(e.text.strip()) < 60:
            return f"text={e.text.strip()[:60]}"
        if e.css_selector and e.css_selector not in {"a", "button", "input", "div", "span", "li", "nav"}:
            return f"css={e.css_selector}"
        if e.xpath and e.xpath not in _generic:
            return f"xpath={e.xpath}"
        return None

    lines = [
        "*** Settings ***",
        "Library    Browser",
        "",
        "Test Setup     Abrir Navegador",
        "Suite Teardown    Close Browser",
        "",
        "*** Variables ***",
        f"${{URL}}        {result.url}",
        "${BROWSER}    chromium",
        "${HEADLESS}    True",
        "",
    ]

    for e in high:
        if e.id:
            var = e.id.upper().replace("-", "_").replace(" ", "_")[:30]
            lines.append(f"${{{var}}}    id={e.id}")
        elif e.data_testid:
            var = e.data_testid.upper().replace("-", "_")[:30]
            lines.append(f"${{{var}}}    [data-testid='{e.data_testid}']")

    lines += [
        "",
        "*** Test Cases ***",
        "",
        "Verificar Carregamento Da Página",
        "    [Documentation]    Verifica que a página carrega corretamente com os elementos essenciais",
        "    [Tags]    smoke",
    ]
    for e in high[:8]:
        loc = _locator(e)
        if loc:
            lines.append(f"    Wait For Elements State    {loc}    attached    timeout=10s")

    lines += [
        "",
        "Verificar Elementos Interativos",
        "    [Documentation]    Verifica presença e visibilidade dos elementos interativos principais",
        "    [Tags]    smoke    functional",
    ]
    for e in (inputs + [x for x in high if x.element_type == "button"])[:5]:
        loc = _locator(e)
        if loc:
            lines.append(f"    Wait For Elements State    {loc}    visible    timeout=10s")

    if nav:
        lines += [
            "",
            "Testar Itens De Navegação",
            "    [Documentation]    Verifica que os itens de navegação funcionam corretamente",
            "    [Tags]    navigation",
        ]
        for e in nav[:4]:
            loc = _locator(e)
            if loc:
                lines.append(f"    Aguardar E Clicar    {loc}")
                lines.append("    Wait For Load State    load    timeout=30s")

    if links:
        lines += [
            "",
            "Verificar Links Principais",
            "    [Documentation]    Verifica que os links principais funcionam",
            "    [Tags]    functional",
        ]
        for e in links[:3]:
            loc = _locator(e)
            if loc:
                lines.append(f"    Wait For Elements State    {loc}    visible    timeout=10s")

    if inputs:
        lines += [
            "",
            "Testar Formulário Com Dados Inválidos",
            "    [Documentation]    Testa validação do formulário com dados inválidos ou vazios",
            "    [Tags]    negative    forms",
        ]
        btn = next((e for e in high if e.element_type == "button"), None)
        if btn:
            bloc = _locator(btn)
            if bloc:
                lines.append(f"    Aguardar E Clicar    {bloc}")
                lines.append("    # Verificar mensagem de erro de validação")

    lines += [
        "",
        "*** Keywords ***",
        "",
        "Abrir Navegador",
        "    [Documentation]    Abre o browser e carrega a URL configurada",
        "    New Browser    ${BROWSER}    headless=${HEADLESS}",
        "    New Page    ${URL}",
        "    Wait For Load State    load    timeout=30s",
        "",
        "Aguardar E Clicar",
        "    [Arguments]    ${locator}",
        "    [Documentation]    Aguarda elemento visível e clica",
        "    Wait For Elements State    ${locator}    visible    timeout=10s",
        "    Click    ${locator}",
        "",
        "Preencher Campo",
        "    [Arguments]    ${locator}    ${valor}",
        "    [Documentation]    Aguarda campo visível e preenche",
        "    Wait For Elements State    ${locator}    visible    timeout=10s",
        "    Fill Text    ${locator}    ${valor}",
    ]

    content = "\n".join(lines)
    output_path.write_text(content, encoding="utf-8")
    logger.success(f"Template padrão salvo: {output_path.name}")
    return content
