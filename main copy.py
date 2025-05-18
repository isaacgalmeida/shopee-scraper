#!/usr/bin/env python3
"""
Shopee scraper – redesign
• Resolve Cloudflare e injeta cookies
• Timeout de 60 s; se falhar reinicia após 30 s (até 3 tentativas)
• Extrai: nome, avaliação, preço, desconto, vídeo e TODAS as imagens grandes .webp
• Descrição agora via seletor:
  #sll2-normal-pdp-main > div > div > div > div.container > div.wAMdpk >
  div > div.page-product__content--left > div.product-detail.page-product__detail >
  section:nth-child(2)
"""

import json, logging, time, re, sys
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from dotenv import load_dotenv
from DrissionPage import ChromiumOptions, ChromiumPage
from DrissionPage.errors import ElementNotFoundError
from CloudflareBypasser import CloudflareBypasser

# ---------------- Config ----------------------------------------------------
COOKIES_FILE   = Path(__file__).parent / 'cookies.json'
TARGET_LINK    = 'https://s.shopee.com.br/6AYZ8nz9HW'
MAX_RETRIES    = 3
PAGE_TIMEOUT   = 60      # s
BACKOFF_TIME   = 30      # s

# ---------------- Chromium --------------------------------------------------
def build_options() -> ChromiumOptions:
    opts = ChromiumOptions()
    opts.set_argument('--start-maximized')
    opts.set_argument('--disable-blink-features=AutomationControlled')
    opts.set_argument('--disable-infobars')
    opts.set_argument(
        '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36')
    return opts

# ---------------- Cloudflare bypass ----------------------------------------
def open_and_bypass(page: ChromiumPage, cf: CloudflareBypasser, url: str):
    page.get(url)
    cf.bypass()

# ---------------- Helpers ---------------------------------------------------
RE_RESIZE = re.compile(r'@resize_w\d+(_nl)?')
RE_WEBP   = re.compile(r'https://[^\s"\'\\]+\.webp')

def to_large(url: str) -> str:
    if not url:
        return url
    url = RE_RESIZE.sub('', url)
    if not url.lower().endswith('.webp'):
        p = urlparse(url)
        url = urlunparse(p._replace(path=re.sub(r'\.\w+$', '.webp', p.path)))
    return url

def biggest_from_srcset(srcset: str) -> str:
    parts = [p.strip().split() for p in srcset.split(',')] if srcset else []
    return parts[-1][0] if parts else ''

def pick_text(page: ChromiumPage, css: str, timeout: float = 6):
    try:
        return page.ele(f'css:{css}', timeout=timeout).text
    except ElementNotFoundError:
        return None

def pick_attr(page: ChromiumPage, css: str, attr: str, timeout: float = 6):
    try:
        return page.ele(f'css:{css}', timeout=timeout).attrs.get(attr)
    except ElementNotFoundError:
        return None

# ---------------- Scraper ---------------------------------------------------
DESC_SEL = ('#sll2-normal-pdp-main > div > div > div > div.container > div.wAMdpk > '
            'div > div.page-product__content--left > '
            'div.product-detail.page-product__detail > section:nth-child(2)')

def scrape_product(page: ChromiumPage) -> dict:
    nome       = pick_text(page, '.WBVL_7 h1') or pick_text(page, '.WBVL_7 .vR6K3w')
    avaliacao  = pick_text(page, '.F9RHbS')
    preco      = pick_text(page, '.IZPeQz') or pick_text(page, 'div.flex-auto div span._1ohNWN')
    desconto   = pick_text(page, '.ZA5sW5')  or pick_text(page, 'div.flex-auto div.CO1sy8')
    descricao  = pick_text(page, DESC_SEL)

    video = pick_attr(page, 'video.tpgcVs', 'src')

    # imagens
    html = page.html
    urls = [to_large(u) for u in RE_WEBP.findall(html)]
    imagens = list(dict.fromkeys(urls))

    return {
        'nome':       nome,
        'avaliacao':  avaliacao,
        'preco':      preco,
        'desconto':   desconto,
        'imagens':    imagens,
        'video':      video,
        'descricao':  descricao
    }

# ---------------- Runner ----------------------------------------------------
def run_once() -> dict | None:
    page = ChromiumPage(addr_or_opts=build_options())
    cf   = CloudflareBypasser(page, max_retries=5, log=False)

    try:
        if COOKIES_FILE.exists():
            page.get('https://shopee.com.br')
            page.set.cookies(json.loads(COOKIES_FILE.read_text('utf-8')))
            page.refresh()

        start = time.perf_counter()
        open_and_bypass(page, cf, TARGET_LINK)

        while (time.perf_counter() - start) < PAGE_TIMEOUT:
            data = scrape_product(page)
            if data['nome'] and data['imagens']:
                return data
            time.sleep(1)
        return None
    finally:
        page.quit()

def main():
    load_dotenv()
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s')

    for attempt in range(1, MAX_RETRIES + 1):
        logging.info(f'🔄 Tentativa {attempt}/{MAX_RETRIES}')
        data = run_once()
        if data:
            logging.info('🧾 Dados extraídos:')
            print(json.dumps(data, indent=2, ensure_ascii=False))
            break
        if attempt < MAX_RETRIES:
            logging.info(f'⏳ Retentando em {BACKOFF_TIME}s…')
            time.sleep(BACKOFF_TIME)
    else:
        logging.error('❌ Falha após várias tentativas.')
        sys.exit(1)

    logging.info('✅ Processo finalizado.')

if __name__ == '__main__':
    main()
