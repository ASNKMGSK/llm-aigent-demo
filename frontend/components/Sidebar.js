// components/Sidebar.js
import { useEffect, useMemo, useState } from 'react';
import { ArrowUpRight, LogOut, Sparkles, Store, Zap, ChevronDown } from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';

const SEEN_KEY = 'app_seen_example_hint';

function SidebarContent({
  auth,
  merchants,
  industries,
  selectedMerchant,
  setSelectedMerchant,
  exampleQuestions,
  onExampleQuestion,
  onLogout,
  onClose,
  isMobile,
}) {
  const merchantIds = (merchants || []).map((m) => m?.merchant_id ?? m);
  const [merchantFilter, setMerchantFilter] = useState('');
  const [hintActive, setHintActive] = useState(false);

  // ✅ 예시 질문 아코디언(카테고리 열림 상태)
  const [openCats, setOpenCats] = useState({});

  // ✅ 카테고리별 구분(보더/배경 + 왼쪽 굵은 컬러보더)
  const CAT_STYLES = [
    { card: 'from-sky-50/70 to-white/70 border-sky-200/70 border-l-sky-400/70' },
    { card: 'from-rose-50/70 to-white/70 border-rose-200/70 border-l-rose-400/70' },
    { card: 'from-violet-50/70 to-white/70 border-violet-200/70 border-l-violet-400/70' },
    { card: 'from-emerald-50/70 to-white/70 border-emerald-200/70 border-l-emerald-400/70' },
    { card: 'from-amber-50/70 to-white/70 border-amber-200/70 border-l-amber-400/70' },
  ];

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const seen = window.localStorage.getItem(SEEN_KEY);
    setHintActive(!seen);
  }, []);

  // ✅ 힌트가 켜질 때는 전체 카테고리 펼치기
  useEffect(() => {
    if (!hintActive) return;
    const keys = Object.keys(exampleQuestions || {});
    if (!keys.length) return;
    const next = {};
    for (const k of keys) next[k] = true;
    setOpenCats(next);
  }, [hintActive, exampleQuestions]);

  const filteredMerchantIds = useMemo(() => {
    const q = merchantFilter.trim().toLowerCase();
    if (!q) return merchantIds;
    return merchantIds.filter((id) => String(id).toLowerCase().includes(q));
  }, [merchantFilter, merchantIds]);

  function markSeen() {
    if (typeof window === 'undefined') return;
    window.localStorage.setItem(SEEN_KEY, '1');
    setHintActive(false);
  }

  function clickExample(q) {
    markSeen();
    onExampleQuestion(q);
    if (isMobile) onClose?.();
  }

  function toggleCat(cat) {
    setOpenCats((prev) => ({ ...prev, [cat]: !prev?.[cat] }));
  }

  const accordionVariants = {
    open: {
      height: 'auto',
      opacity: 1,
      transition: { duration: 0.24, ease: 'easeOut', when: 'beforeChildren', staggerChildren: 0.03 },
    },
    closed: {
      height: 0,
      opacity: 0,
      transition: { duration: 0.18, ease: 'easeIn', when: 'afterChildren' },
    },
  };

  const itemVariants = {
    open: { opacity: 1, y: 0, transition: { duration: 0.18, ease: 'easeOut' } },
    closed: { opacity: 0, y: -6, transition: { duration: 0.12, ease: 'easeIn' } },
  };

  return (
    <div className={isMobile ? 'h-full overflow-auto px-4 py-5' : 'px-4 py-5'}>
      <div className="pb-4 mb-4 border-b border-white/60">
        <div className="flex items-start justify-between gap-2">
          <div className="inline-flex items-center gap-2">
            <div className="h-10 w-10 rounded-2xl bg-gradient-to-br from-violet-200 via-sky-200 to-rose-200 shadow-sm" />
            <div>
              <h2 className="text-base font-black text-slate-900 leading-tight">LLM 기반 DEMO 웹앱</h2>
              <p className="text-xs font-semibold text-slate-500">데이터 분석 플랫폼</p>
            </div>
          </div>

          {isMobile ? (
            <button
              className="inline-flex items-center justify-center rounded-2xl border border-white/60 bg-white/60 px-3 py-2 text-sm font-black text-slate-700 shadow-sm hover:bg-white"
              onClick={onClose}
              aria-label="close"
              type="button"
            >
              ✕
            </button>
          ) : null}
        </div>
      </div>

      <div className="mb-3 rounded-3xl border border-white/60 bg-white/55 p-3 shadow-sm backdrop-blur">
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <div className="text-sm font-black text-slate-900 truncate">{auth?.user_name || auth?.username || '-'}</div>
            <div className="text-xs font-semibold text-slate-500">{auth?.user_role || '-'}</div>
          </div>

          <div className="rounded-2xl border border-white/60 bg-white/60 p-2 shadow-sm">
            <Sparkles size={16} className="text-slate-700" />
          </div>
        </div>
      </div>

      <button
        className="w-full mb-4 inline-flex items-center justify-center gap-2 rounded-2xl border border-white/60 bg-white/60 px-3 py-2 text-xs font-black text-slate-700 shadow-sm hover:bg-white active:translate-y-[1px]"
        onClick={onLogout}
        type="button"
      >
        <LogOut size={16} /> 로그아웃
      </button>

      <div className="rounded-3xl border border-white/60 bg-white/55 p-3 shadow-sm backdrop-blur">
        <div className="flex items-center gap-2 text-sm font-black text-slate-800 mb-2">
          <Store size={16} /> 가맹점 선택
        </div>

        <input
          className="w-full rounded-2xl border border-white/60 bg-white/70 px-3 py-2 text-sm font-semibold text-slate-700 outline-none placeholder:text-slate-400 focus:ring-2 focus:ring-sky-200"
          placeholder="가맹점 검색 (예: M0001)"
          value={merchantFilter}
          onChange={(e) => setMerchantFilter(e.target.value)}
        />

        <select
          className="mt-2 w-full rounded-2xl border border-white/60 bg-white/70 px-3 py-2 text-sm font-semibold text-slate-700 outline-none focus:ring-2 focus:ring-sky-200"
          value={selectedMerchant || ''}
          onChange={(e) => setSelectedMerchant(e.target.value || null)}
        >
          {filteredMerchantIds.length ? (
            filteredMerchantIds.map((id) => (
              <option key={id} value={id}>
                {id}
              </option>
            ))
          ) : (
            <option value="">(없음)</option>
          )}
        </select>

        <div className="mt-3 rounded-2xl border border-white/60 bg-gradient-to-br from-sky-50 to-violet-50 px-3 py-2 text-xs font-semibold text-slate-600">
          <span className="font-black text-slate-700">업종:</span> {industries?.length ? industries.join(', ') : '-'}
        </div>
      </div>

      <div className="mt-4 rounded-3xl border border-white/60 bg-white/55 p-3 shadow-sm backdrop-blur">
        <div className="flex items-center justify-between mb-2">
          <div className="text-sm font-black text-slate-800">예시 질문</div>
          <span className="inline-flex items-center gap-1 rounded-full border border-white/60 bg-white/70 px-2 py-1 text-[10px] font-black text-slate-600">
            <Zap size={12} /> 클릭 즉시 전송
          </span>
        </div>

        <div
          className={
            hintActive
              ? 'rounded-2xl border border-sky-200/70 bg-sky-50/60 p-2 shadow-sm ring-2 ring-sky-200/50'
              : 'rounded-2xl border border-white/60 bg-white/60 p-2 shadow-sm'
          }
        >
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-600 px-2 py-1">
            <Zap size={14} className="text-slate-700" />
            한 번 눌러서 바로 분석 시작
          </div>

          <div className="space-y-3 mt-3">
            {Object.entries(exampleQuestions || {}).map(([cat, qs], idx) => {
              const isOpen = !!openCats?.[cat];
              const palette = CAT_STYLES[idx % CAT_STYLES.length];
              const list = Array.isArray(qs) ? qs : [];

              return (
                <div
                  key={cat}
                  className={[
                    'relative rounded-2xl border border-l-4 bg-gradient-to-br p-2 shadow-sm ring-1 ring-black/5',
                    palette.card,
                    isOpen ? 'shadow-md' : 'hover:shadow-md transition-shadow',
                  ].join(' ')}
                >
                  <button
                    type="button"
                    onClick={() => toggleCat(cat)}
                    className={[
                      'w-full flex items-center justify-between gap-2 rounded-xl px-3 py-2 transition',
                      'border border-white/70 bg-white/70 backdrop-blur',
                      isOpen ? 'shadow-sm' : 'hover:bg-white/85 hover:shadow-sm',
                      'active:translate-y-[1px]',
                    ].join(' ')}
                  >
                    <span className="text-sm font-black text-slate-900 leading-5">{cat}</span>
                    <ChevronDown
                      size={16}
                      className={`text-slate-600 transition-transform ${isOpen ? 'rotate-180' : ''}`}
                    />
                  </button>

                  <AnimatePresence initial={false}>
                    {isOpen ? (
                      <motion.div
                        key={`${cat}-content`}
                        initial="closed"
                        animate="open"
                        exit="closed"
                        variants={accordionVariants}
                        className="overflow-hidden"
                      >
                        <div className="mt-2 space-y-2">
                          {list.map((q) => (
                            <motion.button
                              key={q}
                              variants={itemVariants}
                              title={q}
                              className={[
                                'group w-full text-left rounded-2xl px-3 py-2.5 transition flex items-start gap-3',
                                'border border-slate-200/70 bg-white/85',
                                'hover:bg-white hover:shadow-sm',
                                'active:translate-y-[1px]',
                                'text-[13px] leading-5 font-semibold text-slate-800',
                              ].join(' ')}
                              onClick={() => clickExample(q)}
                              type="button"
                            >
                              <span className="flex-1 min-w-0 whitespace-normal break-words">{q}</span>
                              <span className="inline-flex shrink-0 items-center gap-1 text-xs font-black text-slate-500 group-hover:text-slate-700 ml-auto">
                                실행 <ArrowUpRight size={14} />
                              </span>
                            </motion.button>
                          ))}
                        </div>
                      </motion.div>
                    ) : null}
                  </AnimatePresence>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <div className="mt-4 text-[10px] font-semibold text-slate-400">v2.2 • pastel</div>
    </div>
  );
}

export default function Sidebar(props) {
  const { open, onClose } = props;

  return (
    <>
      <aside className="hidden xl:block rounded-[32px] border border-white/60 bg-white/55 shadow-[0_18px_60px_-40px_rgba(15,23,42,0.35)] backdrop-blur">
        <SidebarContent {...props} isMobile={false} />
      </aside>

      {open ? (
        <div className="xl:hidden fixed inset-0 z-50">
          <div className="absolute inset-0 bg-slate-900/20" onClick={onClose} />
          <div className="absolute left-3 top-3 bottom-3 w-[88%] max-w-[380px] rounded-[32px] border border-white/60 bg-white/70 backdrop-blur shadow-2xl overflow-hidden">
            <SidebarContent {...props} isMobile={true} onClose={onClose} />
          </div>
        </div>
      ) : null}
    </>
  );
}
