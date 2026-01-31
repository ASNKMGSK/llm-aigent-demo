// components/panels/AgentPanel.js
// ✅ "질문/답변 올 때마다 이상한 곳으로 튀는" 자동 스크롤 비활성화 버전
// 핵심: 기존 useEffect(scrollIntoView) 제거 + 사용자가 바닥 근처에 있을 때만 자동 스크롤

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import toast from 'react-hot-toast';
import { motion } from 'framer-motion';
import EmptyState from '@/components/EmptyState';
import SectionHeader from '@/components/SectionHeader';
import { ArrowUpRight, Sparkles, Zap, Loader2 } from 'lucide-react';
import { fetchEventSource } from '@microsoft/fetch-event-source';

// AgentPanel.js 안에서 (return 위 아무데나) 추가
const pastelBtn =
  'w-full rounded-2xl border border-slate-200/70 bg-gradient-to-r from-sky-200 via-indigo-200 to-rose-200 px-4 py-3 text-sm font-extrabold text-slate-700 shadow-sm transition hover:from-sky-300 hover:via-indigo-300 hover:to-rose-300 active:translate-y-[1px] disabled:opacity-60 disabled:cursor-not-allowed';

const pastelBtnSecondary =
  'w-full rounded-2xl border border-slate-200/70 bg-white/70 px-4 py-3 text-sm font-extrabold text-slate-700 shadow-sm transition hover:bg-white active:translate-y-[1px] disabled:opacity-60 disabled:cursor-not-allowed';

// ✅ 인라인(전송/중단 140px 버튼용) - btn/btn-secondary 안 쓰고 이걸로만 스타일 통일
const pastelBtnInline =
  'rounded-2xl border border-slate-200/70 bg-gradient-to-r from-sky-200 via-indigo-200 to-rose-200 px-4 py-3 text-sm font-extrabold text-slate-700 shadow-sm transition hover:from-sky-300 hover:via-indigo-300 hover:to-rose-300 active:translate-y-[1px] disabled:opacity-60 disabled:cursor-not-allowed inline-flex items-center justify-center gap-2 whitespace-nowrap';

const pastelBtnSecondaryInline =
  'rounded-2xl border border-slate-200/70 bg-white/70 px-4 py-3 text-sm font-extrabold text-slate-700 shadow-sm transition hover:bg-white active:translate-y-[1px] disabled:opacity-60 disabled:cursor-not-allowed inline-flex items-center justify-center gap-2 whitespace-nowrap';

const SEEN_KEY = 'app_seen_example_hint';

const DEFAULT_FALLBACK_SYSTEM_PROMPT = [
  'DEMO AI 핀테크 공식 데이터 분석 에이전트 운영 지침서',
  '',
  '- 당신은 DEMO AI 핀테크의 공식 데이터 분석 에이전트입니다.',
  '- 사실/수치는 백엔드 결과만 사용하고, 없는 값은 추측하지 않습니다.',
  '- 최종 답변은 반드시 텍스트 리포트로 출력합니다. (빈 응답 금지)',
].join('\n');

const WAITING_PLACEHOLDER = ['답변 생성 중입니다.', '잠시 기다려주세요.'].join('\n');

function basicAuthHeader(username, password) {
  return 'Basic ' + btoa(`${username}:${password}`);
}

