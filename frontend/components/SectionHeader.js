export default function SectionHeader({ title, subtitle, right }) {
  return (
    <div className="mb-4 flex items-end justify-between gap-3">
      <div>
        <h2 className="text-lg font-black text-slate-900">{title}</h2>
        {subtitle ? <p className="text-xs font-semibold text-slate-500">{subtitle}</p> : null}
      </div>
      {right ? <div className="shrink-0">{right}</div> : null}
    </div>
  );
}
