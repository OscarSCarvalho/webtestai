# WebTestAI

Ferramenta de automação inteligente de testes web com IA. Dado uma URL, o WebTestAI abre a página no browser, mapeia **todos** os elementos interativos (incluindo componentes React, Angular, Vue e navbars customizadas), envia para o **Google Gemini** gerar cenários de teste e executa tudo automaticamente com **Robot Framework**.

---

## Como funciona

```
URL → [Scraper JS] → [IA Gemini] → [Robot Framework] → Relatório HTML
```

| Etapa | Módulo | O que faz |
|-------|--------|-----------|
| 1 | `scraper.py` | Abre o browser com Playwright, renderiza a página e executa JavaScript para mapear **todos** os elementos interativos — incluindo `<div>`, `<span>`, `<li>` com `onclick`, `role="button"`, `cursor:pointer` e componentes de frameworks modernos |
| 2 | `ai_generator.py` | Envia os elementos organizados por seção (navbar, formulários, botões, links) para o Google Gemini 2.5 Flash, que gera um arquivo `.robot` completo com 5+ cenários de teste |
| 3 | `executor.py` | Roda o `.robot` com Robot Framework e Browser Library (Playwright) |
| 4 | `reporter.py` | Salva `report.html`, `log.html`, `elements.json` e abre o relatório no browser |

---

## Pré-requisitos

- Python 3.9 ou superior
- Node.js instalado (necessário para `rfbrowser init`)
- Conta Google para obter API key gratuita do Gemini

---

## Instalação

### 1. Clonar o repositório

```bash
git clone https://github.com/OscarSCarvalho/webtestai.git
cd webtestai
```

### 2. Criar e ativar o ambiente virtual

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Instalar dependências Python

```bash
pip install -r webtestai/requirements.txt
```

### 4. Instalar browsers

```bash
playwright install chromium
rfbrowser init
```

### 5. Configurar a API key do Gemini

Acesse [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey), crie uma API key gratuita e crie o arquivo `webtestai/config/.env`:

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

Execute na raiz do repositório e responda às perguntas no terminal:

```bash
python run_interactive.py
```

O menu apresenta 4 opções:

```
[1] Testes completos com IA  + browser visível   (recomendado)
[2] Testes completos com IA  + headless (sem UI)
[3] Testes sem IA (template padrão) + browser visível
[4] Apenas capturar elementos da página
```

### Linha de comando

```bash
# Execução padrão (headless, com IA)
python webtestai/main.py https://seusite.com

# Mostrar o browser durante a execução (recomendado para sites com anti-bot)
python webtestai/main.py https://seusite.com --headed

# Só fazer scrape, sem gerar testes
python webtestai/main.py https://seusite.com --only-scrape

# Gerar testes sem IA (não precisa de API key)
python webtestai/main.py https://seusite.com --no-ai

# Usar outro browser
python webtestai/main.py https://seusite.com --browser firefox

# Não abrir o relatório automaticamente no browser
python webtestai/main.py https://seusite.com --no-report
```

---

## Elementos detectados

O scraper usa JavaScript nativo via `page.evaluate()` para mapear **todos** os elementos interativos da página, independente da tag HTML usada. Detecta:

### Por tag HTML
| Tag | Tipo detectado |
|-----|---------------|
| `<a>`, `<button>` | link, button |
| `<input>`, `<select>`, `<textarea>` | input, select, textarea |
| `<form>` | form |
| `<details>`, `<summary>`, `<label>` | interactive |

### Por atributos e comportamento
| Critério de detecção | Tipo resultante |
|---------------------|-----------------|
| `role="button"` ou `role="link"` | button / link |
| `role="menuitem"` | menu_item |
| `role="tab"` | tab |
| `role="checkbox"` / `"radio"` / `"switch"` | checkbox / radio / switch |
| `onclick`, `ng-click`, `@click` | interactive |
| `tabindex >= 0` | interactive |
| `cursor: pointer` no CSS + texto visível | interactive |
| `data-toggle`, `data-bs-toggle` | interactive |

### Por contexto na página
Cada elemento recebe metadados de localização:

| Campo | Detectado por |
|-------|--------------|
| `in_nav: true` | Dentro de `<nav>`, `[role="navigation"]`, `.navbar`, `.nav-list`, `.main-nav`, etc. |
| `in_header: true` | Dentro de `<header>`, `.site-header`, `.top-header` |
| `in_footer: true` | Dentro de `<footer>`, `.site-footer` |
| `in_menu: true` | Dentro de `[role="menu"]`, `.dropdown-menu`, `.submenu` |
| `opens_new_tab: true` | `target="_blank"` |
| `has_js_event: true` | `onclick`, `ng-click`, `@click` presentes |

