from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StockQuote:
    symbol: str
    name: str
    price: float | None
    currency: str
    change_percent: float | None
    market_cap: int | None
    volume: int | None
    day_low: float | None
    day_high: float | None
    fifty_two_week_low: float | None
    fifty_two_week_high: float | None


KNOWN_TICKERS = {
    "apple": "AAPL",
    "aapl": "AAPL",
    "tesla": "TSLA",
    "tsla": "TSLA",
    "nvidia": "NVDA",
    "nvda": "NVDA",
    "microsoft": "MSFT",
    "msft": "MSFT",
    "google": "GOOGL",
    "alphabet": "GOOGL",
    "amazon": "AMZN",
    "meta": "META",
    "facebook": "META",
    "netflix": "NFLX",
    "asml": "ASML",
    "asml holding": "ASML",
}


def web_search_stub(query: str) -> list[str]:
    return [
        f"Key background for: {query}",
        "AI agents are useful when tasks require decomposition, memory, and tool use.",
        "Risks include reliability, cost control, observability, and unsafe autonomous actions.",
    ]


def save_note(note: str) -> str:
    return f"Saved note: {note[:120]}"


def is_stock_query(message: str) -> bool:
    lowered = message.lower()
    stock_words = {"stock", "share", "price", "market", "ticker", "quote", "nasdaq", "nyse"}
    if any(word in lowered for word in stock_words):
        return True
    return any(re.search(rf"\b{name}\b", lowered) for name in KNOWN_TICKERS)


def resolve_ticker(message: str) -> str | None:
    lowered = message.lower()
    for name, ticker in KNOWN_TICKERS.items():
        if re.search(rf"\b{re.escape(name)}\b", lowered):
            return ticker
    cashtags = re.findall(r"\$([A-Za-z]{1,5})\b", message)
    if cashtags:
        return cashtags[0].upper()
    explicit = re.findall(r"\b[A-Z]{1,5}\b", message)
    return explicit[0].upper() if explicit else None


def extract_company_or_ticker(message: str) -> str | None:
    lowered = message.lower()
    for name in KNOWN_TICKERS:
        if re.search(rf"\b{re.escape(name)}\b", lowered):
            return name
    cashtags = re.findall(r"\$([A-Za-z]{1,5})\b", message)
    if cashtags:
        return cashtags[0].upper()
    explicit = re.findall(r"\b[A-Z]{1,5}\b", message)
    return explicit[0].upper() if explicit else None


def get_stock_quote(query: str) -> StockQuote:
    ticker = resolve_ticker(query) or query.strip().upper()
    try:
        import yfinance as yf

        stock = yf.Ticker(ticker)
        info: dict[str, Any] = stock.info
        history = stock.history(period="2d")
        price = _first_number(info.get("regularMarketPrice"), info.get("currentPrice"))
        if price is None and not history.empty:
            price = float(history["Close"].iloc[-1])
        previous_close = _first_number(info.get("regularMarketPreviousClose"), info.get("previousClose"))
        change_percent = None
        if price is not None and previous_close:
            change_percent = ((price - previous_close) / previous_close) * 100
        return StockQuote(
            symbol=ticker,
            name=info.get("longName") or info.get("shortName") or ticker,
            price=price,
            currency=info.get("currency") or "USD",
            change_percent=change_percent,
            market_cap=_first_int(info.get("marketCap")),
            volume=_first_int(info.get("volume"), info.get("regularMarketVolume")),
            day_low=_first_number(info.get("dayLow"), info.get("regularMarketDayLow")),
            day_high=_first_number(info.get("dayHigh"), info.get("regularMarketDayHigh")),
            fifty_two_week_low=_first_number(info.get("fiftyTwoWeekLow")),
            fifty_two_week_high=_first_number(info.get("fiftyTwoWeekHigh")),
        )
    except Exception:
        return StockQuote(
            symbol=ticker,
            name=ticker,
            price=None,
            currency="USD",
            change_percent=None,
            market_cap=None,
            volume=None,
            day_low=None,
            day_high=None,
            fifty_two_week_low=None,
            fifty_two_week_high=None,
        )


def format_stock_quote(quote: StockQuote) -> str:
    if quote.price is None:
        return (
            f"I found the ticker {quote.symbol}, but I could not fetch live Yahoo Finance data right now.\n\n"
            "This is market data only, not financial advice."
        )

    lines = [
        f"{quote.name} ({quote.symbol})",
        "",
        f"Price: {quote.currency} {quote.price:,.2f}",
    ]
    if quote.change_percent is not None:
        sign = "+" if quote.change_percent >= 0 else ""
        lines.append(f"Today: {sign}{quote.change_percent:.2f}%")
    if quote.market_cap:
        lines.append(f"Market Cap: {_compact_number(quote.market_cap)}")
    if quote.volume:
        lines.append(f"Volume: {_compact_number(quote.volume)}")
    if quote.day_low is not None and quote.day_high is not None:
        lines.append(f"Day Range: {quote.currency} {quote.day_low:,.2f} - {quote.day_high:,.2f}")
    if quote.fifty_two_week_low is not None and quote.fifty_two_week_high is not None:
        lines.append(
            f"52W Range: {quote.currency} {quote.fifty_two_week_low:,.2f} - {quote.fifty_two_week_high:,.2f}"
        )
    lines.extend(["", "This is market data only, not financial advice."])
    return "\n".join(lines)


def _first_number(*values: Any) -> float | None:
    for value in values:
        if isinstance(value, (int, float)):
            return float(value)
    return None


def _first_int(*values: Any) -> int | None:
    for value in values:
        if isinstance(value, int):
            return value
    return None


def _compact_number(value: int) -> str:
    for suffix, divisor in (("T", 1_000_000_000_000), ("B", 1_000_000_000), ("M", 1_000_000)):
        if abs(value) >= divisor:
            return f"{value / divisor:.2f}{suffix}"
    return f"{value:,}"
