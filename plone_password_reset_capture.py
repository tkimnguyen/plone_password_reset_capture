import argparse
import os
import time
from datetime import datetime

from playwright.sync_api import sync_playwright

from common import (
    PASSWORD,
    click_reset,
    click_set_password,
    fill_passwords,
    fill_username_initial,
    fill_username_reset,
    generate_html,
    generate_markdown,
    generate_pdf,
    is_internal,
    snap,
    wait_for_reset,
)

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
        snap(page, outdir, "02-login", "Click 'Get help'")

        # Step 3
        page.get_by_role("link", name="Get help").click()
        snap(page, outdir, "03-help", "The reset password page")

        # Step 4
        fill_username_initial(page, user)
        snap(page, outdir, "04-user", "Enter username and click 'Reset your password'")

        # Step 5
        click_reset(page)
        snap(page, outdir, "05-reset", "Check your email and open the emailed reset password link")

        # Step 6
        wait_for_reset(page)
        snap(page, outdir, "06-reset", "The form for setting a new password")

        # Wait for reset form
        for _ in range(15):
            if page.locator("#userid").count():
                break
            time.sleep(1)

        # Step 7
        fill_username_reset(page, user)

        if fill_passwords(page, password):
            snap(page, outdir, "07-password",
                 "Enter username and new password then press 'Set my password'")

            click_set_password(page)

        # ✅ Clean UI before final screenshot
        for _ in range(15):
            if page.locator("text=Password reset successful").count():
                break
            time.sleep(1)

        page.evaluate("document.activeElement && document.activeElement.blur()")
        page.wait_for_timeout(800)

        # Step 8 FINAL
        snap(page, outdir, "08-success",
             "Password reset successful: you are logged in now")

        generate_markdown(outdir)
        generate_pdf(outdir)
        generate_html(outdir, "Password Reset Training", "Password Reset Training Guide")

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
