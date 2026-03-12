"""Tools available to the Back-end Agent."""

from __future__ import annotations

import json
import textwrap

from langchain_core.tools import tool


@tool
def generate_fastapi_endpoint(
    route: str,
    method: str = "GET",
    description: str = "",
    response_model_fields: str = "{}",
    data_source: str = "coingecko",
) -> str:
    """Generate a FastAPI endpoint with caching and error handling.

    Args:
        route: URL path, e.g. '/api/prices/{token_id}'.
        method: HTTP method.
        description: Endpoint description for OpenAPI docs.
        response_model_fields: JSON string of field -> type mappings.
        data_source: 'coingecko', 'defillama', or 'database'.
    """
    fields: dict = json.loads(response_model_fields) if response_model_fields else {}
    model_name = "".join(
        part.capitalize()
        for part in route.strip("/").replace("{", "").replace("}", "").split("/")
    ) + "Response"

    field_lines = []
    for fname, ftype in fields.items():
        field_lines.append(f"    {fname}: {ftype}")

    field_block = "\n".join(field_lines) if field_lines else "    pass"

    path_params = [
        seg.strip("{}")
        for seg in route.split("/")
        if seg.startswith("{")
    ]
    func_params = ", ".join(f"{p}: str" for p in path_params)

    cache_ttl = {"coingecko": 30, "defillama": 300, "database": 3600}
    ttl = cache_ttl.get(data_source, 60)

    return textwrap.dedent(f"""\
        from fastapi import APIRouter, HTTPException
        from pydantic import BaseModel
        from functools import lru_cache
        from datetime import datetime
        import httpx

        router = APIRouter()

        class {model_name}(BaseModel):
        {field_block}

        _cache: dict[str, tuple[datetime, dict]] = {{}}
        _CACHE_TTL = {ttl}  # seconds

        def _get_cached(key: str) -> dict | None:
            if key in _cache:
                ts, data = _cache[key]
                if (datetime.utcnow() - ts).total_seconds() < _CACHE_TTL:
                    return data
                del _cache[key]
            return None

        def _set_cached(key: str, data: dict) -> None:
            _cache[key] = (datetime.utcnow(), data)

        @router.{method.lower()}("{route}", response_model={model_name})
        async def handle({func_params}) -> {model_name}:
            \"\"\"{description or "Auto-generated endpoint."}\"\"\"
            cache_key = f"{route}" + "|" + "|".join([{', '.join(path_params)}]) if [{', '.join(f'"{p}"' for p in path_params)}] else "{route}"

            cached = _get_cached(cache_key)
            if cached:
                return {model_name}(**cached)

            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    # TODO: Replace with actual {data_source} API call
                    resp = await client.get("https://api.example.com/data")
                    resp.raise_for_status()
                    payload = resp.json()

                _set_cached(cache_key, payload)
                return {model_name}(**payload)
            except httpx.HTTPStatusError as e:
                raise HTTPException(status_code=e.response.status_code, detail=str(e))
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Internal error: {{e}}")
    """)


@tool
def generate_pydantic_model(
    model_name: str,
    fields: str = "{}",
    description: str = "",
    validators: str = "[]",
) -> str:
    """Generate a Pydantic model for data validation.

    Args:
        model_name: PascalCase model name.
        fields: JSON string of field -> {"type": str, "description": str, "optional": bool}.
        description: Model docstring.
        validators: JSON array of {"field": str, "rule": str} validation rules.
    """
    field_defs: dict = json.loads(fields) if fields else {}
    validator_list: list = json.loads(validators) if validators else []

    lines = [
        "from __future__ import annotations",
        "",
        "from pydantic import BaseModel, Field, field_validator",
        "",
        "",
        f"class {model_name}(BaseModel):",
        f'    """{description or model_name} schema."""',
        "",
    ]

    for fname, finfo in field_defs.items():
        if isinstance(finfo, str):
            finfo = {"type": finfo}
        ftype = finfo.get("type", "str")
        fdesc = finfo.get("description", "")
        optional = finfo.get("optional", False)
        if optional:
            ftype = f"{ftype} | None"
            lines.append(
                f'    {fname}: {ftype} = Field(None, description="{fdesc}")'
            )
        else:
            lines.append(
                f'    {fname}: {ftype} = Field(..., description="{fdesc}")'
            )

    for v in validator_list:
        field = v.get("field", "")
        rule = v.get("rule", "")
        lines.extend([
            "",
            f"    @field_validator('{field}')",
            "    @classmethod",
            f"    def validate_{field}(cls, v):",
            f"        # {rule}",
            f"        return v",
        ])

    return "\n".join(lines)


