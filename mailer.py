"""
mailer.py — Send the market brief email via Gmail SMTP.

Uses an App Password (not OAuth) — simple and reliable for automation.
Setup: Google Account → Security → 2-Step Verification → App Passwords
       Create an App Password for "Mail" → copy the 16-char password.
"""

import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime


# ── HTML email template ───────────────────────────────────────────────────────

def _pct_color(val) -> str:
    if val is None: return "#f0a84a"
    if val > 0:     return "#3ecf8e"
    if val < 0:     return "#e05c5c"
    return "#f0a84a"


def _fmt_pct(val) -> str:
    if val is None: return "—"
    sign = "+" if val > 0 else ""
    return f"{sign}{val:.2f}%"


def _fmt_price(val) -> str:
    try:    return f"${float(val):,.2f}"
    except: return "—"


def build_html(data: dict, gamma_url: str) -> str:
    date = data["date"]

    # Build snapshot rows from indices + macro
    snapshot_rows = ""
    for group in ["Indices", "Macro"]:
        for q in data["groups"].get(group, []):
            color = _pct_color(q["pct"])
            snapshot_rows += f"""
          <tr style="border-bottom:1px solid #1a2d50;">
            <td style="padding:10px 0;font-size:14px;color:#ffffff;font-weight:600;">{q['symbol']}</td>
            <td style="padding:10px 0;font-size:13px;color:#9aafd4;text-align:left;padding-left:12px;">{q['name']}</td>
            <td style="padding:10px 0;font-size:14px;color:#e8eaf0;text-align:right;">{_fmt_price(q['price'])}</td>
            <td style="padding:10px 0;font-size:14px;color:{color};text-align:right;font-weight:600;">{_fmt_pct(q['pct'])}</td>
          </tr>"""

    # Mega-cap rows
    megacap_rows = ""
    for q in data["groups"].get("Mega-cap", []):
        color = _pct_color(q["pct"])
        megacap_rows += f"""
          <tr style="border-top:1px solid #1e3a6e;">
            <td style="padding:10px 16px;font-size:13px;font-weight:700;color:#ffffff;">{q['symbol']}</td>
            <td style="padding:10px 16px;font-size:13px;color:#9aafd4;">{q['name']}</td>
            <td style="padding:10px 16px;font-size:14px;font-weight:700;color:{color};text-align:right;white-space:nowrap;">{_fmt_pct(q['pct'])}</td>
          </tr>"""

    # Signals
    signals_html = ""
    for s in data["signals"]:
        signals_html += f'<p style="margin:4px 0;font-size:13px;line-height:1.6;color:#9aafd4;">• {s}</p>'

    # Sector rotation
    valid = [s for s in data["sectors"] if s["pct"] is not None]
    sector_block = ""
    if valid:
        best, worst = valid[0], valid[-1]
        sector_block = f"""
        <tr><td style="padding:24px 24px 8px;">
          <p style="margin:0 0 12px 0;font-size:10px;letter-spacing:2.5px;text-transform:uppercase;color:#2e5ce6;font-weight:600;">Sector Rotation</p>
          <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f1d3a;border-radius:10px;border:1px solid #1e3a6e;">
            <tr style="background:#0d1830;">
              <td style="padding:10px 16px;font-size:12px;font-weight:700;color:#3ecf8e;">▲ Leading</td>
              <td style="padding:10px 16px;font-size:13px;color:#9aafd4;">{best['symbol']} — {data['sector_names'].get(best['symbol'], '')}</td>
              <td style="padding:10px 16px;font-size:14px;font-weight:700;color:#3ecf8e;text-align:right;">{_fmt_pct(best['pct'])}</td>
            </tr>
            <tr style="border-top:1px solid #1e3a6e;">
              <td style="padding:10px 16px;font-size:12px;font-weight:700;color:#e05c5c;">▼ Lagging</td>
              <td style="padding:10px 16px;font-size:13px;color:#9aafd4;">{worst['symbol']} — {data['sector_names'].get(worst['symbol'], '')}</td>
              <td style="padding:10px 16px;font-size:14px;font-weight:700;color:#e05c5c;text-align:right;">{_fmt_pct(worst['pct'])}</td>
            </tr>
          </table>
        </td></tr>"""

    # News
    news_html = ""
    if data.get("news"):
        items = ""
        for symbol, articles in list(data["news"].items())[:2]:
            for a in articles[:2]:
                url_part = f'<br><a href="{a["url"]}" style="font-size:11px;color:#4a7fff;">Read more →</a>' if a["url"] else ""
                items += f"""
            <tr style="border-top:1px solid #1e3a6e;">
              <td style="padding:10px 16px;">
                <p style="margin:0 0 2px 0;font-size:12px;font-weight:700;color:#7b9cdb;">{symbol}</p>
                <p style="margin:0 0 2px 0;font-size:13px;color:#ffffff;font-weight:600;">{a['title']}</p>
                <p style="margin:0;font-size:12px;color:#5a7ab0;">{a.get('source','')} · {a.get('pub','')}{url_part}</p>
              </td>
            </tr>"""
        news_html = f"""
        <tr><td style="padding:24px 24px 8px;">
          <p style="margin:0 0 12px 0;font-size:10px;letter-spacing:2.5px;text-transform:uppercase;color:#2e5ce6;font-weight:600;">Top Mover News</p>
          <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f1d3a;border-radius:10px;border:1px solid #1e3a6e;">
            {items}
          </table>
        </td></tr>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background-color:#0a0f1e;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;color:#e8eaf0;">

  <table width="100%" cellpadding="0" cellspacing="0" style="background:linear-gradient(135deg,#0d1b3e,#1a2f5e);border-bottom:2px solid #2e5ce6;">
    <tr><td align="center" style="padding:32px 24px 24px;">
      <p style="margin:0 0 4px 0;font-size:11px;letter-spacing:3px;text-transform:uppercase;color:#7b9cdb;">Daily Intelligence</p>
      <h1 style="margin:0;font-size:28px;font-weight:700;color:#ffffff;letter-spacing:-0.5px;">Market Brief</h1>
      <p style="margin:8px 0 0 0;font-size:13px;color:#7b9cdb;">{date}</p>
    </td></tr>
  </table>

  <table width="100%" cellpadding="0" cellspacing="0" style="background:#1a2f5e;">
    <tr><td align="center" style="padding:20px 24px;">
      <a href="{gamma_url}" style="display:inline-block;background:linear-gradient(135deg,#2e5ce6,#4a7fff);color:#ffffff;text-decoration:none;font-size:15px;font-weight:600;padding:14px 32px;border-radius:8px;">
        📈 &nbsp;Open Full Interactive Brief →
      </a>
      <p style="margin:10px 0 0 0;font-size:11px;color:#5a7ab0;">Charts · News · Explainers · All in one page</p>
    </td></tr>
  </table>

  <table width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;margin:0 auto;">

    <tr><td style="padding:28px 24px 8px;">
      <p style="margin:0 0 12px 0;font-size:10px;letter-spacing:2.5px;text-transform:uppercase;color:#2e5ce6;font-weight:600;">Market Context</p>
      {signals_html}
    </td></tr>

    <tr><td style="padding:8px 24px;">
      <p style="margin:0 0 12px 0;font-size:10px;letter-spacing:2.5px;text-transform:uppercase;color:#2e5ce6;font-weight:600;">Snapshot</p>
      <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
        <tr style="border-bottom:1px solid #1e3a6e;">
          <td style="padding:8px 0;font-size:11px;color:#5a7ab0;font-weight:600;text-transform:uppercase;letter-spacing:1px;">Symbol</td>
          <td style="padding:8px 0;font-size:11px;color:#5a7ab0;font-weight:600;text-transform:uppercase;letter-spacing:1px;padding-left:12px;">Name</td>
          <td style="padding:8px 0;font-size:11px;color:#5a7ab0;font-weight:600;text-transform:uppercase;letter-spacing:1px;text-align:right;">Price</td>
          <td style="padding:8px 0;font-size:11px;color:#5a7ab0;font-weight:600;text-transform:uppercase;letter-spacing:1px;text-align:right;">Day %</td>
        </tr>
        {snapshot_rows}
      </table>
    </td></tr>

    <tr><td style="padding:24px 24px 8px;">
      <p style="margin:0 0 12px 0;font-size:10px;letter-spacing:2.5px;text-transform:uppercase;color:#2e5ce6;font-weight:600;">Mega-Cap</p>
      <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;background:#0f1d3a;border-radius:10px;border:1px solid #1e3a6e;">
        {megacap_rows}
      </table>
    </td></tr>

    {sector_block}
    {news_html}

    <tr><td style="padding:24px 24px 8px;">
      <table width="100%" cellpadding="0" cellspacing="0" style="background:linear-gradient(135deg,#0d2060,#1a3a7e);border-radius:10px;border-left:4px solid #2e5ce6;">
        <tr><td style="padding:20px;">
          <p style="margin:0 0 6px 0;font-size:10px;letter-spacing:2px;text-transform:uppercase;color:#7b9cdb;font-weight:600;">Concept of the Day</p>
          <p style="margin:0 0 8px 0;font-size:15px;font-weight:700;color:#ffffff;">Why do rising yields hurt tech stocks?</p>
          <p style="margin:0;font-size:13px;line-height:1.7;color:#9aafd4;">
            Tech companies are valued on <em>future</em> earnings. A higher discount rate makes those future dollars worth less today — lower stock price. This is why Nasdaq falls harder than the Dow during yield spikes.
          </p>
        </td></tr>
      </table>
    </td></tr>

    <tr><td align="center" style="padding:28px 24px 32px;">
      <a href="{gamma_url}" style="display:inline-block;background:linear-gradient(135deg,#2e5ce6,#4a7fff);color:#ffffff;text-decoration:none;font-size:15px;font-weight:600;padding:16px 40px;border-radius:8px;">
        Open Full Brief with Charts &amp; Graphics →
      </a>
    </td></tr>

  </table>

  <table width="100%" cellpadding="0" cellspacing="0" style="background:#060c1a;border-top:1px solid #1a2d50;margin-top:8px;">
    <tr><td align="center" style="padding:20px 24px;">
      <p style="margin:0;font-size:11px;color:#3a4f72;line-height:1.6;">
        Market Brief · Powered by yFinance &amp; Claude<br>
        Data: Yahoo Finance · Bloomberg · TheStreet · Schwab
      </p>
    </td></tr>
  </table>

</body></html>"""
    return html


def send_email(data: dict, gamma_url: str, to_address: str,
               gmail_address: str, app_password: str) -> None:
    """Send the brief via Gmail SMTP using an App Password."""
    subject = f"📊 Market Brief — {data['date']}"
    html    = build_html(data, gamma_url)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = gmail_address
    msg["To"]      = to_address
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.ehlo()
        server.starttls()
        server.login(gmail_address, app_password)
        server.sendmail(gmail_address, to_address, msg.as_string())

    print(f"  Email sent → {to_address}")
