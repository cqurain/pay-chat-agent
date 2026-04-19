"""
Agent loop for 毒舌财神 — direct tool execution + streaming GLM verdict.

Phase 0: LLM intent extraction (product keyword + stated price)
Phase 1: price resolution (user_stated skip-MCP | scrape | unknown) + savings calc + tx analysis
Phase 2: stream GLM verdict with all context injected as tool history
"""
import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from mcp import ClientSession
from openai import AsyncOpenAI

from agent.prompt import build_system_prompt
from tools.price import get_price
from tools.savings import calculate_savings_impact


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
    Phase 0: Use glm-4-flash with JSON mode to extract product name and stated price.
    Returns {"product": str, "stated_price": float | None}.
    Falls back gracefully on any error.
    """
    try:
        resp = await glm_client.chat.completions.create(
            model="glm-4-flash",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "从用户的消费意图中提取信息，以JSON格式返回，格式如下：\n"
                        '{"product": "商品名称（简洁，不含价格）", "stated_price": 数字或null}\n'
                        "stated_price 仅在用户明确提及金额时填写，否则为 null。"
                    ),
                },
                {"role": "user", "content": user_query},
            ],
            response_format={"type": "json_object"},
            stream=False,
        )
        content = resp.choices[0].message.content or "{}"
        data = json.loads(content)
        product = str(data.get("product", user_query[:30])).strip() or user_query[:30]
        stated_price = data.get("stated_price")
        if stated_price is not None:
            stated_price = float(stated_price)
        return {"product": product, "stated_price": stated_price}
    except Exception:
        return {"product": user_query[:30], "stated_price": None}


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
    """
    Async generator yielding Vercel Data Stream Protocol lines.

    Protocol lines emitted (in order):
        f:{messageId}   — stream init
        0:{text}        — streamed text chunks
        2:[{payload}]   — price + savings impact payload
        e:{meta}        — finish event
        d:{meta}        — done event
    """
    msg_id = str(uuid4())
    yield f'f:{json.dumps({"messageId": msg_id})}\n'

    full_messages: list[dict] = [{"role": "system", "content": build_system_prompt(persona)}] + list(messages)
    user_query = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")

    # ── Phase 0: LLM intent extraction ───────────────────────────────────
    intent = await _extract_intent(user_query, glm_client)
    product_keyword = intent["product"]
    stated_price = intent["stated_price"]

    # ── Phase 1: resolve price + savings impact + tx analysis ────────────
    if stated_price is not None:
        price_data = {
            "name": product_keyword,
            "price": stated_price,
            "price_min": stated_price,
            "price_max": stated_price,
            "source": "用户自报",
            "confidence": "user_stated",
            "currency": "CNY",
            "sources": [],
        }
    else:
        price_data = await get_price(product_keyword, mcp_session)

    confidence = price_data.get("confidence", "unknown")
    resolved_price: float = price_data.get("price", 0.0)

    impact = calculate_savings_impact(resolved_price, savings, target)
    tx_analysis = _analyze_transactions(transactions or [])

    # Build a rich context string for GLM
    if confidence == "unknown":
        price_context = "价格未知（搜索失败），请用毒舌角色语气追问用户这个东西到底多少钱。"
    elif confidence == "user_stated":
        price_context = (
            f"用户自己说的价格：¥{resolved_price:.0f}，直接用这个数字。"
        )
    else:
        fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        source_names = "、".join(
            {s["platform"] for s in price_data.get("sources", [])}
        ) or price_data.get("source", "网络搜索")
        price_context = (
            f"市场参考价（{confidence}）：{price_data.get('name', '')} "
            f"¥{price_data.get('price_min', resolved_price):.0f}"
            f"～¥{price_data.get('price_max', resolved_price):.0f}，"
            f"参考中位价 ¥{resolved_price:.0f}。"
            f"数据来源：{source_names}，抓取时间：{fetched_at}。"
            f"此数据来自实时爬取，优先级高于训练知识，请以此数字为准。"
        )

    tool_context = {
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

    # Inject as synthetic tool exchange so GLM sees grounded data
    tc_id = f"call_{uuid4().hex[:16]}"
    full_messages += [
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

    # ── Phase 2: stream GLM verdict ───────────────────────────────────────
    # Emit price+impact payload so frontend renders the card before text starts
    savings_payload = {
        "new_savings": impact["new_savings"],
        "progress_pct": impact["progress"],
        "delta": impact["delta"],
        "product_name": price_data.get("name", ""),
        "price_found": resolved_price,
        "price_min": price_data.get("price_min", resolved_price),
        "price_max": price_data.get("price_max", resolved_price),
        "source": price_data.get("source", ""),
        "confidence": confidence,
        "sources": price_data.get("sources", []),
    }
    yield f'2:{json.dumps([savings_payload])}\n'

    prompt_tokens = 0
    completion_tokens = 0

    response = await glm_client.chat.completions.create(
        model=model,
        messages=full_messages,
        stream=True,
    )

    async for chunk in response:
        choice = chunk.choices[0] if chunk.choices else None
        if not choice:
            continue
        text = (choice.delta.content or "") if choice.delta else ""
        if text:
            yield f'0:{json.dumps(text)}\n'
        if hasattr(chunk, "usage") and chunk.usage:
            prompt_tokens = chunk.usage.prompt_tokens or prompt_tokens
            completion_tokens = chunk.usage.completion_tokens or completion_tokens

    finish_meta = json.dumps(
        {
            "finishReason": "stop",
            "usage": {"promptTokens": prompt_tokens, "completionTokens": completion_tokens},
            "isContinued": False,
        }
    )
    yield f'e:{finish_meta}\n'
    yield f'd:{finish_meta}\n'
