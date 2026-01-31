export default function LogsPanel({ activityLog, clearLog }) {
  return (
    <div>
      <div className="flex items-end justify-between gap-3 mb-3">
        <div>
          <h2 className="text-lg md:text-xl font-semibold text-slate-900">활동 로그</h2>
          <p className="text-sm text-slate-500">클라이언트 측 로그(세션 저장)</p>
        </div>
      </div>

      {activityLog?.length ? (
        <div className="card">
          <div className="card-header">로그</div>
          <div className="overflow-auto">
            <table className="table">
              <thead>
                <tr>
                  <th>시간</th>
                  <th>사용자</th>
                  <th>작업</th>
                  <th>상세</th>
                </tr>
              </thead>
              <tbody>
                {activityLog.slice().reverse().map((r, idx) => (
                  <tr key={idx}>
                    <td>{r['시간']}</td>
                    <td>{r['사용자']}</td>
                    <td>{r['작업']}</td>
                    <td>{r['상세']}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <button className="btn-secondary w-full rounded-lg px-4 py-2 text-sm mt-3" onClick={clearLog}>
            로그 초기화
          </button>
        </div>
      ) : (
        <div className="card text-sm text-slate-600">로그 없음</div>
      )}
    </div>
  );
}
