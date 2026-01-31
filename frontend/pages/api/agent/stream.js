export const config = {
  api: {
    bodyParser: false,
    responseLimit: false,
    externalResolver: true,
  },
};

export default async function handler(req, res) {
  // ✅ 혹시 모를 OPTIONS 대응 (환경 따라 필요)
  if (req.method === 'OPTIONS') {
    res.statusCode = 204;
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Headers', 'authorization, content-type, accept');
    res.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
    res.end();
    return;
  }

  const target = 'http://127.0.0.1:8000/api/agent/stream';

  try {
    const headers = {
      'content-type': req.headers['content-type'] || 'application/json',
      'authorization': req.headers['authorization'] || '',
      'accept': 'text/event-stream',
      'cache-control': 'no-cache',
      'connection': 'keep-alive',
    };

    const init = {
      method: req.method,
      headers,
    };

    // ✅ Node fetch(undici)에서 stream body 보내면 duplex 필수
    if (req.method !== 'GET' && req.method !== 'HEAD') {
      init.body = req;           // 원본 바디 그대로 전달
      init.duplex = 'half';      // ✅ 이거 없으면 Node 24에서 500 나기 쉬움
    }

    const upstream = await fetch(target, init);

    res.statusCode = upstream.status;

    res.setHeader(
      'Content-Type',
      upstream.headers.get('content-type') || 'text/event-stream; charset=utf-8'
    );
    res.setHeader('Cache-Control', 'no-cache, no-transform');
    res.setHeader('Connection', 'keep-alive');
    res.setHeader('X-Accel-Buffering', 'no');
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Headers', 'authorization, content-type, accept');
    res.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');

    if (typeof res.flushHeaders === 'function') res.flushHeaders();

    if (!upstream.body) {
      res.end();
      return;
    }

    const reader = upstream.body.getReader();

    req.on('close', () => {
      try { reader.cancel(); } catch (e) {}
      try { res.end(); } catch (e) {}
    });

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      if (value) res.write(Buffer.from(value));
    }

    res.end();
  } catch (e) {
    console.error('[stream proxy error]', e);
    res.statusCode = 500;
    res.setHeader('Content-Type', 'application/json; charset=utf-8');
    res.end(JSON.stringify({ status: 'FAILED', error: String(e?.message || e) }));
  }
}
