"""
Módulo 1 — Scraper de Elementos Web
Usa Playwright com avaliação JavaScript para detectar TODOS os elementos interativos,
incluindo componentes customizados de frameworks modernos (React, Vue, Angular, Next.js),
divs clicáveis, itens de navbar, menus, tabs, modais e qualquer elemento com cursor:pointer.
"""

import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.models import WebElement, PageScrapeResult, Priority, ElementType
from core import logger
from config.settings import MAX_ELEMENTS_PER_TYPE, HEADLESS, PAGE_TIMEOUT, DEFAULT_BROWSER


# ── JavaScript de extração completa ──────────────────────────────────────────
#
# Executado diretamente no contexto do browser após renderização completa.
# Detecta qualquer elemento interativo independente do tag HTML.

_JS_EXTRACT = """
() => {
    const INTERACTIVE_TAGS = new Set(['a', 'button', 'input', 'select', 'textarea', 'details', 'summary', 'label']);
    const INTERACTIVE_ROLES = new Set([
        'button', 'link', 'menuitem', 'menuitemcheckbox', 'menuitemradio',
        'tab', 'option', 'checkbox', 'radio', 'switch', 'combobox',
        'listbox', 'spinbutton', 'slider', 'searchbox', 'textbox',
        'treeitem', 'row', 'gridcell', 'columnheader', 'rowheader'
    ]);

    function getCssSelector(el) {
        if (el.id) return '#' + el.id;
        const testId = el.getAttribute('data-testid');
        if (testId) return '[data-testid="' + testId + '"]';
        const ariaLabel = el.getAttribute('aria-label');
        if (ariaLabel && ariaLabel.length < 60) return '[aria-label="' + ariaLabel + '"]';
        const classes = Array.from(el.classList).filter(c =>
            !c.match(/^(js-|ng-|v-|_[a-z0-9]{6}|ember|svelte-|css-|sc-)/)
        ).slice(0, 2);
        if (classes.length) return el.tagName.toLowerCase() + '.' + classes.join('.');
        const name = el.getAttribute('name');
        if (name) return el.tagName.toLowerCase() + '[name="' + name + '"]';
        return el.tagName.toLowerCase();
    }

    function getXPath(el) {
        if (el.id) return "//*[@id='" + el.id + "']";
        const testId = el.getAttribute('data-testid');
        if (testId) return "//*[@data-testid='" + testId + "']";
        const ariaLabel = el.getAttribute('aria-label');
        if (ariaLabel && ariaLabel.length < 50) return "//*[@aria-label='" + ariaLabel.replace(/'/g, "\\'") + "']";
        const name = el.getAttribute('name');
        if (name) return '//' + el.tagName.toLowerCase() + "[@name='" + name + "']";
        const text = (el.innerText || el.textContent || '').trim();
        if (text && text.length > 0 && text.length < 50) {
            const safe = text.replace(/'/g, "\\'");
            return '//' + el.tagName.toLowerCase() + "[normalize-space()='" + safe + "']";
        }
        return '//' + el.tagName.toLowerCase();
    }

    function getContext(el) {
        return {
            inNav:     !!el.closest('nav, [role="navigation"], .navbar, .nav-bar, .navigation, .main-nav, .site-nav, .top-nav, header ul, .menu-primary, .primary-menu, .nav-list'),
            inHeader:  !!el.closest('header, [role="banner"], .site-header, .page-header, .top-header'),
            inFooter:  !!el.closest('footer, [role="contentinfo"], .site-footer, .page-footer'),
            inSidebar: !!el.closest('aside, [role="complementary"], .sidebar, .side-nav, .lateral'),
            inMenu:    !!el.closest('[role="menu"], [role="menubar"], .dropdown-menu, .submenu, .sub-menu'),
            inForm:    !!el.closest('form'),
            inDialog:  !!el.closest('[role="dialog"], dialog'),
        };
    }

    function isInteractive(el) {
        const tn = el.tagName;
        if (!tn || tn === 'BODY' || tn === 'HTML' || tn === 'HEAD' || tn === 'SCRIPT' || tn === 'STYLE') return false;
        if (el.closest('script, style, noscript, template')) return false;

        const tag  = tn.toLowerCase();
        const role = (el.getAttribute('role') || '').toLowerCase();

        if (INTERACTIVE_TAGS.has(tag)) return true;
        if (role && INTERACTIVE_ROLES.has(role)) return true;
        if (el.hasAttribute('onclick')) return true;
        if (el.hasAttribute('ng-click') || el.hasAttribute('@click') || el.hasAttribute('v-on:click')) return true;
        if (el.hasAttribute('data-action') || el.hasAttribute('data-toggle') || el.hasAttribute('data-bs-toggle')) return true;

        const tabindex = el.getAttribute('tabindex');
        if (tabindex !== null && tabindex !== '-1') return true;

        try {
            const style = window.getComputedStyle(el);
            if (style.cursor === 'pointer') {
                const text  = (el.innerText || '').trim();
                const label = el.getAttribute('aria-label');
                if ((text && text.length > 0 && text.length < 120) || label) return true;
            }
        } catch(e) {}

        return false;
    }

    function isVisible(el) {
        try {
            const rect  = el.getBoundingClientRect();
            const style = window.getComputedStyle(el);
            return (
                rect.width  > 0 &&
                rect.height > 0 &&
                style.visibility !== 'hidden' &&
                style.display    !== 'none'   &&
                parseFloat(style.opacity) > 0
            );
        } catch(e) { return true; }
    }

    function getElementType(tag, role, context) {
        if (tag === 'a' || role === 'link')                                return 'link';
        if (tag === 'button' || role === 'button')                         return 'button';
        if (tag === 'input')                                               return 'input';
        if (tag === 'select' || role === 'combobox' || role === 'listbox') return 'select';
        if (tag === 'textarea')                                            return 'textarea';
        if (tag === 'form')                                                return 'form';
        if (role === 'tab')                                                return 'tab';
        if (role === 'checkbox')                                           return 'checkbox';
        if (role === 'radio')                                              return 'radio';
        if (role === 'switch')                                             return 'switch';
        if (role === 'menuitem' || role === 'menuitemcheckbox' || role === 'menuitemradio') return 'menu_item';
        if (context.inMenu)    return 'menu_item';
        if (context.inNav || context.inHeader) return 'nav_item';
        if (context.inFooter)  return 'link';
        return 'interactive';
    }

    function getPriority(elementType, context) {
        if (['button', 'input', 'select', 'textarea', 'form', 'tab', 'checkbox', 'radio', 'switch'].includes(elementType)) return 'high';
        if (elementType === 'link')      return 'high';
        if (elementType === 'nav_item')  return 'high';
        if (elementType === 'menu_item') return 'high';
        if (context.inForm)              return 'high';
        if (context.inNav || context.inMenu) return 'high';
        return 'medium';
    }

    const results   = [];
    const seenKeys  = new Set();
    const allEls    = document.querySelectorAll('*');

    allEls.forEach(el => {
        if (!isInteractive(el)) return;

        const tag      = el.tagName.toLowerCase();
        const id       = el.id || null;
        const testId   = el.getAttribute('data-testid') || null;
        const ariaLbl  = el.getAttribute('aria-label')  || null;
        const rawText  = (el.innerText || el.textContent || '').trim().substring(0, 80);
        const role     = el.getAttribute('role') || null;

        const key = tag + '|' + (id || '') + '|' + (testId || '') + '|' + (ariaLbl || rawText).substring(0, 30);
        if (seenKeys.has(key)) return;
        seenKeys.add(key);

        const context     = getContext(el);
        const roleNorm    = (role || '').toLowerCase();
        const elementType = getElementType(tag, roleNorm, context);
        const visible     = isVisible(el);

        results.push({
            tag:           tag,
            role:          role,
            element_type:  elementType,
            text:          rawText || null,
            id:            id,
            name:          el.getAttribute('name')        || null,
            placeholder:   el.getAttribute('placeholder') || null,
            href:          (tag === 'a' ? el.getAttribute('href') : null),
            aria_label:    ariaLbl,
            data_testid:   testId,
            css_selector:  getCssSelector(el),
            xpath:         getXPath(el),
            has_onclick:   el.hasAttribute('onclick') || el.hasAttribute('ng-click') || el.hasAttribute('@click'),
            target:        el.getAttribute('target') || null,
            opens_new_tab: el.getAttribute('target') === '_blank',
            is_visible:    visible,
            is_enabled:    !el.disabled,
            in_nav:        context.inNav,
            in_header:     context.inHeader,
            in_footer:     context.inFooter,
            in_sidebar:    context.inSidebar,
            in_menu:       context.inMenu,
            in_form:       context.inForm,
            priority:      getPriority(elementType, context),
        });
    });

    return results;
}
"""

