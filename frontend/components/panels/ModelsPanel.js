import { useEffect, useState } from 'react';

export default function ModelsPanel({ auth, apiCall }) {
  const [mlflowData, setMlflowData] = useState([]);
  const [registeredModels, setRegisteredModels] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selecting, setSelecting] = useState(null);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    let mounted = true;
    async function load() {
      setLoading(true);

      // Load MLflow experiments
      const mlflowRes = await apiCall({ endpoint: '/api/mlflow/experiments', auth, timeoutMs: 30000 });
      if (!mounted) return;
      if (mlflowRes?.status === 'SUCCESS' && mlflowRes.data) setMlflowData(mlflowRes.data);
      else setMlflowData([]);

      // Load registered models
      const modelsRes = await apiCall({ endpoint: '/api/mlflow/models', auth, timeoutMs: 30000 });
      if (!mounted) return;
      if (modelsRes?.status === 'SUCCESS' && modelsRes.data) setRegisteredModels(modelsRes.data);
      else setRegisteredModels([]);

      setLoading(false);
    }
    load();
    return () => { mounted = false; };
  }, [auth, apiCall]);

  const formatTimestamp = (ts) => {
    if (!ts) return '-';
    const date = new Date(ts);
    return date.toLocaleString('ko-KR');
  };

  const handleSelectModel = async (modelName, version) => {
    setSelecting(`${modelName}-${version}`);
    setMessage(null);

    const res = await apiCall({
      endpoint: '/api/mlflow/models/select',
      auth,
      method: 'POST',
      data: { model_name: modelName, version: String(version) },
      timeoutMs: 30000,
    });

    setSelecting(null);

    if (res?.status === 'SUCCESS') {
      setMessage({ type: 'success', text: res.message });
    } else {
      setMessage({ type: 'error', text: res?.error || '모델 로드 실패' });
    }

    setTimeout(() => setMessage(null), 5000);
  };

  return (
    <div>
      <div className="flex items-end justify-between gap-3 mb-4">
        <div>
          <h2 className="text-lg md:text-xl font-semibold text-slate-900">MLflow 모델 관리</h2>
          <p className="text-sm text-slate-500">모델 학습 실험 기록 및 버전 관리</p>
        </div>
        {loading ? <span className="badge">Loading</span> : null}
      </div>

      {message && (
        <div className={`mb-4 p-3 rounded text-sm ${
          message.type === 'success' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
        }`}>
          {message.text}
        </div>
      )}

      {/* Model Registry Section */}
      {registeredModels.length > 0 && (
        <div className="mb-6">
          <h3 className="text-md font-semibold text-slate-800 mb-3">Model Registry</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {registeredModels.map((model) => (
              <div key={model.name} className="card">
                <div className="card-header text-sm flex items-center justify-between">
                  <span>{model.name}</span>
                  {model.model_type === 'artifact' && (
                    <span className="text-xs px-2 py-0.5 bg-purple-100 text-purple-700 rounded">
                      Artifact
                    </span>
                  )}
                </div>
                <div className="text-xs text-slate-500 mb-2">
                  {model.description || '설명 없음'}
                </div>
                <div className="space-y-2">
                  {model.versions.map((v) => (
                    <div key={v.version} className="flex items-center justify-between p-2 bg-slate-50 rounded">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium">v{v.version}</span>
                        <span className={`text-xs px-2 py-0.5 rounded ${
                          v.stage === 'Production' ? 'bg-green-100 text-green-700' :
                          v.stage === 'Staging' ? 'bg-yellow-100 text-yellow-700' :
                          'bg-gray-100 text-gray-600'
                        }`}>
                          {v.stage || 'None'}
                        </span>
                      </div>
                      <button
                        onClick={() => handleSelectModel(model.name, v.version)}
                        disabled={selecting === `${model.name}-${v.version}`}
                        className="text-xs px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
                      >
                        {selecting === `${model.name}-${v.version}` ? '로딩...' : '선택'}
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Experiments Section */}
      <h3 className="text-md font-semibold text-slate-800 mb-3">실험 기록</h3>
      {mlflowData.length ? mlflowData.map((exp) => (
        <div key={exp.experiment_id} className="card mb-4">
          <div className="card-header flex justify-between items-center">
            <span>{exp.name}</span>
            <span className={`text-xs px-2 py-1 rounded ${
              exp.lifecycle_stage === 'active' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
            }`}>
              {exp.lifecycle_stage}
            </span>
          </div>

          {exp.runs && exp.runs.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200">
                    <th className="text-left py-2 px-2 text-slate-600 font-medium">Run Name</th>
                    <th className="text-left py-2 px-2 text-slate-600 font-medium">Status</th>
                    <th className="text-left py-2 px-2 text-slate-600 font-medium">시작 시간</th>
                    <th className="text-left py-2 px-2 text-slate-600 font-medium">Metrics</th>
                    <th className="text-left py-2 px-2 text-slate-600 font-medium">Params</th>
                  </tr>
                </thead>
                <tbody>
                  {exp.runs.map((run) => (
                    <tr key={run.run_id} className="border-b border-slate-100 hover:bg-slate-50">
                      <td className="py-2 px-2 font-medium text-slate-900">
                        {run.run_name || run.run_id.slice(0, 8)}
                      </td>
                      <td className="py-2 px-2">
                        <span className={`text-xs px-2 py-1 rounded ${
                          run.status === 'FINISHED' ? 'bg-green-100 text-green-700' :
                          run.status === 'RUNNING' ? 'bg-blue-100 text-blue-700' :
                          run.status === 'FAILED' ? 'bg-red-100 text-red-700' :
                          'bg-gray-100 text-gray-600'
                        }`}>
                          {run.status}
                        </span>
                      </td>
                      <td className="py-2 px-2 text-slate-600 text-xs">
                        {formatTimestamp(run.start_time)}
                      </td>
                      <td className="py-2 px-2">
                        <div className="flex flex-wrap gap-1">
                          {Object.entries(run.metrics || {}).map(([k, v]) => (
                            <span key={k} className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded">
                              {k}: {v}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="py-2 px-2">
                        <div className="flex flex-wrap gap-1">
                          {Object.entries(run.params || {}).slice(0, 3).map(([k, v]) => (
                            <span key={k} className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded">
                              {k}: {v}
                            </span>
                          ))}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-sm text-slate-500 py-4">
              실험 기록이 없습니다.
            </div>
          )}
        </div>
      )) : (
        <div className="card text-sm text-slate-600">
          <p>MLflow 실험이 없습니다.</p>
          <p className="mt-2 text-slate-500">
            노트북을 실행하여 모델을 학습하세요.
          </p>
        </div>
      )}
    </div>
  );
}
