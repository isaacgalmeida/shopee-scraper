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
