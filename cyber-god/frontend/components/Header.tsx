/**
 * Fixed 56px header bar (D-05, D-06).
 * Shows title 赛博财神爷 and optional subtitle.
 */
export default function Header() {
  return (
    <header className="h-14 flex items-center px-6 bg-white border-b border-gray-200 shrink-0 shadow-sm">
      <div>
        <h1 className="text-xl font-semibold text-gray-900">赛博财神爷</h1>
        <p className="text-xs text-yellow-600 leading-none mt-0.5">你的AI财务顾问</p>
      </div>
    </header>
  );
}
