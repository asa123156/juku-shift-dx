import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAdminSession } from '../hooks/useAdminSession';
import { clearSession } from '../utils/session';

function AdminSidebar({ navigate, current }) {
  const link = (path, label, key) => (
    <button
      type="button"
      onClick={() => navigate(path)}
      className={`w-full text-left px-4 py-3 rounded-lg transition-colors ${
        current === key ? 'bg-gray-800 font-bold' : 'hover:bg-gray-800 text-gray-400'
      }`}
    >
      {label}
    </button>
  );
  return (
    <div className="w-64 bg-gray-900 text-white p-6 flex flex-col shrink-0">
      <h1 className="text-2xl font-bold mb-10 text-blue-400 flex items-center gap-2">
        <span>🎓</span> JUKU-SHIFT
      </h1>
      <nav className="flex-1 space-y-2">
        {link('/admin', 'ダッシュボード', 'dashboard')}
        {link('/admin/assignments', '生徒割当', 'assignments')}
        {link('/import', 'データインポート', 'import')}
      </nav>
      <button
        type="button"
        onClick={() => { clearSession(); navigate('/'); }}
        className="text-gray-400 hover:text-white text-left text-sm"
      >
        ← ログアウト
      </button>
    </div>
  );
}

function cellLabel(status) {
  if (status === '◎') return '◎';
  if (status === '×') return '×';
  return '';
}

function cellStyle(status) {
  if (status === '◎') return 'bg-slate-100 text-slate-700 border-slate-300 border-2';
  if (status === '×') return 'bg-gray-100 text-gray-500 border-gray-200';
  return 'bg-white text-gray-300 border-gray-100 border border-dashed';
}

