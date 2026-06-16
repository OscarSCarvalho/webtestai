# WebTestAI

Ferramenta de automação inteligente de testes web. Dado uma URL, o WebTestAI abre a página no browser, extrai os elementos interativos, envia para o Google Gemini gerar cenários de teste e executa tudo automaticamente com Robot Framework.

---

## Como funciona

```
URL → [Scraper] → [IA Gemini] → [Robot Framework] → Relatório HTML
```

| Etapa | O que faz |
|-------|-----------|
| 1. Scraper | Abre o browser com Playwright, renderiza a página e extrai inputs, botões, links, selects, formulários e headings com seus seletores CSS e XPath |
| 2. IA | Envia os elementos para o Google Gemini 2.5 Flash que gera um arquivo `.robot` completo com 3+ cenários de teste |
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

Execute e responda às perguntas no terminal:

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
python main.py https://seusite.com

# Mostrar o browser durante a execução (recomendado para sites com anti-bot)
python main.py https://seusite.com --headed

# Só fazer scrape, sem gerar testes
python main.py https://seusite.com --only-scrape

# Gerar testes sem IA (não precisa de API key)
python main.py https://seusite.com --no-ai

# Usar outro browser
python main.py https://seusite.com --browser firefox

# Não abrir o relatório automaticamente no browser
python main.py https://seusite.com --no-report
```

---

## Relatórios gerados

Cada execução cria uma pasta em `reports/` com o nome `dominio_YYYYMMDD_HHMMSS`:

```
reports/
└── www_saucedemo_com_20260615_183000/
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
| `MAX_ELEMENTS_PER_TYPE` | `40` | Máximo de elementos capturados por tipo (input, button, etc.) |

---

## Estrutura do projeto

```
webtestai/
├── main.py                  ← Ponto de entrada CLI
├── run_interactive.py       ← Runner com menu interativo
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
│   ├── scraper.py           ← Módulo 1: abre o browser e extrai elementos
│   ├── ai_generator.py      ← Módulo 2: chama a API Gemini e gera o .robot
│   ├── executor.py          ← Módulo 3: executa o .robot com Robot Framework
│   └── reporter.py          ← Módulo 4: salva arquivos e abre o relatório
│
└── reports/                 ← Relatórios gerados (criado automaticamente)
```

---

## Tipos de elementos capturados

O scraper identifica e classifica os seguintes elementos por prioridade:

| Tipo | Prioridade | Exemplos |
|------|-----------|---------|
| Inputs de texto/email/senha/busca | Alta | Campos de login, busca, formulários |
| Botões e submits | Alta | "Entrar", "Comprar", "Enviar" |
| Links com href | Alta | Navegação principal, menus |
| Selects e textareas | Alta | Dropdowns, campos de comentário |
| Formulários | Alta | Tags `<form>` com ação |
| H1 e H2 | Média | Títulos da página |
| Imagens | Baixa | Tags `<img>` |

Os locators são gerados em ordem de estabilidade:

```
id → data-testid → name → classes CSS → xpath com texto
```

---

## Modo sem IA

Se não tiver a API key do Gemini ou quiser uma execução rápida, use `--no-ai`.
O sistema gera um template básico com os elementos capturados sem precisar de API:

```bash
python main.py https://seusite.com --no-ai
```

Os testes gerados verificam:
- Carregamento da página e título correto
- Presença dos elementos de alta prioridade
- Clicabilidade dos links principais

---

## Dicas por tipo de site

### Sites com proteção anti-bot (Amazon, Mercado Livre, etc.)
Use `--headed` — o browser visível reduz a detecção:
```bash
python main.py https://www.amazon.com.br --headed
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
O `settings.py` aplica UTF-8 automaticamente. Se ainda ocorrer, defina a variável antes de rodar:
```bash
set PYTHONIOENCODING=utf-8
python main.py https://seusite.com
```

### `networkidle atingiu timeout` (aviso em amarelo)
Comportamento normal em sites com requisições contínuas como e-commerces.
O scraper usa `domcontentloaded` como fallback automaticamente. Não afeta o funcionamento.

### Testes falhando por elemento não encontrado (timeout)
- O site pode exigir login para mostrar os elementos
- Use `--headed` para visualizar o que o browser está carregando
- Use `--only-scrape` e inspecione o `elements.json` para ver quais elementos foram capturados

### `Suite contains no tests or tasks`
O arquivo `.robot` foi gerado incompleto (limite de tokens). Execute novamente.

### Testes com assertions erradas (texto esperado diferente do real)
A IA pode não conhecer o texto exato das mensagens de erro do site.
Edite o `scenarios.robot` gerado e ajuste os valores esperados, ou rode novamente.

---

## Exemplo de execução completa

```
╭──────────────────────────────────────────────────────────────────────────────╮
│  WebTestAI                                                                   │
│  Automação inteligente de testes web                                         │
╰──────────────────────────────────────────────────────────────────────────────╯

[ 1 ] Abrindo browser e carregando página
  →  URL: https://www.saucedemo.com
  →  Browser: chromium | headless=True
  ✓  Página carregada: Swag Labs

[ 2 ] Inspecionando e classificando elementos
  ✓  4 elementos capturados  (4 alta prioridade)
  ●  INPUT   //*   Username
  ●  INPUT   //*   Password
  ●  INPUT   //*   (submit)
  ●  FORM    //form

[ 3 ] Gerando cenários de teste com IA
  →  Modelo: gemini-2.5-flash
  →  Elementos enviados: 4
  ✓  Cenários salvos: scenarios.robot
  →  Test cases gerados: ~30

[ 4 ] Executando testes com Robot Framework
  Login Com Sucesso                        | PASS |
  Login Com Credenciais Invalidas          | PASS |
  Login Com Usuario Vazio                  | PASS |
  Login Com Senha Vazia                    | PASS |
  4 tests, 4 passed, 0 failed

[ 5 ] Resumo da execução
  Página:  Swag Labs
  URL:     https://www.saucedemo.com/
  Relatórios em: reports/www_saucedemo_com_20260615_183000
  Status dos testes: PASSOU ✓
```
