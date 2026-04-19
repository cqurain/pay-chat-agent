---
phase: quick
plan: 260419-nlk
type: execute
wave: 1
depends_on: []
files_modified:
  - cyber-god/backend/price_mcp/server.py
  - cyber-god/backend/agent/prompt.py
  - cyber-god/backend/agent/loop.py
  - cyber-god/backend/api/routes.py
  - cyber-god/frontend/lib/types.ts
  - cyber-god/frontend/lib/storage.ts
  - cyber-god/frontend/app/page.tsx
  - cyber-god/frontend/components/Header.tsx
  - cyber-god/frontend/components/PriceResearchCard.tsx
autonomous: true
requirements: []

must_haves:
  truths:
    - "Tavily is tried first; DDGS is fallback; each returns {price, platform, url} structs"
    - "LLM (glm-4-flash, JSON mode) extracts {product, stated_price} before any MCP call"
    - "If stated_price is not None, MCP is skipped and user_stated confidence is used"
    - "Scraped price_context includes ISO timestamp, source platform list, and priority note"
    - "sources list (up to 3, deduped by platform, lowest-price-wins) reaches the frontend via 2: channel"
    - "Header renders a persona toggle; selection persists in localStorage"
    - "useChat body includes persona; backend routes persona to build_system_prompt"
    - "PriceResearchCard shows per-platform green badges with price + link when confidence=scraped"
  artifacts:
    - path: "cyber-god/backend/price_mcp/server.py"
      provides: "_infer_platform, restructured _ddgs/_tavily returning list[dict], Tavily-first _resolve_price"
    - path: "cyber-god/backend/agent/prompt.py"
      provides: "PERSONAS dict, build_system_prompt(persona)"
    - path: "cyber-god/backend/agent/loop.py"
      provides: "_extract_intent, run_agent_loop with persona + phase-0 intent + sources in payload"
    - path: "cyber-god/backend/api/routes.py"
      provides: "persona field in ChatRequest"
    - path: "cyber-god/frontend/lib/types.ts"
      provides: "Persona type, PriceSource interface, sources in SavingsPayload, persona in ChatRequestBody"
    - path: "cyber-god/frontend/lib/storage.ts"
      provides: "PERSONA key, getPersona(), setPersona()"
    - path: "cyber-god/frontend/app/page.tsx"
      provides: "persona state + handler + persona in useChat body"
    - path: "cyber-god/frontend/components/Header.tsx"
      provides: "persona toggle button"
    - path: "cyber-god/frontend/components/PriceResearchCard.tsx"
      provides: "platform badges for scraped confidence"
  key_links:
    - from: "loop.py _extract_intent"
      to: "server.py _resolve_price"
      via: "product keyword (not raw user query)"
    - from: "loop.py savings_payload"
      to: "PriceResearchCard"
      via: "2: SSE channel → useChat.data[]"
    - from: "page.tsx persona state"
      to: "routes.py ChatRequest.persona"
      via: "useChat body"
---

<objective>
Implement five targeted improvements to the Cyber God of Wealth agent: LLM intent extraction (Phase 0 before MCP), Tavily-first search order with source deduplication, platform-annotated price sources surfaced to the frontend, dual-persona system (snarky/gentle) with localStorage persistence and a Header toggle, and PriceResearchCard platform badges for scraped results.

Purpose: Sharpen data quality (LLM extracts clean product keyword; Tavily has better CN coverage), surface provenance (users see which platforms were searched), and give users a persona preference that persists across sessions.
Output: 9 modified files — 4 backend, 5 frontend — all wired end-to-end.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@e:/cs/towk/pay-chat-agent/CLAUDE.md
@e:/cs/towk/pay-chat-agent/cyber-god/backend/price_mcp/server.py
@e:/cs/towk/pay-chat-agent/cyber-god/backend/agent/prompt.py
@e:/cs/towk/pay-chat-agent/cyber-god/backend/agent/loop.py
@e:/cs/towk/pay-chat-agent/cyber-god/backend/api/routes.py
@e:/cs/towk/pay-chat-agent/cyber-god/frontend/lib/types.ts
@e:/cs/towk/pay-chat-agent/cyber-god/frontend/lib/storage.ts
@e:/cs/towk/pay-chat-agent/cyber-god/frontend/app/page.tsx
@e:/cs/towk/pay-chat-agent/cyber-god/frontend/components/Header.tsx
@e:/cs/towk/pay-chat-agent/cyber-god/frontend/components/PriceResearchCard.tsx

