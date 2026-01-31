// components/panels/SettingsPanel.js
import { useEffect, useMemo, useState } from "react";

const DEFAULT_FALLBACK_SYSTEM_PROMPT = [
  "DEMO AI 핀테크 공식 데이터 분석 에이전트 운영 지침서",
  "",
  "1. 역할 및 정체성",
  "당신은 DEMO AI 핀테크의 공식 데이터 분석 에이전트입니다.",
  "사용자의 요청에 따라 가맹점 지표를 조회, 예측, 분석하고 그 결과를 이해하기 쉬운 리포트 형태로 설명합니다.",
  "",
  "2. 데이터 처리 원칙 (가장 중요)",
  "- 분석 질문(매출 예측, 이상 탐지 등)에 대해서는 오직 내부 데이터/도구 결과만을 사실로 간주합니다.",
  "- 내부 데이터/도구 결과에 없는 수치나 통계를 절대 추측하여 생성하지 마세요.",
  "- 중요: 최종 답변은 반드시 텍스트 content로 출력해야 합니다. (빈 응답 금지)",
  "",
  "3. 출력 형식",
  "- 요약 -> 근거(주요 참고 변수) -> 점검 포인트 -> 권장 액션 순서를 포함합니다.",
].join("\n");

const clampNumber = (v, min, max, fallback) => {
  const n = Number(v);
  if (!Number.isFinite(n)) return fallback;
  if (typeof min === "number" && n < min) return min;
  if (typeof max === "number" && n > max) return max;
  return n;
};

