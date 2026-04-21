"""
Agent loop for 毒舌财神 — direct tool execution + streaming GLM verdict.

Phase 0: LLM intent extraction (products[] list + is_purchase flag)
Phase 1: concurrent price resolution via asyncio.gather + savings calc + tx analysis
Phase 2: stream GLM verdict with all context injected as tool history
"""
import asyncio
import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from mcp import ClientSession
from openai import AsyncOpenAI

from agent.prompt import build_system_prompt
from tools.price import get_price
from tools.savings import calculate_savings_impact

_MODEL_CTX_LIMIT = 131_072   # GLM 128 K token window
_COMPRESS_THRESHOLD = 0.80
_COMPRESS_KEEP_RECENT = 6    # messages kept verbatim at the tail

# Tool definitions passed to GLM for native tool calling
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_product_price",
            "description": "查询指定商品的市场参考价格",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_name": {
                        "type": "string",
                        "description": "要查询价格的商品名称，简洁清晰，不含价格信息"
                    }
                },
                "required": ["product_name"]
            }
        }
    }
]


def _estimate_tokens(messages: list[dict]) -> int:
    total = 0
    for m in messages:
        content = m.get("content") or ""
        if isinstance(content, str):
            total += len(content) // 2 + 4
        if m.get("tool_calls"):
            total += len(json.dumps(m["tool_calls"])) // 2
    return total


async def _compress_history(messages: list[dict], glm_client: AsyncOpenAI) -> list[dict]:
    """
    Summarize old messages into a single system note; keep the most recent
    _COMPRESS_KEEP_RECENT messages verbatim.  Called only when token estimate
    exceeds the compression threshold.
    """
    if len(messages) <= _COMPRESS_KEEP_RECENT:
        return messages

    old = messages[:-_COMPRESS_KEEP_RECENT]
    recent = messages[-_COMPRESS_KEEP_RECENT:]

    lines = []
    for m in old:
        label = "用户" if m["role"] == "user" else "财神"
        text = m.get("content") or ""
        if text:
            lines.append(f"{label}：{text}")

    try:
        resp = await glm_client.chat.completions.create(
            model="glm-4-flash",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "请将以下对话历史压缩成简洁摘要（100字以内），"
                        "重点保留：用户的消费意图、财神的判断结论、涉及金额与储蓄变化。"
                        "直接输出摘要，不加任何前缀。"
                    ),
                },
                {"role": "user", "content": "\n".join(lines)},
            ],
            stream=False,
        )
        summary = (resp.choices[0].message.content or "").strip()
    except Exception:
        summary = f"（{len(old)} 条历史对话已压缩）"

    return [{"role": "system", "content": f"[早期对话摘要] {summary}"}] + recent


def _analyze_transactions(transactions: list[dict]) -> dict:
    """
    Compute behavioral patterns from recent transaction history.
    All timestamps expected as ISO 8601 strings.
    """
    if not transactions:
        return {
            "has_history": False,
            "summary": "无历史消费记录",
        }

    now = datetime.now(timezone.utc)

    withdrawals_7d: list[dict] = []
    today_str = now.strftime("%Y-%m-%d")
    today_spent = 0.0

    for tx in transactions:
        if tx.get("type") != "withdraw":
            continue
        try:
            ts = datetime.fromisoformat(tx["timestamp"].replace("Z", "+00:00"))
        except (KeyError, ValueError):
            continue
        days_ago = (now - ts).days
        if days_ago <= 7:
            withdrawals_7d.append({**tx, "_date": ts.strftime("%Y-%m-%d")})
        if ts.strftime("%Y-%m-%d") == today_str:
            today_spent += tx.get("amount", 0)

    total_7d = sum(t.get("amount", 0) for t in withdrawals_7d)
    spend_dates = sorted({t["_date"] for t in withdrawals_7d}, reverse=True)

    # Count consecutive spending days ending today or yesterday
    consecutive = 0
    check_date = now
    for _ in range(8):
        d = check_date.strftime("%Y-%m-%d")
        if d in spend_dates:
            consecutive += 1
            check_date -= timedelta(days=1)
        else:
            break

    lines: list[str] = []
    if consecutive >= 3:
        lines.append(f"⚠️ 连续 {consecutive} 天有消费记录")
    if total_7d > 0:
        lines.append(f"近7天取出共 ¥{total_7d:.0f}，共 {len(withdrawals_7d)} 笔")
    if today_spent > 0:
        lines.append(f"今天已取出 ¥{today_spent:.0f}")

    return {
        "has_history": True,
        "consecutive_spend_days": consecutive,
        "last_7d_total": total_7d,
        "last_7d_count": len(withdrawals_7d),
        "today_spent": today_spent,
        "summary": "；".join(lines) if lines else "近期无异常消费",
    }