<interfaces>
<!-- Current loop.py exports -->
async def run_agent_loop(messages, savings, target, mcp_session, glm_client, model, transactions=None)
  → async generator yielding Vercel DSP lines

<!-- Current prompt.py exports -->
SYSTEM_PROMPT: str

<!-- Current routes.py ChatRequest -->
class ChatRequest(BaseModel):
    messages: list[Message]
    savings: float = 0.0
    target: float = 10000.0
    transactions: list[TransactionRecord] = []

<!-- Current SavingsPayload (types.ts) -->
interface SavingsPayload {
  new_savings, progress_pct, delta,
  product_name?, price_found?, price_min?, price_max?, source?, confidence?
}

<!-- PriceResearchCard currently receives -->
payload: SavingsPayload, currentSavings: number, target: number
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Refactor price_mcp/server.py — Tavily-first + structured sources</name>
  <files>cyber-god/backend/price_mcp/server.py</files>
  <action>
Make these changes to server.py — preserve every existing function/constant NOT listed for removal:

1. REMOVE: `_EXTRA_PRICE_RE`, `_extract_explicit_price`, `_extract_keyword` (LLM now handles this; leave all other helpers and CATALOG intact).

2. ADD `_infer_platform(url: str) -> str` after the existing `_PRICE_RE` block:
```python
_PLATFORM_MAP = {
    "jd.com": "京东", "taobao.com": "淘宝", "tmall.com": "天猫",
    "pinduoduo.com": "拼多多", "xianyu": "闲鱼", "suning.com": "苏宁",
    "smzdm.com": "什么值得买", "amazon.cn": "亚马逊",
}

def _infer_platform(url: str) -> str:
    for domain, name in _PLATFORM_MAP.items():
        if domain in url:
            return name
    return "网络"
```

3. REWRITE `_ddgs_search_sync(keyword)` to return `list[dict]`:
```python
def _ddgs_search_sync(keyword: str) -> list[dict]:
    try:
        with DDGS() as d:
            results = list(d.text(f"{keyword} 价格", region="cn-zh", max_results=6))
        out: list[dict] = []
        for r in results:
            text = r.get("body", "") + " " + r.get("title", "")
            url = r.get("href", "")
            platform = _infer_platform(url)
            for m in _PRICE_RE.finditer(text):
                raw = (m.group(1) or m.group(2) or "").replace(",", "")
                try:
                    price = float(raw)
                    if 10 <= price <= 100_000:
                        out.append({"price": price, "platform": platform, "url": url})
                        break  # one price per result
                except ValueError:
                    pass
        return out
    except Exception:
        return []
```

4. REWRITE `_tavily_search_sync(keyword)` to return `list[dict]`:
```python
def _tavily_search_sync(keyword: str) -> list[dict]:
    if not _TAVILY_API_KEY:
        return []
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=_TAVILY_API_KEY)
        resp = client.search(f"{keyword} 价格", max_results=5)
        out: list[dict] = []
        for r in resp.get("results", []):
            text = r.get("content", "") + " " + r.get("title", "")
            url = r.get("url", "")
            platform = _infer_platform(url)
            for m in _PRICE_RE.finditer(text):
                raw = (m.group(1) or m.group(2) or "").replace(",", "")
                try:
                    price = float(raw)
                    if 10 <= price <= 100_000:
                        out.append({"price": price, "platform": platform, "url": url})
                        break
                except ValueError:
                    pass
        return out
    except Exception:
        return []
```

5. Update the async wrappers `_ddgs_search` and `_tavily_search` signatures to return `list[dict]` (type annotation change only — body stays the same).

