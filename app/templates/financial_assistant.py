from __future__ import annotations

from app.templates.types import WorkflowTemplate


FINANCIAL_ASSISTANT_TEMPLATE = WorkflowTemplate(
    key="financial_assistant",
    name="Financial Assistant",
    description="Telegram-first workflow that detects stock queries, resolves tickers, fetches Yahoo Finance data, and formats a clean reply.",
    nodes=[
        "query_detector_agent",
        "company_extractor_agent",
        "ticker_resolver_agent",
        "market_data_agent",
        "response_formatter_agent",
    ],
    edges=[
        ("telegram_user", "query_detector_agent"),
        ("query_detector_agent", "company_extractor_agent"),
        ("company_extractor_agent", "ticker_resolver_agent"),
        ("ticker_resolver_agent", "market_data_agent"),
        ("market_data_agent", "response_formatter_agent"),
        ("response_formatter_agent", "telegram_user"),
    ],
    sample_input="What is Apple's stock price today?",
    default_config={
        "roles": {
            "query_detector_agent": "Detect whether a Telegram message is a stock-related query.",
            "company_extractor_agent": "Extract the company name or ticker mentioned by the user.",
            "ticker_resolver_agent": "Resolve the extracted company or ticker to the exact stock symbol.",
            "market_data_agent": "Fetch latest stock price and key stats from Yahoo Finance.",
            "response_formatter_agent": "Format a simplified Telegram response with a short disclaimer.",
        },
        "tools": ["get_stock_quote"],
    },
)
