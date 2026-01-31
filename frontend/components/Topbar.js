import { LogOut, Menu } from 'lucide-react';

export default function Topbar({ username, onOpenSidebar, onLogout }) {
  return (
    <header className="sticky top-0 z-40">
      <div className="mx-auto max-w-[1320px] px-3 sm:px-4">
        <div className="mt-3 rounded-3xl border border-white/60 bg-white/55 px-3 py-2 shadow-[0_12px_40px_-30px_rgba(15,23,42,0.35)] backdrop-blur">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={onOpenSidebar}
                className="inline-flex items-center justify-center rounded-2xl border border-white/60 bg-white/60 p-2 text-slate-700 shadow-sm hover:bg-white active:translate-y-[1px] xl:hidden"
                aria-label="Open menu"
              >
                <Menu size={18} />
              </button>

              <div className="flex items-center gap-2">
                <div className="h-9 w-9 rounded-2xl bg-gradient-to-br from-violet-200 via-sky-200 to-rose-200 shadow-sm" />
                <div>
                  <div className="text-xs font-extrabold tracking-wide text-slate-700">
                    LLM 기반 DEMO 웹앱
                  </div>
                  <div className="text-[11px] font-semibold text-slate-500">
                    {username}
                  </div>
                </div>
              </div>
            </div>

            <button
              type="button"
              onClick={onLogout}
              className="inline-flex items-center gap-2 rounded-2xl border border-white/60 bg-white/60 px-3 py-2 text-xs font-extrabold text-slate-700 shadow-sm hover:bg-white active:translate-y-[1px]"
              title="로그아웃"
            >
              <LogOut size={16} />
              로그아웃
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