async def _extract_intent(user_query: str, glm_client: AsyncOpenAI) -> dict:
    """
    Phase 0: Use glm-4-flash with JSON mode to extract all products mentioned,
    their stated prices, and whether the message expresses a purchase intent.
    Returns {"products": [{"name": str, "stated_price": float | None}], "is_purchase": bool}.
    Falls back gracefully on any error (defaults to is_purchase=True to avoid missed verdicts).
    """
    try:
        resp = await glm_client.chat.completions.create(
            model="glm-4-flash",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "从用户消息中提取信息，以JSON格式返回，格式如下：\n"
                        '{"products": [{"name": "商品名称（简洁，不含价格）", "stated_price": 数字或null}], "is_purchase": true或false}\n'
                        "products 是数组，包含用户提到的所有商品（通常1个，偶尔多个）。\n"
                        "is_purchase: 用户是否在表达购买/消费/花钱的意愿（true），还是在闲聊/问候/提问（false）。\n"
                        "stated_price 仅在用户明确为该商品提及金额时填写，否则为 null。"
                    ),
                },
                {"role": "user", "content": user_query},
            ],
            response_format={"type": "json_object"},
            stream=False,
        )
        content = resp.choices[0].message.content or "{}"
        data = json.loads(content)
        raw_products = data.get("products", [])
        products: list[dict] = []
        for item in raw_products:
            name = str(item.get("name", "")).strip() or user_query[:30]
            stated_price = item.get("stated_price")
            if stated_price is not None:
                stated_price = float(stated_price)
            products.append({"name": name, "stated_price": stated_price})
        if not products:
            products = [{"name": user_query[:30], "stated_price": None}]
        is_purchase = bool(data.get("is_purchase", True))
        return {"products": products, "is_purchase": is_purchase}
    except Exception:
        return {"products": [{"name": user_query[:30], "stated_price": None}], "is_purchase": True}


async def _resolve_price(intent: dict, mcp_session: ClientSession) -> dict:
    """
    Resolve the price for a single product intent.
    If user stated a price, return it directly without MCP call.
    Otherwise delegate to get_price via MCP.
    intent must have keys: "product" (str) and "stated_price" (float | None).
    """
    stated_price = intent["stated_price"]
    if stated_price is not None:
        return {
            "name": intent["product"],
            "price": stated_price,
            "price_min": stated_price,
            "price_max": stated_price,
            "source": "用户自报",
            "confidence": "user_stated",
            "currency": "CNY",
            "sources": [],
        }
    return await get_price(intent["product"], mcp_session)


async def _resolve_prices(products: list[dict], mcp_session: ClientSession) -> list[dict]:
    """
    Concurrently resolve prices for all products using asyncio.gather.
    Each element of `products` is {"name": str, "stated_price": float | None}.
    Returns a list of price_data dicts in the same order as `products`.
    """
    tasks = [_resolve_price({"product": p["name"], "stated_price": p["stated_price"]}, mcp_session)
             for p in products]
    return list(await asyncio.gather(*tasks))


def _build_single_price_context(price_data: dict) -> str:
    """
    Build the natural-language price context string for a single product,
    injected into GLM's tool history.
    """
    confidence = price_data.get("confidence", "unknown")
    resolved_price: float = price_data.get("price", 0.0)

    if confidence == "unknown":
        return "价格未知（搜索失败），请用角色语气追问用户这个东西到底多少钱。"
    elif confidence == "user_stated":
        return f"用户自己说的价格：¥{resolved_price:.0f}，直接用这个数字。"
    else:
        fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        source_names = "、".join(
            {s["platform"] for s in price_data.get("sources", [])}
        ) or price_data.get("source", "网络搜索")
        return (
            f"市场参考价（{confidence}）：{price_data.get('name', '')} "
            f"¥{price_data.get('price_min', resolved_price):.0f}"
            f"～¥{price_data.get('price_max', resolved_price):.0f}，"
            f"参考中位价 ¥{resolved_price:.0f}。"
            f"数据来源：{source_names}，抓取时间：{fetched_at}。"
            f"此数据来自实时爬取，优先级高于训练知识，请以此数字为准。"
        )


def _build_price_context(resolved: list[dict]) -> str:
    """
    Build a combined natural-language price context string for all resolved products.
    Loops over each item and calls _build_single_price_context; joins with newline.
    """
    parts = [_build_single_price_context(price_data) for price_data in resolved]
    return "\n".join(parts)


def _build_tool_context(
    price_context: str,
    savings: float,
    target: float,
    impact: dict,
    tx_analysis: dict,
) -> dict:
    """
    Assemble the tool result dict that gets injected as a synthetic tool exchange.
    """
    return {
        "price_info": price_context,
        "savings_impact": {
            "current_savings": savings,
            "new_savings": impact["new_savings"],
            "target": target,
            "progress_before": round(savings / target * 100, 1) if target else 0,
            "progress_after": impact["progress"],
            "delta": impact["delta"],
        },
        "transaction_analysis": tx_analysis["summary"],
    }


def _inject_tool_exchange(
    messages: list[dict],
    tool_context: dict,
    user_query: str,
) -> list[dict]:
    """
    Append a synthetic assistant tool_call + tool result pair to the message list.
    Does NOT mutate the input list.
    """
    tc_id = f"call_{uuid4().hex[:16]}"
    return messages + [
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": tc_id,
                    "type": "function",
                    "function": {
                        "name": "get_financial_context",
                        "arguments": json.dumps({"query": user_query}, ensure_ascii=False),
                    },
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": tc_id,
            "content": json.dumps(tool_context, ensure_ascii=False),
        },
    ]