PRIORITY_ORDER = {Priority.HIGH: 0, Priority.MEDIUM: 1, Priority.LOW: 2}


def scrape(url: str, browser_name: Optional[str] = None, headless: Optional[bool] = None) -> PageScrapeResult:
    """
    Abre o browser, renderiza a página e extrai todos os elementos interativos via JavaScript.
    Detecta elementos customizados de React/Vue/Angular, navbars, menus, tabs, dropdowns, etc.
    """
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

    _browser  = browser_name or DEFAULT_BROWSER
    _headless = headless if headless is not None else HEADLESS

    logger.step(1, "Abrindo browser e carregando página")
    logger.info(f"URL: {url}")
    logger.info(f"Browser: {_browser} | headless={_headless}")

    raw_elements: list = []
    page_title = ""
    final_url  = url

    with sync_playwright() as p:
        launcher = getattr(p, _browser)
        browser  = launcher.launch(headless=_headless)
        page     = browser.new_page(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36"
            )
        )

        try:
            page.goto(url, wait_until="networkidle", timeout=PAGE_TIMEOUT * 1000)
        except PWTimeout:
            logger.warning("networkidle atingiu timeout, tentando domcontentloaded")
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=20_000)
            except PWTimeout:
                logger.warning("domcontentloaded também atingiu timeout, continuando com o que foi carregado")
        except Exception as exc:
            # Captura erros de rede (ERR_CONNECTION_REFUSED, ERR_CONNECTION_TIMED_OUT, etc.)
            err_msg = str(exc)
            logger.warning(f"Erro ao carregar com networkidle: {err_msg[:100]}")
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=20_000)
            except Exception as exc2:
                logger.warning(f"Falha também com domcontentloaded: {str(exc2)[:80]}. Continuando.")

        # Aguarda renderização de frameworks JS (React/Vue/Angular hidratam após load)
        page.wait_for_timeout(2000)

        # Segunda tentativa de networkidle para SPAs que carregam dados assíncronos
        try:
            page.wait_for_load_state("networkidle", timeout=5_000)
        except PWTimeout:
            pass

        page_title = page.title()
        final_url  = page.url

        # Extração principal via JavaScript no contexto do browser renderizado
        try:
            raw_elements = page.evaluate(_JS_EXTRACT)
        except Exception as exc:
            logger.warning(f"Extração JS falhou ({exc}), usando fallback HTML")
            raw_elements = _fallback_html_extract(page)

        browser.close()

    logger.success(f"Página carregada: {page_title}")

    # ── Conversão para WebElement ─────────────────────────────────────────────
    logger.step(2, "Inspecionando e classificando elementos")

    elements: list[WebElement] = []
    type_counts: dict[str, int] = {}

    for raw in raw_elements:
        el_type = raw.get("element_type", "interactive")

        # Limite por tipo para evitar overflow de contexto na IA
        count = type_counts.get(el_type, 0)
        if count >= MAX_ELEMENTS_PER_TYPE:
            continue
        type_counts[el_type] = count + 1

        el = WebElement(
            tag           = raw.get("tag", ""),
            element_type  = el_type,
            text          = raw.get("text"),
            id            = raw.get("id"),
            name          = raw.get("name"),
            placeholder   = raw.get("placeholder"),
            href          = raw.get("href"),
            aria_label    = raw.get("aria_label"),
            css_selector  = raw.get("css_selector", ""),
            xpath         = raw.get("xpath", ""),
            priority      = raw.get("priority", Priority.MEDIUM),
            role          = raw.get("role"),
            data_testid   = raw.get("data_testid"),
            is_visible    = raw.get("is_visible", True),
            is_enabled    = raw.get("is_enabled", True),
            opens_new_tab = raw.get("opens_new_tab", False),
            has_js_event  = raw.get("has_onclick", False),
            in_nav        = raw.get("in_nav", False),
            in_header     = raw.get("in_header", False),
            in_footer     = raw.get("in_footer", False),
        )
        elements.append(el)

    # Ordena: alta prioridade primeiro
    elements.sort(key=lambda e: PRIORITY_ORDER.get(e.priority, 3))

    result = PageScrapeResult(url=final_url, title=page_title, elements=elements)

    # ── Log resumo ────────────────────────────────────────────────────────────
    high = len(result.high_priority)
    nav  = len(result.nav_items)
    logger.success(
        f"{len(elements)} elementos capturados  "
        f"({high} alta prioridade, {nav} de navegação)"
    )
    logger.divider()

    for e in result.high_priority[:20]:
        logger.element_row(e.priority, e.element_type, e.xpath, e.placeholder or e.text or "")

    return result