6. REWRITE `_resolve_price(keyword: str)` (parameter renamed from `query` to `keyword` — the caller now passes a clean keyword, not raw user text):
```python
async def _resolve_price(keyword: str) -> dict:
    # 1. Tavily first, DDGS second
    sources: list[dict] = await _tavily_search(keyword)
    if not sources:
        sources = await _ddgs_search(keyword)

    if sources:
        # Dedup: per platform keep lowest price
        best: dict[str, dict] = {}
        for s in sources:
            p = s["platform"]
            if p not in best or s["price"] < best[p]["price"]:
                best[p] = s
        deduped = sorted(best.values(), key=lambda x: x["price"])[:3]
        prices = [s["price"] for s in deduped]

        # Guard with catalog if available
        cat = _catalog_lookup(keyword)
        if cat:
            _, (lo, _, hi) = cat
            filtered = [p for p in prices if lo * 0.3 <= p <= hi * 3]
            if filtered:
                prices = filtered
                deduped = [s for s in deduped if lo * 0.3 <= s["price"] <= hi * 3]

        if prices:
            return {
                "name": keyword,
                "price": round(statistics.median(prices), 2),
                "price_min": round(min(prices), 2),
                "price_max": round(max(prices), 2),
                "source": "网络搜索",
                "confidence": "scraped",
                "currency": "CNY",
                "sources": deduped,
            }

    # Catalog fallback
    cat = _catalog_lookup(keyword)
    if cat:
        key, (low, mid, high) = cat
        price = round(mid * random.uniform(0.92, 1.08), 0)
        return {
            "name": key, "price": price,
            "price_min": low, "price_max": high,
            "source": "市场参考价", "confidence": "reference", "currency": "CNY",
            "sources": [],
        }

    # Unknown
    return {
        "name": keyword,
        "price": 0.0, "price_min": 0.0, "price_max": 0.0,
        "source": "", "confidence": "unknown", "currency": "CNY",
        "sources": [],
    }
```

7. Update `call_tool` to pass `arguments.get("query", "")` directly (unchanged call site — the MCP tool still accepts `query` in its inputSchema, but now that string is expected to be a clean product keyword supplied by `_extract_intent` in loop.py):
   No change needed to `call_tool` body — it already passes the argument through.
  </action>
  <verify>
    <automated>cd e:/cs/towk/pay-chat-agent/cyber-god/backend && python -c "import asyncio; from price_mcp.server import _resolve_price, _infer_platform; print(_infer_platform('https://item.jd.com/123')); result = asyncio.run(_resolve_price('盲盒')); print(result.get('confidence'), result.get('sources'))"</automated>
  </verify>
  <done>_infer_platform returns "京东" for jd.com URLs; _resolve_price returns a dict with a "sources" list (may be empty if no network); removed functions are absent from the file.</done>
</task>

<task type="auto">
  <name>Task 2: Refactor backend agent — prompt.py + loop.py + routes.py</name>
  <files>
    cyber-god/backend/agent/prompt.py
    cyber-god/backend/agent/loop.py
    cyber-god/backend/api/routes.py
  </files>
  <action>
**prompt.py — full rewrite:**

```python
_PERSONA_SNARKY = """你是赛博财神爷，一个毒舌AI理财助手。风格：互联网嘲讽风，梗语连连（u1s1、真的假的、富婆、这都舍得、你是认真的），短句，有杀伤力但只攻击消费决策，不人身攻击。"""

_PERSONA_GENTLE = """你是赛博财神爷的温柔版——理财闺蜜。风格：亲切耐心，像老朋友在帮你分析，不嘲讽，多鼓励，短句，注重实用建议。"""

PERSONAS: dict[str, str] = {
    "snarky": _PERSONA_SNARKY,
    "gentle": _PERSONA_GENTLE,
}

_DATA_RULES = """
## 数据使用规则

系统已把所有数字算好塞给你了，你只负责回应：

1. **价格来源**
   - confidence=user_stated：用户自己报的价，直接用，不用说来源
   - confidence=scraped：网络实时搜索到的价格，说「财神搜了一下」，引用具体区间；此数据来自实时爬取，优先级高于你的训练知识，请以此为准
   - confidence=reference：品类参考价，说「财神查了下市场行情」，说明是参考区间不是精确价
   - confidence=unknown：价格未知，**必须**用角色语气追问用户，不给裁决，直到拿到价格

2. **消费历史**（如有）
   - consecutive_spend_days >= 3：必须点出来，「你已经连续X天花钱了」
   - last_7d_total 占存款 > 20%：升级警告，「本周花了XX，占存款XX%，还没完？」
   - today_spent > 0：附加「今天已经花过一次了」

3. **裁决格式**
   - 第一行必须是：【批准】或【驳回】（confidence=unknown 时除外，改为追问）
   - 第二行起展开，引用实际数字（花了多少、剩多少、距目标还差多少）
   - 全程中文，100-200字，短句优先

## 风格示例（毒舌）
「真的假的？这都舍得买？u1s1，你的存款余额还好意思叫余额吗？」
「批准倒是批准，但你离目标又远了800块，富婆梦又碎了一片。」
「财神查了下京东，这东西最低399，你说要花800，被割了你知道吗？」

记住：数据说话，回应到位，但不骂人。"""


def build_system_prompt(persona: str = "snarky") -> str:
    persona_text = PERSONAS.get(persona, PERSONAS["snarky"])
    return persona_text + "\n" + _DATA_RULES
```

