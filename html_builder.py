"""
html_builder.py — Generates the full standalone HTML page (GitHub Pages).
This is richer than the email — includes full sector table, all news, charts.
"""


def _pct_color(val) -> str:
    if val is None: return "#f0a84a"
    return "#3ecf8e" if val > 0 else ("#e05c5c" if val < 0 else "#f0a84a")


def _pct_arrow(val) -> str:
    if val is None: return "—"
    sign = "+" if val > 0 else ""
    return f"{sign}{val:.2f}%"


def _price(val) -> str:
    try:    return f"${float(val):,.2f}"
    except: return "—"


def _trend_bar(val, width=60) -> str:
    """Render a tiny inline bar proportional to pct change (±5% = full bar)."""
    if val is None:
        return ""
    clamped = max(-5, min(5, val))
    pct_of_max = abs(clamped) / 5 * 100
    color = _pct_color(val)
    direction = "right" if val >= 0 else "left"
    return (
        f'<div style="display:flex;align-items:center;gap:4px;">'
        f'<div style="width:{width}px;height:4px;background:#1a2d50;border-radius:2px;overflow:hidden;">'
        f'<div style="width:{pct_of_max:.0f}%;height:100%;background:{color};'
        f'float:{direction};border-radius:2px;"></div></div>'
        f'<span style="color:{color};font-weight:600;font-size:13px;">{_pct_arrow(val)}</span>'
        f'</div>'
    )