function newMsgId() {
  return `${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

function ToolCalls({ toolCalls }) {
  if (!toolCalls?.length) return null;
  return (
    <details className="details mt-2">
      <summary>도구 실행 결과</summary>
      <div className="mt-2 space-y-3">
        {toolCalls.map((tc, idx) => {
          const ok = tc?.result?.status === 'SUCCESS';
          return (
            <div
              key={idx}
              className="rounded-2xl border border-slate-200/70 bg-white/70 p-3 shadow-sm backdrop-blur"
            >
              <div className="flex items-center justify-between">
                <div className="font-extrabold text-slate-800">{tc.tool}</div>
                <span className={ok ? 'badge badge-success' : 'badge badge-danger'}>
                  {ok ? '성공' : '실패'}
                </span>
              </div>
              <pre className="mt-2 overflow-auto rounded-xl bg-slate-50/70 p-3 text-xs text-slate-700">
                {JSON.stringify(tc.result, null, 2)}
              </pre>
            </div>
          );
        })}
      </div>
    </details>
  );
}

function Chip({ label, onClick }) {
  return (
    <button
      className="inline-flex items-center gap-2 rounded-full border border-slate-200/70 bg-white/70 px-3 py-1.5 text-xs font-extrabold text-slate-700 hover:bg-white hover:shadow-sm transition active:translate-y-[1px] whitespace-nowrap"
      onClick={onClick}
      title="클릭하면 질문이 바로 전송됩니다"
      type="button"
    >
      <Sparkles size={14} className="text-slate-700" />
      <span className="max-w-[220px] truncate">{label}</span>
      <ArrowUpRight size={14} className="text-slate-500" />
    </button>
  );
}

function TypingDots() {
  return (
    <div className="flex items-center gap-1 py-1">
      <span className="h-2 w-2 rounded-full bg-slate-400 animate-bounce [animation-delay:-0.2s]" />
      <span className="h-2 w-2 rounded-full bg-slate-400 animate-bounce [animation-delay:-0.1s]" />
      <span className="h-2 w-2 rounded-full bg-slate-400 animate-bounce" />
      <span className="ml-2 text-xs text-slate-500">답변 생성 중…</span>
    </div>
  );
}

function TopProgressBar({ active }) {
  if (!active) return null;
  return (
    <div className="mb-3 h-1 w-full overflow-hidden rounded-full bg-slate-200">
      <div className="h-full w-1/3 animate-[app_progress_1.2s_ease-in-out_infinite] bg-slate-600" />
    </div>
  );
}

function useRemarkGfm() {
  const [remarkGfm, setRemarkGfm] = useState(null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const mod = await import('remark-gfm');
        if (!mounted) return;
        setRemarkGfm(() => (mod?.default ? mod.default : mod));
      } catch (e) {
        if (!mounted) return;
        setRemarkGfm(null);
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  return remarkGfm;
}

function MarkdownMessage({ content }) {
  const remarkGfm = useRemarkGfm();
  const remarkPlugins = useMemo(() => (remarkGfm ? [remarkGfm] : []), [remarkGfm]);

  return (
    <ReactMarkdown
      remarkPlugins={remarkPlugins}
      components={{
        table: ({ node, ...props }) => (
          <div className="overflow-x-auto -mx-1 my-2">
            <table className="w-full border-collapse" {...props} />
          </div>
        ),
        thead: ({ node, ...props }) => <thead className="bg-slate-50/80" {...props} />,
        th: ({ node, ...props }) => (
          <th
            className="border border-slate-200 px-3 py-2 text-left text-xs font-extrabold text-slate-700"
            {...props}
          />
        ),
        td: ({ node, ...props }) => (
          <td
            className="border border-slate-200 px-3 py-2 align-top text-xs text-slate-700 whitespace-nowrap"
            {...props}
          />
        ),
        pre: ({ node, ...props }) => (
          <pre className="overflow-x-auto rounded-xl bg-slate-50/70 p-3 text-xs text-slate-700" {...props} />
        ),
        code: ({ node, inline, className, children, ...props }) => {
          if (inline) {
            return (
              <code className="rounded bg-slate-100 px-1 py-0.5 text-[11px] text-slate-800" {...props}>
                {children}
              </code>
            );
          }
          return (
            <code className={className} {...props}>
              {children}
            </code>
          );
        },
        a: ({ node, ...props }) => (
          <a
            {...props}
            target="_blank"
            rel="noopener noreferrer"
            className="font-extrabold text-slate-700 underline underline-offset-2 hover:text-slate-900"
          />
        ),
      }}
    >
      {content || ''}
    </ReactMarkdown>
  );
}

export default function AgentPanel({
  auth,
  selectedMerchant,
  addLog,
  settings,
  setSettings,
  agentMessages,
  setAgentMessages,
  totalQueries,
  setTotalQueries,
  apiCall,
}) {
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [quickResult, setQuickResult] = useState(null);

  // ✅ 채팅 영역 ref (scrollIntoView 대신 이 컨테이너만 스크롤 제어)
  const chatBoxRef = useRef(null);
  const scrollRef = useRef(null);

  const abortRef = useRef(null);
  const timeoutRef = useRef(null);

  const stoppedRef = useRef(false);
  const runIdRef = useRef(0);
  const activeAssistantIdRef = useRef(null);

  const canSend = useMemo(() => !!input?.trim() && !loading, [input, loading]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const seen = window.localStorage.getItem(SEEN_KEY);
    if (!seen) toast('왼쪽 예시 질문을 클릭하면 바로 분석이 시작됩니다', { icon: '👉' });
  }, []);

  function markSeen() {
    if (typeof window === 'undefined') return;
    window.localStorage.setItem(SEEN_KEY, '1');
  }

  const chips = useMemo(() => {
    const mid = selectedMerchant || 'M0001';
    return [
      `${mid} 현황 분석해줘`,
      `${mid} 매출 예측해줘`,
      `${mid} 이상 탐지해줘`,
      '전체 가맹점 목록',
      'LTV/CAC 정의',
      '재구매율 설명',
    ];
  }, [selectedMerchant]);

  // ✅ 사용자가 "바닥 근처"에 있을 때만 자동 스크롤
  const shouldAutoScrollRef = useRef(true);

  const updateAutoScrollFlag = useCallback(() => {
    const el = chatBoxRef.current;
    if (!el) return;
    const threshold = 80; // px
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    shouldAutoScrollRef.current = distanceFromBottom <= threshold;
  }, []);

  useEffect(() => {
    const el = chatBoxRef.current;
    if (!el) return;
    el.addEventListener('scroll', updateAutoScrollFlag, { passive: true });
    return () => el.removeEventListener('scroll', updateAutoScrollFlag);
  }, [updateAutoScrollFlag]);

  // ✅ 컨테이너 내부에서만, 그리고 바닥 근처일 때만 scrollTop 이동
  useEffect(() => {
    const el = chatBoxRef.current;
    if (!el) return;
    if (!shouldAutoScrollRef.current) return;
    el.scrollTop = el.scrollHeight;
  }, [agentMessages, loading]);

  const stopStream = useCallback(() => {
    setLoading(false);

    try {
      runIdRef.current += 1;
      stoppedRef.current = true;

      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }

      if (abortRef.current) {
        abortRef.current.abort();
        abortRef.current = null;
      }

      const aid = activeAssistantIdRef.current;

      setAgentMessages((prev) => {
        const arr = prev || [];

        let targetId = aid;
        if (!targetId) {
          const lastPending = [...arr].reverse().find((m) => m?.role === 'assistant' && m?._pending);
          targetId = lastPending?._id || null;
        }
        if (!targetId) return arr;

        const idx = arr.findIndex((m) => m?._id === targetId);
        if (idx < 0) return arr;

        const msg = arr[idx] || {};
        const content = String(msg.content || '').trim();
        const isPending = !!msg._pending;
        const isOnlyWaiting = content === String(WAITING_PLACEHOLDER).trim();

        if (!content || isPending || isOnlyWaiting) return arr.filter((m) => m?._id !== targetId);

        return arr.map((m) => {
          if (m?._id !== targetId) return m;
          const cur = String(m.content || '');
          return { ...m, content: cur + '\n\n[중단됨]', _pending: false };
        });
      });

      activeAssistantIdRef.current = null;
    } catch (e) {
      activeAssistantIdRef.current = null;
    } finally {
      setLoading(false);
    }
  }, [setAgentMessages]);

  const userKey = useMemo(() => String(auth?.username || '').trim(), [auth?.username]);
  const prevUserKeyRef = useRef(userKey);

  useEffect(() => {
    // ✅ 최초 마운트 시에는 실행하지 않고, userKey가 실제로 변경되었을 때만 초기화
    if (prevUserKeyRef.current === userKey) return;

    prevUserKeyRef.current = userKey;

    stopStream();
    setAgentMessages([]);
    setTotalQueries(0);
    setQuickResult(null);
    setInput('');
    setLoading(false);
  }, [userKey, stopStream, setAgentMessages, setTotalQueries]);

  const sendQuestion = useCallback(
    async (question) => {
      const q = String(question || '').trim();
      if (!q) return;

      markSeen();
      stopStream();

      stoppedRef.current = false;
      runIdRef.current += 1;
      const myRunId = runIdRef.current;

      setLoading(true);
      addLog('질문', q.slice(0, 30));

      const userMsg = { _id: newMsgId(), role: 'user', content: q };
      const assistantId = newMsgId();
      activeAssistantIdRef.current = assistantId;

      const assistantMsg = {
        _id: assistantId,
        role: 'assistant',
        content: WAITING_PLACEHOLDER,
        tool_calls: [],
        _pending: true,
      };

      setAgentMessages((prev) => [...(prev || []), userMsg, assistantMsg]);

      const systemPromptToSend =
        settings?.systemPrompt && String(settings.systemPrompt).trim().length > 0
          ? String(settings.systemPrompt)
          : DEFAULT_FALLBACK_SYSTEM_PROMPT;

      const username = auth?.username || '';
      const password = auth?.password || '';

      const ctrl = new AbortController();
      abortRef.current = ctrl;

      const timeoutMs = 60000;
      timeoutRef.current = setTimeout(() => {
        try {
          stoppedRef.current = true;
          ctrl.abort();
        } catch (e) {}
      }, timeoutMs);

      let deltaBuf = '';
      let flushTimer = null;

      const flushDelta = () => {
        if (!deltaBuf) return;
        const chunk = deltaBuf;
        deltaBuf = '';

        setAgentMessages((prev) =>
          (prev || []).map((m) => {
            if (m?._id !== assistantId) return m;

            const isPending = !!m?._pending;
            if (isPending) return { ...m, content: chunk, _pending: false };
            return { ...m, content: String(m.content || '') + chunk, _pending: false };
          })
        );
      };

      const isStale = () =>
        myRunId !== runIdRef.current ||
        stoppedRef.current ||
        ctrl.signal.aborted ||
        activeAssistantIdRef.current !== assistantId;

      try {
        // ✅ 외부에서도 동작하게: 프론트(ngrok) 기준 상대경로로 호출
        // pages/api/agent/stream.js(프록시)로 태워서 백엔드로 전달
        await fetchEventSource(`/api/agent/stream`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Accept: 'text/event-stream',
            Authorization: basicAuthHeader(username, password),
          },
          body: JSON.stringify({
            user_input: q,
            merchant_id: selectedMerchant || null,
            api_key: settings.apiKey || '',
            model: settings.selectedModel || 'gpt-4o',
            max_tokens: Number(settings.maxTokens ?? 4000),
            system_prompt: systemPromptToSend,
            debug: true,
          }),
          signal: ctrl.signal,

          async onopen(res) {
            if (isStale()) return;
            const ct = res.headers.get('content-type') || '';
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            if (!ct.includes('text/event-stream')) throw new Error('Not an SSE response');
          },

          onmessage(ev) {
            if (isStale()) return;

            let data = {};
            try {
              data = ev.data ? JSON.parse(ev.data) : {};
            } catch (e) {
              return;
            }

            if (ev.event === 'delta') {
              const delta = String(data.delta || '');
              if (!delta) return;

              deltaBuf += delta;

              if (!flushTimer) {
                flushTimer = setTimeout(() => {
                  flushTimer = null;
                  if (isStale()) return;
                  flushDelta();
                }, 50);
              }
              return;
            }

            if (ev.event === 'done') {
              if (isStale()) return;

              if (flushTimer) {
                clearTimeout(flushTimer);
                flushTimer = null;
              }
              flushDelta();

              const ok = !!data.ok;
              const finalText = String(data.final || '');
              const toolCalls = Array.isArray(data.tool_calls) ? data.tool_calls : [];

              setAgentMessages((prev) =>
                (prev || []).map((m) => {
                  if (m?._id !== assistantId) return m;
                  return {
                    ...m,
                    content: finalText || String(m.content || ''),
                    tool_calls: toolCalls,
                    _pending: false,
                  };
                })
              );

              setTotalQueries((prev) => (prev || 0) + 1);
              setLoading(false);

              if (timeoutRef.current) {
                clearTimeout(timeoutRef.current);
                timeoutRef.current = null;
              }
              abortRef.current = null;
              activeAssistantIdRef.current = null;

              if (ok) toast.success('분석 완료');
              else toast.error('요청 실패: 백엔드/네트워크를 확인하세요');
              return;
            }

            if (ev.event === 'error') {
              if (isStale()) return;

              if (flushTimer) {
                clearTimeout(flushTimer);
                flushTimer = null;
              }
              flushDelta();

              const msg = data?.message ? String(data.message) : '스트리밍 오류';

              setAgentMessages((prev) =>
                (prev || []).map((m) => {
                  if (m?._id !== assistantId) return m;
                  const cur = String(m.content || '');
                  return { ...m, content: cur + `\n\n[오류]\n${msg}`, _pending: false };
                })
              );

              toast.error(msg);
              return;
            }
          },

          onerror(err) {
            throw err;
          },

          onclose() {
            if (isStale()) return;
            throw new Error('SSE closed');
          },
        });
      } catch (e) {
        if (isStale()) {
          setLoading(false);
          return;
        }

        if (flushTimer) {
          clearTimeout(flushTimer);
          flushTimer = null;
        }
        flushDelta();

        const msg = String(e || '요청 실패');

        setAgentMessages((prev) =>
          (prev || []).map((m) => {
            if (m?._id !== assistantId) return m;
            const cur = String(m.content || '');
            return { ...m, content: cur + `\n\n[오류]\n${msg}`, _pending: false };
          })
        );

        setLoading(false);
        toast.error('요청 실패');
      } finally {
        if (flushTimer) {
          clearTimeout(flushTimer);
          flushTimer = null;
        }

        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current);
          timeoutRef.current = null;
        }
        abortRef.current = null;

        if (activeAssistantIdRef.current === assistantId) {
          activeAssistantIdRef.current = null;
        }
      }
    },
    [addLog, auth, settings, setAgentMessages, setTotalQueries, stopStream]
  );

  useEffect(() => {
    function handler(ev) {
      const q = ev?.detail?.q;
      if (!q) return;
      sendQuestion(q);
    }
    window.addEventListener('app_send_question', handler);
    return () => window.removeEventListener('app_send_question', handler);
  }, [sendQuestion]);

  async function runQuick(endpoint, method = 'GET', payload = null) {
    if (!selectedMerchant) return;
    setQuickResult(null);

    const res = await apiCall({
      endpoint,
      method,
      auth,
      data: payload,
      timeoutMs: 60000,
    });

    setQuickResult(res);
    addLog('빠른분석', endpoint);
  }

  return (
    <div className="grid grid-cols-12 gap-4">
      <div className="col-span-12 xl:col-span-9">
        <SectionHeader
          title="AI 에이전트"
          subtitle="GPT + ML 기반 가맹점 분석"
          right={<span className="badge">쿼리 {totalQueries || 0}</span>}
        />

        <div className="card">

          {/* ✅ 여기! 채팅 스크롤 컨테이너에 ref 부여 */}
          <div ref={chatBoxRef} className="max-h-[62vh] md:max-h-[70vh] overflow-auto pr-1">
            {(agentMessages || []).map((m, idx) => {
              const isUser = m.role === 'user';
              const isPending = !!m?._pending;

              return (
                <motion.div
                  key={m?._id || idx}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.18 }}
                  className={isUser ? 'flex justify-end mb-3' : 'flex justify-start mb-3'}
                >
                  <div
                    className={
                      isUser
                        ? 'chat-bubble chat-bubble-user w-full md:max-w-[78%]'
                        : 'chat-bubble w-full md:max-w-[78%]'
                    }
                  >
                    <div className="text-[11px] font-extrabold text-slate-500 mb-2 flex items-center justify-between">
                      <span>{isUser ? auth?.username || 'USER' : 'ASSISTANT'}</span>

                      {!isUser && isPending ? (
                        <span className="inline-flex items-center gap-2 text-slate-500">
                          <span className="h-3 w-3 rounded-full border-2 border-slate-300 border-t-slate-600 animate-spin" />
                          <span className="text-[10px]">streaming</span>
                        </span>
                      ) : null}
                    </div>

                    <div className="prose prose-sm max-w-none">
                      {!isUser && isPending ? <TypingDots /> : <MarkdownMessage content={m.content || ''} />}
                    </div>

                    <ToolCalls toolCalls={m.tool_calls} />
                  </div>
                </motion.div>
              );
            })}

            {!agentMessages?.length ? (
              <EmptyState
                title="대화를 시작해보세요"
                desc="왼쪽 예시 질문을 누르거나 아래 추천 질문을 클릭하면 바로 시작됩니다."
              />
            ) : null}

            <div ref={scrollRef} />
          </div>

          <div className="mt-3 flex flex-wrap gap-2">
            {chips.map((c) => (
              <Chip
                key={c}
                label={c}
                onClick={() => {
                  sendQuestion(c);
                  setInput('');
                }}
              />
            ))}
          </div>

          <div className="mt-3 flex flex-col md:flex-row gap-2">
            <input
              className="input"
              placeholder="질문 입력 (Enter로 전송)"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && canSend) {
                  sendQuestion(input);
                  setInput('');
                }
              }}
            />

            {/* ✅ 전송 버튼: btn 제거 + 파스텔 인라인 적용 */}
            <button
              className={`${pastelBtnInline} w-[140px]`}
              onClick={() => {
                sendQuestion(input);
                setInput('');
              }}
              disabled={!canSend}
              type="button"
            >
              {loading ? <Loader2 size={16} className="animate-spin" /> : <Zap size={16} />}
              {loading ? '분석중...' : '전송'}
            </button>

            {/* ✅ 중단 버튼: btn-secondary 제거 + 파스텔 인라인 적용 */}
            <button
              className={`${pastelBtnSecondaryInline} w-[140px]`}
              onClick={() => {
                stopStream();
                toast('중단됨');
              }}
              disabled={!loading}
              title="스트리밍 중단"
              type="button"
            >
              중단
            </button>
          </div>
        </div>
      </div>

      <div className="col-span-12 xl:col-span-3">
        <div className="card">
          <div className="card-header">빠른 분석</div>
          <div className="text-sm text-slate-600 mb-3">
            선택: <span className="font-mono">{selectedMerchant || '-'}</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-1 gap-2">
            <button
              className={pastelBtn}
              onClick={() => runQuick(`/api/merchants/${selectedMerchant}`)}
              disabled={!selectedMerchant}
              type="button"
            >
              지표 조회
            </button>
            <button
              className={pastelBtn}
              onClick={() => runQuick('/api/predict/revenue', 'POST', { merchant_id: selectedMerchant })}
              disabled={!selectedMerchant}
              type="button"
            >
              매출 예측
            </button>
            <button
              className={pastelBtn}
              onClick={() => runQuick('/api/detect/anomaly', 'POST', { merchant_id: selectedMerchant })}
              disabled={!selectedMerchant}
              type="button"
            >
              이상 탐지
            </button>
            <button
              className={pastelBtn}
              onClick={() => runQuick('/api/classify/growth', 'POST', { merchant_id: selectedMerchant })}
              disabled={!selectedMerchant}
              type="button"
            >
              성장 분류
            </button>
          </div>

          <div className="mt-3">
            <button className="btn-secondary w-full" onClick={() => setAgentMessages([])} type="button">
              대화 초기화
            </button>
          </div>

          {quickResult ? (
            <pre className="mt-3 max-h-[45vh] overflow-auto rounded-2xl bg-slate-50/70 p-3 text-xs text-slate-700">
              {JSON.stringify(quickResult, null, 2)}
            </pre>
          ) : (
            <div className="mt-3 text-xs text-slate-500">오른쪽 버튼으로 즉시 API 호출 결과를 확인할 수 있어요.</div>
          )}
        </div>

        <div className="card mt-4">
          <div className="card-header">LLM 설정 요약</div>
          <div className="text-sm text-slate-600 space-y-1">
            <div>
              <span className="text-slate-500">모델</span>: <span className="font-mono">{settings.selectedModel}</span>
            </div>
            <div>
              <span className="text-slate-500">Max Tokens</span>: <span className="font-mono">{settings.maxTokens}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
