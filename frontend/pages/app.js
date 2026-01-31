// pages/app.js  (그대로 교체)
// ✅ 핵심 수정: router.replace('/login')를 "이미 /login이면 안 함" + router.isReady 가드
// ✅ Invariant: attempted to hard navigate to the same URL 방지

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/router';

import Layout from '@/components/Layout';
import Tabs from '@/components/Tabs';

import AgentPanel from '@/components/panels/AgentPanel';
import DashboardPanel from '@/components/panels/DashboardPanel';
import AnalysisPanel from '@/components/panels/AnalysisPanel';
import ModelsPanel from '@/components/panels/ModelsPanel';
import SettingsPanel from '@/components/panels/SettingsPanel';
import UsersPanel from '@/components/panels/UsersPanel';
import LogsPanel from '@/components/panels/LogsPanel';
import RagPanel from '@/components/panels/RagPanel';

import { apiCall as apiCallRaw } from '@/lib/api';
import {
  loadFromStorage,
  saveToStorage,
  loadFromSession,
  removeFromSession,
  STORAGE_KEYS,
} from '@/lib/storage';

const EXAMPLE_QUESTIONS = {
  '가맹점 심층 분석': [
    'M0001 현황 분석해줘',
    'M0005 다음 달 매출 예측해줘',
    'M0010 이상 거래 패턴 탐지해줘',
    'M0003 성장 유형 분류하고 개선 방안 제시해줘',
    'M0020 최근 6개월 추이 분석해줘',
  ],
  '랭킹 & 비교': [
    '음식점 업종 Top 10 가맹점',
    '서울 지역 매출 상위 5개',
    '급성장 가맹점 Top 20',
    '재구매율 상위 10개 가맹점',
    '카페 업종 평균 지표 분석',
  ],
  '추천 시스템': [
    'C00055에게 추천할 가맹점 Top 10',
    'M0001과 유사한 가맹점 Top 10',
    'C00100 고객 맞춤 추천 5개',
    'M0025와 비슷한 업종 가맹점 추천',
  ],
  '용어 & 지표 설명': [
    'LTV/CAC가 뭐야?',
    '재구매율 설명해줘',
    '매출 성장률 계산 방법은?',
    '이상 탐지는 어떻게 작동해?',
    'SAR 추천 모델이란?',
  ],
  '종합 분석': [
    '전체 가맹점 목록 보여줘',
    '전체 업종별 평균 매출 비교',
    '하락 가맹점 현황 분석',
    '이번 달 주목할 만한 가맹점은?',
  ],
};

const DEFAULT_SETTINGS = {
  apiKey: '',
  selectedModel: 'gpt-4o',
  maxTokens: 4000,
  systemPrompt: '',
};

