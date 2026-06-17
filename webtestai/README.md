# WebTestAI

Ferramenta de automação inteligente de testes web. Dado uma URL, o WebTestAI abre a página no browser, mapeia **todos** os elementos interativos, envia para o Google Gemini gerar cenários de teste e executa tudo automaticamente com Robot Framework.

---

## Como funciona

```
URL → [Scraper JS] → [IA Gemini] → [Robot Framework] → Relatório HTML
```

| Etapa | O que faz |
|-------|-----------|
| 1. Scraper | Abre o browser com Playwright e executa JavaScript para mapear todos os elementos interativos — incluindo `<div>`, `<span>`, `<li>` com `onclick`, `role="button"`, `cursor:pointer` e componentes de frameworks modernos (React, Vue, Angular) |
| 2. IA | Envia os elementos organizados por seção (navbar, formulários, botões, links) para o Google Gemini 2.5 Flash, que gera um arquivo `.robot` completo com 5+ cenários de teste |
| 3. Executor | Roda o `.robot` com Robot Framework e Browser Library |
| 4. Relatório | Salva `report.html`, `log.html`, `elements.json` e abre o relatório no browser |

---

## Pré-requisitos

- Python 3.9 ou superior
- Node.js instalado (necessário para `rfbrowser init`)
- Conta Google para obter API key gratuita do Gemini

---

## Instalação

### 1. Criar e ativar o ambiente virtual

```bash
cd webtestai
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 2. Instalar dependências Python

```bash
pip install -r requirements.txt
```

### 3. Instalar browsers

```bash
playwright install chromium
rfbrowser init
```

### 4. Configurar a API key do Gemini

Acesse [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey), crie uma API key gratuita e crie o arquivo `config/.env`:

```env
GEMINI_API_KEY=AIzaSy...sua_chave_aqui
DEFAULT_BROWSER=chromium
HEADLESS=true
PAGE_TIMEOUT=30
MAX_ELEMENTS_PER_TYPE=40
```

> A API key do Gemini 2.5 Flash é gratuita com limite de 1.500 requisições por dia.

---

## Como usar

### Modo interativo (recomendado)

Execute na raiz do repositório:

```bash
python run_interactive.py
```

```
[1] Testes completos com IA  + browser visível   (recomendado)
[2] Testes completos com IA  + headless (sem UI)
[3] Testes sem IA (template padrão) + browser visível
[4] Apenas capturar elementos da página
```

### Linha de comando

```bash
# Execução padrão (headless, com IA)
python main.py https://seusite.com

# Mostrar o browser durante a execução
python main.py https://seusite.com --headed

# Só fazer scrape, sem gerar testes
python main.py https://seusite.com --only-scrape

# Gerar testes sem IA
python main.py https://seusite.com --no-ai

# Usar outro browser
python main.py https://seusite.com --browser firefox

