export function getApiBase() {
  // ✅ 중요: 외부 접속에서도 동작하게 기본값을 '같은 오리진'으로 둠
  // - 로컬 개발에서 백엔드가 다른 호스트/포트면 NEXT_PUBLIC_API_BASE를 지정
  //   예) NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000
  const base = process.env.NEXT_PUBLIC_API_BASE || '';
  return String(base).replace(/\/$/, '');
}

export function makeBasicAuthHeader(username, password) {
  if (typeof window === 'undefined') return '';
  const token = window.btoa(`${username}:${password}`);
  return `Basic ${token}`;
}

export async function apiCall({
  endpoint,
  method = 'GET',
  data = null,
  auth = null,
  timeoutMs = 60000,
  headers = {},
  responseType = 'json',
}) {
  const controller = new AbortController();
  const t = setTimeout(() => controller.abort(), timeoutMs);

  const base = getApiBase();
  const url = `${base}${endpoint}`;

  const init = {
    method,
    signal: controller.signal,
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
  };

  if (auth?.username && auth?.password) {
    init.headers['Authorization'] = makeBasicAuthHeader(auth.username, auth.password);
  }

  if (method !== 'GET' && method !== 'HEAD' && data !== null) {
    init.body = JSON.stringify(data);
  }

  try {
    const resp = await fetch(url, init);
    clearTimeout(t);

    if (responseType === 'blob') {
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      return await resp.blob();
    }

    const json = await resp.json().catch(() => ({}));
    return json;
  } catch (e) {
    clearTimeout(t);
    return { status: 'FAILED', error: String(e?.message || e) };
  }
}
