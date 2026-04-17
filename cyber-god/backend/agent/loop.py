"""
Agent loop for 毒舌财神 — two-phase GLM calling with Vercel Data Stream Protocol output.

Phase 1: stream=False (avoids GLM-4.6+ streaming tool_calls bug) to resolve tool calls.
Phase 2: stream=True to generate the streaming Chinese verdict.

Yields Vercel Data Stream Protocol lines (f:, 0:, 2:, e:, d:).
Raises exception on hard GLM failure (before any yield) — caller converts to HTTP 500.
"""
import json
from uuid import uuid4

from mcp import ClientSession
from openai import AsyncOpenAI

from agent.prompt import SYSTEM_PROMPT
from tools.price import get_price
from tools.savings import calculate_savings_impact

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "搜索商品价格，返回RMB价格数据",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "商品名称或描述"}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_savings_impact",
            "description": "计算购买对存款目标的影响",
            "parameters": {
                "type": "object",
                "properties": {
                    "price": {"type": "number", "description": "商品价格（RMB）"},
                    "savings": {"type": "number", "description": "当前存款（RMB）"},
                    "target": {"type": "number", "description": "存款目标（RMB）"},
                },
                "required": ["price", "savings", "target"],
            },
        },
    },
]


async def _execute_tool_calls(
    tool_calls, mcp_session: ClientSession, savings: float, target: float
) -> tuple[list[dict], float | None]:
    """
    Execute tool calls and return (list of role=tool message dicts, resolved_price).

    resolved_price is the price returned by search_products (used for 2: channel payload).
    """
    results = []
    price_for_impact: float | None = None

    for tc in tool_calls:
        args = json.loads(tc.function.arguments)
        if tc.function.name == "search_products":
            price_data = await get_price(args.get("query", ""), mcp_session)
            price_for_impact = price_data["price"]
            results.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(price_data),
                }
            )
        elif tc.function.name == "calculate_savings_impact":
            # Use price from search_products if not explicitly supplied in args
            price = args.get("price", price_for_impact or 0.0)
            impact = calculate_savings_impact(
                price=price,
                savings=args.get("savings", savings),
                target=args.get("target", target),
            )
            results.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(impact),
                }
            )

    return results, price_for_impact


async def run_agent_loop(
    messages: list[dict],
    savings: float,
    target: float,
    mcp_session: ClientSession,
    glm_client: AsyncOpenAI,
    model: str,
):
    """
    Async generator yielding Vercel Data Stream Protocol lines.

    Raises an exception (before any yield) if the first GLM call fails with a
    network or auth error — the caller (routes.py) converts this to HTTP 500.

    Protocol lines emitted (in order):
        f:{id}          — stream init
        0:{text}        — streamed text chunks (verdict in Chinese)
        2:[{payload}]   — savings impact payload (array-wrapped JSON, D-13)
        e:{meta}        — finish event
        d:{meta}        — done event
    """
    # Prepend system prompt to full message history
    full_messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}] + list(messages)

    # --- Phase 1: non-streaming tool resolution ---
    # stream=False avoids GLM-4.6+ streaming tool_calls parsing bug (D-12)
    # tool_choice="auto" — "required" triggers confirmed GLM infinite loop (D-12, Pitfall 5)
    # This call raises on network/auth error — propagates to caller → HTTP 500 (D-07)
    response1 = await glm_client.chat.completions.create(
        model=model,
        messages=full_messages,
        tools=TOOLS_SCHEMA,
        tool_choice="auto",
        stream=False,
    )

    tool_calls = response1.choices[0].message.tool_calls

    # --- D-05: retry once with reinforcement if no tool calls returned ---
    if not tool_calls:
        retry_injection = {
            "role": "system",
            "content": "你必须先调用 search_products 和 calculate_savings_impact 这两个工具，然后才能回复。请立即调用工具。",
        }
        full_messages_retry = full_messages + [retry_injection]
        response1_retry = await glm_client.chat.completions.create(
            model=model,
            messages=full_messages_retry,
            tools=TOOLS_SCHEMA,
            tool_choice="auto",
            stream=False,
        )
        tool_calls = response1_retry.choices[0].message.tool_calls

    # --- D-06: in-character fallback if retry also returns no tool calls ---
    if not tool_calls:
        msg_id = str(uuid4())
        yield f'f:{json.dumps({"id": msg_id})}\n'
        error_text = "财神出岁了！天机不可泄露，稍后再来。"
        yield f'0:{json.dumps(error_text)}\n'
        finish_meta = json.dumps(
            {"finishReason": "error", "usage": {"promptTokens": 0, "completionTokens": 0}}
        )
        yield f'e:{finish_meta}\n'
        yield f'd:{finish_meta}\n'
        return

    # --- Execute tool calls and collect results ---
    tool_messages, resolved_price = await _execute_tool_calls(
        tool_calls, mcp_session, savings, target
    )

    # Build updated message history:
    #   assistant turn (with tool_calls) + tool result turns
    # Note: assistant content may be None when GLM makes tool calls — that is valid
    assistant_msg = {
        "role": "assistant",
        "content": response1.choices[0].message.content,  # May be None — keep as-is
        "tool_calls": [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in tool_calls
        ],
    }
    full_messages = full_messages + [assistant_msg] + tool_messages

    # --- Phase 2: streaming verdict generation ---
    # stream=True now safe — model generates plain text, no tool parsing needed
    response2 = await glm_client.chat.completions.create(
        model=model,
        messages=full_messages,
        tools=TOOLS_SCHEMA,
        tool_choice="auto",
        stream=True,
    )

    msg_id = str(uuid4())
    yield f'f:{json.dumps({"id": msg_id})}\n'

    prompt_tokens = 0
    completion_tokens = 0

    async for chunk in response2:
        choice = chunk.choices[0] if chunk.choices else None
        if not choice:
            continue
        # GLM-4.6+ gotcha: delta.content can be None (e.g., reasoning_content chunks)
        # Guard: always use delta.content or ""
        text = (choice.delta.content or "") if choice.delta else ""
        if text:
            yield f'0:{json.dumps(text)}\n'
        # Usage data only appears on certain chunks (often the last one)
        if hasattr(chunk, "usage") and chunk.usage:
            prompt_tokens = chunk.usage.prompt_tokens or prompt_tokens
            completion_tokens = chunk.usage.completion_tokens or completion_tokens

    # --- D-13: savings payload on 2: channel ---
    # Compute final impact using the price resolved from search_products.
    # The frontend reads this from useChat.data[] via onData callback.
    final_price = resolved_price or 0.0
    impact = calculate_savings_impact(final_price, savings, target)
    savings_payload = {
        "new_savings": impact["new_savings"],
        "progress_pct": impact["progress"],  # key is progress_pct for frontend (D-13)
        "delta": impact["delta"],
    }
    yield f'2:{json.dumps([savings_payload])}\n'

    # --- D-11: e: and d: finish lines ---
    finish_meta = json.dumps(
        {
            "finishReason": "stop",
            "usage": {
                "promptTokens": prompt_tokens,
                "completionTokens": completion_tokens,
            },
            "isContinued": False,
        }
    )
    yield f'e:{finish_meta}\n'
    yield f'd:{finish_meta}\n'
