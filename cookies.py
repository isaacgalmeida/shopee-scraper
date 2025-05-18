#!/usr/bin/env python3
import json, logging, time
from pathlib import Path
from dotenv import load_dotenv
from DrissionPage import ChromiumOptions, ChromiumPage

COOKIES_FILE = Path(__file__).parent / 'cookies.json'

def build_options():
    opts = ChromiumOptions()
    # Usamos o Chromium interno – não chame set_paths()
    opts.set_argument('--start-maximized')
    opts.set_argument('--disable-blink-features=AutomationControlled')
    opts.set_argument(
        '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36')
    return opts

def main():
    load_dotenv()
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s')

    driver = ChromiumPage(addr_or_opts=build_options())  # Chromium embutido
    try:
        driver.get('https://shopee.com.br')
        logging.info('👉 Faça login manualmente e depois pressione ENTER no terminal.')
        input()  # bloqueia até confirmar

        # ---- NOVA API ----
        cookies = driver.cookies(all_info=True)  # ← aqui está a mudança crucial
        # -------------------

        COOKIES_FILE.write_text(
            json.dumps(cookies, indent=2, ensure_ascii=False), encoding='utf-8')
        logging.info(f'✅ Cookies salvos em {COOKIES_FILE.resolve()}')
        time.sleep(1)
    finally:
        driver.quit()
        logging.info('🚪 Navegador fechado. Processo concluído.')

if __name__ == '__main__':
    main()