# ── Fallback HTML (BeautifulSoup) usado apenas se JS falhar ──────────────────

def _fallback_html_extract(page) -> list:
    """Extração via BeautifulSoup como fallback se o evaluate JS falhar."""
    from bs4 import BeautifulSoup

    html = page.content()
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "meta", "head"]):
        tag.decompose()

    TARGETS = [
        ("input",    "input"),
        ("button",   "button"),
        ("a",        "link"),
        ("select",   "select"),
        ("textarea", "textarea"),
        ("form",     "form"),
    ]

    results = []
    seen    = set()

    for selector, el_type in TARGETS:
        for el in soup.find_all(selector)[:MAX_ELEMENTS_PER_TYPE]:
            text_raw = el.get_text(separator=" ", strip=True)
            xp_key   = f"{el.name}|{el.get('id','')}|{text_raw[:20]}"
            if xp_key in seen:
                continue
            seen.add(xp_key)

            id_val   = el.get("id") or None
            testid   = el.get("data-testid") or None
            name_val = el.get("name") or None

            if id_val:
                css_sel = f"#{id_val}"
                xpath   = f"//*[@id='{id_val}']"
            elif testid:
                css_sel = f"[data-testid='{testid}']"
                xpath   = f"//*[@data-testid='{testid}']"
            elif name_val:
                css_sel = f"{el.name}[name='{name_val}']"
                xpath   = f"//{el.name}[@name='{name_val}']"
            else:
                txt_safe = (text_raw[:40]).replace("'", "\\'") if text_raw else ""
                xpath    = f"//{el.name}[normalize-space()='{txt_safe}']" if txt_safe else f"//{el.name}"
                css_sel  = el.name

            in_nav    = bool(el.find_parent("nav"))
            in_header = bool(el.find_parent("header"))
            in_footer = bool(el.find_parent("footer"))

            priority = "high"
            if el_type in ("input", "button", "select", "textarea", "form"):
                priority = "high"
            elif el_type == "link" and el.get("href"):
                priority = "high"

            results.append({
                "tag":          el.name,
                "role":         el.get("role"),
                "element_type": el_type,
                "text":         text_raw[:80] if text_raw else None,
                "id":           id_val,
                "name":         name_val,
                "placeholder":  el.get("placeholder"),
                "href":         el.get("href"),
                "aria_label":   el.get("aria-label"),
                "data_testid":  testid,
                "css_selector": css_sel,
                "xpath":        xpath,
                "has_onclick":  bool(el.get("onclick")),
                "opens_new_tab": el.get("target") == "_blank",
                "is_visible":   True,
                "is_enabled":   not el.get("disabled"),
                "in_nav":       in_nav,
                "in_header":    in_header,
                "in_footer":    in_footer,
                "in_menu":      False,
                "in_form":      bool(el.find_parent("form")),
                "priority":     priority,
            })

    return results
