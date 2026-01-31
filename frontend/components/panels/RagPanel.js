// components/panels/RagPanel.js
import { useCallback, useEffect, useState } from 'react';
import { Upload, FileText, Trash2, RefreshCw, CheckCircle, XCircle, AlertCircle, Image, ScanText, Zap, GitBranch, Search, Network, Loader2 } from 'lucide-react';
import SectionHeader from '../SectionHeader';

export default function RagPanel({ auth, apiCall, addLog }) {
  const [files, setFiles] = useState([]);
  const [status, setStatus] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [selectedOcrFile, setSelectedOcrFile] = useState(null);
  const [ocrUploading, setOcrUploading] = useState(false);
  const [ocrResult, setOcrResult] = useState(null);
  const [graphRagBuilding, setGraphRagBuilding] = useState(false);

  // RAG 상태 로드
  const loadStatus = useCallback(async () => {
    if (!auth) return;
    setLoading(true);

    try {
      const res = await apiCall({
        endpoint: '/api/rag/status',
        method: 'GET',
        auth,
      });

      if (res?.status === 'SUCCESS') {
        setStatus(res);
      }
    } catch (e) {
      console.error('RAG 상태 로드 실패:', e);
    } finally {
      setLoading(false);
    }
  }, [apiCall, auth]);

  // 파일 목록 로드
  const loadFiles = useCallback(async () => {
    if (!auth) return;

    try {
      const res = await apiCall({
        endpoint: '/api/rag/files',
        method: 'GET',
        auth,
      });

      if (res?.status === 'SUCCESS' && Array.isArray(res.files)) {
        setFiles(res.files);
      }
    } catch (e) {
      console.error('파일 목록 로드 실패:', e);
    }
  }, [apiCall, auth]);

  // 초기 로드
  useEffect(() => {
    loadStatus();
    loadFiles();
  }, [loadStatus, loadFiles]);

  // 파일 업로드
  const handleFileUpload = useCallback(async () => {
    if (!selectedFile || !auth) return;

    setUploading(true);
    addLog?.('RAG 문서 업로드', selectedFile.name);

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);

      const base = process.env.NEXT_PUBLIC_API_BASE || '';
      const url = `${base}/api/rag/upload`;

      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Authorization': `Basic ${window.btoa(`${auth.username}:${auth.password}`)}`,
        },
        body: formData,
      });

      const result = await response.json();

      if (result.status === 'SUCCESS') {
        alert(`파일이 업로드되었습니다: ${result.filename}`);
        setSelectedFile(null);

        // 파일 목록 및 상태 새로고침
        await loadFiles();
        await loadStatus();
      } else {
        alert(`업로드 실패: ${result.error || '알 수 없는 오류'}`);
      }
    } catch (e) {
      alert(`업로드 실패: ${e.message}`);
    } finally {
      setUploading(false);
    }
  }, [selectedFile, auth, addLog, loadFiles, loadStatus]);

  // 파일 삭제
  const handleFileDelete = useCallback(async (filename) => {
    if (!confirm(`"${filename}" 파일을 삭제하시겠습니까?`)) return;
    if (!auth) return;

    addLog?.('RAG 문서 삭제', filename);

    try {
      const res = await apiCall({
        endpoint: '/api/rag/delete',
        method: 'POST',
        auth,
        data: { filename },
      });

      if (res?.status === 'SUCCESS') {
        alert('파일이 삭제되었습니다.');
        await loadFiles();
        await loadStatus();
      } else {
        alert(`삭제 실패: ${res.error || '알 수 없는 오류'}`);
      }
    } catch (e) {
      alert(`삭제 실패: ${e.message}`);
    }
  }, [apiCall, auth, addLog, loadFiles, loadStatus]);

  // OCR 업로드
  const handleOcrUpload = useCallback(async () => {
    if (!selectedOcrFile || !auth) return;

    setOcrUploading(true);
    setOcrResult(null);
    addLog?.('OCR 이미지 업로드', selectedOcrFile.name);

    try {
      const formData = new FormData();
      formData.append('file', selectedOcrFile);
      formData.append('save_to_rag', 'true');

      const base = process.env.NEXT_PUBLIC_API_BASE || '';
      const url = `${base}/api/ocr/extract`;

      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Authorization': `Basic ${window.btoa(`${auth.username}:${auth.password}`)}`,
        },
        body: formData,
      });

      const result = await response.json();

      if (result.status === 'SUCCESS') {
        setOcrResult(result);
        setSelectedOcrFile(null);
        await loadFiles();
        await loadStatus();
      } else {
        alert(`OCR 실패: ${result.error || '알 수 없는 오류'}`);
      }
    } catch (e) {
      alert(`OCR 실패: ${e.message}`);
    } finally {
      setOcrUploading(false);
    }
  }, [selectedOcrFile, auth, addLog, loadFiles, loadStatus]);

  // 인덱스 재빌드
  const handleReindex = useCallback(async () => {
    if (!confirm('RAG 인덱스를 재빌드하시겠습니까?')) return;
    if (!auth) return;

    addLog?.('RAG 인덱스 재빌드', '');
    setLoading(true);

    try {
      const res = await apiCall({
        endpoint: '/api/rag/reload',
        method: 'POST',
        auth,
        data: { force: true },
      });

      if (res?.status === 'SUCCESS') {
        alert('인덱스가 재빌드되었습니다.');
        await loadStatus();
      } else {
        alert(`재빌드 실패: ${res.error || '알 수 없는 오류'}`);
      }
    } catch (e) {
      alert(`재빌드 실패: ${e.message}`);
    } finally {
      setLoading(false);
    }
  }, [apiCall, auth, addLog, loadStatus]);

  // GraphRAG 빌드
  const handleGraphRagBuild = useCallback(async () => {
    if (!confirm('GraphRAG 지식 그래프를 빌드하시겠습니까?\n(LLM API 호출 비용이 발생합니다)')) return;
    if (!auth) return;

    addLog?.('GraphRAG 빌드', '');
    setGraphRagBuilding(true);

    try {
      const res = await apiCall({
        endpoint: '/api/graphrag/build',
        method: 'POST',
        auth,
        data: { maxChunks: 20 },
      });

      if (res?.status === 'SUCCESS') {
        alert(`GraphRAG 빌드가 시작되었습니다.\n${res.message}`);
        // 빌드 완료까지 주기적으로 상태 확인
        setTimeout(() => loadStatus(), 5000);
      } else {
        alert(`GraphRAG 빌드 실패: ${res.error || '알 수 없는 오류'}`);
      }
    } catch (e) {
      alert(`GraphRAG 빌드 실패: ${e.message}`);
    } finally {
      setGraphRagBuilding(false);
    }
  }, [apiCall, auth, addLog, loadStatus]);

  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
  };

  const formatDate = (isoString) => {
    try {
      const date = new Date(isoString);
      return date.toLocaleString('ko-KR', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="space-y-4">
      <SectionHeader title="RAG 문서 관리" subtitle="PDF 및 문서 업로드/관리" />

      {/* RAG 상태 */}
      <div className="rounded-3xl border border-slate-200 bg-white/70 p-5 shadow-sm backdrop-blur">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-black text-slate-900">RAG 시스템 상태</h3>
          <button
            onClick={loadStatus}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-2xl border border-slate-200 bg-white px-3 py-2 text-xs font-black text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            type="button"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            새로고침
          </button>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-4">
            <div className="flex items-center gap-2 mb-2">
              {status?.rag_ready ? (
                <CheckCircle size={18} className="text-green-600" />
              ) : (
                <XCircle size={18} className="text-red-600" />
              )}
              <span className="text-xs font-black text-slate-600">인덱스 상태</span>
            </div>
            <div className="text-lg font-black text-slate-900">
              {status?.rag_ready ? '준비됨' : '비활성'}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-4">
            <div className="flex items-center gap-2 mb-2">
              <FileText size={18} className="text-blue-600" />
              <span className="text-xs font-black text-slate-600">문서 수</span>
            </div>
            <div className="text-lg font-black text-slate-900">
              {status?.files_count || 0}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-4">
            <div className="flex items-center gap-2 mb-2">
              <FileText size={18} className="text-purple-600" />
              <span className="text-xs font-black text-slate-600">청크 수</span>
            </div>
            <div className="text-lg font-black text-slate-900">
              {status?.chunks_count || 0}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-4">
            <div className="flex items-center gap-2 mb-2">
              <AlertCircle size={18} className="text-amber-600" />
              <span className="text-xs font-black text-slate-600">임베딩 모델</span>
            </div>
            <div className="text-sm font-bold text-slate-900">
              {status?.embed_model || '-'}
            </div>
          </div>
        </div>

        {/* Advanced RAG Features */}
        <div className="mt-4 rounded-2xl border border-indigo-200 bg-indigo-50/50 p-4">
          <div className="flex items-center gap-2 mb-3">
            <Zap size={16} className="text-indigo-600" />
            <span className="text-xs font-black text-indigo-800">RAG 기능 동작 여부</span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {/* Hybrid Search (BM25 + Vector) */}
            <div className="flex items-center gap-2">
              <Search size={14} className={status?.bm25_ready ? 'text-green-600' : 'text-slate-400'} />
              <div>
                <div className="text-xs font-black text-slate-700">Hybrid Search</div>
                <div className="text-[10px] text-slate-500">
                  {status?.bm25_available ? (
                    status?.bm25_ready ? (
                      <span className="text-green-600">BM25 + Vector ✓</span>
                    ) : (
                      <span className="text-amber-600">BM25 대기중</span>
                    )
                  ) : (
                    <span className="text-slate-400">미설치</span>
                  )}
                </div>
              </div>
            </div>

            {/* Reranking */}
            <div className="flex items-center gap-2">
              <Zap size={14} className={status?.reranker_available ? 'text-green-600' : 'text-slate-400'} />
              <div>
                <div className="text-xs font-black text-slate-700">Reranking</div>
                <div className="text-[10px] text-slate-500">
                  {status?.reranker_available ? (
                    <span className="text-green-600">Cross-Encoder ✓</span>
                  ) : (
                    <span className="text-slate-400">미설치</span>
                  )}
                </div>
              </div>
            </div>

            {/* Simple Knowledge Graph */}
            <div className="flex items-center gap-2">
              <GitBranch size={14} className={status?.kg_ready ? 'text-green-600' : 'text-slate-400'} />
              <div>
                <div className="text-xs font-black text-slate-700">Simple KG</div>
                <div className="text-[10px] text-slate-500">
                  {status?.kg_ready ? (
                    <span className="text-green-600">
                      {status?.kg_entities_count || 0}개 엔티티
                    </span>
                  ) : (
                    <span className="text-slate-400">비활성</span>
                  )}
                </div>
              </div>
            </div>

            {/* GraphRAG (LLM 기반) */}
            <div className="flex items-center gap-2">
              <Network size={14} className={status?.graphrag_ready ? 'text-green-600' : 'text-slate-400'} />
              <div>
                <div className="text-xs font-black text-slate-700">GraphRAG</div>
                <div className="text-[10px] text-slate-500">
                  {status?.graphrag_available ? (
                    status?.graphrag_ready ? (
                      <span className="text-green-600">
                        {status?.graphrag_entities || 0}개 / {status?.graphrag_communities || 0}커뮤니티
                      </span>
                    ) : (
                      <span className="text-amber-600">빌드 필요</span>
                    )
                  ) : (
                    <span className="text-slate-400">미설치</span>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* GraphRAG 빌드 버튼 - 비용 발생으로 비활성화 */}
          {status?.graphrag_available && auth?.user_role === '관리자' && (
            <button
              disabled={true}
              className="mt-3 w-full rounded-xl border border-slate-300 bg-slate-100 px-3 py-2 text-xs font-black text-slate-400 cursor-not-allowed flex items-center justify-center gap-2"
              type="button"
              title="GraphRAG 빌드는 현재 비활성화되어 있습니다 (API 비용 절감)"
            >
              <Network size={14} />
              GraphRAG 빌드 (비활성화됨)
            </button>
          )}
        </div>

        {status?.error && (
          <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 p-3 text-xs font-semibold text-red-800">
            <strong>오류:</strong> {status.error}
          </div>
        )}

        <button
          onClick={handleReindex}
          disabled={loading}
          className="mt-4 w-full rounded-2xl border border-slate-300 bg-slate-100 px-4 py-2 text-sm font-black text-slate-700 hover:bg-slate-200 disabled:opacity-50"
          type="button"
        >
          <RefreshCw size={16} className="inline mr-2" />
          인덱스 재빌드
        </button>
      </div>

      {/* 파일 업로드 */}
      <div className="rounded-3xl border border-slate-200 bg-white/70 p-5 shadow-sm backdrop-blur">
        <h3 className="text-sm font-black text-slate-900 mb-4">문서 업로드</h3>

        <div className="space-y-3">
          <div className="rounded-2xl border-2 border-dashed border-slate-300 bg-slate-50/50 p-6 text-center">
            <Upload size={32} className="mx-auto mb-3 text-slate-400" />
            <input
              type="file"
              accept=".pdf,.txt,.md,.json,.csv,.log"
              onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
              className="hidden"
              id="file-upload"
            />
            <label
              htmlFor="file-upload"
              className="inline-flex items-center gap-2 rounded-2xl border border-slate-300 bg-white px-4 py-2 text-sm font-black text-slate-700 hover:bg-slate-50 cursor-pointer"
            >
              <Upload size={16} />
              파일 선택
            </label>

            {selectedFile && (
              <div className="mt-3 text-sm font-semibold text-slate-600">
                선택됨: <strong>{selectedFile.name}</strong> ({formatBytes(selectedFile.size)})
              </div>
            )}
          </div>

          <button
            onClick={handleFileUpload}
            disabled={!selectedFile || uploading}
            className="w-full rounded-2xl border border-slate-900 bg-slate-900 px-4 py-3 text-sm font-black text-white hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed"
            type="button"
          >
            {uploading ? '업로드 중...' : '업로드'}
          </button>

          <div className="text-xs font-semibold text-slate-500">
            지원 형식: PDF, TXT, MD, JSON, CSV, LOG (최대 10MB)
          </div>
        </div>
      </div>

      {/* OCR 업로드 */}
      <div className="rounded-3xl border border-slate-200 bg-white/70 p-5 shadow-sm backdrop-blur">
        <div className="flex items-center gap-2 mb-4">
          <ScanText size={18} className="text-purple-600" />
          <h3 className="text-sm font-black text-slate-900">OCR 이미지 업로드</h3>
          <span className="text-xs px-2 py-0.5 bg-purple-100 text-purple-700 rounded-full font-bold">NEW</span>
        </div>

        <div className="space-y-3">
          <div className="rounded-2xl border-2 border-dashed border-purple-300 bg-purple-50/50 p-6 text-center">
            <Image size={32} className="mx-auto mb-3 text-purple-400" />
            <input
              type="file"
              accept=".jpg,.jpeg,.png,.bmp,.tiff,.tif,.gif,.webp"
              onChange={(e) => setSelectedOcrFile(e.target.files?.[0] || null)}
              className="hidden"
              id="ocr-file-upload"
            />
            <label
              htmlFor="ocr-file-upload"
              className="inline-flex items-center gap-2 rounded-2xl border border-purple-300 bg-white px-4 py-2 text-sm font-black text-purple-700 hover:bg-purple-50 cursor-pointer"
            >
              <Image size={16} />
              이미지 선택
            </label>

            {selectedOcrFile && (
              <div className="mt-3 text-sm font-semibold text-purple-600">
                선택됨: <strong>{selectedOcrFile.name}</strong> ({formatBytes(selectedOcrFile.size)})
              </div>
            )}
          </div>

          <button
            onClick={handleOcrUpload}
            disabled={!selectedOcrFile || ocrUploading}
            className="w-full rounded-2xl border border-purple-600 bg-purple-600 px-4 py-3 text-sm font-black text-white hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
            type="button"
          >
            <ScanText size={16} className="inline mr-2" />
            {ocrUploading ? 'OCR 처리 중...' : 'OCR 추출 → RAG 저장'}
          </button>

          <div className="text-xs font-semibold text-slate-500">
            지원 형식: JPG, PNG, BMP, TIFF, GIF, WEBP (최대 20MB) • 한국어/영어 지원
          </div>
        </div>

        {/* OCR 결과 */}
        {ocrResult && (
          <div className="mt-4 rounded-2xl border border-green-200 bg-green-50 p-4">
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle size={16} className="text-green-600" />
              <span className="text-sm font-black text-green-800">OCR 추출 완료</span>
            </div>
            <div className="text-xs font-semibold text-green-700 mb-2">
              파일: {ocrResult.rag_filename} • {ocrResult.text_length}자 추출
            </div>
            <div className="rounded-xl border border-green-200 bg-white p-3 max-h-40 overflow-y-auto">
              <pre className="text-xs text-slate-700 whitespace-pre-wrap font-mono">
                {ocrResult.extracted_text?.slice(0, 500)}
                {ocrResult.extracted_text?.length > 500 && '...'}
              </pre>
            </div>
          </div>
        )}
      </div>

      {/* 파일 목록 */}
      <div className="rounded-3xl border border-slate-200 bg-white/70 p-5 shadow-sm backdrop-blur">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-black text-slate-900">업로드된 문서</h3>
          <span className="text-xs font-black text-slate-500">{files.length}개</span>
        </div>

        {files.length === 0 ? (
          <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 text-center text-sm font-semibold text-slate-500">
            업로드된 문서가 없습니다
          </div>
        ) : (
          <div className="space-y-2">
            {files.map((file) => (
              <div
                key={file.filename}
                className="flex items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white p-3 hover:shadow-sm transition"
              >
                <div className="flex items-center gap-3 min-w-0 flex-1">
                  <FileText size={20} className="text-blue-600 flex-shrink-0" />
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-bold text-slate-900 truncate">{file.filename}</div>
                    <div className="text-xs font-semibold text-slate-500">
                      {formatBytes(file.size)} • {formatDate(file.modified)}
                    </div>
                  </div>
                </div>

                {auth?.user_role === '관리자' && (
                  <button
                    onClick={() => handleFileDelete(file.filename)}
                    className="flex-shrink-0 rounded-xl border border-red-200 bg-red-50 p-2 text-red-600 hover:bg-red-100"
                    title="삭제"
                    type="button"
                  >
                    <Trash2 size={16} />
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