---

## Estratégia de locators gerados

Os locators são gerados em ordem de estabilidade, priorizando seletores semânticos:

```
1. id               → id=login-button
2. data-testid      → [data-testid="submit"]
3. aria-label       → [aria-label="Fechar menu"]
4. classes CSS      → button.btn-primary
5. name             → input[name="email"]
6. xpath com texto  → //button[normalize-space()='Login']
```

Na geração de testes, a IA usa adicionalmente **role selectors** do Playwright, que são os mais robustos para apps modernas:

```
role=button[name="Login"]        → funciona seja <button>, <div> ou <span>
role=link[name="Home"]           → exact match — não confunde "Home" com "Homepage"
role=tab[name="Detalhes"]        → detecta tabs mesmo sem tag <tab>
```

---

## Relatórios gerados

Cada execução cria uma pasta em `reports/` com o nome `dominio_YYYYMMDD_HHMMSS`:

```
reports/
└── www_saucedemo_com_20260617_183000/
    ├── elements.json     ← Todos os elementos extraídos da página
    ├── scenarios.robot   ← Arquivo de testes gerado pela IA
    ├── report.html       ← Relatório visual (abra no browser)
    ├── log.html          ← Log detalhado de cada passo executado
    └── output.xml        ← Saída XML do Robot Framework
```

### Como ler o relatório

Abra `report.html` em qualquer browser. Você verá:

- **Verde** — testes que passaram
- **Vermelho** — testes que falharam, com a mensagem de erro
- Clique em qualquer teste para expandir os passos executados

---

## Configurações (config/.env)

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `GEMINI_API_KEY` | — | API key do Google Gemini (obrigatória para modo IA) |
| `DEFAULT_BROWSER` | `chromium` | Browser padrão: `chromium`, `firefox` ou `webkit` |
| `HEADLESS` | `true` | `true` = sem janela, `false` = browser visível |
| `PAGE_TIMEOUT` | `30` | Segundos para aguardar o carregamento da página no scrape |
| `MAX_ELEMENTS_PER_TYPE` | `40` | Máximo de elementos capturados por tipo |

---

## Estrutura do repositório

```
webtestai/                       ← raiz do repositório
├── README.md                    ← esta documentação
├── run_interactive.py           ← runner com menu interativo
├── .gitignore
│
└── webtestai/                   ← código principal da ferramenta
    ├── main.py                  ← ponto de entrada CLI
    ├── requirements.txt         ← dependências Python
    │
    ├── config/
    │   ├── settings.py          ← carrega variáveis do .env
    │   ├── .env.example         ← modelo de configuração
    │   └── .env                 ← sua config local (não commitar)
    │
    ├── core/
    │   ├── models.py            ← dataclasses WebElement e PageScrapeResult
    │   └── logger.py            ← output colorido com Rich
    │
    ├── modules/
    │   ├── scraper.py           ← módulo 1: detecção via JavaScript + fallback BeautifulSoup
    │   ├── ai_generator.py      ← módulo 2: geração de testes via Gemini REST API
    │   ├── executor.py          ← módulo 3: execução com Robot Framework
    │   └── reporter.py          ← módulo 4: relatório e abertura no browser
    │
    └── reports/                 ← relatórios gerados (ignorado pelo git)
```

---

## Modo sem IA

Se não tiver a API key do Gemini ou quiser uma execução rápida, use `--no-ai`.
O sistema gera um template básico com os elementos capturados:

```bash
python webtestai/main.py https://seusite.com --no-ai
```

Os testes gerados verificam:
- Carregamento da página e presença dos elementos essenciais
- Funcionamento dos itens de navegação detectados
- Validação de formulário com envio sem dados

---

## Dicas por tipo de site

### Sites com navegação rica (React, Angular, Vue, Next.js)
O scraper detecta automaticamente componentes customizados via `role`, `onclick` e `cursor:pointer`.
Use `--only-scrape` para inspecionar o `elements.json` e validar a detecção antes de rodar os testes:
```bash
python webtestai/main.py https://meusite.com --only-scrape
```

### Sites com proteção anti-bot (Amazon, Mercado Livre, etc.)
Use `--headed` — o browser visível reduz a detecção:
```bash
python webtestai/main.py https://www.amazon.com.br --headed
```

### Sites de login e formulários (sistemas internos, demos)
Funcionam muito bem em headless. A IA gera automaticamente:
- Teste de login com credenciais válidas
- Teste com credenciais inválidas
- Teste com campos obrigatórios vazios

