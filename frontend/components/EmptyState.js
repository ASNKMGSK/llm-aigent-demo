import { Sparkles } from 'lucide-react';

export default function EmptyState({ title = '데이터가 없습니다', desc = '조건을 바꿔 다시 시도해보세요.' }) {
  return (
    <div className="rounded-3xl border border-white/60 bg-white/55 p-6 shadow-sm backdrop-blur">
      <div className="flex items-center gap-3">
        <div className="rounded-2xl border border-white/60 bg-gradient-to-br from-violet-100 via-sky-100 to-rose-100 p-3 shadow-sm">
          <Sparkles className="text-slate-800" size={18} />
        </div>
        <div>
          <div className="text-sm font-black text-slate-900">{title}</div>
          <div className="text-xs font-semibold text-slate-600">{desc}</div>
        </div>
      </div>
    </div>
  );
}
