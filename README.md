# Shopee Scraper API

Este repositório contém dois scripts Python que juntos permitem autenticar numa conta Shopee (via cookies) e expor um micro-serviço HTTP que raspa detalhes de qualquer link de produto encurtado da Shopee.

## Arquivos

- **`cookies.py`**  
  Script interativo que abre um navegador Chromium embutido, permite login manual na Shopee e salva todos os cookies em `cookies.json`.

- **`api.py`**  
  Micro-serviço FastAPI que expõe:
  - **`POST /scrape`**  
    Recebe JSON `{ "url": "<link-encurtado-Shopee>" }`  
    Devolve JSON com:
    - `nome`, `avaliacao`, `preco`, `desconto`, `descricao`
    - `video` (URL do vídeo, se houver)
    - `imagens` (lista de todas as .webp em alta resolução)
  - Lógica de retry (até 3 vezes), timeout de 60 s e back-off de 30 s
  - Bypass automático do Cloudflare e injeção de cookies salvos

---

## Pré-requisitos

- Python 3.10 ou superior
- Chromium embutido (via DrissionPage)
- Variáveis de ambiente em arquivo `.env` (opcional)

---

## Instalação

1. Clone este repositório e entre na pasta:
   ```bash
   git clone https://github.com/SEU_USUARIO/shopee-scraper.git
   cd shopee-scraper
   ```

````

2. Crie e ative um ambiente virtual:

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Linux/macOS
   .venv\Scripts\activate      # Windows
   ```

3. Instale as dependências:

   ```bash
   pip install -r requirements.txt
   ```

---

## Geração de Cookies

Antes de rodar o scraper, gere um `cookies.json` válido:

```bash
python cookies.py
```

* Uma janela de navegador Chromium será aberta.
* Faça login manualmente na Shopee.
* Volte ao terminal e pressione **ENTER**.
* Os cookies autenticados serão salvos em `cookies.json`.

---

## Executando a API

Por padrão a API roda em **`0.0.0.0:8051`** (conforme configurado em `api.py`).

```bash
python api.py
```

Ou usando **uvicorn**:

```bash
uvicorn api:app --host 0.0.0.0 --port 8051
```

---

## Exemplo de Requisição

```bash
curl -X POST http://localhost:8051/scrape \
     -H "Content-Type: application/json" \
     -d "{\"url\":\"https://s.shopee.com.br/6AYZ8nz9HW\"}"
```

Resposta:

```json
{
  "nome": "...",
  "avaliacao": "...",
  "preco": "...",
  "desconto": "...",
  "descricao": "...",
  "video": "...",
  "imagens": [
    "https://.../file1.webp",
    "https://.../file2.webp",
    …
  ]
}
```

---

## Variáveis de Ambiente

Você pode ajustar as configurações de host e porta via `.env`:

```env
API_HOST=0.0.0.0
API_PORT=8051
```

---

## Licença

MIT © 2025


````
