"""
Agent loop for 毒舌财神 — direct tool execution + streaming GLM verdict.

Phase 1: call MCP price server and savings calculator directly (no GLM tool-calling,
         which proved unreliable with tool_choice="auto" on Zhipu models).
Phase 2: stream=True GLM call with tool results injected as message history,
         yielding Vercel Data Stream Protocol lines (f:, 0:, 2:, e:, d:).
"""
import json
from uuid import uuid4

from mcp import ClientSession
from openai import AsyncOpenAI

from agent.prompt import SYSTEM_PROMPT
from tools.price import get_price
from tools.savings import calculate_savings_impact


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

    Protocol lines emitted (in order):
        f:{id}          — stream init
        0:{text}        — streamed text chunks (verdict in Chinese)
        2:[{payload}]   — savings impact payload (array-wrapped JSON, D-13)
        e:{meta}        — finish event
        d:{meta}        — done event
    """
    # Prepend system prompt to full message history
    full_messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}] + list(messages)

    # --- Phase 1: call tools directly ---
    # GLM tool_choice="auto" is unreliable — model skips tools despite system prompt.
    # We call MCP + savings ourselves and inject results as a simulated tool exchange
    # so Phase 2 GLM sees real data and generates a grounded verdict.
    user_query = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
    price_data = await get_price(user_query, mcp_session)
    resolved_price: float = price_data["price"]
    impact = calculate_savings_impact(resolved_price, savings, target)

    tc_id_price = f"call_{uuid4().hex[:16]}"
    tc_id_impact = f"call_{uuid4().hex[:16]}"
    assistant_msg = {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": tc_id_price,
                "type": "function",
                "function": {"name": "search_products", "arguments": json.dumps({"query": user_query})},
            },
            {
                "id": tc_id_impact,
                "type": "function",
                "function": {
                    "name": "calculate_savings_impact",
                    "arguments": json.dumps({"price": resolved_price, "savings": savings, "target": target}),
                },
            },
        ],
    }
    tool_messages = [
        {"role": "tool", "tool_call_id": tc_id_price, "content": json.dumps(price_data)},
        {"role": "tool", "tool_call_id": tc_id_impact, "content": json.dumps(impact)},
    ]
    full_messages = full_messages + [assistant_msg] + tool_messages

    # --- Phase 2: streaming verdict ---
    # No tools passed — GLM generates plain text verdict based on injected tool results.
    response2 = await glm_client.chat.completions.create(
        model=model,
        messages=full_messages,
        stream=True,
    )

    msg_id = str(uuid4())
    yield f'f:{json.dumps({"messageId": msg_id})}\n'

    prompt_tokens = 0
    completion_tokens = 0

    async for chunk in response2:
        choice = chunk.choices[0] if chunk.choices else None
        if not choice:
            continue
        # GLM-4.6+ gotcha: delta.content can be None on reasoning_content chunks
        text = (choice.delta.content or "") if choice.delta else ""
        if text:
            yield f'0:{json.dumps(text)}\n'
        if hasattr(chunk, "usage") and chunk.usage:
            prompt_tokens = chunk.usage.prompt_tokens or prompt_tokens
            completion_tokens = chunk.usage.completion_tokens or completion_tokens

    # --- D-13: savings payload on 2: channel (array-wrapped for useChat.data[]) ---
    savings_payload = {
        "new_savings": impact["new_savings"],
        "progress_pct": impact["progress"],
        "delta": impact["delta"],
    }
    yield f'2:{json.dumps([savings_payload])}\n'

    # --- D-11: finish lines ---
    finish_meta = json.dumps(
        {
            "finishReason": "stop",
            "usage": {"promptTokens": prompt_tokens, "completionTokens": completion_tokens},
            "isContinued": False,
        }
    )
    yield f'e:{finish_meta}\n'
    yield f'd:{finish_meta}\n'
