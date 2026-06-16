"""
Módulo 1 — Scraper de Elementos Web
Abre o browser com Playwright, renderiza a página e extrai
todos os elementos interativos com seus seletores.
"""

import re
import sys
from pathlib import Path
from typing import Optional

from bs4 import BeautifulSoup, Tag

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.models import WebElement, PageScrapeResult, Priority, ElementType
from core import logger
from config.settings import MAX_ELEMENTS_PER_TYPE, HEADLESS, PAGE_TIMEOUT, DEFAULT_BROWSER


# ── Seletor CSS ──────────────────────────────────────────────────────────────

def _build_css(el: Tag) -> str:
    if el.get("id"):
        return f"#{el['id']}"
    if el.get("data-testid"):
        return f"[data-testid='{el['data-testid']}']"
    classes = [c for c in el.get("class", []) if not c.startswith(("js-", "ng-", "v-"))]
    if classes:
        return f"{el.name}.{'.'.join(classes[:2])}"
    if el.get("name"):
        return f"{el.name}[name='{el['name']}']"
    if el.get("aria-label"):
        return f"{el.name}[aria-label='{el['aria-label'][:40]}']"
    parent = el.parent
    if parent and parent.name:
        siblings = list(parent.find_all(el.name, recursive=False))
        if el in siblings:
            idx = siblings.index(el) + 1
            pid = f"#{parent['id']}" if parent.get("id") else ""
            return f"{parent.name}{pid} > {el.name}:nth-of-type({idx})"
    return el.name


# ── XPath ────────────────────────────────────────────────────────────────────

def _build_xpath(el: Tag) -> str:
    if el.get("id"):
        return f"//*[@id='{el['id']}']"
    if el.get("data-testid"):
        return f"//*[@data-testid='{el['data-testid']}']"
    if el.get("name"):
        return f"//{el.name}[@name='{el['name']}']"
    text = el.get_text(strip=True)
    if text and len(text) < 50:
        safe = text.replace("'", "\\'")
        return f"//{el.name}[normalize-space()='{safe}']"
    return f"//{el.name}"


# ── Prioridade ───────────────────────────────────────────────────────────────

def _priority(el: Tag) -> str:
    tag  = el.name
    kind = el.get("type", "").lower()
    if tag == "button" or kind in {"submit", "button", "reset"}:
        return Priority.HIGH
    if tag == "a" and el.get("href"):
        return Priority.HIGH
    if tag == "input" and kind in {"text", "email", "password", "search", "tel", "number", ""}:
        return Priority.HIGH
    if tag in {"select", "textarea", "form"}:
        return Priority.HIGH
    if tag in {"h1", "h2"}:
        return Priority.MEDIUM
    return Priority.LOW


# ── Construção do elemento ────────────────────────────────────────────────────

def _make_element(el: Tag, el_type: str) -> WebElement:
    text_raw = el.get_text(separator=" ", strip=True)
    return WebElement(
        tag          = el.name,
        element_type = el_type,
        text         = text_raw[:80] if text_raw else None,
        id           = el.get("id") or None,
        name         = el.get("name") or None,
        placeholder  = el.get("placeholder") or None,
        href         = el.get("href") or None,
        aria_label   = el.get("aria-label") or None,
        css_selector = _build_css(el),
        xpath        = _build_xpath(el),
        priority     = _priority(el),
    )


# ── Scrape principal ──────────────────────────────────────────────────────────

TARGETS = [
    ("input",    ElementType.INPUT),
    ("button",   ElementType.BUTTON),
    ("a",        ElementType.LINK),
    ("select",   ElementType.SELECT),
    ("textarea", ElementType.TEXTAREA),
    ("form",     ElementType.FORM),
    ("h1",       ElementType.HEADING),
    ("h2",       ElementType.HEADING),
    ("h3",       ElementType.HEADING),
    ("img",      ElementType.IMAGE),
]

PRIORITY_ORDER = {Priority.HIGH: 0, Priority.MEDIUM: 1, Priority.LOW: 2}


def scrape(url: str, browser_name: Optional[str] = None, headless: Optional[bool] = None) -> PageScrapeResult:
    """
    Abre o browser, renderiza a página e extrai elementos.
    Retorna um PageScrapeResult com todos os elementos encontrados.
    """
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

    _browser = browser_name or DEFAULT_BROWSER
    _headless = headless if headless is not None else HEADLESS

    logger.step(1, "Abrindo browser e carregando página")
    logger.info(f"URL: {url}")
    logger.info(f"Browser: {_browser} | headless={_headless}")

    html = ""
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
            logger.warning("networkidle atingiu timeout, usando domcontentloaded")
            page.goto(url, wait_until="domcontentloaded", timeout=15_000)

        # Aguarda renderização JS
        page.wait_for_timeout(1500)

        page_title = page.title()
        final_url  = page.url
        html       = page.content()
        browser.close()

    logger.success(f"Página carregada: {page_title}")

    # ── Parsing ──────────────────────────────────────────────────────────────
    logger.step(2, "Inspecionando e classificando elementos")

    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "meta", "head"]):
        tag.decompose()

    elements: list[WebElement] = []
    seen_xpaths: set[str] = set()

    for selector, el_type in TARGETS:
        found = soup.find_all(selector)[:MAX_ELEMENTS_PER_TYPE]
        for el in found:
            xp = _build_xpath(el)
            if xp in seen_xpaths:
                continue
            seen_xpaths.add(xp)
            elements.append(_make_element(el, el_type))

    # Ordena por prioridade
    elements.sort(key=lambda e: PRIORITY_ORDER.get(e.priority, 3))

    result = PageScrapeResult(url=final_url, title=page_title, elements=elements)

    # Log resumo
    high = len(result.high_priority)
    logger.success(f"{len(elements)} elementos capturados  ({high} alta prioridade)")
    logger.divider()

    for e in result.high_priority[:20]:
        logger.element_row(e.priority, e.element_type, e.xpath, e.placeholder or e.text or "")

    return result
