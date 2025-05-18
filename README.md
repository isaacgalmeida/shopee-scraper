# Shopee Scraper API

Este repositório contém dois scripts Python que permitem:

1. **Gerar cookies** autenticados na Shopee (`cookies.py`);
2. **Expor um micro-serviço HTTP** com FastAPI (`api.py`) que recebe um link encurtado de produto da Shopee e retorna um JSON estruturado com:
   - `nome`, `avaliacao`, `preco`, `desconto`, `descricao`
   - `video` (URL do vídeo, se houver)
   - `imagens` (lista de todas as `.webp` em alta resolução)

---

## Pré-requisitos

- Python 3.10+
- (Opcional) Docker
- Variáveis de ambiente em arquivo `.env`

---

## Instalação

1. **Clone o repositório**

   ```bash
   git clone https://github.com/SEU_USUARIO/shopee-scraper.git
   cd shopee-scraper
   ```

2. **Crie e ative um ambiente virtual**

   ```bash
   python -m venv .venv
   source .venv/bin/activate    # Linux / macOS
   .venv\Scripts\activate       # Windows
   ```

3. **Instale as dependências**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure o `.env`**
   Copie o exemplo e ajuste se necessário:

   ```bash
   cp .env.example .env
   ```

---

## `.env.example`

```dotenv
# Endereço e porta onde a API irá escutar
API_HOST=0.0.0.0
API_PORT=8051

# (Opcional) Caminho para o Chrome/Brave se usar set_paths()
# CHROME_PATH=/usr/bin/google-chrome

# (Opcional) Ajuste de nível de logs
# LOG_LEVEL=INFO
```

---

## Gerando os Cookies

Antes de usar a API, gere um `cookies.json` válido executando:

```bash
python cookies.py
```

- Uma janela do Chromium embutido abrirá.
- Faça login manualmente em `shopee.com.br`.
- Volte ao terminal e pressione **ENTER**.
- O arquivo `cookies.json` será criado/atualizado.

---

## Executando a API

### Via Python

```bash
python api.py
```

Por padrão, a FastAPI irá iniciar em `http://0.0.0.0:8051` (ou o que você definiu no `.env`).

### Via Uvicorn

```bash
uvicorn api:app --host ${API_HOST} --port ${API_PORT}
```

---

## Exemplo de Requisição

### cURL (Linux/macOS)

```bash
curl -X POST http://localhost:8051/scrape \
     -H "Content-Type: application/json" \
     -d '{"url":"https://s.shopee.com.br/6AYZ8nz9HW"}'
```

### cURL (Windows CMD)

```bat
curl -X POST http://localhost:8051/scrape ^
     -H "Content-Type: application/json" ^
     -d "{\"url\":\"https://s.shopee.com.br/6AYZ8nz9HW\"}"
```

### PowerShell

```powershell
Invoke-RestMethod -Method POST `
  -Uri http://localhost:8051/scrape `
  -ContentType "application/json" `
  -Body '{ "url": "https://s.shopee.com.br/6AYZ8nz9HW" }'
```

#### Exemplo de resposta

```json
{
  "nome": "Tapete Banheiro Antiderrapante …",
  "avaliacao": "4.7",
  "preco": "R$13,99 - R$19,00",
  "desconto": "R$80,00",
  "descricao": "🩰✨- Seja Bem vindo(a)…",
  "video": "https://…mp4",
  "imagens": ["https://…file1.webp", "https://…file2.webp", "…"]
}
```

---

## Integração com n8n

1. **Ler planilha** com **Spreadsheet to JSON**.
2. **SplitInBatches** (Batch Size = 1).
3. **HTTP Request**:

   - **Method**: POST
   - **URL**: `http://host.docker.internal:${API_PORT}/scrape`
   - **Body** (RAW/JSON):

     ```json
     {
       "url": "={{$json.links}}"
     }
     ```

4. **Set/Merge** para combinar link original e dados raspados.
5. **Salvar** em Google Sheets, Banco de dados, etc.

---

## Docker (Opcional)

**Dockerfile** exemplo:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
EXPOSE ${API_PORT}
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8051"]
```

Build & Run:

```bash
docker build -t shopee-scraper .
docker run -d --name scraper -p 8051:8051 shopee-scraper
```

---

## Licença

MIT © 2025

```

```