def _build_no_intent_sentinel(savings: float, target: float) -> dict:
    """Sentinel payload emitted on the 2: channel when there is no purchase intent."""
    return {
        "confidence": "no_intent",
        "new_savings": savings,
        "progress_pct": round(savings / target * 100, 1) if target else 0,
        "delta": 0,
        "product_name": "",
        "price_found": 0,
        "price_min": 0,
        "price_max": 0,
        "source": "",
        "sources": [],
    }


def _build_savings_payload(resolved: list[dict], impact: dict) -> dict:
    """
    Build the 2: channel payload dict sent to the frontend before the verdict stream.
    When multiple products are resolved, total_price = sum of all prices.
    items[] is included only when len(resolved) > 1.
    The top-level price fields (price_found, price_min, price_max, product_name,
    source, confidence, sources) reflect the first item for backward-compat display.
    """
    first = resolved[0] if resolved else {}
    resolved_price: float = first.get("price", 0.0)
    payload: dict = {
        "new_savings": impact["new_savings"],
        "progress_pct": impact["progress"],
        "delta": impact["delta"],
        "product_name": first.get("name", ""),
        "price_found": resolved_price,
        "price_min": first.get("price_min", resolved_price),
        "price_max": first.get("price_max", resolved_price),
        "source": first.get("source", ""),
        "confidence": first.get("confidence", "unknown"),
        "sources": first.get("sources", []),
    }
    if len(resolved) > 1:
        payload["items"] = [
            {
                "name": pd.get("name", ""),
                "price": pd.get("price", 0.0),
                "confidence": pd.get("confidence", "unknown"),
            }
            for pd in resolved
        ]
    return payload


async def _stream_verdict(glm_client: AsyncOpenAI, model: str, messages: list[dict]):
    """
    Async generator that streams the GLM verdict and emits Vercel Data Stream
    Protocol lines: 0: text chunks, then e: and d: finish events.
    """
    response = await glm_client.chat.completions.create(
        model=model,
        messages=messages,
        stream=True,
    )
    prompt_tokens = 0
    completion_tokens = 0
    full_text = ""
    async for chunk in response:
        choice = chunk.choices[0] if chunk.choices else None
        if not choice:
            continue
        text = (choice.delta.content or "") if choice.delta else ""
        if text:
            full_text += text
            yield f'0:{json.dumps(text)}\n'
        if hasattr(chunk, "usage") and chunk.usage:
            prompt_tokens = chunk.usage.prompt_tokens or prompt_tokens
            completion_tokens = chunk.usage.completion_tokens or completion_tokens

    verdict: str | None = "批准" if "批准" in full_text else "驳回" if "驳回" in full_text else None
    yield f'2:{json.dumps([{"verdict": verdict}])}\n'

    finish_meta = json.dumps({
        "finishReason": "stop",
        "usage": {"promptTokens": prompt_tokens, "completionTokens": completion_tokens},
        "isContinued": False,
    })
    yield f'e:{finish_meta}\n'
    yield f'd:{finish_meta}\n'


async def run_agent_loop(
    messages: list[dict],
    savings: float,
    target: float,
    mcp_session: ClientSession,
    glm_client: AsyncOpenAI,
    model: str,
    transactions: list[dict] | None = None,
    persona: str = "snarky",
):
    """Async generator: yields Vercel Data Stream Protocol lines (f/0/2/e/d)."""
    msg_id = str(uuid4())
    yield f'f:{json.dumps({"messageId": msg_id})}\n'
    history = list(messages)
    if _estimate_tokens([{"role": "system", "content": build_system_prompt(persona)}] + history) > int(_MODEL_CTX_LIMIT * _COMPRESS_THRESHOLD):
        history = await _compress_history(history, glm_client)
    full_messages: list[dict] = [{"role": "system", "content": build_system_prompt(persona)}] + history
    user_query = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
    intent = await _extract_intent(user_query, glm_client)
    if not intent["is_purchase"]:
        yield f'2:{json.dumps([_build_no_intent_sentinel(savings, target)])}\n'
        async for line in _stream_verdict(glm_client, model, full_messages):
            yield line
        return
    resolved = await _resolve_prices(intent["products"], mcp_session)
    total_price: float = sum(pd.get("price", 0.0) for pd in resolved)
    impact = calculate_savings_impact(total_price, savings, target)
    tx_analysis = _analyze_transactions(transactions or [])
    price_context = _build_price_context(resolved)
    tool_context = _build_tool_context(price_context, savings, target, impact, tx_analysis)
    full_messages = _inject_tool_exchange(full_messages, tool_context, user_query)
    savings_payload = _build_savings_payload(resolved, impact)
    yield f'2:{json.dumps([savings_payload])}\n'
    async for line in _stream_verdict(glm_client, model, full_messages):
        yield line
