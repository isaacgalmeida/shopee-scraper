#!/usr/bin/env python3
"""
FastAPI wrapper para o scraper Shopee
• Endpoint POST /scrape recebe {"url": "<link>"} e devolve JSON com:
  nome, avaliação, preço, desconto, descrição, vídeo e lista "imagens"
• Resolve Cloudflare (CloudflareBypasser) e injeta cookies se existir cookies.json
• Timeout de 60 s por página, até 3 tentativas com back-off de 30 s
• HOST e PORT lidos do .env (API_HOST, API_PORT)
"""

import os
import json
import logging
import time
import re
import sys
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

# --- Carrega variáveis de ambiente ---
load_dotenv()
API_HOST   = os.getenv("API_HOST", "127.0.0.1")
API_PORT   = int(os.getenv("API_PORT", "8051"))
MAX_RETRIES   = 3
PAGE_TIMEOUT  = 60   # segundos
BACKOFF_TIME  = 30   # segundos
COOKIES_FILE  = Path(__file__).parent / "cookies.json"

# --- FastAPI setup ---
app = FastAPI(title="Shopee Scraper API")

class Req(BaseModel):
    url: str

# --- Navegador & Helpers ---
from DrissionPage import ChromiumOptions, ChromiumPage
from DrissionPage.errors import ElementNotFoundError
from CloudflareBypasser import CloudflareBypasser

def build_options() -> ChromiumOptions:
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
    cf.bypass()

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

def _scrape_dom(page: ChromiumPage) -> dict:
    nome      = pick_text(page, ".WBVL_7 h1") or pick_text(page, ".WBVL_7 .vR6K3w")
    avaliacao = pick_text(page, ".F9RHbS")
    preco     = pick_text(page, ".IZPeQz") or pick_text(page, "div.flex-auto div span._1ohNWN")
    desconto  = pick_text(page, ".ZA5sW5")  or pick_text(page, "div.flex-auto div.CO1sy8")
    descricao = pick_text(page, DESC_SEL)
    video     = pick_attr(page, "video.tpgcVs", "src")

    html = page.html
    imgs = [to_large(u) for u in RE_WEBP.findall(html)]
    imagens = list(dict.fromkeys(imgs))

    return {
        "nome":      nome,
        "avaliacao": avaliacao,
        "preco":     preco,
        "desconto":  desconto,
        "descricao": descricao,
        "video":     video,
        "imagens":   imagens,
    }

def scrape_single(url: str) -> dict:
    page = ChromiumPage(addr_or_opts=build_options())
    cf   = CloudflareBypasser(page, max_retries=5, log=False)
    try:
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

@app.post("/scrape")
def scrape(req: Req):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return scrape_single(req.url)
        except Exception as e:
            logging.warning(f"Tentativa {attempt}/{MAX_RETRIES} falhou: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(BACKOFF_TIME)
            else:
                raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    uvicorn.run("api:app", host=API_HOST, port=API_PORT, reload=False)