def build_page(data: dict, page_url: str = "") -> str:
    date = data["date"]

    # ── Indices + Macro rows ─────────────────────────────────────────────────
    def quote_rows(group_name):
        rows = ""
        for q in data["groups"].get(group_name, []):
            color = _pct_color(q["pct"])
            rows += f"""
              <tr class="data-row">
                <td class="sym">{q['symbol']}</td>
                <td class="name">{q['name']}</td>
                <td class="num">{_price(q['price'])}</td>
                <td>{_trend_bar(q['pct'])}</td>
                <td style="color:{_pct_color(q['pct5'])};font-weight:600;">{_pct_arrow(q['pct5'])}</td>
                <td style="color:{_pct_color(q['pct1m'])};font-weight:600;">{_pct_arrow(q['pct1m'])}</td>
              </tr>"""
        return rows

    # ── Sector rows ──────────────────────────────────────────────────────────
    sector_rows = ""
    for s in data["sectors"]:
        sec_name = data["sector_names"].get(s["symbol"], "")
        sector_rows += f"""
          <tr class="data-row">
            <td class="sym">{s['symbol']}</td>
            <td class="name">{sec_name}</td>
            <td class="num">{_price(s['price'])}</td>
            <td>{_trend_bar(s['pct'])}</td>
            <td style="color:{_pct_color(s['pct5'])};font-weight:600;">{_pct_arrow(s['pct5'])}</td>
            <td style="color:{_pct_color(s['pct1m'])};font-weight:600;">{_pct_arrow(s['pct1m'])}</td>
          </tr>"""

    # ── Sector rotation callout ──────────────────────────────────────────────
    valid = [s for s in data["sectors"] if s["pct"] is not None]
    rotation_block = ""
    if valid:
        best, worst = valid[0], valid[-1]
        spread = abs((best["pct"] or 0) - (worst["pct"] or 0))
        conviction = "Wide — clear rotation" if spread > 1.5 else "Narrow — low conviction"
        rotation_block = f"""
        <div class="callout-grid">
          <div class="callout green">
            <div class="callout-label">▲ Leading Today</div>
            <div class="callout-ticker">{best['symbol']}</div>
            <div class="callout-name">{data['sector_names'].get(best['symbol'], '')}</div>
            <div class="callout-pct" style="color:#3ecf8e">{_pct_arrow(best['pct'])}</div>
          </div>
          <div class="callout red">
            <div class="callout-label">▼ Lagging Today</div>
            <div class="callout-ticker">{worst['symbol']}</div>
            <div class="callout-name">{data['sector_names'].get(worst['symbol'], '')}</div>
            <div class="callout-pct" style="color:#e05c5c">{_pct_arrow(worst['pct'])}</div>
          </div>
          <div class="callout neutral">
            <div class="callout-label">Spread</div>
            <div class="callout-ticker">{spread:.2f}pp</div>
            <div class="callout-name">{conviction}</div>
          </div>
        </div>"""

    # ── Signals ──────────────────────────────────────────────────────────────
    signals_html = "".join(
        f'<li>{s}</li>' for s in data["signals"]
    )

    # ── News cards ───────────────────────────────────────────────────────────
    news_cards = ""
    for symbol, articles in data.get("news", {}).items():
        for a in articles:
            url_part = f'<a href="{a["url"]}" class="read-more" target="_blank">Read more →</a>' if a["url"] else ""
            summary_part = f'<p class="article-summary">{a["summary"]}</p>' if a["summary"] else ""
            news_cards += f"""
            <div class="news-card">
              <div class="news-ticker">{symbol}</div>
              <div class="news-title">{a['title']}</div>
              {summary_part}
              <div class="news-meta">{a.get('source','')}{'  ·  ' + a['pub'] if a.get('pub') else ''}</div>
              {url_part}
            </div>"""

    if not news_cards:
        news_cards = '<p style="color:#5a7ab0;font-size:14px;">No news available for today\'s top movers.</p>'

    # ── Full HTML ─────────────────────────────────────────────────────────────
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Market Brief — {date}</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      background: #070d1a;
      color: #e8eaf0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      line-height: 1.5;
    }}

    /* ── Header ── */
    .header {{
      background: linear-gradient(135deg, #0d1b3e 0%, #1a2f5e 100%);
      border-bottom: 2px solid #2e5ce6;
      padding: 36px 24px 28px;
      text-align: center;
    }}
    .header-label {{ font-size: 11px; letter-spacing: 3px; text-transform: uppercase; color: #7b9cdb; margin-bottom: 6px; }}
    .header h1 {{ font-size: 32px; font-weight: 700; color: #fff; letter-spacing: -0.5px; }}
    .header-date {{ font-size: 14px; color: #7b9cdb; margin-top: 6px; }}

    /* ── Layout ── */
    .container {{ max-width: 900px; margin: 0 auto; padding: 0 16px 60px; }}

    /* ── Section headings ── */
    .section-label {{
      font-size: 10px; letter-spacing: 2.5px; text-transform: uppercase;
      color: #2e5ce6; font-weight: 700; margin: 32px 0 12px;
    }}

    /* ── Tables ── */
    .data-table {{ width: 100%; border-collapse: collapse; }}
    .data-table th {{
      font-size: 11px; color: #5a7ab0; font-weight: 600;
      text-transform: uppercase; letter-spacing: 1px;
      padding: 8px 0; border-bottom: 1px solid #1e3a6e; text-align: left;
    }}
    .data-table th.num, .data-table td.num {{ text-align: right; }}
    .data-row {{ border-bottom: 1px solid #111e38; }}
    .data-row:hover {{ background: #0f1d3a; }}
    .data-row td {{ padding: 11px 0; font-size: 14px; }}
    td.sym {{ font-weight: 700; color: #fff; width: 70px; }}
    td.name {{ color: #9aafd4; max-width: 200px; font-size: 13px; padding-right: 12px; }}
    td.num {{ text-align: right; color: #e8eaf0; padding-right: 16px; }}

    /* ── Context box ── */
    .context-box {{
      background: #0f1d3a; border: 1px solid #1e3a6e; border-radius: 10px;
      padding: 18px 20px; margin-top: 12px;
    }}
    .context-box ul {{ list-style: none; padding: 0; }}
    .context-box li {{ font-size: 14px; color: #9aafd4; padding: 4px 0; line-height: 1.6; }}
    .context-box li::before {{ content: "• "; color: #2e5ce6; font-weight: 700; }}

    /* ── Callout grid ── */
    .callout-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin-top: 12px; }}
    .callout {{
      background: #0f1d3a; border: 1px solid #1e3a6e; border-radius: 10px;
      padding: 16px; text-align: center;
    }}
    .callout.green {{ border-top: 3px solid #3ecf8e; }}
    .callout.red   {{ border-top: 3px solid #e05c5c; }}
    .callout.neutral {{ border-top: 3px solid #2e5ce6; }}
    .callout-label {{ font-size: 10px; letter-spacing: 1.5px; text-transform: uppercase; color: #5a7ab0; margin-bottom: 8px; }}
    .callout-ticker {{ font-size: 22px; font-weight: 700; color: #fff; }}
    .callout-name {{ font-size: 12px; color: #7b9cdb; margin-top: 2px; }}
    .callout-pct {{ font-size: 18px; font-weight: 700; margin-top: 6px; }}

    /* ── News ── */
    .news-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px; margin-top: 12px; }}
    .news-card {{
      background: #0f1d3a; border: 1px solid #1e3a6e; border-radius: 10px;
      padding: 16px; display: flex; flex-direction: column; gap: 6px;
    }}
    .news-ticker {{ font-size: 11px; font-weight: 700; color: #2e5ce6; letter-spacing: 1px; text-transform: uppercase; }}
    .news-title {{ font-size: 14px; font-weight: 600; color: #fff; line-height: 1.4; }}
    .article-summary {{ font-size: 12px; color: #7b9cdb; line-height: 1.5; }}
    .news-meta {{ font-size: 11px; color: #3a4f72; margin-top: auto; padding-top: 6px; }}
    .read-more {{ font-size: 12px; color: #4a7fff; text-decoration: none; margin-top: 4px; display: inline-block; }}
    .read-more:hover {{ text-decoration: underline; }}

    /* ── Concept box ── */
    .concept-box {{
      background: linear-gradient(135deg, #0d2060, #1a3a7e);
      border-left: 4px solid #2e5ce6; border-radius: 10px;
      padding: 22px; margin-top: 12px;
    }}
    .concept-label {{ font-size: 10px; letter-spacing: 2px; text-transform: uppercase; color: #7b9cdb; font-weight: 600; margin-bottom: 8px; }}
    .concept-title {{ font-size: 18px; font-weight: 700; color: #fff; margin-bottom: 10px; }}
    .concept-body {{ font-size: 14px; color: #9aafd4; line-height: 1.7; }}

    /* ── Footer ── */
    .footer {{
      background: #060c1a; border-top: 1px solid #1a2d50;
      text-align: center; padding: 20px 16px;
      font-size: 11px; color: #3a4f72; line-height: 1.8;
    }}

    /* ── Mobile ── */
    @media (max-width: 600px) {{
      .header h1 {{ font-size: 24px; }}
      .data-table th:nth-child(5),
      .data-table td:nth-child(5),
      .data-table th:nth-child(6),
      .data-table td:nth-child(6) {{ display: none; }}
      td.name {{ max-width: 100px; }}
    }}
  </style>
</head>
<body>

  <div class="header">
    <div class="header-label">Daily Intelligence</div>
    <h1>Market Brief</h1>
    <div class="header-date">{date}</div>
  </div>

  <div class="container">

    <p class="section-label">Market Context</p>
    <div class="context-box">
      <ul>{signals_html}</ul>
    </div>

    <p class="section-label">Indices</p>
    <table class="data-table">
      <thead><tr>
        <th>Symbol</th><th>Name</th><th class="num">Price</th>
        <th>Day %</th><th>5-Day %</th><th>1-Mo %</th>
      </tr></thead>
      <tbody>{quote_rows('Indices')}</tbody>
    </table>

    <p class="section-label">Mega-Cap</p>
    <table class="data-table">
      <thead><tr>
        <th>Symbol</th><th>Name</th><th class="num">Price</th>
        <th>Day %</th><th>5-Day %</th><th>1-Mo %</th>
      </tr></thead>
      <tbody>{quote_rows('Mega-cap')}</tbody>
    </table>

    <p class="section-label">Macro (Gold · Oil · Bonds · Dollar)</p>
    <table class="data-table">
      <thead><tr>
        <th>Symbol</th><th>Name</th><th class="num">Price</th>
        <th>Day %</th><th>5-Day %</th><th>1-Mo %</th>
      </tr></thead>
      <tbody>{quote_rows('Macro')}</tbody>
    </table>

    <p class="section-label">Sector Rotation — SPDR ETFs</p>
    {rotation_block}
    <table class="data-table" style="margin-top:14px;">
      <thead><tr>
        <th>ETF</th><th>Sector</th><th class="num">Price</th>
        <th>Day %</th><th>5-Day %</th><th>1-Mo %</th>
      </tr></thead>
      <tbody>{sector_rows}</tbody>
    </table>

    <p class="section-label">Top Mover News</p>
    <div class="news-grid">{news_cards}</div>

    <p class="section-label">Concept of the Day</p>
    <div class="concept-box">
      <div class="concept-label">Build Your Knowledge</div>
      <div class="concept-title">Why do rising bond yields hurt tech stocks?</div>
      <div class="concept-body">
        Tech companies are valued on <em>future</em> earnings. A higher interest rate (yield)
        is the "discount rate" applied to those future dollars — making them worth less in
        today's terms. So when yields spike, growth and tech stocks fall hardest. Industrials
        and banks are less affected because they earn more in a high-rate environment.
        This is why the Nasdaq often diverges from the Dow during rate-driven moves.
      </div>
    </div>

  </div>

  <div class="footer">
    Market Brief · Updated daily via GitHub Actions<br>
    Data: yFinance (Yahoo Finance) · {date}
  </div>

</body>
</html>"""
