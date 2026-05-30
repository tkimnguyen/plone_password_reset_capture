import argparse
import os
import time
import re
import subprocess
import pyperclip
from datetime import datetime
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw, ImageFont

PASSWORD = "chumpchump10!"
steps = []
last_bbox = None

# ---------- LOG ----------
def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

# ---------- INTERNAL URL ----------
def is_internal(url):
    host = urlparse(url).hostname or ""
    return host.endswith(".local") or "." not in host

# ---------- HIGHLIGHT ----------
def highlight_element(locator):
    global last_bbox
    try:
        box = locator.bounding_box()
        if box:
            last_bbox = box
        locator.evaluate("el => el.style.outline='3px solid red'")
    except:
        last_bbox = None

# ---------- SCREENSHOT ----------
def snap(page, outdir, name, caption):
    path = os.path.join(outdir, f"{name}.png")

    viewport = page.viewport_size
    page.wait_for_timeout(400)

    page.screenshot(path=path, clip={
        "x": 0,
        "y": 0,
        "width": viewport["width"],
        "height": viewport["height"]
    })

    steps.append({"file": f"{name}.png", "caption": caption})
    decorate(path, caption)

    log(f"📸 Screenshot: {path}")

# ---------- CLEAN LABEL (NO ARROWS, NO HEADER) ----------
def decorate(path, label):
    global last_bbox

    img = Image.open(path)
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("Arial.ttf", 20)
    except:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), label, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    if last_bbox:
        tx = int(last_bbox["x"] + last_bbox["width"] / 2)
        ty = int(last_bbox["y"] + last_bbox["height"] / 2)

        lx = max(10, tx - tw // 2)
        ly = max(10, ty - 60)

        draw.rectangle(
            (lx - 8, ly - 8, lx + tw + 8, ly + th + 8),
            fill=(255, 255, 200)
        )

        draw.text((lx, ly), label, fill="black", font=font)

    img.save(path)

# ---------- USERNAME STEP 4 ----------
def fill_username_initial(page, user):
    loc = page.locator("#form-widgets-reset_password")
    if not loc.count():
        raise Exception("Username field not found")

    loc.fill(user)

    for _ in range(20):
        if loc.input_value() == user:
            break
        time.sleep(0.05)

    page.wait_for_timeout(300)
    highlight_element(loc)

# ---------- USERNAME RESET PAGE ----------
def fill_username_reset(page, user):
    loc = page.locator("#userid")
    if not loc.count():
        raise Exception("Reset username field '#userid' not found")

    loc.fill(user)

    for _ in range(20):
        if loc.input_value() == user:
            break
        time.sleep(0.05)

    highlight_element(loc)

# ---------- PASSWORD ----------
def fill_passwords(page):
    pwds = page.locator("input[type='password']")
    if not pwds.count():
        return False

    pwds.nth(0).fill(PASSWORD)
    highlight_element(pwds.nth(0))

    if pwds.count() > 1:
        pwds.nth(1).fill(PASSWORD)
        highlight_element(pwds.nth(1))

    return True

# ---------- CLICK RESET (STEP 5 ONLY) ----------
def click_reset(page):
    btn = page.locator("#form-buttons-reset")
    if not btn.count():
        raise Exception("Reset button not found")

    highlight_element(btn)
    page.wait_for_timeout(400)
    btn.click()

# ---------- CLICK SET PASSWORD ----------
def click_set_password(page):
    if page.locator("#form-buttons-reset_password").count():
        btn = page.locator("#form-buttons-reset_password")
    elif page.get_by_role("button", name=re.compile("set my password", re.I)).count():
        btn = page.get_by_role("button", name=re.compile("set my password", re.I))
    else:
        btn = page.locator("input[type='submit']")

    if not btn.count():
        raise Exception("Set password button not found")

    highlight_element(btn)
    page.wait_for_timeout(400)
    btn.click()

# ---------- CLIPBOARD ----------
def wait_for_reset(page):
    pattern = re.compile(r"http.*passwordreset/")
    last = pyperclip.paste()

    log("📋 Copy reset link from email...")

    while True:
        txt = pyperclip.paste()
        if txt != last:
            last = txt
            if txt and pattern.search(txt):
                log("✅ Reset URL detected")
                page.goto(txt)
                return
        time.sleep(1)

# ---------- PDF ----------
def generate_pdf(outdir):
    md_file = os.path.join(outdir, "guide.md")
    pdf_file = os.path.join(outdir, "guide.pdf")

    log("📄 Generating PDF...")

    subprocess.run([
        "pandoc",
        md_file,
        "-o", pdf_file,
        "--pdf-engine=weasyprint",
        f"--resource-path={outdir}"
    ], check=True)

    log(f"✅ PDF created: {pdf_file}")

# ---------- HTML ----------
def generate_html(outdir):
    html_path = os.path.join(outdir, "guide.html")

    log("🌐 Generating HTML guide...")

    html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Password Reset Training</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 40px;
            background-color: #f9f9f9;
        }
        h1 {
            color: #2c3e50;
        }
        h2 {
            color: #34495e;
        }
        .step {
            margin-bottom: 40px;
            padding: 20px;
            background: #ffffff;
            border: 1px solid #ddd;
            border-radius: 6px;
        }
        img {
            width: 100%;
            max-width: 1000px;
            border: 1px solid #ccc;
            margin-top: 10px;
        }
    </style>
</head>
<body>

<h1>Password Reset Training Guide</h1>
<hr>
"""

    # Insert each step
    for i, step in enumerate(steps, 1):
        html += f"""
<div class="step">
    <h2>Step {i}: {step['caption']}</h2>
    <img src="{step['file']}" alt="Step {i}">
</div>
"""

    html += """
</body>
</html>
"""

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    log(f"✅ HTML guide created: {html_path}")

# ---------- FLOW ----------
def run(url, user, outdir):
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

        if fill_passwords(page):
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

        # OUTPUT FILES
        md_file = os.path.join(outdir, "guide.md")
        with open(md_file, "w") as f:
            for i, s in enumerate(steps, 1):
                f.write(f"## Step {i}: {s['caption']}\n\n")
                f.write(f"![]({s['file']})\n\n")

        generate_pdf(outdir)
        generate_html(outdir)

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

    run(args.url, args.user, outdir)

if __name__ == "__main__":
    main()