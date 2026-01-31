import { cn } from '@/lib/cn';

export default function Tabs({ tabs = [], active, onChange }) {
  return (
    <div className="mb-4">
      <div className="flex flex-wrap gap-2 rounded-3xl border border-white/60 bg-white/55 p-2 shadow-sm backdrop-blur">
        {tabs.map((t) => {
          const isActive = t.key === active;
          return (
            <button
              key={t.key}
              type="button"
              onClick={() => onChange(t.key)}
              className={cn(
                'rounded-2xl px-4 py-2 text-sm font-black transition active:translate-y-[1px]',
                isActive
                  ? 'bg-gradient-to-br from-violet-200 via-sky-200 to-rose-200 text-slate-900 shadow-sm'
                  : 'bg-white/70 text-slate-600 hover:bg-white'
              )}
            >
              {t.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
