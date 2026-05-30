import argparse
import os
import time
from datetime import datetime

from playwright.sync_api import sync_playwright

from common import (
    PASSWORD,
    clear_highlight,
    generate_html,
    generate_markdown,
    generate_pdf,
    is_internal,
    snap,
)

# ---------- LOGIN ----------
def first_present(page, selectors, description):
    for selector in selectors:
        loc = page.locator(selector)
        if loc.count():
            return loc.first

    raise Exception(f"{description} not found")

def fill_login_and_submit(page, user, password):
    username = first_present(page, [
        "#__ac_name",
        "input[name='__ac_name']",
        "#login",
        "input[name='login']",
        "#userid",
        "input[name='userid']",
        "input[type='text']",
    ], "Login name field")
    username.fill(user)

    password_field = first_present(page, [
        "#__ac_password",
        "input[name='__ac_password']",
        "input[name='password']",
        "input[type='password']",
    ], "Password field")
    password_field.fill(password)
    page.wait_for_timeout(400)
    password_field.press("Enter")

def wait_for_login_success(page, user):
    page.wait_for_load_state("networkidle")

    for _ in range(20):
        if not page.locator("input[type='password']").count():
            break
        time.sleep(0.5)

    page.get_by_text(user).first.wait_for(timeout=10000)

# ---------- FLOW ----------
def run(url, user, password, outdir):
    with sync_playwright() as p:

        browser = p.chromium.launch(headless=False, slow_mo=300)
        context = browser.new_context(
            ignore_https_errors=is_internal(url),
            viewport={"width": 1280, "height": 900}
        )
        page = context.new_page()

        # Step 1
        page.goto(url)
        snap(page, outdir, "01-home", f"Open {url} and click 'Log in'")

        # Step 2
        page.get_by_role("link", name="Log in").click()
        snap(page, outdir, "02-login", "Enter login name and password, then press 'Log in'")

        # Step 3
        fill_login_and_submit(page, user, password)
        wait_for_login_success(page, user)

        page.evaluate("document.activeElement && document.activeElement.blur()")
        page.wait_for_timeout(800)
        clear_highlight()

        snap(page, outdir, "03-success",
             "Login successful: your name appears at the bottom of the left toolbar")

        generate_markdown(outdir)
        generate_pdf(outdir)
        generate_html(outdir, "Login Training", "Login Training Guide")

        browser.close()

# ---------- MAIN ----------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", required=True)
    parser.add_argument("--password", default=PASSWORD)
    parser.add_argument("--url", default="https://classic.demo.plone.org/en")
    parser.add_argument("--out", default=None)

    args = parser.parse_args()

    outdir = args.out or f"screens_{args.user}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(outdir, exist_ok=True)

    run(args.url, args.user, args.password, outdir)

if __name__ == "__main__":
    main()