@tool
def generate_data_transformer(
    source_format: str = "coingecko_price",
    output_fields: str = '["token_id", "price_usd", "change_24h", "market_cap"]',
) -> str:
    """Generate a data transformation function that normalizes raw API data.

    Args:
        source_format: The data source format to transform from.
        output_fields: JSON array of desired output field names.
    """
    fields: list[str] = json.loads(output_fields)

    transformers = {
        "coingecko_price": textwrap.dedent("""\
            def transform_coingecko_prices(raw: dict) -> list[dict]:
                \"\"\"Transform CoinGecko /simple/price response.\"\"\"
                results = []
                for token_id, data in raw.items():
                    results.append({
                        "token_id": token_id,
                        "price_usd": data.get("usd", 0),
                        "change_24h": data.get("usd_24h_change", 0),
                        "market_cap": data.get("usd_market_cap", 0),
                        "last_updated": datetime.utcnow().isoformat(),
                    })
                return results
        """),
        "defillama_tvl": textwrap.dedent("""\
            def transform_defillama_tvl(raw: dict) -> dict:
                \"\"\"Transform DefiLlama /protocol response.\"\"\"
                tvl_history = []
                for point in raw.get("tvl", []):
                    tvl_history.append({
                        "date": datetime.utcfromtimestamp(point["date"]).isoformat(),
                        "tvl_usd": point["totalLiquidityUSD"],
                    })
                return {
                    "protocol": raw.get("name", ""),
                    "symbol": raw.get("symbol", ""),
                    "current_tvl": raw.get("currentChainTvls", {}),
                    "tvl_history": tvl_history[-90:],  # Last 90 days
                }
        """),
        "defillama_yields": textwrap.dedent("""\
            def transform_defillama_yields(raw: list[dict]) -> list[dict]:
                \"\"\"Transform DefiLlama /pools yield data.\"\"\"
                return [
                    {
                        "pool_id": p.get("pool", ""),
                        "project": p.get("project", ""),
                        "chain": p.get("chain", ""),
                        "symbol": p.get("symbol", ""),
                        "tvl_usd": p.get("tvlUsd", 0),
                        "apy": p.get("apy", 0),
                        "apy_base": p.get("apyBase", 0),
                        "apy_reward": p.get("apyReward", 0),
                    }
                    for p in raw
                ]
        """),
    }

    if source_format in transformers:
        return "from datetime import datetime\n\n" + transformers[source_format]

    # Generic transformer
    field_assignments = "\n".join(
        f'            "{f}": item.get("{f}"),' for f in fields
    )
    return textwrap.dedent(f"""\
        from datetime import datetime

        def transform_{source_format}(raw: dict | list) -> list[dict]:
            \"\"\"Transform {source_format} data into normalized format.\"\"\"
            items = raw if isinstance(raw, list) else [raw]
            return [
                {{
        {field_assignments}
                    "transformed_at": datetime.utcnow().isoformat(),
                }}
                for item in items
            ]
    """)


@tool
def generate_api_aggregator(
    endpoints: str = '[]',
    aggregator_name: str = "fetch_data",
) -> str:
    """Generate an async aggregator that fetches from multiple APIs in parallel.

    Args:
        endpoints: JSON array of {"name": str, "url": str, "transform": str}.
        aggregator_name: Function name for the aggregator.
    """
    endpoint_list: list[dict] = json.loads(endpoints) if endpoints else []

    fetch_blocks = []
    for ep in endpoint_list:
        name = ep.get("name", "data")
        url = ep.get("url", "")
        fetch_blocks.append(
            f'        tasks["{name}"] = client.get("{url}")'
        )

    task_lines = "\n".join(fetch_blocks) if fetch_blocks else '        # Add API calls here'

    return textwrap.dedent(f"""\
        import asyncio
        import httpx
        from datetime import datetime

        async def {aggregator_name}() -> dict:
            \"\"\"Fetch data from multiple sources in parallel.\"\"\"
            async with httpx.AsyncClient(timeout=15.0) as client:
                tasks: dict[str, asyncio.Task] = {{}}
        {task_lines}

                results = {{}}
                for name, coro in tasks.items():
                    try:
                        resp = await coro
                        resp.raise_for_status()
                        results[name] = {{
                            "data": resp.json(),
                            "status": "ok",
                            "fetched_at": datetime.utcnow().isoformat(),
                        }}
                    except Exception as e:
                        results[name] = {{
                            "data": None,
                            "status": "error",
                            "error": str(e),
                            "fetched_at": datetime.utcnow().isoformat(),
                        }}

                return results
    """)


BACKEND_TOOLS = [
    generate_fastapi_endpoint,
    generate_pydantic_model,
    generate_data_transformer,
    generate_api_aggregator,
]