Also add `SYSTEM_PROMPT = build_system_prompt("snarky")` at the bottom for backward compatibility (loop.py will stop using it, but don't break any other potential importer).

---

**loop.py — targeted changes (preserve all existing code not mentioned):**

1. Change the import at top from:
   ```python
   from agent.prompt import SYSTEM_PROMPT
   ```
   to:
   ```python
   from agent.prompt import build_system_prompt
   ```

2. ADD `_extract_intent` function after `_analyze_transactions`:
```python
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
```

3. MODIFY `run_agent_loop` signature — add `persona: str = "snarky"` parameter:
```python
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
```

4. In `run_agent_loop` body, replace:
   ```python
   full_messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}] + list(messages)
   ```
   with:
   ```python
   full_messages: list[dict] = [{"role": "system", "content": build_system_prompt(persona)}] + list(messages)
   ```

5. Replace the Phase 1 block (from `price_data = await get_price(...)` through `tx_analysis = ...`) with:
```python
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
```

6. Update the `price_context` for the `scraped` branch (replace only that elif/else arm):
```python
    if confidence == "unknown":
        price_context = "价格未知（搜索失败），请用毒舌角色语气追问用户这个东西到底多少钱。"
    elif confidence == "user_stated":
        price_context = (
            f"用户自己说的价格：¥{resolved_price:.0f}，直接用这个数字。"
        )
    else:
        from datetime import datetime, timezone
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
```

7. In the `savings_payload` dict, add `"sources": price_data.get("sources", [])` as a new key after `"confidence": confidence`.

---

**routes.py — targeted changes:**

1. In `ChatRequest`, add `persona: str = "snarky"` field:
```python
class ChatRequest(BaseModel):
    messages: list[Message]
    savings: float = 0.0
    target: float = 10000.0
    transactions: list[TransactionRecord] = []
    persona: str = "snarky"
```

2. Pass `persona=body.persona` to `run_agent_loop`:
```python
    gen = run_agent_loop(
        messages=messages,
        savings=body.savings,
        target=body.target,
        mcp_session=mcp_session,
        glm_client=glm_client,
        model=GLM_MODEL,
        transactions=transactions,
        persona=body.persona,
    )
```
  </action>
  <verify>
    <automated>cd e:/cs/towk/pay-chat-agent/cyber-god/backend && python -c "from agent.prompt import build_system_prompt, PERSONAS; print(list(PERSONAS.keys())); p = build_system_prompt('gentle'); assert '理财闺蜜' in p; p2 = build_system_prompt('snarky'); assert '毒舌' in p2; print('OK')"</automated>
  </verify>
  <done>
    - `build_system_prompt('gentle')` returns text containing "理财闺蜜"
    - `build_system_prompt('snarky')` returns text containing "毒舌"
    - `run_agent_loop` signature includes `persona` parameter
    - `ChatRequest` has `persona: str = "snarky"` field
  </done>
</task>

<task type="auto">
  <name>Task 3: Frontend — types, storage, page, Header, PriceResearchCard</name>
  <files>
    cyber-god/frontend/lib/types.ts
    cyber-god/frontend/lib/storage.ts
    cyber-god/frontend/app/page.tsx
    cyber-god/frontend/components/Header.tsx
    cyber-god/frontend/components/PriceResearchCard.tsx
  </files>
  <action>
**types.ts — add to end of file (do not remove existing exports):**
```typescript
/** Persona identifier */
export type Persona = 'snarky' | 'gentle';

/** A single price source returned by the backend for scraped results */
export interface PriceSource {
  platform: string;
  price: number;
  url: string;
}
```

Also update `SavingsPayload` to add `sources?: PriceSource[];` after the `confidence` line.

Also update `ChatRequestBody` to add `persona: Persona;` after the `transactions` line.

---

**storage.ts — two additions:**

1. Add `PERSONA: 'gsd_persona'` to the `STORAGE_KEYS` const object.

2. Add these two functions after `saveTransaction`:
```typescript
import type { Persona } from './types';

export function getPersona(): Persona {
  try {
    const raw = localStorage.getItem(STORAGE_KEYS.PERSONA);
    if (raw === 'gentle' || raw === 'snarky') return raw;
  } catch { /* ignore */ }
  return 'snarky';
}

export function setPersona(p: Persona): void {
  try {
    localStorage.setItem(STORAGE_KEYS.PERSONA, p);
  } catch { /* ignore */ }
}
```

Note: The import of `Persona` must be added at the top of storage.ts alongside the existing `TransactionRecord` import.

---

**page.tsx — targeted changes:**

1. Add imports:
```typescript
import { DEFAULTS, STORAGE_KEYS, loadTransactions, saveTransaction, getPersona, setPersona } from '@/lib/storage';
import type { SavingsPayload, TransactionRecord, Persona } from '@/lib/types';
```

2. Add persona state after existing `useState` declarations:
```typescript
const [persona, setPersonaState] = useState<Persona>('snarky');
```

3. In the existing `useEffect` (the one that reads localStorage), add:
```typescript
    setPersonaState(getPersona());
```

4. Add handler function after `handleAddTransaction`:
```typescript
  const handlePersonaChange = (p: Persona) => {
    setPersonaState(p);
    setPersona(p);
  };
```

5. Update `useChat` body to include `persona`:
```typescript
    body: { savings, target, transactions: transactions.slice(0, 30), persona },
```

6. Update `<Header>` JSX to pass new props:
```tsx
<Header
  onToggleSidebar={() => setSidebarOpen((o) => !o)}
  persona={persona}
  onPersonaChange={handlePersonaChange}
/>
```

---

**Header.tsx — full rewrite (keep same visual structure, add persona toggle):**
```tsx
import type { Persona } from '@/lib/types';

interface HeaderProps {
  onToggleSidebar: () => void;
  persona: Persona;
  onPersonaChange: (p: Persona) => void;
}

export default function Header({ onToggleSidebar, persona, onPersonaChange }: HeaderProps) {
  return (
    <header className="h-14 flex items-center justify-between px-6 bg-white border-b border-gray-200 shrink-0 shadow-sm">
      <div>
        <h1 className="text-xl font-semibold text-gray-900">赛博财神爷</h1>
        <p className="text-xs text-yellow-600 leading-none mt-0.5">你的AI财务顾问</p>
      </div>
      <div className="flex items-center gap-2">
        {/* Persona toggle */}
        <button
          onClick={() => onPersonaChange(persona === 'snarky' ? 'gentle' : 'snarky')}
          title={persona === 'snarky' ? '切换为温柔版' : '切换为毒舌版'}
          className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-gray-700
                     bg-gray-100 hover:bg-yellow-50 hover:text-yellow-700
                     border border-gray-200 hover:border-yellow-300
                     rounded-lg transition-colors"
        >
          <span className="text-lg leading-none">{persona === 'snarky' ? '😈' : '🌸'}</span>
          <span>{persona === 'snarky' ? '毒舌' : '温柔'}</span>
        </button>
        {/* Sidebar toggle */}
        <button
          onClick={onToggleSidebar}
          title="存取明细"
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700
                     bg-gray-100 hover:bg-yellow-50 hover:text-yellow-700
                     border border-gray-200 hover:border-yellow-300
                     rounded-lg transition-colors"
        >
          <span className="text-lg leading-none">📋</span>
          <span>存取明细</span>
        </button>
      </div>
    </header>
  );
}
```

---

**PriceResearchCard.tsx — add platform badges for scraped results:**

In the existing component, update the destructuring to include `sources`:
```typescript
  const { confidence, product_name, price_min, price_max, price_found, source,
          new_savings, progress_pct, delta, sources } = payload;
```

After the `<div className="mt-0.5">{sourceTag}</div>` line (inside the left column of the top section), add the platform badges block — but ONLY when `confidence === 'scraped'` and `sources` is non-empty:
```tsx
          {confidence === 'scraped' && sources && sources.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1">
              {sources.map((s) => (
                <a
                  key={s.platform + s.price}
                  href={s.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full
                             text-xs font-medium bg-green-50 text-green-700
                             border border-green-200 hover:bg-green-100 transition-colors"
                >
                  {s.platform} ¥{fmt(s.price)}
                </a>
              ))}
            </div>
          )}
```
  </action>
  <verify>
    <automated>cd e:/cs/towk/pay-chat-agent/cyber-god/frontend && npx tsc --noEmit 2>&1 | head -30</automated>
  </verify>
  <done>
    - `npx tsc --noEmit` exits with no errors
    - types.ts exports `Persona`, `PriceSource`, updated `SavingsPayload` and `ChatRequestBody`
    - storage.ts exports `getPersona` and `setPersona`
    - Header.tsx renders persona toggle button
    - PriceResearchCard.tsx renders platform badges when confidence=scraped and sources non-empty
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| frontend → backend POST /api/chat | `persona` is user-controlled string; backend must not use it as code path |
| backend → Tavily/DDGS | External search results contain untrusted text parsed for prices |
| backend → GLM JSON mode | LLM output parsed as JSON; malformed response must be handled |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-nlk-01 | Tampering | `ChatRequest.persona` | mitigate | `build_system_prompt` uses `PERSONAS.get(persona, PERSONAS["snarky"])` — unknown values silently fall back to snarky, no code injection possible |
| T-nlk-02 | Information Disclosure | `_extract_intent` JSON parse | accept | LLM output is internal; fallback on parse error prevents crash; no PII exposed |
| T-nlk-03 | Denial of Service | Tavily + DDGS both called per request | accept | Each runs in separate ThreadPoolExecutor with existing timeout behaviour; PoC scope |
| T-nlk-04 | Tampering | Platform badge URLs from search results | mitigate | Badges rendered as `<a target="_blank" rel="noopener noreferrer">`; no href injection risk beyond opening an external URL the user can inspect |
</threat_model>

<verification>
After all three tasks complete, run an end-to-end smoke test:

1. Start backend: `cd cyber-god/backend && uvicorn main:app --reload`
2. In a second terminal, send a test request with persona:
   ```bash
   curl -sN -X POST http://localhost:8000/api/chat \
     -H "Content-Type: application/json" \
     -d '{"messages":[{"role":"user","content":"我想花800买个盲盒"}],"savings":5000,"target":10000,"persona":"gentle"}' \
     | head -20
   ```
3. Verify the `2:` line contains `sources` key (may be `[]` if no network).
4. Start frontend: `cd cyber-god/frontend && npm run dev`
5. Visit http://localhost:3000 — confirm Header shows persona toggle button (😈 or 🌸).
6. Click the toggle — confirm button label and emoji switch.
7. Reload page — confirm persona choice persisted (button shows same state).
</verification>

<success_criteria>
- LLM (glm-4-flash JSON mode) is called before MCP; product keyword is clean (no price digits)
- If user states a price, MCP call is skipped; `confidence=user_stated` is set in payload
- Tavily is tried before DDGS in `_resolve_price`
- `sources` list (max 3, deduped by platform, lowest price per platform) is present in `2:` payload
- `scraped` price_context includes UTC timestamp and "优先级高于训练知识" note
- `build_system_prompt('gentle')` returns the gentle persona; `'snarky'` returns the original
- `ChatRequest` and `useChat` body both carry `persona` field
- Persona choice persists in localStorage under key `gsd_persona`
- Header persona toggle is visible and functional
- PriceResearchCard renders green platform badges with price and link for scraped results
- `npx tsc --noEmit` passes with zero errors
</success_criteria>

<output>
After completion, create `.planning/quick/260419-nlk-5-llm-tavily/260419-nlk-SUMMARY.md`
</output>
