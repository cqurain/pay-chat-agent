# Feature Landscape

**Domain:** AI finance companion agent (PoC) — streaming verdict chat with function calling
**Project:** Cyber God of Wealth (赛博财神爷)
**Researched:** 2026-04-18
**Research mode:** Ecosystem

---

## Table Stakes

Features users expect from a streaming chat UI. Missing any of these and the experience feels broken or unfinished.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Token-by-token streaming (typewriter) | Baseline since ChatGPT; waiting for full response feels broken | Low | Vercel AI SDK `useChat` handles this natively via SSE |
| Streaming markdown rendering | Agent replies will include bold, lists, numbers — partial markdown must render without flicker | Medium | Use Vercel's Streamdown or react-markdown with streaming-safe parser; avoid full re-render on each token |
| Input disabled / loading state during stream | Users expect the input to block while the agent is responding | Low | `useChat` `isLoading` flag wires directly to input `disabled` |
| Stop-generation button | Prominent during streaming; saves cost and respects user time | Low | `useChat` `stop()` method; must be visible, not tucked in a menu |
| Error state with retry | Network errors, LLM timeouts, tool failures — must show a human message with one-click retry | Low | Toast or inline error bubble; `reload()` from `useChat` |
| Empty state / first-run prompt | Blank chat box with no guidance = users don't know what to type | Low | Pre-fill example prompt: "我想花 800 买个盲盒" |
| Persistent chat history (session) | Losing the conversation on refresh is jarring | Low | Already in scope via React state; no need for DB |

**Confidence: HIGH** — These are universal expectations confirmed across ChatGPT, Claude, Gemini, and all major chat UI pattern libraries (Vercel AI SDK docs, Stream.io, assistant-ui).

---

## Differentiators

Features that make this specific PoC concept feel alive and on-brand. Not universally expected, but what elevates a demo from "chat wrapper" to "product."

### D1: Tool-call transparency (the "thinking moment")
**Value proposition:** Makes the agent feel like it is actually working, not making things up.
**What it is:** While the backend is executing `get_mock_price` or `calculate_savings_impact`, show an inline status line in the chat: "正在查询价格..." then "正在计算储蓄影响...". Transition to the streaming verdict once tools complete.
**Why it works:** The gap between user submit and first token is where agents feel robotic. A visible tool-execution step fills that gap and signals real computation, not a lookup table.
**Complexity:** Low-Medium. Vercel AI SDK `useChat` exposes `toolInvocations` on each message object. Render a custom component for `state: "call"` (in progress) vs `state: "result"` (done). No backend changes needed.
**PoC implementation:** Show a single spinner line with tool name in Chinese. No need for full step-by-step logs.

### D2: Live savings progress bar that reacts to the verdict
**Value proposition:** The core hook of the PoC — makes the financial consequence tangible and visual, not just textual.
**What it is:** A progress bar (current savings / target) that updates in real time as the agent streams its final verdict. The structured JSON payload appended at stream end contains `new_savings` and `progress_pct`, which triggers the bar to animate.
**Why it works:** Chat is abstract; a bar moving from 63% to 58% is concrete. The visual change lands the decision emotionally.
**Complexity:** Medium. Requires the backend to append a structured data chunk at stream end (e.g., `data: {"type":"savings_update","progress_pct":58,"delta":-5}` as the final SSE event). Frontend parses via `useChat`'s `data` array and updates React state. The pattern is well-established in Vercel AI SDK 4.1+ via custom data stream parts.
**PoC implementation:** Single horizontal bar with percentage label. Animate with CSS transition. Red flash if delta is negative (purchase approved but savings drop), green pulse if rejected (savings preserved). Keep the bar always visible above or beside the chat.

### D3: Clear approve / reject verdict styling
**Value proposition:** Eliminates ambiguity in the agent's decision — the user should never have to parse a paragraph to find out the answer.
**What it is:** The final assistant message gets a visual treatment based on the verdict: a red banner/badge for "rejected" (劝退), a reluctant amber for "approved with caveats." The verdict word appears first in the stream before the explanation, so users know instantly.
**Why it works:** Finance decisions need clarity. Burying the verdict in paragraph 2 is anti-UX. "NO — and here's why" beats "Well, considering your current savings balance and the price of the item..."
**Complexity:** Low. Agent system prompt instructs 财神 to lead with verdict keyword. Frontend pattern-matches the first streamed token chunk for verdict keyword and applies CSS class to the message bubble.
**PoC implementation:** Two classes: `verdict-reject` (red left border, red emoji prefix 🚫) and `verdict-caution` (amber). No third "approve" class needed — 财神 is劝退-first.

### D4: Snarky persona consistency (毒舌财神)
**Value proposition:** The persona is the product's identity. Without it, this is just another finance calculator with a chat box.
**What it is:** Every response maintains the 财神 character — data-driven sarcasm, culturally specific references, no generic "I understand your financial goals" filler. The system prompt is the differentiator, not a feature flag.
**Why it works:** A distinct chatbot persona measurably increases engagement over neutral bots, particularly in lifestyle and finance contexts (chatbot.com research, 2026). Users share screenshots of funny verdicts; the persona is the virality vector.
**Complexity:** Low (prompt engineering, no code). Medium to tune well — sarcasm that reads as attacking vs. playful is a thin line. System prompt needs test cases.
**PoC implementation:** System prompt only. No dynamic persona selection, no tone sliders. Ship one voice, make it consistent.

