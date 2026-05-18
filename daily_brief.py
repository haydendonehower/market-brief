#!/usr/bin/env python3
"""
daily_brief.py — Full pipeline: fetch → build page → commit to GitHub Pages → email.

Environment variables (.env or GitHub Actions secrets):
  GMAIL_ADDRESS    — your Gmail address
  GMAIL_APP_PASS   — 16-char App Password (Google Account → Security → App Passwords)
  RECIPIENT_EMAIL  — where to deliver the brief (can be same or different)
  PAGE_URL         — your GitHub Pages URL, e.g. https://haydendonehower.github.io/market-brief/
                     (used as the link in the email — set once, never changes)

Usage:
  python3 daily_brief.py
  python3 daily_brief.py --skip-email    # just build the HTML, don't send
  python3 daily_brief.py --skip-html     # just send email (no page build)
"""

import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DOCS_DIR = Path(__file__).parent / "docs"


def require_env(key: str) -> str:
    val = os.environ.get(key)
    if not val:
        print(f"ERROR: missing environment variable: {key}")
        sys.exit(1)
    return val


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-email", action="store_true")
    parser.add_argument("--skip-html",  action="store_true")
    args = parser.parse_args()

    page_url = os.environ.get("PAGE_URL", "")

    # ── 1. Fetch ─────────────────────────────────────────────────────────────
    print("▶ Fetching market data...")
    from fetcher import fetch_all
    data = fetch_all()
    print(f"  {data['date']} | movers: {[m['symbol'] for m in data['movers']]}")

    # ── 2. Build HTML page ───────────────────────────────────────────────────
    if not args.skip_html:
        print("▶ Building HTML page...")
        from html_builder import build_page
        DOCS_DIR.mkdir(exist_ok=True)
        html = build_page(data, page_url)
        out_path = DOCS_DIR / "index.html"
        out_path.write_text(html, encoding="utf-8")
        print(f"  Saved → {out_path}")
    else:
        print("▶ Skipping HTML build (--skip-html)")

    # ── 3. Send email ────────────────────────────────────────────────────────
    if not args.skip_email:
        print("▶ Sending email...")
        gmail_address = require_env("GMAIL_ADDRESS")
        app_password  = require_env("GMAIL_APP_PASS")
        recipient     = os.environ.get("RECIPIENT_EMAIL") or gmail_address
        from mailer import send_email
        send_email(data, page_url, recipient, gmail_address, app_password)
    else:
        print("▶ Skipping email (--skip-email)")

    print(f"\n✓ Done.  Page: {page_url or str(DOCS_DIR / 'index.html')}")


if __name__ == "__main__":
    main()
