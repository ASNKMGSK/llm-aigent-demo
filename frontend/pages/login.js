import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { apiCall } from '@/lib/api';
import { saveToSession, loadFromSession, STORAGE_KEYS } from '@/lib/storage';

const pastelPrimary =
  'w-full rounded-2xl border border-slate-200/70 bg-gradient-to-r from-sky-200 via-indigo-200 to-rose-200 px-4 py-3 text-sm font-extrabold text-slate-800 shadow-sm transition hover:from-sky-300 hover:via-indigo-300 hover:to-rose-300 active:translate-y-[1px] disabled:opacity-60 disabled:cursor-not-allowed';

const pastelGhost =
  'w-full rounded-2xl border border-slate-200/70 bg-white/70 px-4 py-3 text-sm font-extrabold text-slate-800 shadow-sm transition hover:bg-white active:translate-y-[1px] disabled:opacity-60 disabled:cursor-not-allowed';

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState('');

  useEffect(() => {
    const auth = loadFromSession(STORAGE_KEYS.AUTH, null);
    if (auth?.username && auth?.password) router.replace('/app');
  }, [router]);

  async function onLogin() {
    setErr('');
    setLoading(true);

    const res = await apiCall({
      endpoint: '/api/login',
      method: 'POST',
      auth: { username, password },
      timeoutMs: 30000,
    });

    setLoading(false);

    if (res?.status === 'SUCCESS') {
      const auth = {
        username,
        password,
        user_name: res.user_name,
        user_role: res.user_role,
      };
      saveToSession(STORAGE_KEYS.AUTH, auth);
      router.replace('/app');
    } else {
      setErr('아이디 또는 비밀번호가 틀렸습니다');
    }
  }

  function fillAdmin() {
    setUsername('admin');
    setPassword('admin123');
  }
  function fillTest() {
    setUsername('test');
    setPassword('test');
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4 bg-gradient-to-br from-sky-50 via-white to-rose-50">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="text-4xl mb-2">💳</div>
          <h1 className="text-xl font-extrabold text-slate-900">LLM 기반 DEMO 웹앱</h1>
          <p className="text-sm text-slate-500">데이터 분석 플랫폼</p>
        </div>

        <div className="card border border-slate-200/70 bg-white/70 backdrop-blur">
          <div className="space-y-3">
            <div>
              <label className="text-sm font-bold text-slate-700">아이디</label>
              <input
                className="input mt-1"
                placeholder="아이디"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
              />
            </div>

            <div>
              <label className="text-sm font-bold text-slate-700">비밀번호</label>
              <input
                className="input mt-1"
                placeholder="비밀번호"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') onLogin();
                }}
              />
            </div>

            {err ? (
              <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm font-bold text-red-700">
                {err}
              </div>
            ) : null}

            <button className={pastelPrimary} onClick={onLogin} disabled={loading || !username || !password} type="button">
              {loading ? '로그인 중...' : '로그인'}
            </button>

            <details className="details">
              <summary>테스트 계정</summary>
              <div className="mt-3 grid grid-cols-2 gap-2">
                <button className={pastelGhost} type="button" onClick={fillAdmin}>
                  관리자 입력
                </button>
                <button className={pastelGhost} type="button" onClick={fillTest}>
                  사용자 입력
                </button>

                <div className="col-span-2 rounded-xl border border-slate-200/70 bg-white/60 p-3 text-sm text-slate-700">
                  <div>
                    관리자: <span className="font-mono font-bold">admin</span> / <span className="font-mono font-bold">admin123</span>
                  </div>
                  <div className="mt-1">
                    사용자: <span className="font-mono font-bold">test</span> / <span className="font-mono font-bold">test</span>
                  </div>
                </div>
              </div>
            </details>
          </div>
        </div>

        <div className="mt-4 text-center text-xs text-slate-400">
          © LLM Fintech · Internal Tools
        </div>
      </div>
    </div>
  );
}
