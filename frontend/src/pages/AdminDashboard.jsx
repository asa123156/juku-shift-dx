import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAdminSession } from '../hooks/useAdminSession';
import { clearSession } from '../utils/session';

export default function AdminDashboard() {
  const navigate = useNavigate();
  const isReady = useAdminSession();
  const [selectedDate, setSelectedDate] = useState('2026-06-10');
  const [teachers, setTeachers] = useState([]);
  const [metrics, setMetrics] = useState({ unsubmitted_teachers: 0, shortage_slots: 0 });
  const [assignments, setAssignments] = useState([]);
  const [proposals, setProposals] = useState([]);
  const [loadError, setLoadError] = useState(null);

  const [isCalculating, setIsCalculating] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const [modalOpen, setModalOpen] = useState(false);
  const [selectedCell, setSelectedCell] = useState(null);
  const [candidates, setCandidates] = useState([]);
  const [selectedCandidateIdx, setSelectedCandidateIdx] = useState(0);
  const [candidatesLoading, setCandidatesLoading] = useState(false);
  const [candidatesError, setCandidatesError] = useState(null);

  const applyDashboard = useCallback((dashboard) => {
    setTeachers(dashboard.teachers);
    setMetrics(dashboard.metrics);
  }, []);

  const fetchDashboard = useCallback(async (date) => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const res = await fetch(`/api/shifts?date=${encodeURIComponent(date)}`);
      if (!res.ok) throw new Error('シフトデータの取得に失敗しました');
      const data = await res.json();
      applyDashboard(data);
    } catch (err) {
      setLoadError(err.message);
      setTeachers([]);
    } finally {
      setIsLoading(false);
    }
  }, [applyDashboard]);

  useEffect(() => {
    fetchDashboard(selectedDate);
  }, [selectedDate, fetchDashboard]);

  const getStatusStyle = (status) => {
    switch (status) {
      case '確定': return 'bg-emerald-100 text-emerald-700 border-emerald-200';
      case '通常授業': return 'bg-slate-100 text-slate-600 border-slate-300 border-2';
      case '待機': return 'bg-white text-blue-600 border-blue-400 border-2 hover:bg-blue-50';
      case '不可': return 'bg-gray-100 text-gray-400 border-gray-100';
      case '不足': return 'bg-yellow-100 text-yellow-700 border-yellow-300 animate-pulse';
      case 'AI提案': return 'bg-purple-100 text-purple-700 border-purple-400 border-2 shadow-[0_0_10px_rgba(168,85,247,0.4)]';
      default: return 'bg-white text-gray-400 border-gray-200';
    }
  };

  const handleAutoAssign = async () => {
    setIsCalculating(true);
    setLoadError(null);
    try {
      const res = await fetch('/api/admin/auto-assign', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ date: selectedDate }),
      });
      if (!res.ok) throw new Error('自動割当に失敗しました');
      const data = await res.json();
      applyDashboard(data.dashboard);
      setAssignments(data.assignments);
      setProposals(data.proposals);
    } catch (err) {
      setLoadError(err.message);
    } finally {
      setIsCalculating(false);
    }
  };

  const resolveAssignmentContext = (teacherId, slot) => {
    const fromAssignment = assignments.find(
      (a) => a.teacher_id === teacherId && a.slot === slot,
    );
    if (fromAssignment) {
      return { student_id: fromAssignment.student_id, subject: fromAssignment.subject };
    }
    const fromProposal = proposals.find(
      (p) => p.teacher_id === teacherId && p.slot === slot,
    );
    if (fromProposal) {
      return { student_id: fromProposal.student_id, subject: fromProposal.subject };
    }
    return { student_id: 1, subject: '数学I' };
  };

  const handleCellClick = async (teacherId, teacherName, slot, currentStatus) => {
    if (currentStatus === '不可' || currentStatus === '未提出' || currentStatus === '通常授業') return;

    const context = resolveAssignmentContext(teacherId, slot);
    setSelectedCell({ teacherId, teacherName, slot, currentStatus, ...context });
    setModalOpen(true);
    setCandidates([]);
    setSelectedCandidateIdx(0);
    setCandidatesLoading(true);
    setCandidatesError(null);

    try {
      const res = await fetch('/api/admin/assignments/candidates', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          date: selectedDate,
          student_id: context.student_id,
          subject: context.subject,
        }),
      });
      if (!res.ok) throw new Error('候補の取得に失敗しました');
      const data = await res.json();
      setCandidates(data.candidates);
    } catch (err) {
      setCandidatesError(err.message);
    } finally {
      setCandidatesLoading(false);
    }
  };

  const handleConfirmCandidate = async () => {
    const candidate = candidates[selectedCandidateIdx];
    if (!candidate) {
      setModalOpen(false);
      return;
    }
    try {
      const res = await fetch('/api/admin/shifts/slot', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          date: selectedDate,
          teacher_id: candidate.teacher_id,
          slot: candidate.slot,
          status: 'AI提案',
        }),
      });
      if (!res.ok) throw new Error('変更の確定に失敗しました');
      const dashboard = await res.json();
      applyDashboard(dashboard);
      setModalOpen(false);
    } catch (err) {
      setCandidatesError(err.message);
    }
  };

  const handleConfirmShifts = async () => {
    try {
      const res = await fetch('/api/admin/shifts/confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ date: selectedDate }),
      });
      if (!res.ok) throw new Error('シフト確定に失敗しました');
      const data = await res.json();
      applyDashboard(data.dashboard);
    } catch (err) {
      setLoadError(err.message);
    }
  };

  if (!isReady) return null;

  return (
    <div className="min-h-screen bg-gray-50 flex font-sans relative">
      {isCalculating && (
        <div className="absolute inset-0 bg-white/70 backdrop-blur-sm z-50 flex flex-col items-center justify-center">
          <div className="w-16 h-16 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin mb-4"></div>
          <h2 className="text-2xl font-bold text-blue-800">最適シフトを計算中...</h2>
          <p className="text-gray-500 mt-2">条件に合致する講師をマッチングしています</p>
        </div>
      )}

      {modalOpen && selectedCell && (
        <div className="absolute inset-0 bg-black/50 z-40 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-md w-full">
            <h3 className="text-xl font-bold text-gray-800 mb-2">シフトの個別調整</h3>
            <p className="text-gray-500 mb-2">
              {selectedCell.slot}コマ目 - {selectedCell.teacherName} ({selectedCell.currentStatus})
            </p>
            <p className="text-sm text-gray-400 mb-6">
              生徒ID: {selectedCell.student_id} / {selectedCell.subject}
            </p>

            <div className="space-y-3 mb-8">
              <p className="text-sm font-bold text-gray-700">代替可能な講師候補（AIスコア順）</p>
              {candidatesLoading && (
                <p className="text-gray-500 text-sm">候補を取得中...</p>
              )}
              {candidatesError && (
                <p className="text-red-500 text-sm">{candidatesError}</p>
              )}
              {!candidatesLoading && candidates.length === 0 && !candidatesError && (
                <p className="text-gray-500 text-sm">条件に合う候補がありません</p>
              )}
              {candidates.map((c, idx) => (
                <button
                  key={`${c.teacher_id}-${c.slot}`}
                  type="button"
                  onClick={() => setSelectedCandidateIdx(idx)}
                  className={`w-full text-left p-3 rounded-xl flex justify-between transition-colors ${
                    idx === selectedCandidateIdx
                      ? 'border-2 border-emerald-500 bg-emerald-50 font-bold text-emerald-800'
                      : 'border border-gray-200 hover:bg-gray-50 text-gray-700'
                  }`}
                >
                  <span>👨‍🏫 {c.teacher_name} ({c.slot}コマ)</span>
                  <span className={idx === selectedCandidateIdx ? 'text-emerald-600' : 'text-gray-400'}>
                    マッチ度: {c.match_score}%
                  </span>
                </button>
              ))}
            </div>

            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => setModalOpen(false)}
                className="flex-1 py-3 bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-xl font-bold transition-colors"
              >
                キャンセル
              </button>
              <button
                type="button"
                onClick={handleConfirmCandidate}
                disabled={candidates.length === 0}
                className="flex-1 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white rounded-xl font-bold shadow-md transition-colors"
              >
                変更を確定
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="w-64 bg-gray-900 text-white p-6 flex flex-col">
        <h1 className="text-2xl font-bold mb-10 text-blue-400 flex items-center gap-2"><span>🎓</span> JUKU-SHIFT</h1>
        <nav className="flex-1 space-y-2">
          <button type="button" className="w-full text-left bg-gray-800 px-4 py-3 rounded-lg font-bold">ダッシュボード</button>
          <button type="button" onClick={() => navigate('/import')} className="w-full text-left hover:bg-gray-800 px-4 py-3 rounded-lg text-gray-400 transition-colors">データインポート</button>
        </nav>
        <button type="button" onClick={() => { clearSession(); navigate('/'); }} className="text-gray-400 hover:text-white text-left text-sm">← ログアウト</button>
      </div>

      <div className="flex-1 p-8 overflow-y-auto">
        <header className="mb-8 flex justify-between items-center">
          <div>
            <h2 className="text-3xl font-bold text-gray-800">ダッシュボード</h2>
            <div className="flex items-center gap-3 mt-3">
              <input
                type="date"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                className="bg-white border border-gray-300 text-gray-700 px-3 py-2 rounded-lg font-bold shadow-sm focus:ring-2 focus:ring-blue-500 outline-none cursor-pointer"
              />
              <p className="text-gray-500 font-bold">のシフト状況</p>
            </div>
            {loadError && <p className="text-red-500 text-sm mt-2">{loadError}</p>}
          </div>
          <div className="flex gap-3">
            <button
              type="button"
              onClick={handleAutoAssign}
              disabled={isCalculating || isLoading}
              className="bg-purple-600 hover:bg-purple-700 disabled:bg-purple-400 text-white px-6 py-3 rounded-xl font-bold shadow-md transition-all active:scale-95 flex items-center gap-2"
            >
              ✨ AI自動割当を実行
            </button>
            <button
              type="button"
              onClick={handleConfirmShifts}
              disabled={isLoading}
              className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white px-6 py-3 rounded-xl font-bold shadow-md transition-all active:scale-95"
            >
              シフトを確定する
            </button>
          </div>
        </header>

        <div className="grid grid-cols-3 gap-6 mb-8">
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 font-bold mb-1">未提出の講師</p>
              <p className="text-3xl font-bold text-red-500">
                {metrics.unsubmitted_teachers} <span className="text-lg text-gray-400 font-normal">名</span>
              </p>
            </div>
          </div>
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 font-bold mb-1">不足しているコマ</p>
              <p className="text-3xl font-bold text-yellow-500">
                {metrics.shortage_slots} <span className="text-lg text-gray-400 font-normal">枠</span>
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
          {isLoading ? (
            <p className="p-8 text-gray-500 text-center">読み込み中...</p>
          ) : (
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-100 text-gray-600 text-sm border-b border-gray-200">
                  <th className="p-4 font-bold border-r border-gray-200">講師名 \ 時間</th>
                  <th className="p-4 font-bold text-center">1コマ (13:00)</th>
                  <th className="p-4 font-bold text-center">2コマ (14:30)</th>
                  <th className="p-4 font-bold text-center">3コマ (16:00)</th>
                  <th className="p-4 font-bold text-center">4コマ (17:30)</th>
                </tr>
              </thead>
              <tbody>
                {teachers.map((t) => (
                  <tr key={t.id} className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
                    <td className="p-4 border-r border-gray-200 font-bold flex items-center gap-3">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${t.color}`}>{t.name.charAt(0)}</div>
                      {t.name}
                    </td>
                    <td className="p-3 text-center" onClick={() => handleCellClick(t.id, t.name, 1, t.s1)}>
                      <div className={`py-2 rounded-lg text-sm font-bold border cursor-pointer ${getStatusStyle(t.s1)}`}>{t.s1}</div>
                    </td>
                    <td className="p-3 text-center" onClick={() => handleCellClick(t.id, t.name, 2, t.s2)}>
                      <div className={`py-2 rounded-lg text-sm font-bold border cursor-pointer ${getStatusStyle(t.s2)}`}>{t.s2}</div>
                    </td>
                    <td className="p-3 text-center" onClick={() => handleCellClick(t.id, t.name, 3, t.s3)}>
                      <div className={`py-2 rounded-lg text-sm font-bold border cursor-pointer ${getStatusStyle(t.s3)}`}>{t.s3}</div>
                    </td>
                    <td className="p-3 text-center" onClick={() => handleCellClick(t.id, t.name, 4, t.s4)}>
                      <div className={`py-2 rounded-lg text-sm font-bold border cursor-pointer ${getStatusStyle(t.s4)}`}>{t.s4}</div>
                    </td>
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
