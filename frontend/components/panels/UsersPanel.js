import { useEffect, useState } from 'react';

export default function UsersPanel({ auth, apiCall }) {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);

  const [newId, setNewId] = useState('');
  const [newName, setNewName] = useState('');
  const [newPw, setNewPw] = useState('');
  const [newRole, setNewRole] = useState('사용자');
  const [msg, setMsg] = useState('');

  async function loadUsers() {
    setLoading(true);
    const res = await apiCall({ endpoint: '/api/users', auth, timeoutMs: 30000 });
    setLoading(false);
    if (res?.status === 'SUCCESS' && Array.isArray(res.data)) setUsers(res.data);
    else setUsers([]);
  }

  useEffect(() => {
    loadUsers();
  }, []);

  async function addUser() {
    setMsg('');
    if (!newId || !newName || !newPw) return;

    const res = await apiCall({
      endpoint: '/api/users',
      method: 'POST',
      auth,
      data: { user_id: newId, name: newName, password: newPw, role: newRole },
      timeoutMs: 30000,
    });

    if (res?.status === 'SUCCESS') {
      setMsg(`${newName} 추가됨`);
      setNewId('');
      setNewName('');
      setNewPw('');
      setNewRole('사용자');
      await loadUsers();
    } else {
      setMsg('추가 실패');
    }
  }

  return (
    <div>
      <div className="flex items-end justify-between gap-3 mb-3">
        <div>
          <h2 className="text-lg md:text-xl font-semibold text-slate-900">사용자 관리</h2>
          <p className="text-sm text-slate-500">계정 목록 확인 및 추가</p>
        </div>
      </div>

      <div className="card mb-4">
        <div className="card-header">사용자 목록</div>
        {loading ? <div className="text-sm text-slate-500">로딩 중...</div> : null}
        <div className="overflow-auto">
          <table className="table">
            <thead>
              <tr>
                {users?.length ? Object.keys(users[0]).map((k) => (
                  <th key={k}>{k}</th>
                )) : <th>-</th>}
              </tr>
            </thead>
            <tbody>
              {users?.length ? users.map((u, idx) => (
                <tr key={idx}>
                  {Object.keys(users[0]).map((k) => (
                    <td key={k}>{String(u[k])}</td>
                  ))}
                </tr>
              )) : (
                <tr><td className="py-3 text-slate-600">데이터 없음</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <div className="card-header">사용자 추가</div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <div>
            <label className="text-sm text-slate-600">아이디</label>
            <input className="input mt-1" value={newId} onChange={(e) => setNewId(e.target.value)} />
          </div>
          <div>
            <label className="text-sm text-slate-600">이름</label>
            <input className="input mt-1" value={newName} onChange={(e) => setNewName(e.target.value)} />
          </div>
          <div>
            <label className="text-sm text-slate-600">비밀번호</label>
            <input className="input mt-1" type="password" value={newPw} onChange={(e) => setNewPw(e.target.value)} />
          </div>
          <div>
            <label className="text-sm text-slate-600">권한</label>
            <select className="input mt-1" value={newRole} onChange={(e) => setNewRole(e.target.value)}>
              <option value="사용자">사용자</option>
              <option value="관리자">관리자</option>
            </select>
          </div>
        </div>

        <button className="btn w-full mt-3" onClick={addUser} disabled={!newId || !newName || !newPw}>
          추가
        </button>

        {msg ? (
          <div className="mt-3 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
            {msg}
          </div>
        ) : null}
      </div>
    </div>
  );
}
