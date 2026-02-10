def html_to_pdf_bytes(html: str) -> bytes:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            'playwright no esta instalado. Ejecuta pip install -r requirements.txt y '
            'python -m playwright install chromium.'
        ) from exc

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage'],
        )
        try:
            page = browser.new_page()
            page.set_content(html, wait_until='networkidle')
            return page.pdf(
                format='A4',
                print_background=True,
                prefer_css_page_size=True,
                margin={'top': '0', 'right': '0', 'bottom': '0', 'left': '0'},
            )
        finally:
            browser.close()
