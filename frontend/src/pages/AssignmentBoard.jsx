import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAdminSession } from '../hooks/useAdminSession';
import { AdminSidebar } from './AdminDashboard';

export default function AssignmentBoard() {
  const navigate = useNavigate();
  const isReady = useAdminSession();
  const [selectedDate, setSelectedDate] = useState('2026-06-10');
  const [grid, setGrid] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAutoAssigning, setIsAutoAssigning] = useState(false);
  const [message, setMessage] = useState(null);

  const [manualOpen, setManualOpen] = useState(false);
  const [manualTarget, setManualTarget] = useState(null);
  const [selectedRequestIdx, setSelectedRequestIdx] = useState(0);

  const fetchGrid = useCallback(async (date) => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const res = await fetch(`/api/admin/assignments/grid?date=${encodeURIComponent(date)}`);
      if (!res.ok) throw new Error('割当データの取得に失敗しました');
      setGrid(await res.json());
    } catch (err) {
      setLoadError(err.message);
      setGrid(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchGrid(selectedDate);
  }, [selectedDate, fetchGrid]);

  const handleAutoAssign = async () => {
    setIsAutoAssigning(true);
    setMessage(null);
    setLoadError(null);
    try {
      const res = await fetch('/api/admin/auto-assign', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ date: selectedDate }),
      });
      if (!res.ok) throw new Error('自動割当に失敗しました');
      const data = await res.json();
      setGrid(data.grid);
      setMessage(data.message);
    } catch (err) {
      setLoadError(err.message);
    } finally {
      setIsAutoAssigning(false);
    }
  };

  const openManual = (teacherId, teacherName, slot) => {
    setManualTarget({ teacherId, teacherName, slot });
    setSelectedRequestIdx(0);
    setManualOpen(true);
  };

  const handleManualAssign = async () => {
    const req = grid?.pending_requests?.[selectedRequestIdx];
    if (!req || !manualTarget) return;
    try {
      const res = await fetch('/api/admin/assignments/manual', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          date: selectedDate,
          student_id: req.student_id,
          student_name: req.student_name,
          subject: req.subject,
          teacher_id: manualTarget.teacherId,
          slot: manualTarget.slot,
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || '手動割当に失敗しました');
      }
      setGrid(await res.json());
      setManualOpen(false);
      setMessage(`${req.student_name} を ${manualTarget.teacherName} ${manualTarget.slot}コマに割当しました`);
    } catch (err) {
      setLoadError(err.message);
    }
  };

  if (!isReady) return null;

  const timeSlots = grid?.time_slots ?? [];

  return (
    <div className="min-h-screen bg-gray-50 flex font-sans relative">
      {isAutoAssigning && (
        <div className="absolute inset-0 bg-white/70 backdrop-blur-sm z-50 flex flex-col items-center justify-center">
          <div className="w-16 h-16 border-4 border-purple-200 border-t-purple-600 rounded-full animate-spin mb-4" />
          <h2 className="text-2xl font-bold text-purple-800">自動マッチング中...</h2>
        </div>
      )}

      {manualOpen && manualTarget && (
        <div className="absolute inset-0 bg-black/50 z-40 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-md w-full">
            <h3 className="text-xl font-bold mb-2">手動割当</h3>
            <p className="text-gray-500 mb-4">
              {manualTarget.teacherName} — {manualTarget.slot}コマ目
            </p>
            {(grid?.pending_requests?.length ?? 0) === 0 ? (
              <p className="text-gray-500 text-sm mb-6">未割当リクエストがありません。インポート画面から追加してください。</p>
            ) : (
              <div className="space-y-2 mb-6 max-h-48 overflow-y-auto">
                {grid.pending_requests.map((r, idx) => (
                  <button
                    key={`${r.student_id}-${r.subject}`}
                    type="button"
                    onClick={() => setSelectedRequestIdx(idx)}
                    className={`w-full text-left p-3 rounded-xl border ${
                      idx === selectedRequestIdx ? 'border-emerald-500 bg-emerald-50 font-bold' : 'border-gray-200'
                    }`}
                  >
                    {r.student_name} — {r.subject}
                  </button>
                ))}
              </div>
            )}
            <div className="flex gap-3">
              <button type="button" onClick={() => setManualOpen(false)} className="flex-1 py-3 bg-gray-200 rounded-xl font-bold">キャンセル</button>
              <button
                type="button"
                onClick={handleManualAssign}
                disabled={!grid?.pending_requests?.length}
                className="flex-1 py-3 bg-blue-600 text-white rounded-xl font-bold disabled:bg-blue-300"
              >
                割当する
              </button>
            </div>
          </div>
        </div>
      )}

      <AdminSidebar navigate={navigate} current="assignments" />

      <div className="flex-1 p-8 overflow-y-auto">
        <header className="mb-8 flex justify-between items-start flex-wrap gap-4">
          <div>
            <h2 className="text-3xl font-bold text-gray-800">生徒割当</h2>
            <p className="text-sm text-gray-500 mt-1">列＝コマ（13:30〜 / 80分授業 / 10分空け）。空きコマに生徒を割り当てます。</p>
            <input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="mt-3 bg-white border border-gray-300 px-3 py-2 rounded-lg font-bold"
            />
          </div>
          <button
            type="button"
            onClick={handleAutoAssign}
            disabled={isAutoAssigning || isLoading}
            className="bg-purple-600 hover:bg-purple-700 text-white px-6 py-3 rounded-xl font-bold shadow-md"
          >
            ✨ 自動マッチング
          </button>
        </header>

        {loadError && <p className="text-red-500 mb-4">{loadError}</p>}
        {message && <p className="text-emerald-600 font-bold mb-4">{message}</p>}

        {grid?.pending_requests?.length > 0 && (
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-6">
            <p className="font-bold text-amber-800 mb-2">未割当リクエスト ({grid.pending_requests.length})</p>
            <ul className="text-sm text-amber-900 space-y-1">
              {grid.pending_requests.map((r) => (
                <li key={`${r.student_id}-${r.subject}`}>{r.student_name} — {r.subject}</li>
              ))}
            </ul>
          </div>
        )}

        <div className="bg-white rounded-2xl shadow-sm border overflow-x-auto">
          {isLoading ? (
            <p className="p-8 text-center text-gray-500">読み込み中...</p>
          ) : (
            <table className="w-full text-left border-collapse min-w-[800px]">
              <thead>
                <tr className="bg-gray-100 text-sm border-b">
                  <th className="p-4 border-r font-bold">講師</th>
                  {timeSlots.map((ts) => (
                    <th key={ts.slot} className="p-3 text-center font-bold min-w-[140px]">
                      <div>{ts.slot}コマ</div>
                      <div className="text-xs font-normal text-gray-500">{ts.start}~{ts.end}</div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {grid?.teachers?.map((t) => (
                  <tr key={t.id} className="border-b">
                    <td className="p-4 border-r font-bold whitespace-nowrap">
                      <span className={`inline-block w-8 h-8 rounded-full text-center leading-8 text-xs mr-2 ${t.color}`}>{t.name.charAt(0)}</span>
                      {t.name}
                    </td>
                    {t.slots.map((s) => {
                      const a = s.assignment;
                      const blocked = s.availability === '◎' || s.availability === '×';
                      return (
                        <td key={s.slot} className="p-2">
                          {a ? (
                            <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-2 text-center">
                              <div className="font-bold text-emerald-800 text-sm">{a.student_name}</div>
                              <div className="text-xs text-emerald-600">{a.subject}</div>
                            </div>
                          ) : blocked ? (
                            <div className="py-4 text-center text-gray-400 text-sm bg-gray-50 rounded-lg">
                              {s.availability === '◎' ? '◎' : '×'}
                            </div>
                          ) : (
                            <button
                              type="button"
                              onClick={() => openManual(t.id, t.name, s.slot)}
                              className="w-full py-4 border-2 border-dashed border-blue-200 rounded-lg text-blue-400 hover:bg-blue-50 hover:border-blue-400 text-sm font-bold"
                            >
                              ＋ 割当
                            </button>
                          )}
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