export default function AdminDashboard() {
  const navigate = useNavigate();
  const isReady = useAdminSession();
  const [selectedDate, setSelectedDate] = useState('2026-06-10');
  const [teachers, setTeachers] = useState([]);
  const [timeSlots, setTimeSlots] = useState([]);
  const [metrics, setMetrics] = useState({ unsubmitted_teachers: 0, shortage_slots: 0 });
  const [loadError, setLoadError] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [periods, setPeriods] = useState([]);
  const [activePeriodId, setActivePeriodId] = useState(null);
  const [periodMessage, setPeriodMessage] = useState(null);
  const [finalized, setFinalized] = useState(false);

  const fetchDashboard = useCallback(async (date) => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const res = await fetch(`/api/shifts?date=${encodeURIComponent(date)}`);
      if (!res.ok) throw new Error('シフトデータの取得に失敗しました');
      const data = await res.json();
      setTeachers(data.teachers);
      setTimeSlots(data.time_slots ?? []);
      setMetrics(data.metrics);
      setFinalized(data.finalized ?? false);
    } catch (err) {
      setLoadError(err.message);
      setTeachers([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboard(selectedDate);
  }, [selectedDate, fetchDashboard]);

  useEffect(() => {
    fetch('/api/admin/periods')
      .then((r) => r.json())
      .then((data) => {
        setPeriods(data.periods ?? []);
        setActivePeriodId(data.active_period_id ?? null);
      })
      .catch(() => {});
  }, []);

  const handlePeriodStatus = async (status) => {
    if (!activePeriodId) return;
    setPeriodMessage(null);
    try {
      const res = await fetch(`/api/admin/periods/${activePeriodId}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status }),
      });
      if (!res.ok) throw new Error('期間ステータスの更新に失敗しました');
      const data = await res.json();
      setPeriods((prev) => prev.map((p) => (p.id === data.period.id ? data.period : p)));
      setPeriodMessage(data.message);
      if (status === 'FINALIZED') fetchDashboard(selectedDate);
    } catch (err) {
      setLoadError(err.message);
    }
  };

  const handleExport = () => {
    if (!activePeriodId) return;
    window.open(`/api/admin/shifts/export-excel?period_id=${activePeriodId}`, '_blank');
  };

  const activePeriod = periods.find((p) => p.id === activePeriodId);

  if (!isReady) return null;

  return (
    <div className="min-h-screen bg-gray-50 flex font-sans">
      <AdminSidebar navigate={navigate} current="dashboard" />

      <div className="flex-1 p-8 overflow-y-auto">
        <header className="mb-8 flex justify-between items-start gap-4 flex-wrap">
          <div>
            <h2 className="text-3xl font-bold text-gray-800">シフトダッシュボード</h2>
            <p className="text-sm text-gray-500 mt-1">◎ 通常授業 / × 無理 / 空 空き（Excel ◎ はシフト確定後に反映）</p>
            <div className="flex items-center gap-3 mt-3">
              <input
                type="date"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                className="bg-white border border-gray-300 text-gray-700 px-3 py-2 rounded-lg font-bold shadow-sm"
              />
            </div>
            {loadError && <p className="text-red-500 text-sm mt-2">{loadError}</p>}
            {periodMessage && <p className="text-emerald-600 text-sm mt-2 font-bold">{periodMessage}</p>}
            {activePeriod && (
              <p className="text-sm text-gray-600 mt-2">
                募集期間: {activePeriod.name}（{activePeriod.status}）
                {finalized && ' — 確定済み'}
              </p>
            )}
          </div>
          <div className="flex flex-wrap gap-3">
            {activePeriod?.status === 'DRAFT' && (
              <button type="button" onClick={() => handlePeriodStatus('COLLECTING')} className="bg-amber-500 hover:bg-amber-600 text-white px-4 py-3 rounded-xl font-bold">配布開始</button>
            )}
            {activePeriod?.status === 'COLLECTING' && (
              <button type="button" onClick={() => handlePeriodStatus('FINALIZED')} className="bg-emerald-700 hover:bg-emerald-800 text-white px-4 py-3 rounded-xl font-bold">シフト確定</button>
            )}
            <button type="button" onClick={() => navigate('/admin/assignments')} className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-3 rounded-xl font-bold">生徒割当へ</button>
            <button type="button" onClick={handleExport} disabled={!activePeriodId} className="bg-gray-600 hover:bg-gray-700 disabled:bg-gray-400 text-white px-4 py-3 rounded-xl font-bold">Excel DL</button>
          </div>
        </header>

        <div className="grid grid-cols-2 gap-6 mb-8 max-w-xl">
          <div className="bg-white p-6 rounded-2xl shadow-sm border">
            <p className="text-sm text-gray-500 font-bold">未提出の講師</p>
            <p className="text-3xl font-bold text-red-500">{metrics.unsubmitted_teachers} 名</p>
          </div>
          <div className="bg-white p-6 rounded-2xl shadow-sm border">
            <p className="text-sm text-gray-500 font-bold">不足コマ</p>
            <p className="text-3xl font-bold text-yellow-500">{metrics.shortage_slots} 枠</p>
          </div>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border overflow-hidden">
          {isLoading ? (
            <p className="p-8 text-gray-500 text-center">読み込み中...</p>
          ) : (
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-100 text-gray-600 text-sm border-b">
                  <th className="p-4 font-bold border-r">講師 \ 時間</th>
                  {(timeSlots.length ? timeSlots : [1, 2, 3, 4].map((s) => ({ slot: s, start: '', end: '' }))).map((ts) => (
                    <th key={ts.slot} className="p-4 font-bold text-center">
                      {ts.slot}コマ
                      {ts.start && <div className="text-xs font-normal">{ts.start}~{ts.end}</div>}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {teachers.map((t) => (
                  <tr key={t.id} className="border-b hover:bg-gray-50">
                    <td className="p-4 border-r font-bold flex items-center gap-3">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs ${t.color}`}>{t.name.charAt(0)}</div>
                      {t.name}
                    </td>
                    {[1, 2, 3, 4].map((slot) => {
                      const val = t[`s${slot}`];
                      return (
                        <td key={slot} className="p-3 text-center">
                          <div className={`py-3 rounded-lg text-lg font-bold border min-h-[48px] flex items-center justify-center ${cellStyle(val)}`}>
                            {cellLabel(val) || '　'}
                          </div>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

export { AdminSidebar };
