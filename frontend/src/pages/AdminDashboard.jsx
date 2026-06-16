import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAdminSession } from '../hooks/useAdminSession';
import { AdminSidebar } from '../components/AdminSidebar';

function cellLabel(status) {
  if (status === '◎' || status === '通常授業') return '◎';
  if (status === '×' || status === '不可') return '×';
  if (status === '未提出') return '未提出';
  return '空き';
}

function cellStyle(status) {
  if (status === '◎' || status === '通常授業') return 'bg-slate-100 text-slate-700 border-slate-300 border-2';
  if (status === '×' || status === '不可') return 'bg-gray-100 text-gray-500 border-gray-200';
  if (status === '未提出') return 'bg-amber-50 text-amber-700 border-amber-200';
  return 'bg-white text-gray-500 border-gray-200 border border-dashed text-sm font-bold';
}

export default function AdminDashboard() {
  const navigate = useNavigate();
  const isReady = useAdminSession();
  const [selectedDate, setSelectedDate] = useState('2026-06-10');
  const [teachers, setTeachers] = useState([]);
  const [timeSlots, setTimeSlots] = useState([]);
  const [metrics, setMetrics] = useState({ unsubmitted_teachers: 0 });
  const [loadError, setLoadError] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [periods, setPeriods] = useState([]);
  const [activePeriodId, setActivePeriodId] = useState(null);
  const [periodMessage, setPeriodMessage] = useState(null);
  const [finalized, setFinalized] = useState(false);
  const [googleConfigured, setGoogleConfigured] = useState(false);
  const [googleExportRef, setGoogleExportRef] = useState('');
  const [googleExportMessage, setGoogleExportMessage] = useState(null);
  const [isGoogleExporting, setIsGoogleExporting] = useState(false);
  const [changeRequests, setChangeRequests] = useState([]);
  const [pendingChangeCount, setPendingChangeCount] = useState(0);
  const [isPublishingAll, setIsPublishingAll] = useState(false);

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

  const fetchChangeRequests = useCallback(async (pid) => {
    if (!pid) return;
    try {
      const res = await fetch(`/api/admin/change-requests?period_id=${pid}&status=PENDING`);
      if (!res.ok) return;
      const data = await res.json();
      setChangeRequests(data.requests ?? []);
      setPendingChangeCount(data.pending_count ?? 0);
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    fetch('/api/admin/periods')
      .then((r) => r.json())
      .then((data) => {
        setPeriods(data.periods ?? []);
        const pid = data.active_period_id ?? null;
        setActivePeriodId(pid);
        if (pid) fetchChangeRequests(pid);
      })
      .catch(() => {});
    fetch('/api/google/status')
      .then((r) => r.json())
      .then((data) => setGoogleConfigured(Boolean(data.configured)))
      .catch(() => {});
  }, [fetchChangeRequests]);

  const handlePeriodStatus = async (status, force = false) => {
    if (!activePeriodId) return;
    setPeriodMessage(null);
    try {
      const res = await fetch(`/api/admin/periods/${activePeriodId}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status, force }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        if (status === 'FINALIZED' && res.status === 409 && !force) {
          const ok = window.confirm(
            `${data.detail || '未割当が残っています。'}\n\n強制確定しますか？`,
          );
          if (ok) return handlePeriodStatus(status, true);
        }
        throw new Error(data.detail || '期間ステータスの更新に失敗しました');
      }
      setPeriods((prev) => prev.map((p) => (p.id === data.period.id ? data.period : p)));
      setPeriodMessage(data.message);
      if (status === 'FINALIZED') fetchDashboard(selectedDate);
    } catch (err) {
      setLoadError(err.message);
    }
  };

  const handlePublishAll = async () => {
    if (!activePeriodId || isPublishingAll) return;
    setIsPublishingAll(true);
    setPeriodMessage(null);
    try {
      const res = await fetch('/api/admin/assignments/publish-all', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ period_id: activePeriodId }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || '一括送付に失敗しました');
      setPeriodMessage(data.message);
    } catch (err) {
      setLoadError(err.message);
    } finally {
      setIsPublishingAll(false);
    }
  };

  const handleResolveChange = async (requestId, action) => {
    try {
      const res = await fetch(`/api/admin/change-requests/${requestId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || '処理に失敗しました');
      setPeriodMessage(data.message);
      fetchChangeRequests(activePeriodId);
    } catch (err) {
      setLoadError(err.message);
    }
  };

  const handleExport = () => {
    if (!activePeriodId) return;
    window.open(`/api/admin/shifts/export-excel?period_id=${activePeriodId}`, '_blank');
  };

  const handleJukuExport = () => {
    if (!activePeriodId) return;
    window.open(`/api/export/juku-schedule?period_id=${activePeriodId}`, '_blank');
  };

  const handleGoogleExport = async () => {
    if (!activePeriodId || isGoogleExporting) return;
    setIsGoogleExporting(true);
    setGoogleExportMessage(null);
    try {
      const body = { period_id: activePeriodId };
      if (googleExportRef.trim()) body.spreadsheet_ref = googleExportRef.trim();
      const res = await fetch('/api/google/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || 'Google 書き込みに失敗しました');
      setGoogleExportMessage(data.message);
      if (data.web_view_link) window.open(data.web_view_link, '_blank');
    } catch (err) {
      setLoadError(err.message);
    } finally {
      setIsGoogleExporting(false);
    }
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
            <p className="text-sm text-gray-500 mt-1">◎ 通常授業 / × 無理 / 空き 空いている（Excel ◎ はシフト確定後に反映）</p>
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
            {googleExportMessage && <p className="text-emerald-600 text-sm mt-2 font-bold">{googleExportMessage}</p>}
            {activePeriod?.status === 'FINALIZED' && googleConfigured && (
              <label className="block mt-3 max-w-md">
                <span className="text-xs text-gray-500">Google 書き出し先（空欄で新規作成）</span>
                <input
                  type="text"
                  value={googleExportRef}
                  onChange={(e) => setGoogleExportRef(e.target.value)}
                  placeholder="スプレッドシート URL / ID（任意）"
                  className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                />
              </label>
            )}
            {activePeriod && (
              <p className="text-sm text-gray-600 mt-2">
                募集期間: {activePeriod.name}（{activePeriod.status}）
                {finalized && ' — 確定済み'}
              </p>
            )}
            {activePeriod?.status === 'COLLECTING' && (
              <p className="text-xs text-gray-500 mt-2 max-w-xl">
                「全員にスケジュール送付」で生徒・講師に個別スケジュールを届けます。
                「シフト確定」で募集を締め切り、Excel/Google 書き出しが可能になります。
                個別送付は「生徒の割り当て」画面でも行えます。
              </p>
            )}
          </div>
          <div className="flex flex-wrap gap-3">
            {activePeriod?.status === 'DRAFT' && (
              <button type="button" onClick={() => handlePeriodStatus('COLLECTING')} className="bg-amber-500 hover:bg-amber-600 text-white px-4 py-3 rounded-xl font-bold">配布開始</button>
            )}
            {activePeriod?.status === 'COLLECTING' && (
              <>
                <button type="button" onClick={() => handlePublishAll()} disabled={isPublishingAll} className="bg-blue-700 hover:bg-blue-800 disabled:bg-blue-400 text-white px-4 py-3 rounded-xl font-bold">
                  {isPublishingAll ? '送付中...' : '全員にスケジュール送付'}
                </button>
                <button type="button" onClick={() => handlePeriodStatus('FINALIZED')} className="bg-emerald-700 hover:bg-emerald-800 text-white px-4 py-3 rounded-xl font-bold">シフト確定</button>
              </>
            )}
            <button type="button" onClick={handleExport} disabled={!activePeriodId} className="bg-gray-600 hover:bg-gray-700 disabled:bg-gray-400 text-white px-4 py-3 rounded-xl font-bold">データ DL</button>
            {activePeriod?.status === 'FINALIZED' && (
              <>
                <button type="button" onClick={handleJukuExport} className="bg-indigo-700 hover:bg-indigo-800 text-white px-4 py-3 rounded-xl font-bold">
                  時間割 DL
                </button>
                {googleConfigured && (
                  <button
                    type="button"
                    onClick={handleGoogleExport}
                    disabled={isGoogleExporting}
                    className="bg-green-700 hover:bg-green-800 disabled:bg-green-400 text-white px-4 py-3 rounded-xl font-bold"
                  >
                    {isGoogleExporting ? 'Google 書込中...' : 'Google へ書き出し'}
                  </button>
                )}
              </>
            )}
          </div>
        </header>

        <div className="mb-8 grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-2xl">
          <div className="bg-white p-6 rounded-2xl shadow-sm border">
            <p className="text-sm text-gray-500 font-bold">未提出の講師</p>
            <p className="text-3xl font-bold text-red-500">{metrics.unsubmitted_teachers} 名</p>
          </div>
          <div className="bg-white p-6 rounded-2xl shadow-sm border">
            <p className="text-sm text-gray-500 font-bold">変更申請（承認待ち）</p>
            <p className="text-3xl font-bold text-amber-600">{pendingChangeCount} 件</p>
          </div>
        </div>

        {changeRequests.length > 0 && (
          <div className="mb-8 bg-white rounded-2xl shadow-sm border p-6">
            <h3 className="text-lg font-bold text-gray-800 mb-4">変更申請（承認待ち）</h3>
            <div className="space-y-3">
              {changeRequests.map((req) => (
                <div key={req.id} className="flex flex-wrap items-center justify-between gap-3 p-4 bg-amber-50 border border-amber-200 rounded-xl">
                  <div className="text-sm">
                    <span className="font-bold">{req.entity_name}</span>
                    <span className="text-gray-500 ml-2">({req.role === 'teacher' ? '講師' : '生徒'})</span>
                    <div className="text-gray-700 mt-1">
                      {req.date} · {req.slot}コマ:
                      {' '}{req.current_symbol || '空'} → {req.requested_symbol || '空'}
                      {req.reason && <span className="text-gray-500 ml-2">— {req.reason}</span>}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button type="button" onClick={() => handleResolveChange(req.id, 'approve')} className="px-3 py-1 bg-emerald-600 text-white rounded-lg text-sm font-bold">承認</button>
                    <button type="button" onClick={() => handleResolveChange(req.id, 'reject')} className="px-3 py-1 bg-gray-500 text-white rounded-lg text-sm font-bold">却下</button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="bg-white rounded-2xl shadow-sm border overflow-hidden">
          {isLoading ? (
            <p className="p-8 text-gray-500 text-center">読み込み中...</p>
          ) : (
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-100 text-gray-600 text-sm border-b">
                  <th className="p-4 font-bold border-r">講師 \ 時間</th>
                  {(timeSlots.length ? timeSlots : [1, 2, 3, 4, 5, 6].map((s) => ({ slot: s, start: '', end: '' }))).map((ts) => (
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
                    {[1, 2, 3, 4, 5, 6].map((slot) => {
                      const val = t[`s${slot}`];
                      return (
                        <td key={slot} className="p-3 text-center">
                          <div className={`py-3 rounded-lg font-bold border min-h-[48px] flex items-center justify-center ${cellStyle(val)}`}>
                            {cellLabel(val)}
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

