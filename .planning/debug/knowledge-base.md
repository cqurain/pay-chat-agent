# GSD Debug Knowledge Base

Resolved debug sessions. Used by `gsd-debugger` to surface known-pattern hypotheses at the start of new investigations.

---

## usechat-error-and-dark-ui — useChat.error set on every message; wrong f: frame key

- **Date:** 2026-04-18
- **Error patterns:** useChat.error, error banner, 财神系统故障, f: frame, messageId, stream parse, SSE, dark UI, bg-gray-950
- **Root cause:** loop.py emitted `f:{"id":...}` but @ai-sdk/ui-utils validates the f: init frame by checking `"messageId" in value` — missing key throws a parse error which sets useChat.error. Separately, all UI components used dark Tailwind classes (bg-gray-950 / bg-gray-800 / text-gray-100).
- **Fix:** Changed `{"id": msg_id}` to `{"messageId": msg_id}` in `agent/loop.py` line 86 (the `f:` yield). Replaced dark Tailwind classes with white/light equivalents across 8 frontend files.
- **Files changed:** cyber-god/backend/agent/loop.py, cyber-god/frontend/app/globals.css, cyber-god/frontend/app/layout.tsx, cyber-god/frontend/app/page.tsx, cyber-god/frontend/components/ChatArea.tsx, cyber-god/frontend/components/Header.tsx, cyber-god/frontend/components/InputArea.tsx, cyber-god/frontend/components/ProgressBar.tsx, cyber-god/frontend/components/SavingsPanel.tsx
---

