# api.py  ---------------------------------------------------------------
"""
FastAPI wrapper para o scraper Shopee
• Endpoint POST /scrape recebe {"url": "<link>"} e devolve JSON com:
  nome, avaliação, preço, desconto, descrição, vídeo e lista "imagens"
• Resolve Cloudflare (CloudflareBypasser) e injeta cookies se existir cookies.json
• Timeout de 60 s por página, até 3 tentativas com back-off de 30 s
"""

import json, logging, time, re, sys
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from DrissionPage import ChromiumOptions, ChromiumPage
from DrissionPage.errors import ElementNotFoundError
from CloudflareBypasser import CloudflareBypasser

# ---------- Configuração global ---------------------------------------------
COOKIES_FILE  = Path(__file__).parent / "cookies.json"
MAX_RETRIES   = 3
PAGE_TIMEOUT  = 60   # segundos
BACKOFF_TIME  = 30   # segundos

# ---------- FastAPI ----------------------------------------------------------
app = FastAPI(title="Shopee Scraper API")

class Req(BaseModel):
    url: str

# ---------- Navegador & Helpers ---------------------------------------------
def build_options() -> ChromiumOptions:  # FastAPI cria um navegador por request
    opts = ChromiumOptions()
    opts.set_argument("--start-maximized")
    opts.set_argument("--disable-blink-features=AutomationControlled")
    opts.set_argument("--disable-infobars")
    opts.set_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
    )
    return opts

def open_and_bypass(page: ChromiumPage, cf: CloudflareBypasser, url: str):
    page.get(url)
    cf.bypass()  # contorna Cloudflare

# ---- utilidades de URL/imagem ----------------------------------------------
RE_RESIZE = re.compile(r"@resize_w\d+(_nl)?")
RE_WEBP   = re.compile(r"https://[^\s\"'\\]+\.webp")

def to_large(url: str) -> str:
    if not url:
        return url
    url = RE_RESIZE.sub("", url)
    if not url.lower().endswith(".webp"):
        p = urlparse(url)
        url = urlunparse(p._replace(path=re.sub(r"\.\w+$", ".webp", p.path)))
    return url

def pick_text(page: ChromiumPage, css: str, timeout: float = 6):
    try:
        return page.ele(f"css:{css}", timeout=timeout).text
    except ElementNotFoundError:
        return None

def pick_attr(page: ChromiumPage, css: str, attr: str, timeout: float = 6):
    try:
        return page.ele(f"css:{css}", timeout=timeout).attrs.get(attr)
    except ElementNotFoundError:
        return None

DESC_SEL = ("#sll2-normal-pdp-main > div > div > div > div.container > div.wAMdpk > "
            "div > div.page-product__content--left > "
            "div.product-detail.page-product__detail > section:nth-child(2)")

# ---------- Scraper principal ----------------------------------------------
def scrape_single(url: str) -> dict:
    """Raspa um único link Shopee; aplica timeout e tentativas."""
    page = ChromiumPage(addr_or_opts=build_options())
    cf   = CloudflareBypasser(page, max_retries=5, log=False)

    try:
        # injeta cookies se existirem
        if COOKIES_FILE.exists():
            page.get("https://shopee.com.br")
            page.set.cookies(json.loads(COOKIES_FILE.read_text("utf-8")))
            page.refresh()

        start = time.perf_counter()
        open_and_bypass(page, cf, url)

        while (time.perf_counter() - start) < PAGE_TIMEOUT:
            data = _scrape_dom(page)
            if data["nome"] and data["imagens"]:
                return data
            time.sleep(1)

        raise TimeoutError("Timeout interno de scraping (60 s).")

    finally:
        page.quit()

def _scrape_dom(page: ChromiumPage) -> dict:
    nome      = pick_text(page, ".WBVL_7 h1") or pick_text(page, ".WBVL_7 .vR6K3w")
    avaliacao = pick_text(page, ".F9RHbS")
    preco     = pick_text(page, ".IZPeQz") or pick_text(page, "div.flex-auto div span._1ohNWN")
    desconto  = pick_text(page, ".ZA5sW5")  or pick_text(page, "div.flex-auto div.CO1sy8")
    descricao = pick_text(page, DESC_SEL)
    video     = pick_attr(page, "video.tpgcVs", "src")

    # imagens grandes via regex
    html = page.html
    imgs = [to_large(u) for u in RE_WEBP.findall(html)]
    imagens = list(dict.fromkeys(imgs))

    return {
        "nome":       nome,
        "avaliacao":  avaliacao,
        "preco":      preco,
        "desconto":   desconto,
        "imagens":    imagens,
        "video":      video,
        "descricao":  descricao,
    }

# ---------- Endpoint FastAPI -------------------------------------------------
@app.post("/scrape")
def scrape(req: Req):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            data = scrape_single(req.url)
            return data
        except Exception as e:
            logging.warning(f"Tentativa {attempt}/{MAX_RETRIES} falhou: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(BACKOFF_TIME)
            else:
                raise HTTPException(status_code=500, detail=str(e))

# ---------- Execução standalone ---------------------------------------------
if __name__ == "__main__":
    """
    Execute localmente com:
        uvicorn api:app --host 0.0.0.0 --port 8051 --workers 1
    """
    import uvicorn
    load_dotenv()
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    uvicorn.run("api:app", host="0.0.0.0", port=8051, reload=False)
