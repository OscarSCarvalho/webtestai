"""Modelos de dados compartilhados entre os módulos."""

from dataclasses import dataclass, field, asdict
from typing import Optional, List
from enum import Enum


class Priority(str, Enum):
    HIGH   = "high"
    MEDIUM = "medium"
    LOW    = "low"


class ElementType(str, Enum):
    INPUT       = "input"
    BUTTON      = "button"
    LINK        = "link"
    SELECT      = "select"
    TEXTAREA    = "textarea"
    FORM        = "form"
    HEADING     = "heading"
    IMAGE       = "image"
    NAV_ITEM    = "nav_item"     # itens de navbar/menu de navegação
    MENU_ITEM   = "menu_item"    # itens de menu (role=menuitem, dropdown)
    TAB         = "tab"          # abas (role=tab)
    CHECKBOX    = "checkbox"     # checkboxes customizadas
    RADIO       = "radio"        # radio buttons customizados
    SWITCH      = "switch"       # toggles/switches
    INTERACTIVE = "interactive"  # qualquer elemento clicável customizado
    OTHER       = "other"


@dataclass
class WebElement:
    tag:           str
    element_type:  str
    text:          Optional[str] = None
    id:            Optional[str] = None
    name:          Optional[str] = None
    placeholder:   Optional[str] = None
    href:          Optional[str] = None
    aria_label:    Optional[str] = None
    css_selector:  str = ""
    xpath:         str = ""
    priority:      str = Priority.MEDIUM
    # Campos estendidos de detecção moderna
    role:          Optional[str] = None
    data_testid:   Optional[str] = None
    is_visible:    bool = True
    is_enabled:    bool = True
    opens_new_tab: bool = False
    has_js_event:  bool = False
    in_nav:        bool = False
    in_header:     bool = False
    in_footer:     bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    def best_locator(self) -> str:
        """Retorna o locator mais estável disponível."""
        if self.id:
            return f"id={self.id}"
        if self.data_testid:
            return f"[data-testid='{self.data_testid}']"
        if self.css_selector:
            return f"css={self.css_selector}"
        return f"xpath={self.xpath}"

    def display(self) -> str:
        parts = [f"[{self.element_type}]", self.xpath]
        if self.text:
            parts.append(f'"{self.text[:40]}"')
        if self.placeholder:
            parts.append(f"placeholder='{self.placeholder}'")
        return "  ".join(parts)


@dataclass
class PageScrapeResult:
    url:      str
    title:    str
    elements: List[WebElement] = field(default_factory=list)

    @property
    def high_priority(self) -> List[WebElement]:
        return [e for e in self.elements if e.priority == Priority.HIGH]

    @property
    def inputs(self) -> List[WebElement]:
        return [e for e in self.elements if e.element_type == ElementType.INPUT]

    @property
    def buttons(self) -> List[WebElement]:
        return [e for e in self.elements if e.element_type == ElementType.BUTTON]

    @property
    def links(self) -> List[WebElement]:
        return [e for e in self.elements if e.element_type == ElementType.LINK]

    @property
    def nav_items(self) -> List[WebElement]:
        return [e for e in self.elements if e.element_type in (ElementType.NAV_ITEM, ElementType.MENU_ITEM) or e.in_nav]

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "title": self.title,
            "total": len(self.elements),
            "elements": [e.to_dict() for e in self.elements],
        }
