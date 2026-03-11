"""Tools available to the Researcher Agent."""

from __future__ import annotations

import os
from typing import Any

import httpx
from langchain_core.tools import tool

_COINGECKO_BASE = "https://api.coingecko.com/api/v3"
_DEFILLAMA_BASE = os.getenv("DEFILLAMA_BASE_URL", "https://api.llama.fi")
_CLIENT_TIMEOUT = 15.0


def _cg_headers() -> dict[str, str]:
    key = os.getenv("COINGECKO_API_KEY", "")
    if key:
        return {"x-cg-demo-api-key": key}
    return {}


@tool
def fetch_token_price(token_ids: str) -> dict[str, Any]:
    """Fetch current USD prices for one or more CoinGecko token IDs (comma-separated).

    Example: fetch_token_price("bitcoin,ethereum,pendle")
    """
    with httpx.Client(timeout=_CLIENT_TIMEOUT) as client:
        resp = client.get(
            f"{_COINGECKO_BASE}/simple/price",
            params={
                "ids": token_ids,
                "vs_currencies": "usd",
                "include_24hr_change": "true",
                "include_market_cap": "true",
            },
            headers=_cg_headers(),
        )
        resp.raise_for_status()
        return resp.json()


@tool
def fetch_token_market_chart(
    token_id: str, days: int = 30
) -> dict[str, Any]:
    """Fetch historical price, market cap, and volume for a token over N days."""
    with httpx.Client(timeout=_CLIENT_TIMEOUT) as client:
        resp = client.get(
            f"{_COINGECKO_BASE}/coins/{token_id}/market_chart",
            params={"vs_currency": "usd", "days": str(days)},
            headers=_cg_headers(),
        )
        resp.raise_for_status()
        return resp.json()


@tool
def fetch_defi_tvl(protocol: str = "") -> dict[str, Any] | list[Any]:
    """Fetch TVL data from DefiLlama. Pass a protocol slug for a specific
    protocol, or leave empty for all protocols summary."""
    url = (
        f"{_DEFILLAMA_BASE}/protocol/{protocol}"
        if protocol
        else f"{_DEFILLAMA_BASE}/protocols"
    )
    with httpx.Client(timeout=_CLIENT_TIMEOUT) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.json()


@tool
def fetch_defi_yields(pool_id: str = "") -> dict[str, Any] | list[Any]:
    """Fetch yield/APY data from DefiLlama yields API."""
    base = "https://yields.llama.fi"
    url = f"{base}/pool/{pool_id}" if pool_id else f"{base}/pools"
    with httpx.Client(timeout=_CLIENT_TIMEOUT) as client:
        resp = client.get(url)
        resp.raise_for_status()
        data = resp.json()
        # The pools endpoint returns {"status": "success", "data": [...]}
        if isinstance(data, dict) and "data" in data:
            return data["data"][:50]  # Limit to top 50 for context size
        return data


@tool
def search_coingecko(query: str) -> list[dict[str, Any]]:
    """Search CoinGecko for tokens matching a query string."""
    with httpx.Client(timeout=_CLIENT_TIMEOUT) as client:
        resp = client.get(
            f"{_COINGECKO_BASE}/search",
            params={"query": query},
            headers=_cg_headers(),
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("coins", [])[:20]


RESEARCH_TOOLS = [
    fetch_token_price,
    fetch_token_market_chart,
    fetch_defi_tvl,
    fetch_defi_yields,
    search_coingecko,
]