export default function SettingsPanel({ settings, setSettings, addLog, apiCall, auth }) {
  // ✅ GPT-4 계열 중심 + 필요시 확장
  const models = useMemo(
    () => [
      "gpt-4o",
      "gpt-4o-mini",
      "gpt-4.1",
      "gpt-4.1-mini",
      "gpt-4-turbo",
    ],
    []
  );

  const selectedModel = (settings?.selectedModel || "gpt-4o").trim();
  const isGpt5 = selectedModel.toLowerCase().startsWith("gpt-5");

  const [loadingDefault, setLoadingDefault] = useState(false);

  useEffect(() => {
    const cur = settings?.systemPrompt ? String(settings.systemPrompt).trim() : "";
    if (cur.length > 0) return;

    let mounted = true;

    async function loadDefault() {
      setLoadingDefault(true);
      try {
        if (typeof apiCall !== "function") {
          if (!mounted) return;
          setSettings((s) => ({
            ...s,
            selectedModel: s?.selectedModel || "gpt-4o",
            maxTokens: Number(s?.maxTokens ?? 4000),
            temperature: s?.temperature ?? 0.7,
            topP: s?.topP ?? 1,
            presencePenalty: s?.presencePenalty ?? 0,
            frequencyPenalty: s?.frequencyPenalty ?? 0,
            seed: s?.seed ?? "",
            timeoutMs: Number(s?.timeoutMs ?? 30000),
            retries: Number(s?.retries ?? 2),
            stream: Boolean(s?.stream ?? true),
            systemPrompt: DEFAULT_FALLBACK_SYSTEM_PROMPT,
          }));
          return;
        }

        const res = await apiCall({
          endpoint: "/api/settings/default",
          method: "GET",
          auth,
          timeoutMs: 30000,
        });

        if (!mounted) return;

        const data = res?.data || res || {};
        const payload = data?.data || data || {};
        const prompt = String(payload?.systemPrompt || payload?.system_prompt || "").trim();

        setSettings((s) => ({
          ...s,
          selectedModel: s?.selectedModel || payload?.selectedModel || payload?.selected_model || "gpt-4o",
          maxTokens: Number(s?.maxTokens ?? payload?.maxTokens ?? payload?.max_tokens ?? 4000),
          temperature: s?.temperature ?? payload?.temperature ?? 0.7,
          topP: s?.topP ?? payload?.topP ?? payload?.top_p ?? 1,
          presencePenalty: s?.presencePenalty ?? payload?.presencePenalty ?? payload?.presence_penalty ?? 0,
          frequencyPenalty: s?.frequencyPenalty ?? payload?.frequencyPenalty ?? payload?.frequency_penalty ?? 0,
          seed: s?.seed ?? payload?.seed ?? "",
          timeoutMs: Number(s?.timeoutMs ?? payload?.timeoutMs ?? payload?.timeout_ms ?? 30000),
          retries: Number(s?.retries ?? payload?.retries ?? 2),
          stream: Boolean(s?.stream ?? payload?.stream ?? true),
          systemPrompt: prompt.length > 0 ? prompt : DEFAULT_FALLBACK_SYSTEM_PROMPT,
        }));

        if (addLog) addLog("LLM설정", "기본 시스템 프롬프트 자동 로드");
      } catch (e) {
        if (!mounted) return;
        setSettings((s) => ({
          ...s,
          selectedModel: s?.selectedModel || "gpt-4o",
          maxTokens: Number(s?.maxTokens ?? 4000),
          temperature: s?.temperature ?? 0.7,
          topP: s?.topP ?? 1,
          presencePenalty: s?.presencePenalty ?? 0,
          frequencyPenalty: s?.frequencyPenalty ?? 0,
          seed: s?.seed ?? "",
          timeoutMs: Number(s?.timeoutMs ?? 30000),
          retries: Number(s?.retries ?? 2),
          stream: Boolean(s?.stream ?? true),
          systemPrompt: DEFAULT_FALLBACK_SYSTEM_PROMPT,
        }));
      } finally {
        if (mounted) setLoadingDefault(false);
      }
    }

    loadDefault();

    return () => {
      mounted = false;
    };
  }, [apiCall, auth, addLog, setSettings, settings?.systemPrompt]);

  return (
    <div>
      <div className="flex items-end justify-between gap-3 mb-3">
        <div>
          <h2 className="text-lg md:text-xl font-semibold text-slate-900">LLM 설정</h2>
          <p className="text-sm text-slate-500">모델 파라미터 및 시스템 프롬프트</p>
        </div>
        <span className="badge">Admin</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card">
          <div className="card-header">모델 파라미터</div>

          <div className="space-y-3">
            <div>
              <label className="text-sm text-slate-600">모델</label>
              <select
                className="input mt-1"
                value={selectedModel}
                onChange={(e) => {
                  const nextModel = e.target.value;
                  setSettings((s) => ({
                    ...s,
                    selectedModel: nextModel,
                  }));
                }}
              >
                {models.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>

              <div className="mt-2">
                <label className="text-xs text-slate-500">모델명 직접 입력(선택)</label>
                <input
                  className="input mt-1"
                  type="text"
                  value={settings?.customModel ?? ""}
                  placeholder="예: gpt-4o (비우면 위 선택값 사용)"
                  onChange={(e) =>
                    setSettings((s) => ({
                      ...s,
                      customModel: e.target.value,
                      selectedModel: (e.target.value || "").trim() ? e.target.value : s?.selectedModel,
                    }))
                  }
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="text-sm text-slate-600">Temperature</label>
                <input
                  className="input mt-1"
                  type="number"
                  step="0.1"
                  min="0"
                  max="2"
                  value={isGpt5 ? "" : settings?.temperature ?? 0.7}
                  disabled={isGpt5}
                  placeholder={isGpt5 ? "gpt-5 계열은 미지원" : ""}
                  onChange={(e) =>
                    setSettings((s) => ({
                      ...s,
                      temperature: clampNumber(e.target.value, 0, 2, 0.7),
                    }))
                  }
                />
                {isGpt5 ? <div className="text-xs text-slate-500 mt-1">gpt-5 계열은 temperature를 사용하지 않습니다.</div> : null}
              </div>

              <div>
                <label className="text-sm text-slate-600">Top P</label>
                <input
                  className="input mt-1"
                  type="number"
                  step="0.05"
                  min="0"
                  max="1"
                  value={settings?.topP ?? 1}
                  onChange={(e) =>
                    setSettings((s) => ({
                      ...s,
                      topP: clampNumber(e.target.value, 0, 1, 1),
                    }))
                  }
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="text-sm text-slate-600">Presence Penalty</label>
                <input
                  className="input mt-1"
                  type="number"
                  step="0.1"
                  min="-2"
                  max="2"
                  value={settings?.presencePenalty ?? 0}
                  onChange={(e) =>
                    setSettings((s) => ({
                      ...s,
                      presencePenalty: clampNumber(e.target.value, -2, 2, 0),
                    }))
                  }
                />
              </div>

              <div>
                <label className="text-sm text-slate-600">Frequency Penalty</label>
                <input
                  className="input mt-1"
                  type="number"
                  step="0.1"
                  min="-2"
                  max="2"
                  value={settings?.frequencyPenalty ?? 0}
                  onChange={(e) =>
                    setSettings((s) => ({
                      ...s,
                      frequencyPenalty: clampNumber(e.target.value, -2, 2, 0),
                    }))
                  }
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="text-sm text-slate-600">Max Tokens</label>
                <input
                  className="input mt-1"
                  type="number"
                  step="100"
                  min="100"
                  max="6500"
                  value={settings?.maxTokens ?? 4000}
                  onChange={(e) =>
                    setSettings((s) => ({
                      ...s,
                      maxTokens: clampNumber(e.target.value, 100, 6500, 4000),
                    }))
                  }
                />
              </div>

              <div>
                <label className="text-sm text-slate-600">Seed (선택)</label>
                <input
                  className="input mt-1"
                  type="number"
                  step="1"
                  min="0"
                  value={settings?.seed ?? ""}
                  placeholder="비우면 미사용"
                  onChange={(e) =>
                    setSettings((s) => ({
                      ...s,
                      seed: e.target.value === "" ? "" : clampNumber(e.target.value, 0, 2147483647, 0),
                    }))
                  }
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="text-sm text-slate-600">요청 Timeout(ms)</label>
                <input
                  className="input mt-1"
                  type="number"
                  step="1000"
                  min="1000"
                  max="120000"
                  value={settings?.timeoutMs ?? 30000}
                  onChange={(e) =>
                    setSettings((s) => ({
                      ...s,
                      timeoutMs: clampNumber(e.target.value, 1000, 120000, 30000),
                    }))
                  }
                />
              </div>

              <div>
                <label className="text-sm text-slate-600">Retry 횟수</label>
                <input
                  className="input mt-1"
                  type="number"
                  step="1"
                  min="0"
                  max="10"
                  value={settings?.retries ?? 2}
                  onChange={(e) =>
                    setSettings((s) => ({
                      ...s,
                      retries: clampNumber(e.target.value, 0, 10, 2),
                    }))
                  }
                />
              </div>
            </div>

            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="text-sm text-slate-600">스트리밍 사용</div>
                <div className="text-xs text-slate-500">UI에서 /api/agent/stream 사용 여부 플래그</div>
              </div>
              <input
                type="checkbox"
                className="toggle"
                checked={Boolean(settings?.stream ?? true)}
                onChange={(e) => setSettings((s) => ({ ...s, stream: e.target.checked }))}
              />
            </div>

            <div>
              <label className="text-sm text-slate-600">OpenAI API Key</label>
              <input
                className="input mt-1"
                type="password"
                value={settings?.apiKey ?? ""}
                onChange={(e) => setSettings((s) => ({ ...s, apiKey: e.target.value }))}
              />
            </div>

            <button
              className="btn w-full"
              onClick={() => addLog && addLog("설정 변경", `모델: ${selectedModel} / temp=${settings?.temperature ?? 0.7} / top_p=${settings?.topP ?? 1}`)}
            >
              설정 저장
            </button>
          </div>
        </div>

        <div className="card">
          <div className="card-header">시스템 프롬프트</div>
          <textarea
            className="input"
            style={{ height: 280 }}
            value={settings?.systemPrompt || ""}
            placeholder={loadingDefault ? "기본 프롬프트 불러오는 중..." : "시스템 프롬프트를 입력하세요"}
            onChange={(e) => setSettings((s) => ({ ...s, systemPrompt: e.target.value }))}
          />
          <button className="btn w-full mt-3" onClick={() => addLog && addLog("프롬프트 변경", "system_prompt")}>
            프롬프트 저장
          </button>
        </div>
      </div>
    </div>
  );
}
