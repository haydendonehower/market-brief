"""
fetcher.py — Pull daily market data and news via yFinance.
"""

from datetime import datetime
import yfinance as yf

WATCHLIST = {
    "Indices":  ["^GSPC", "^DJI", "^IXIC", "^VIX"],
    "Mega-cap": ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META"],
    "Macro":    ["GLD", "USO", "TLT", "DXY=X"],
}

SECTOR_ETFS = {
    "XLK": "Technology",    "XLV": "Health Care",
    "XLF": "Financials",    "XLE": "Energy",
    "XLY": "Consumer Disc.","XLP": "Consumer Staples",
    "XLI": "Industrials",   "XLB": "Materials",
    "XLU": "Utilities",     "XLRE": "Real Estate",
    "XLC": "Comm. Services",
}


def _fetch_one(symbol: str) -> dict:
    t = yf.Ticker(symbol)
    fi = t.fast_info
    try:
        prev  = fi.previous_close
        price = fi.last_price
        high  = fi.day_high
        low   = fi.day_low
        vol   = fi.last_volume
        pct   = ((price - prev) / prev * 100) if prev else None
    except Exception:
        prev = price = high = low = vol = pct = None

    try:
        name = t.info.get("shortName") or t.info.get("longName") or symbol
    except Exception:
        name = symbol

    try:
        h5 = t.history(period="5d")
        pct5 = (h5["Close"].iloc[-1] - h5["Close"].iloc[0]) / h5["Close"].iloc[0] * 100 if len(h5) >= 2 else None
    except Exception:
        pct5 = None

    try:
        h1m = t.history(period="1mo")
        pct1m = (h1m["Close"].iloc[-1] - h1m["Close"].iloc[0]) / h1m["Close"].iloc[0] * 100 if len(h1m) >= 2 else None
    except Exception:
        pct1m = None

    return dict(symbol=symbol, name=name, price=price, pct=pct,
                pct5=pct5, pct1m=pct1m, high=high, low=low, volume=vol)


def _fetch_news(symbol: str, max_items: int = 4) -> list[dict]:
    try:
        raw = yf.Ticker(symbol).news or []
        out = []
        for item in raw[:max_items]:
            c = item.get("content", {})
            title   = c.get("title", item.get("title", ""))
            summary = c.get("summary", "")
            pub     = c.get("pubDate", "")[:10]
            prov    = c.get("provider", {})
            source  = prov.get("displayName", "") if isinstance(prov, dict) else str(prov)
            url_d   = c.get("canonicalUrl", {})
            url     = url_d.get("url", "") if isinstance(url_d, dict) else ""
            if title:
                out.append(dict(title=title, summary=summary, pub=pub, source=source, url=url))
        return out
    except Exception:
        return []


def fetch_all() -> dict:
    """Return a dict with all market data needed for the brief."""
    groups = {}
    all_quotes = []
    for group, tickers in WATCHLIST.items():
        quotes = [_fetch_one(sym) for sym in tickers]
        groups[group] = quotes
        all_quotes.extend(quotes)

    sectors = [_fetch_one(sym) for sym in SECTOR_ETFS]
    sectors.sort(key=lambda s: s["pct"] if s["pct"] is not None else 0, reverse=True)

    # Top movers for news
    movers = sorted(
        [q for q in all_quotes if q["pct"] is not None],
        key=lambda q: abs(q["pct"]), reverse=True,
    )[:3]
    news = {}
    for m in movers:
        articles = _fetch_news(m["symbol"])
        if articles:
            news[m["symbol"]] = articles

    # Market context signals
    idx = {q["symbol"]: q for q in all_quotes}
    sp   = idx.get("^GSPC", {}).get("pct")
    nsdq = idx.get("^IXIC", {}).get("pct")
    vix  = idx.get("^VIX",  {}).get("pct")

    signals = []
    if sp is not None:
        if sp > 1:    signals.append("Broad market risk-on — S&P 500 rallying.")
        elif sp < -1: signals.append("Broad market risk-off — S&P 500 under pressure.")
        else:         signals.append("S&P 500 consolidating near flat.")
    if nsdq is not None and sp is not None:
        diff = nsdq - sp
        if diff > 0.5:    signals.append("Nasdaq outperforming → growth/tech leading.")
        elif diff < -0.5: signals.append("Nasdaq lagging → rotation away from growth/tech.")
    if vix is not None:
        if vix > 10:    signals.append(f"VIX spiking +{vix:.1f}% — traders pricing in uncertainty.")
        elif vix < -10: signals.append(f"VIX falling {vix:.1f}% — fear subsiding.")
    if movers:
        m = movers[0]
        signals.append(f"Biggest mover: {m['symbol']} ({'+' if (m['pct'] or 0) > 0 else ''}{m['pct']:.2f}%)")

    return dict(
        date=datetime.now().strftime("%A, %B %d, %Y"),
        groups=groups,
        sectors=sectors,
        sector_names=SECTOR_ETFS,
        news=news,
        signals=signals,
        movers=movers,
    )
