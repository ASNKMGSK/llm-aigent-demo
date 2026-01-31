// components/panels/DashboardPanel.js
import { useEffect, useMemo, useState } from 'react';
import dynamic from 'next/dynamic';
import toast from 'react-hot-toast';
import KpiCard from '@/components/KpiCard';
import EmptyState from '@/components/EmptyState';
import { SkeletonCard } from '@/components/Skeleton';
import { Wallet, TrendingUp, Repeat, Ratio } from 'lucide-react';
import SectionHeader from '@/components/SectionHeader';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

const PLOT_CONFIG = {
  displayModeBar: false,
  responsive: true,
  scrollZoom: false,
  doubleClick: false,
  staticPlot: false,
};

export default function DashboardPanel({ auth, selectedMerchant, apiCall }) {
  const [metrics, setMetrics] = useState([]);
  const [loading, setLoading] = useState(false);
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
    if (!selectedMerchant) return;

    let mounted = true;

    async function load() {
      setLoading(true);
      const res = await apiCall({
        endpoint: `/api/merchants/${selectedMerchant}/metrics`,
        auth,
        timeoutMs: 30000,
      });
      setLoading(false);

      if (!mounted) return;

      if (res?.status === 'SUCCESS' && Array.isArray(res.data)) {
        setMetrics(res.data);
      } else {
        setMetrics([]);
        toast.error('대시보드 데이터를 불러오지 못했습니다');
      }
    }

    load();
    return () => {
      mounted = false;
    };
  }, [auth, apiCall, selectedMerchant]);

  const latest = useMemo(() => {
    if (!metrics?.length) return null;
    return metrics[metrics.length - 1];
  }, [metrics]);

  const chartH = isMobile ? 320 : 340;

  const months = useMemo(() => (metrics || []).map((r) => r.txn_month), [metrics]);
  const revenues = useMemo(() => (metrics || []).map((r) => Number(r.total_revenue ?? 0)), [metrics]);

  const last6 = useMemo(() => (metrics || []).slice(-6), [metrics]);
  const last6Months = useMemo(() => (last6 || []).map((r) => r.txn_month), [last6]);
  const last6Txn = useMemo(() => (last6 || []).map((r) => Number(r.txn_count ?? 0)), [last6]);

  const baseLayout = useMemo(
    () => ({
      height: chartH,
      margin: { t: 8, b: 56, l: 56, r: 16 },
      paper_bgcolor: 'rgba(255,255,255,0)',
      plot_bgcolor: 'rgba(255,255,255,0)',
      font: { family: 'ui-sans-serif', size: 12, color: 'rgb(51,65,85)' },
      hovermode: 'x unified',
      showlegend: false,
      dragmode: false,
      uirevision: 'keep',
      xaxis: {
        tickfont: { size: 11 },
        tickangle: -25,
        automargin: true,
        showgrid: false,
        zeroline: false,
        showline: true,
        linewidth: 1,
        linecolor: 'rgba(148,163,184,0.45)',
        fixedrange: true,
      },
      yaxis: {
        tickfont: { size: 11 },
        automargin: true,
        showgrid: true,
        gridcolor: 'rgba(148,163,184,0.22)',
        zeroline: false,
        showline: false,
        fixedrange: true,
      },
      hoverlabel: {
        font: { size: 12, family: 'ui-sans-serif' },
        bgcolor: 'rgba(255,255,255,0.92)',
        bordercolor: 'rgba(148,163,184,0.45)',
      },
    }),
    [chartH]
  );

  const revenueLayout = useMemo(
    () => ({
      ...baseLayout,
      yaxis: {
        ...baseLayout.yaxis,
        tickformat: ',.0f',
        separatethousands: true,
      },
    }),
    [baseLayout]
  );

  const txnLayout = useMemo(
    () => ({
      ...baseLayout,
      yaxis: {
        ...baseLayout.yaxis,
        tickformat: ',.0f',
        separatethousands: true,
      },
      bargap: 0.35,
    }),
    [baseLayout]
  );

  return (
    <div>
      <SectionHeader
        title={`${selectedMerchant || '-'} 대시보드`}
        subtitle="월별 매출/거래 지표 요약"
        right={
          latest ? (
            <span className="rounded-full border border-white/60 bg-white/70 px-2 py-1 text-[10px] font-black text-slate-600">
              UPDATED
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

      {latest ? (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
            <KpiCard
              title="월 매출"
              value={`${Number(latest.total_revenue || 0).toLocaleString()}원`}
              subtitle={`성장률: ${latest.revenue_growth_rate ?? '-'}%`}
              icon={<Wallet size={18} className="text-slate-800" />}
              tone="violet"
            />
            <KpiCard
              title="성장률"
              value={`${latest.revenue_growth_rate ?? '-'}%`}
              subtitle="전월 대비"
              icon={<TrendingUp size={18} className="text-slate-800" />}
              tone="mint"
            />
            <KpiCard
              title="재구매율"
              value={`${latest.repeat_purchase_rate ?? '-'}%`}
              subtitle="최근 월 기준"
              icon={<Repeat size={18} className="text-slate-800" />}
              tone="peach"
            />
            <KpiCard
              title="LTV/CAC"
              value={`${latest.ltv_cac_ratio ?? '-'}`}
              subtitle="수익/비용 비율"
              icon={<Ratio size={18} className="text-slate-800" />}
              tone="sky"
            />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="rounded-3xl border border-white/60 bg-white/55 p-4 shadow-sm backdrop-blur">
              <div className="mb-2 text-sm font-black text-slate-800">월별 매출</div>
              <Plot
                data={[
                  {
                    x: months,
                    y: revenues,
                    type: 'scatter',
                    mode: 'lines+markers',
                    line: { width: 2 },
                    marker: { size: 5 },
                    hovertemplate: '%{x}<br>매출: %{y:,.0f}원<extra></extra>',
                  },
                ]}
                layout={revenueLayout}
                config={PLOT_CONFIG}
                style={{ width: '100%' }}
              />
            </div>

            <div className="rounded-3xl border border-white/60 bg-white/55 p-4 shadow-sm backdrop-blur">
              <div className="mb-2 text-sm font-black text-slate-800">거래 건수 (최근 6개월)</div>
              <Plot
                data={[
                  {
                    x: last6Months,
                    y: last6Txn,
                    type: 'bar',
                    hovertemplate: '%{x}<br>거래건수: %{y:,.0f}<extra></extra>',
                  },
                ]}
                layout={txnLayout}
                config={PLOT_CONFIG}
                style={{ width: '100%' }}
              />
            </div>
          </div>
        </>
      ) : (
        <EmptyState title="데이터가 없습니다" desc="해당 가맹점의 월별 지표가 아직 없어요." />
      )}
    </div>
  );
}
