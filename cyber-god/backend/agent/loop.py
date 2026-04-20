"""
Agent loop for 毒舌财神 — ReAct-lite: GLM-5 drives real tool calling natively.

Loop structure:
  1. Build message history + system prompt
  2. Run _run_agentic_loop: GLM calls search_product_price as needed (up to MAX_TOOL_ROUNDS=5)
  3. Aggregate price results, calculate savings impact
  4. Emit 2: savings payload
  5. Stream verdict via _stream_verdict
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


async def _execute_tool(name: str, args: dict, mcp_session: ClientSession) -> str:
    """Dispatch a single tool call by name; return result as JSON string."""
    if name == "search_product_price":
        product_name = str(args.get("product_name", "")).strip()[:100]
        result = await get_price(product_name, mcp_session)
        return json.dumps(result, ensure_ascii=False)
    else:
        return json.dumps({"error": f"unknown tool: {name}"}, ensure_ascii=False)


async def _execute_tool_with_retry(
    tc: dict,
    mcp_session: ClientSession,
    retries: int = 2,
) -> tuple[str, str]:
    """
    Execute a tool call with timeout and exponential backoff retry.
    Returns (tool_call_id, result_json_str).
    """
    tc_id = tc["id"]
    name = tc["function"]["name"]
    args = json.loads(tc["function"].get("arguments") or "{}")

    for attempt in range(retries + 1):
        try:
            result_str = await asyncio.wait_for(
                _execute_tool(name, args, mcp_session),
                timeout=12.0,
            )
            return (tc_id, result_str)
        except (asyncio.TimeoutError, Exception):
            if attempt < retries:
                await asyncio.sleep(0.5 * (2 ** attempt))

    return (tc_id, json.dumps({"error": "timeout"}, ensure_ascii=False))


async def _run_agentic_loop(
    messages: list[dict],
    glm_client: AsyncOpenAI,
    model: str,
    mcp_session: ClientSession,
) -> tuple[list[dict], list[dict]]:
    """
    ReAct-lite loop: let GLM drive tool calling until it stops or MAX_TOOL_ROUNDS reached.

    Returns (updated_messages, price_results) where price_results is a list of valid
    price dicts extracted from tool responses.
    """
    MAX_TOOL_ROUNDS = 5

    for _ in range(MAX_TOOL_ROUNDS):
        resp = await glm_client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            stream=False,
        )
        msg = resp.choices[0].message

        # No tool calls → GLM is done reasoning
        if not msg.tool_calls:
            break

        # Append assistant message with tool_calls
        messages.append({
            "role": "assistant",
            "content": msg.content,
            "tool_calls": [tc.model_dump() for tc in msg.tool_calls],
        })

        # Execute all tool calls in parallel
        results = await asyncio.gather(*[
            _execute_tool_with_retry(tc.model_dump(), mcp_session)
            for tc in msg.tool_calls
        ])

        # Append one tool result message per result
        for tc_id, result_str in results:
            messages.append({
                "role": "tool",
                "tool_call_id": tc_id,
                "content": result_str,
            })

    price_results = _extract_price_results(messages)
    return (messages, price_results)


def _extract_price_results(messages: list[dict]) -> list[dict]:
    """
    Scan messages for tool responses and extract valid price dicts.
    Skips entries with "error" key or without "price" key.
    """
    results = []
    for m in messages:
        if m.get("role") != "tool":
            continue
        try:
            data = json.loads(m.get("content", "{}"))
        except (json.JSONDecodeError, TypeError):
            continue
        if "error" in data:
            continue
        if "price" in data:
            results.append(data)
    return results


def _build_multi_savings_payload(
    price_results: list[dict],
    savings: float,
    target: float,
    impact: dict,
) -> dict:
    """
    Build the 2: channel payload.

    - No results: sentinel with confidence="no_intent"
    - Single item: backward-compatible single-item shape
    - Multiple items: includes items[] list plus aggregate fields
    """
    progress_pct = round(savings / target * 100, 1) if target else 0

    if not price_results:
        return {
            "confidence": "no_intent",
            "new_savings": savings,
            "progress_pct": progress_pct,
            "delta": 0,
            "product_name": "",
            "price_found": 0,
        }

    first = price_results[0]
    total_price = sum(r.get("price", 0.0) for r in price_results)
    resolved_price = first.get("price", 0.0)

    payload: dict = {
        "new_savings": impact["new_savings"],
        "progress_pct": impact["progress"],
        "delta": impact["delta"],
        "product_name": first.get("name", ""),
        "price_found": total_price,
        "price_min": first.get("price_min", resolved_price),
        "price_max": first.get("price_max", resolved_price),
        "source": first.get("source", ""),
        "confidence": first.get("confidence", "unknown"),
        "sources": first.get("sources", []),
    }

    if len(price_results) > 1:
        payload["items"] = [
            {
                "name": r.get("name", ""),
                "price": r.get("price", 0.0),
                "confidence": r.get("confidence", "unknown"),
            }
            for r in price_results
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
    system_prompt = build_system_prompt(persona)
    if _estimate_tokens([{"role": "system", "content": system_prompt}] + history) > int(_MODEL_CTX_LIMIT * _COMPRESS_THRESHOLD):
        history = await _compress_history(history, glm_client)

    full_messages: list[dict] = [{"role": "system", "content": system_prompt}] + history

    # ReAct-lite: GLM calls tools natively as needed
    full_messages, price_results = await _run_agentic_loop(
        full_messages, glm_client, model, mcp_session
    )

    # Aggregate savings impact
    tx_analysis = _analyze_transactions(transactions or [])
    total_price = sum(r.get("price", 0.0) for r in price_results)
    impact = calculate_savings_impact(total_price, savings, target)

    # Inject transaction + savings context as system message after tool history
    full_messages.append({
        "role": "system",
        "content": (
            f"[消费历史分析] {tx_analysis['summary']}\n"
            f"[储蓄影响] 当前存款¥{savings:.0f}，购后¥{impact['new_savings']:.0f}，"
            f"进度{impact['progress']:.1f}%，变化{impact['delta']:.0f}"
        ),
    })

    # Emit 2: savings payload BEFORE streaming verdict
    savings_payload = _build_multi_savings_payload(price_results, savings, target, impact)
    yield f'2:{json.dumps([savings_payload])}\n'

    async for line in _stream_verdict(glm_client, model, full_messages):
        yield line
