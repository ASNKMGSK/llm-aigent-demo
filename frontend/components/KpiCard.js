import React from 'react';
import { cn } from '@/lib/cn';

export default function KpiCard({
  title,
  value,
  subtitle,
  icon = null,
  tone = 'violet', // violet | sky | mint | peach | rose | slate
  className = '',
}) {
  const toneMap = {
    violet: 'from-violet-50 to-fuchsia-50 border-violet-100/70',
    sky: 'from-sky-50 to-cyan-50 border-sky-100/70',
    mint: 'from-emerald-50 to-teal-50 border-emerald-100/70',
    peach: 'from-amber-50 to-orange-50 border-amber-100/70',
    rose: 'from-rose-50 to-pink-50 border-rose-100/70',
    slate: 'from-slate-50 to-zinc-50 border-slate-200/70',
  };

  return (
    <div
      className={cn(
        'rounded-3xl border bg-gradient-to-br p-4 shadow-[0_10px_30px_-18px_rgba(15,23,42,0.35)] backdrop-blur',
        toneMap[tone] || toneMap.violet,
        className
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-[11px] font-extrabold tracking-wide text-slate-600/90">{title}</div>
          <div className="mt-1 text-2xl font-black text-slate-900">{value}</div>
          {subtitle ? <div className="mt-1 text-xs font-semibold text-slate-600">{subtitle}</div> : null}
        </div>

        {icon ? (
          <div className="shrink-0 rounded-2xl border border-white/70 bg-white/60 p-2 shadow-sm">
            {icon}
          </div>
        ) : null}
      </div>
    </div>
  );
}
