/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    const backendBase = process.env.BACKEND_INTERNAL_URL || 'http://127.0.0.1:8000';
    const backend = String(backendBase).replace(/\/$/, '');

    return [
      // ✅ 1) 스트리밍은 Next API Route(= pages/api/agent/stream.js)로 처리
      { source: '/api/agent/stream', destination: '/api/agent/stream' },

      // ✅ 2) 나머지 /api/* 는 전부 백엔드로 프록시 → 브라우저는 항상 같은 오리진만 호출
      { source: '/api/:path*', destination: `${backend}/api/:path*` },
    ];
  },
};

module.exports = nextConfig;