### D5: Editable savings context above the chat
**Value proposition:** Users need to see what data the agent is working with. A verdict against invisible numbers feels arbitrary.
**What it is:** Two editable fields at the top: "当前储蓄" and "储蓄目标". Pre-populated with sensible defaults. Changes persist to localStorage. The values are included in the prompt context (or system prompt) for each request.
**Why it works:** It answers "why did 财神 say no?" before the user asks. Transparency in inputs = trust in outputs.
**Complexity:** Low. React controlled inputs + `localStorage` write on blur. Pass values as part of the system prompt or as a pre-message context injection.
**PoC implementation:** Inline edit fields, not a settings modal. Show current values always visible.

**Confidence: MEDIUM** — D1, D2, D5 are confirmed patterns from Vercel AI SDK docs and agent UI research. D3 and D4 are product design decisions based on engagement research and this specific PoC brief.

---

## Anti-Features

Things to deliberately NOT build for this PoC. Including these wastes time, adds surface area for bugs, and dilutes the core value proposition.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Chat history persistence (DB / localStorage) | No DB is in scope; localStorage for messages gets complex with streaming state and is not the core demo | Session memory only; page refresh wipes chat. Savings state (target + current) persists, chat does not. |
| Message editing / regeneration UI | Standard in ChatGPT but adds state complexity; the PoC is one-shot verdict per impulse | Keep it linear: one question, one verdict, move on |
| Multi-turn financial planning | "What if I also want to buy..." multi-item tracking requires session state, tool orchestration beyond scope | One purchase impulse per conversation thread |
| Markdown rich text input (user side) | User input is plain text spending impulses; rich formatting adds no value and complicates parsing | Plain `<textarea>` or `<input>` |
| Authentication / user accounts | Explicitly out of scope in PROJECT.md | No auth. Single-user, no-login PoC |
| Real price API integration | Mock ±30% randomization is the spec; real APIs add latency, key management, rate limits | Stick to `get_mock_price` with seeded randomness |
| Voice input | Cool but adds browser API complexity and zero relevance to the Chinese text use case | Text only |
| Mobile-responsive polish | Web-only PoC; don't optimize for mobile at the cost of shipping | Desktop-first layout is fine |
| Streaming cancellation mid-tool-execution | Stop button is table stakes for token streaming but tool cancellation on the backend (FastAPI) requires async task management | Show stop button; if clicked during tool execution, let current tool finish then stop text stream |
| Settings / preferences panel | Tone selector, model picker, language toggle — all scope creep | Single fixed config via env vars |
| Feedback / thumbs up-down | Valuable for production; zero value for a PoC with one developer | Skip entirely |
| Explanation of how mock price works | Users don't need to know it's random; breaks the fiction | Never expose "mock" in the UI; treat prices as real |

**Confidence: HIGH** — Anti-feature list derived from PROJECT.md Out of Scope section combined with general AI PoC scoping research (ochk.cloud, vodworks.com) and common scope creep patterns.

---

## Feature Dependencies

```
Editable savings context (D5)
  └─> savings values injected into prompt
        └─> calculate_savings_impact tool runs
              └─> structured data chunk returned at stream end
                    └─> Live progress bar updates (D2)

Tool-call transparency (D1)
  └─> useChat toolInvocations state
        └─> inline "calculating..." UI component
              └─> transitions to streaming verdict text

Streaming verdict text
  └─> verdict keyword detected in first token chunk
        └─> Approve/reject styling applied (D3)
              └─> Persona voice (D4) is consistent throughout
```

---

## MVP Recommendation

For the PoC to prove its value (agent makes data-backed decision and streams it in character, with a live progress bar), ship in this priority order:

**Must ship (core loop works without these = demo fails):**
1. Streaming typewriter display — table stakes; demo is broken without it
2. Live savings progress bar updating from stream-end JSON (D2) — the visual payoff
3. Tool-call transparency spinner (D1) — fills the dead-air gap; without it the 2-3 second tool execution feels like a hang
4. Editable savings context (D5) — agent needs real numbers to work with
5. Approve/reject verdict styling (D3) — makes the decision legible

**Polish if time remains:**
6. Stop-generation button — expected but not critical for a demo where queries are short
7. Error state handling — basic "something went wrong, retry" is sufficient
8. Empty state example prompt — reduces friction for first-time users

**Explicitly defer:**
- Everything in the Anti-Features table
- Message history persistence
- Any feature not in the Active requirements list in PROJECT.md

---

## Sources

- Vercel AI SDK stream protocol and useChat docs: https://ai-sdk.dev/docs/ai-sdk-ui/stream-protocol
- Vercel AI SDK 4.1 annotations and structured data: https://vercel.com/blog/ai-sdk-4-1
- Vercel AI SDK 5 SSE streaming: https://vercel.com/blog/ai-sdk-5
- Vercel Chat SDK streaming markdown (Streamdown): https://vercel.com/changelog/introducing-streamdown
- AI Chat UI best practices (thefrontkit): https://thefrontkit.com/blogs/ai-chat-ui-best-practices
- AI Chat UI best practices (DEV Community): https://dev.to/greedy_reader/ai-chat-ui-best-practices-designing-better-llm-interfaces-18jj
- Chat UI design patterns 2025: https://bricxlabs.com/blogs/message-screen-ui-deisgn
- Agent UX tool call display (Microsoft Teams pattern): https://learn.microsoft.com/en-us/microsoftteams/platform/bots/streaming-ux
- Chatbot persona engagement impact: https://www.chatbot.com/blog/personality/
- AI PoC scope and anti-feature guidance: https://ochk.cloud/blog/poc-mvp-avoid-costly-ai
- AI MVP scope creep prevention: https://mitrix.io/blog/the-mvp-trap-for-ai-features/
- Frontend in the Age of AI (agent UI integration): https://medium.com/@ignatovich.dm/frontend-in-the-age-of-ai-how-to-integrate-llm-agents-right-into-the-ui-0514cd7a20fe
- AI UI Patterns (patterns.dev): https://www.patterns.dev/react/ai-ui-patterns/
