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