### Sites institucionais e portais públicos
Funcionam sem problemas com as configurações padrão.

---

## Solução de problemas

### `UnicodeEncodeError` no terminal Windows
O `settings.py` aplica UTF-8 automaticamente. Se ainda ocorrer:
```bash
set PYTHONIOENCODING=utf-8
python webtestai/main.py https://seusite.com
```

### `networkidle atingiu timeout` (aviso em amarelo)
Comportamento normal em sites com requisições contínuas (e-commerces, analytics).
O scraper usa `domcontentloaded` como fallback automaticamente. Não afeta o funcionamento.

### Poucos elementos capturados no `elements.json`
- Use `--only-scrape` e abra o `elements.json` para inspecionar o que foi capturado
- Se o site carrega conteúdo com atraso, aumente `PAGE_TIMEOUT` no `.env`
- Use `--headed` para ver se o site exige login ou resolve um captcha

### Testes falhando com "strict mode violation"
Ocorre quando um seletor como `text=Produtos` resolve para mais de um elemento.
A IA gera locators mais precisos nas próximas execuções. Como contorno manual, edite o `scenarios.robot` adicionando `>> nth=0` ao seletor ou troque por `role=link[name="Produtos"]`.

### `Suite contains no tests or tasks`
O arquivo `.robot` foi gerado incompleto (limite de tokens atingido). Execute novamente ou aumente `AI_MAX_TOKENS` em `config/settings.py`.

### Testes com assertions erradas
A IA pode assumir textos de erro ou URLs que diferem do site real.
Edite o `scenarios.robot` gerado e ajuste os valores esperados, ou execute novamente.

---

## Exemplo de execução — site com navbar

```
╭──────────────────────────────────────────────────────────────────────────────╮
│  WebTestAI                                                                   │
│  Automação inteligente de testes web                                         │
╰──────────────────────────────────────────────────────────────────────────────╯

[ 1 ] Abrindo browser e carregando página
  →  URL: https://books.toscrape.com
  →  Browser: chromium | headless=True
  ✓  Página carregada: All products | Books to Scrape - Sandbox

[ 2 ] Inspecionando e classificando elementos
  ✓  41 elementos capturados  (41 alta prioridade, 38 de navegação)
  ●  link   //a   Books to Scrape
  ●  link   //a   Home
  ●  link   //a   Travel
  ●  link   //a   Mystery
  ●  link   //a   Historical Fiction
  ...

[ 3 ] Gerando cenários de teste com IA
  →  Modelo: gemini-2.5-flash
  →  Elementos: 41 total | 38 navegação | 0 formulário
  ✓  Cenários salvos: scenarios.robot
  →  Test cases gerados: ~29

[ 4 ] Executando testes com Robot Framework
  Testar Carregamento Inicial E Elementos Essenciais   | PASS |
  Testar Navegação Principal Por Categorias            | PASS |
  Testar Visualização Detalhes Do Primeiro Livro       | FAIL |
  Testar Navegação De Paginação                        | FAIL |
  Testar Acesso A URL Inexistente                      | FAIL |
  5 tests, 2 passed, 3 failed

[ 5 ] Resumo da execução
  Página:  All products | Books to Scrape - Sandbox
  URL:     https://books.toscrape.com/
  Status dos testes: COM FALHAS ⚠
```

---

## Prompts da IA

Os prompts estão em `webtestai/modules/ai_generator.py`:

| Constante / Função | Descrição |
|--------------------|-----------|
| `SYSTEM_PROMPT` | Instruções fixas enviadas a cada chamada: role selectors, prevenção de strict mode violation, padrões para navbar/dropdown/modal/tab/SPA, keywords válidas e proibidas da Browser Library |
| `_build_prompt()` | Prompt dinâmico com URL, título e elementos organizados por seção (navegação, formulários, botões, links, elementos interativos customizados) |

Para personalizar os cenários gerados, edite o `SYSTEM_PROMPT` diretamente.

---

## Tecnologias utilizadas

| Tecnologia | Versão | Uso |
|-----------|--------|-----|
| Python | 3.9+ | Linguagem principal |
| Playwright | 1.60+ | Renderização do browser e execução de JavaScript para detecção de elementos |
| BeautifulSoup4 | 4.12+ | Fallback de parsing HTML quando a avaliação JS falha |
| Robot Framework | 7.0+ | Execução dos testes gerados |
| Browser Library | 20.0+ | Keywords Playwright dentro do Robot Framework |
| Google Gemini 2.5 Flash | — | Geração de cenários de teste com IA (REST API, gratuito) |
| Rich | 13.7+ | Output colorido e formatado no terminal |

---

## Licença

MIT
