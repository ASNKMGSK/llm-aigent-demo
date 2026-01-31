import { useEffect, useMemo, useState } from 'react';
import dynamic from 'next/dynamic';
import toast from 'react-hot-toast';
import KpiCard from '@/components/KpiCard';
import EmptyState from '@/components/EmptyState';
import { SkeletonCard } from '@/components/Skeleton';
import { Store, Database, Coins, Activity } from 'lucide-react';
import SectionHeader from '@/components/SectionHeader';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

export default function AnalysisPanel({ auth, apiCall }) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    function onResize() {
      setIsMobile(window.innerWidth < 768);
    }
    onResize();
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  useEffect(() => {
    let mounted = true;

    async function load() {
      setLoading(true);
      const res = await apiCall({ endpoint: '/api/stats/summary', auth, timeoutMs: 30000 });
      setLoading(false);

      if (!mounted) return;

      if (res?.status === 'SUCCESS') {
        setStats(res);
      } else {
        setStats(null);
        toast.error('통계 데이터를 불러오지 못했습니다');
      }
    }

    load();
    return () => {
      mounted = false;
    };
  }, [auth, apiCall]);

  const industryData = useMemo(() => {
    if (!stats?.industry_stats) return [];
    return Object.entries(stats.industry_stats).map(([k, v]) => ({ 업종: k, 매출: v }));
  }, [stats]);

  const regionData = useMemo(() => {
    if (!stats?.region_stats) return [];
    return Object.entries(stats.region_stats).map(([k, v]) => ({ 지역: k, 매출: v }));
  }, [stats]);

  async function downloadFile(type) {
    setDownloading(true);
    toast.loading('다운로드 준비 중...', { id: 'dl' });

    try {
      const endpoint = type === 'excel' ? '/api/export/excel' : '/api/export/csv';
      const blob = await apiCall({ endpoint, auth, responseType: 'blob', timeoutMs: 60000 });

      const now = new Date();
      const yyyy = now.getFullYear();
      const mm = String(now.getMonth() + 1).padStart(2, '0');
      const dd = String(now.getDate()).padStart(2, '0');
      const filename = type === 'excel' ? `data_${yyyy}${mm}${dd}.xlsx` : `data_${yyyy}${mm}${dd}.csv`;

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);

      toast.success('다운로드 시작', { id: 'dl' });
    } catch (e) {
      toast.error('다운로드 실패', { id: 'dl' });
    } finally {
      setDownloading(false);
    }
  }

  const chartH = isMobile ? 320 : 360;

  return (
    <div>
      <SectionHeader
        title="종합 분석"
        subtitle="전체 가맹점/업종/지역 지표 요약"
        right={
          stats?.status === 'SUCCESS' ? (
            <span className="rounded-full border border-white/60 bg-white/70 px-2 py-1 text-[10px] font-black text-slate-600">
              LIVE
            </span>
          ) : null
        }
      />

      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      ) : null}

      {stats?.status === 'SUCCESS' ? (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
            <KpiCard
              title="가맹점"
              value={`${stats.merchant_count ?? '-'}개`}
              icon={<Store size={18} className="text-slate-800" />}
              tone="violet"
            />
            <KpiCard
              title="데이터"
              value={`${Number(stats.data_count || 0).toLocaleString()}건`}
              icon={<Database size={18} className="text-slate-800" />}
              tone="sky"
            />
            <KpiCard
              title="총 매출"
              value={stats.total_revenue != null ? `${(Number(stats.total_revenue) / 1e8).toFixed(1)}억` : '-'}
              icon={<Coins size={18} className="text-slate-800" />}
              tone="mint"
            />
            <KpiCard
              title="평균 성장률"
              value={`${stats.avg_growth_rate ?? '-'}%`}
              icon={<Activity size={18} className="text-slate-800" />}
              tone="peach"
            />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="rounded-3xl border border-white/60 bg-white/55 p-4 shadow-sm backdrop-blur">
              <div className="mb-2 text-sm font-black text-slate-800">업종별 평균 매출</div>
              <Plot
                data={[
                  {
                    labels: industryData.map((r) => r.업종),
                    values: industryData.map((r) => r.매출),
                    type: 'pie',
                  },
                ]}
                layout={{
                  height: chartH,
                  margin: { t: 10, b: 10, l: 10, r: 10 },
                  paper_bgcolor: 'rgba(255,255,255,0)',
                  font: { family: 'ui-sans-serif' },
                }}
                config={{ displayModeBar: false, responsive: true }}
                style={{ width: '100%' }}
              />
            </div>

            <div className="rounded-3xl border border-white/60 bg-white/55 p-4 shadow-sm backdrop-blur">
              <div className="mb-2 text-sm font-black text-slate-800">지역별 평균 매출</div>
              <Plot
                data={[
                  {
                    x: regionData.map((r) => r.지역),
                    y: regionData.map((r) => r.매출),
                    type: 'bar',
                  },
                ]}
                layout={{
                  height: chartH,
                  margin: { t: 10, b: 70, l: 48, r: 16 },
                  paper_bgcolor: 'rgba(255,255,255,0)',
                  plot_bgcolor: 'rgba(255,255,255,0)',
                  font: { family: 'ui-sans-serif' },
                }}
                config={{ displayModeBar: false, responsive: true }}
                style={{ width: '100%' }}
              />
            </div>
          </div>

          <div className="mt-4 rounded-3xl border border-white/60 bg-white/55 p-4 shadow-sm backdrop-blur">
            <div className="mb-2 text-sm font-black text-slate-800">데이터 다운로드</div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              <button
                className="rounded-2xl border border-white/60 bg-white/70 px-4 py-3 text-sm font-black text-slate-700 shadow-sm hover:bg-white active:translate-y-[1px] disabled:opacity-60"
                onClick={() => downloadFile('excel')}
                disabled={downloading}
                type="button"
              >
                Excel 다운로드
              </button>
              <button
                className="rounded-2xl border border-white/60 bg-white/70 px-4 py-3 text-sm font-black text-slate-700 shadow-sm hover:bg-white active:translate-y-[1px] disabled:opacity-60"
                onClick={() => downloadFile('csv')}
                disabled={downloading}
                type="button"
              >
                CSV 다운로드
              </button>
            </div>
          </div>
        </>
      ) : (
        <EmptyState title="통계 데이터를 불러오지 못했습니다" desc="(외부 접속이면) API_BASE 기본값을 수정해야 합니다." />
      )}
    </div>
  );
}