function formatTimestamp(d) {
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(
    d.getMinutes()
  )}:${pad(d.getSeconds())}`;
}

export default function AppPage() {
  const router = useRouter();

  const [auth, setAuth] = useState(null);
  const [merchants, setMerchants] = useState([]);
  const [industries, setIndustries] = useState([]);
  const [selectedMerchant, setSelectedMerchant] = useState(null);

  const [settings, setSettings] = useState(DEFAULT_SETTINGS);

  const [agentMessages, setAgentMessages] = useState([]);
  const [activityLog, setActivityLog] = useState([]);
  const [totalQueries, setTotalQueries] = useState(0);

  const [activeTab, setActiveTab] = useState('agent');

  const isAdmin = auth?.user_role === '관리자';

  const tabs = useMemo(() => {
    if (isAdmin) {
      return [
        { key: 'agent', label: 'AI 에이전트' },
        { key: 'dashboard', label: '대시보드' },
        { key: 'analysis', label: '분석' },
        { key: 'models', label: 'ML 모델' },
        { key: 'rag', label: 'RAG 문서' },
        { key: 'settings', label: 'LLM 설정' },
        { key: 'users', label: '사용자' },
        { key: 'logs', label: '로그' },
      ];
    }
    return [
      { key: 'agent', label: 'AI 에이전트' },
      { key: 'dashboard', label: '대시보드' },
      { key: 'analysis', label: '분석' },
    ];
  }, [isAdmin]);

  const apiCall = useCallback((args) => apiCallRaw(args), []);

  const addLog = useCallback(
    (action, detail) => {
      const row = {
        시간: formatTimestamp(new Date()),
        사용자: auth?.username || '-',
        작업: action,
        상세: detail,
      };
      setActivityLog((prev) => [...prev, row]);
    },
    [auth?.username]
  );

  // ✅ 안전 라우팅 헬퍼
  const safeReplace = useCallback(
    (path) => {
      if (!router.isReady) return;
      const cur = router.asPath || '';
      if (cur === path) return; // ✅ 같은 URL이면 이동 안 함
      router.replace(path);
    },
    [router]
  );

  const onLogout = useCallback(() => {
    removeFromSession(STORAGE_KEYS.AUTH);
    safeReplace('/login');
  }, [safeReplace]);

  const clearLog = useCallback(() => {
    setActivityLog([]);
  }, []);

  // ✅ 세션/스토리지 초기 로드 (router.isReady + safeReplace 적용)
  useEffect(() => {
    if (!router.isReady) return;

    const a = loadFromSession(STORAGE_KEYS.AUTH, null);
    if (!a?.username || !a?.password) {
      safeReplace('/login');
      return;
    }
    setAuth(a);

    const savedSettings = loadFromStorage(STORAGE_KEYS.SETTINGS, DEFAULT_SETTINGS);
    setSettings({ ...DEFAULT_SETTINGS, ...(savedSettings || {}) });

    setAgentMessages(loadFromStorage(STORAGE_KEYS.AGENT_MESSAGES, []));
    setActivityLog(loadFromStorage(STORAGE_KEYS.ACTIVITY_LOG, []));
    setTotalQueries(loadFromStorage(STORAGE_KEYS.TOTAL_QUERIES, 0));
  }, [router.isReady, safeReplace]);

  // ✅ 시스템 프롬프트 로드
  useEffect(() => {
    if (!auth?.username || !auth?.password) return;

    const cur = settings?.systemPrompt ? String(settings.systemPrompt).trim() : '';
    if (cur.length > 0) return;

    let mounted = true;

    async function loadDefaultPrompt() {
      try {
        const res = await apiCall({
          endpoint: '/api/settings/default',
          method: 'GET',
          auth,
          timeoutMs: 30000,
        });

        if (!mounted) return;

        const prompt = res?.system_prompt || res?.data?.system_prompt || '';
        const promptStr = String(prompt || '').trim();

        if (promptStr.length > 0) {
          setSettings((prev) => ({ ...prev, systemPrompt: promptStr }));
        }
      } catch (e) {}
    }

    loadDefaultPrompt();

    return () => {
      mounted = false;
    };
  }, [apiCall, auth, settings?.systemPrompt]);

  // ✅ 가맹점/업종 로드
  useEffect(() => {
    if (!auth?.username || !auth?.password) return;

    let mounted = true;

    async function loadMerchants() {
      const res = await apiCall({ endpoint: '/api/merchants', auth, timeoutMs: 30000 });
      if (!mounted) return;

      if (res?.status === 'SUCCESS' && Array.isArray(res.data)) {
        setMerchants(res.data);
        const ids = res.data.map((r) => r.merchant_id ?? r).filter(Boolean);
        if (!selectedMerchant && ids.length) setSelectedMerchant(ids[0]);
      } else {
        setMerchants([]);
      }
    }

    async function loadIndustries() {
      const res = await apiCall({ endpoint: '/api/industries', auth, timeoutMs: 30000 });
      if (!mounted) return;

      if (res?.status === 'SUCCESS' && Array.isArray(res.data)) setIndustries(res.data);
      else setIndustries([]);
    }

    loadMerchants();
    loadIndustries();

    return () => {
      mounted = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiCall, auth]);

  // ✅ 스토리지 저장
  useEffect(() => {
    saveToStorage(STORAGE_KEYS.SETTINGS, settings);
  }, [settings]);

  useEffect(() => {
    saveToStorage(STORAGE_KEYS.AGENT_MESSAGES, agentMessages);
  }, [agentMessages]);

  useEffect(() => {
    saveToStorage(STORAGE_KEYS.ACTIVITY_LOG, activityLog);
  }, [activityLog]);

  useEffect(() => {
    saveToStorage(STORAGE_KEYS.TOTAL_QUERIES, totalQueries);
  }, [totalQueries]);

  const onExampleQuestion = useCallback((q) => {
    setActiveTab('agent');
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('app_example_question', { detail: { q } }));
    }
  }, []);

  if (!auth) return null;

  return (
    <Layout
      auth={auth}
      merchants={merchants}
      industries={industries}
      selectedMerchant={selectedMerchant}
      setSelectedMerchant={setSelectedMerchant}
      exampleQuestions={EXAMPLE_QUESTIONS}
      onExampleQuestion={onExampleQuestion}
      onLogout={onLogout}
    >
      <div className="mb-3">
        <h1 className="text-2xl font-bold text-slate-900">LLM 기반 DEMO 웹앱</h1>
        <p className="text-sm text-slate-500">GPT + ML 기반 가맹점 분석 시스템</p>
      </div>

      <Tabs tabs={tabs} active={activeTab} onChange={setActiveTab} />

      {activeTab === 'agent' ? (
        <ExampleQuestionBridge>
          <AgentPanel
            auth={auth}
            selectedMerchant={selectedMerchant}
            addLog={addLog}
            settings={settings}
            setSettings={setSettings}
            agentMessages={agentMessages}
            setAgentMessages={setAgentMessages}
            totalQueries={totalQueries}
            setTotalQueries={setTotalQueries}
            apiCall={apiCall}
          />
        </ExampleQuestionBridge>
      ) : null}

      {activeTab === 'dashboard' ? (
        <DashboardPanel auth={auth} selectedMerchant={selectedMerchant} apiCall={apiCall} />
      ) : null}

      {activeTab === 'analysis' ? <AnalysisPanel auth={auth} apiCall={apiCall} /> : null}

      {activeTab === 'models' && isAdmin ? <ModelsPanel auth={auth} apiCall={apiCall} /> : null}

      {activeTab === 'rag' && isAdmin ? <RagPanel auth={auth} apiCall={apiCall} addLog={addLog} /> : null}

      {activeTab === 'settings' && isAdmin ? (
        <SettingsPanel settings={settings} setSettings={setSettings} addLog={addLog} />
      ) : null}

      {activeTab === 'users' && isAdmin ? <UsersPanel auth={auth} apiCall={apiCall} /> : null}

      {activeTab === 'logs' && isAdmin ? (
        <LogsPanel activityLog={activityLog} clearLog={clearLog} />
      ) : null}
    </Layout>
  );
}

function ExampleQuestionBridge({ children }) {
  useEffect(() => {
    function handler(ev) {
      const q = ev?.detail?.q;
      if (!q) return;
      window.dispatchEvent(new CustomEvent('app_send_question', { detail: { q } }));
    }
    window.addEventListener('app_example_question', handler);
    return () => window.removeEventListener('app_example_question', handler);
  }, []);

  return children;
}