# Não abrir o relatório automaticamente
python main.py https://seusite.com --no-report
```

---

## Elementos detectados

O scraper usa JavaScript nativo via `page.evaluate()` para mapear todos os elementos interativos:

### Por tag HTML
`<a>`, `<button>`, `<input>`, `<select>`, `<textarea>`, `<form>`, `<details>`, `<summary>`, `<label>`

### Por atributos e comportamento
| Critério | Tipo resultante |
|----------|----------------|
| `role="button"` | button |
| `role="link"` | link |
| `role="menuitem"` | menu_item |
| `role="tab"` | tab |
| `role="checkbox"` / `"radio"` / `"switch"` | checkbox / radio / switch |
| `onclick`, `ng-click`, `@click` | interactive |
| `tabindex >= 0` | interactive |
| `cursor: pointer` + texto visível | interactive |
| `data-toggle`, `data-bs-toggle` | interactive |

### Metadados de contexto por elemento

```json
{
  "in_nav": true,          // dentro de <nav>, .navbar, .nav-list, etc.
  "in_header": true,       // dentro de <header>, .site-header
  "in_footer": true,       // dentro de <footer>, .site-footer
  "in_menu": true,         // dentro de [role="menu"], .dropdown-menu
  "opens_new_tab": true,   // target="_blank"
  "has_js_event": true,    // onclick, ng-click, @click presentes
  "is_visible": true,
  "is_enabled": true
}
```

---

## Estratégia de locators

Gerados em ordem de estabilidade:

```
1. id               → id=login-button
2. data-testid      → [data-testid="submit"]
3. aria-label       → [aria-label="Fechar menu"]
4. classes CSS      → button.btn-primary
5. name             → input[name="email"]
6. xpath com texto  → //button[normalize-space()='Login']
```

A IA usa adicionalmente **role selectors** do Playwright:

```
role=button[name="Login"]     → funciona seja <button>, <div> ou <span>
role=link[name="Home"]        → exact match — diferencia "Home" de "Homepage"
role=tab[name="Detalhes"]     → detecta tabs sem <tab> nativa
```

---

## Relatórios gerados

```
reports/
└── dominio_YYYYMMDD_HHMMSS/
    ├── elements.json     ← Todos os elementos extraídos da página
    ├── scenarios.robot   ← Arquivo de testes gerado pela IA
    ├── report.html       ← Relatório visual
    ├── log.html          ← Log detalhado de cada passo
    └── output.xml        ← Saída XML do Robot Framework
```

---

## Configurações (config/.env)

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `GEMINI_API_KEY` | — | API key do Google Gemini (obrigatória para modo IA) |
| `DEFAULT_BROWSER` | `chromium` | Browser padrão: `chromium`, `firefox` ou `webkit` |
| `HEADLESS` | `true` | `true` = sem janela, `false` = browser visível |
| `PAGE_TIMEOUT` | `30` | Segundos para aguardar o carregamento da página |
| `MAX_ELEMENTS_PER_TYPE` | `40` | Máximo de elementos capturados por tipo |

---

## Estrutura do projeto

```
webtestai/
├── main.py                  ← Ponto de entrada CLI
├── requirements.txt         ← Dependências Python
│
├── config/
│   ├── settings.py          ← Carrega variáveis do .env
│   ├── .env                 ← Sua configuração local (não commitar)
│   └── .env.example         ← Modelo de configuração
│
├── core/
│   ├── models.py            ← Dataclasses: WebElement, PageScrapeResult
│   └── logger.py            ← Output colorido no terminal
│
├── modules/
│   ├── scraper.py           ← Módulo 1: detecção via JavaScript + fallback BeautifulSoup
│   ├── ai_generator.py      ← Módulo 2: geração de testes via Gemini REST API
│   ├── executor.py          ← Módulo 3: execução com Robot Framework
│   └── reporter.py          ← Módulo 4: salva arquivos e abre o relatório
│
└── reports/                 ← Relatórios gerados (criado automaticamente)
```

---

## Modo sem IA

```bash
python main.py https://seusite.com --no-ai
```

Gera um template básico verificando:
- Carregamento da página e presença dos elementos essenciais
- Funcionamento dos itens de navegação detectados
- Validação de formulário com envio sem dados

---

## Solução de problemas

### `networkidle atingiu timeout`
Normal em sites com requisições contínuas. O scraper usa `domcontentloaded` como fallback automaticamente.

### Poucos elementos capturados
Use `--only-scrape` e inspecione o `elements.json`. Se o site carrega conteúdo com atraso, aumente `PAGE_TIMEOUT` no `.env`.

### Testes falhando com "strict mode violation"
Um seletor resolve para múltiplos elementos. Edite o `scenarios.robot` adicionando `>> nth=0` ao seletor ou use `role=link[name="texto exato"]`.

### `Suite contains no tests or tasks`
Arquivo `.robot` gerado incompleto (limite de tokens). Execute novamente ou aumente `AI_MAX_TOKENS` em `config/settings.py`.
