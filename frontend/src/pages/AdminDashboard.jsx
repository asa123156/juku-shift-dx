import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAdminSession } from '../hooks/useAdminSession';
import { AdminSidebar } from '../components/AdminSidebar';
import { WorkflowGuide, DEFAULT_WORKFLOW_STEPS } from '../components/WorkflowGuide';

function NameList({ items, emptyLabel, accent = 'gray' }) {
  const border = {
    indigo: 'border-indigo-200 bg-indigo-50/40',
    red: 'border-red-200 bg-red-50/40',
    emerald: 'border-emerald-200 bg-emerald-50/40',
    violet: 'border-violet-200 bg-violet-50/40',
  }[accent] || 'border-gray-200 bg-gray-50/40';

  if (!items?.length) {
    return (
      <p className="text-sm text-gray-400 py-6 text-center">{emptyLabel}</p>
    );
  }

  return (
    <ul className={`rounded-xl border ${border} divide-y divide-gray-200/80 max-h-[420px] overflow-y-auto`}>
      {items.map((person) => (
        <li
          key={person.id}
          className="px-3 py-2.5 flex items-center gap-2.5 text-sm hover:bg-white/60 transition-colors"
        >
          {person.color ? (
            <span className={`w-7 h-7 rounded-full shrink-0 flex items-center justify-center text-[10px] font-bold ${person.color}`}>
              {person.name.charAt(0)}
            </span>
          ) : person.grade_label ? null : (
            <span className="w-7 h-7 rounded-full shrink-0 bg-gray-200 flex items-center justify-center text-[10px] font-bold text-gray-600">
              {person.name.charAt(0)}
            </span>
          )}
          {person.grade_label && (
            <span className="text-xs text-gray-500 font-medium shrink-0 min-w-[2.5rem]">{person.grade_label}</span>
          )}
          <span className="font-bold text-gray-900 truncate">{person.name}</span>
        </li>
      ))}
    </ul>
  );
}

function StatusColumn({ title, count, subtitle, items, emptyLabel, accent }) {
  return (
    <div className="flex flex-col min-h-0">
      <div className="mb-2">
        <div className="flex items-baseline justify-between gap-2">
          <h4 className="text-sm font-bold text-gray-800">{title}</h4>
          <span className="text-lg font-bold text-gray-900 tabular-nums">{count}</span>
        </div>
        {subtitle && <p className="text-[11px] text-gray-500 mt-0.5">{subtitle}</p>}
      </div>
      <NameList items={items} emptyLabel={emptyLabel} accent={accent} />
    </div>
  );
}

function RolePanel({ roleLabel, roleKey, data, openDays }) {
  const proposal = data?.proposal_sent ?? [];
  const unsubmitted = data?.unsubmitted ?? [];
  const published = data?.schedule_published ?? [];

  const proposalTitle = '提案書送付済み';
  const proposalSub = '初回スケジュール表を送付済み';

  return (
    <section className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-100 bg-slate-50/80">
        <h3 className="text-lg font-bold text-gray-900">{roleLabel}</h3>
        <p className="text-xs text-gray-500 mt-0.5">
          開校 {openDays} 日分 · 時間割登録 {data?.on_grid ?? 0} 名
        </p>
      </div>
      <div className="p-4 grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatusColumn
          title={proposalTitle}
          count={proposal.length}
          subtitle={proposalSub}
          items={proposal}
          emptyLabel="該当者なし"
          accent="indigo"
        />
        <StatusColumn
          title="未提出"
          count={unsubmitted.length}
          subtitle="全開校日の提出が未完了"
          items={unsubmitted}
          emptyLabel="全員提出済み"
          accent="red"
        />
        <StatusColumn
          title="確定送付済み"
          count={published.length}
          subtitle="確定版スケジュールを送付済み"
          items={published}
          emptyLabel="該当者なし"
          accent="emerald"
        />
      </div>
    </section>
  );
}

export default function AdminDashboard() {
  const navigate = useNavigate();
  const isReady = useAdminSession();
  const [summary, setSummary] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [periods, setPeriods] = useState([]);
  const [activePeriodId, setActivePeriodId] = useState(null);
  const [periodMessage, setPeriodMessage] = useState(null);

  const fetchSummary = useCallback(async (pid) => {
    if (!pid) return;
    setLoadError(null);
    try {
      const res = await fetch(`/api/admin/dashboard/summary?period_id=${pid}`);
      if (!res.ok) throw new Error('ダッシュボードデータの取得に失敗しました');
      setSummary(await res.json());
    } catch (err) {
      setLoadError(err.message);
      setSummary(null);
    }
  }, []);

  useEffect(() => {
    fetch('/api/admin/periods')
      .then((r) => r.json())
      .then((data) => {
        setPeriods(data.periods ?? []);
        const pid = data.active_period_id ?? null;
        setActivePeriodId(pid);
        if (pid) fetchSummary(pid);
      })
      .catch(() => {});
  }, [fetchSummary]);

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
      fetchSummary(activePeriodId);
    } catch (err) {
      setLoadError(err.message);
    }
  };

  const activePeriod = periods.find((p) => p.id === activePeriodId);
  const changeRequests = summary?.change_requests ?? [];

  const handleExportSchedule = () => {
    if (!activePeriodId) return;
    window.open(`/api/export/juku-schedule?period_id=${activePeriodId}`, '_blank');
  };

  if (!isReady) return null;

  return (
    <div className="min-h-screen bg-gray-50 flex font-sans">
      <AdminSidebar navigate={navigate} current="dashboard" />

      <div className="flex-1 p-6 lg:p-8 overflow-y-auto max-w-6xl">
        <header className="mb-6">
          <div className="mb-4">
            <h2 className="text-2xl font-bold text-gray-900">管理ダッシュボード</h2>
            {loadError && <p className="text-red-500 text-sm mt-2">{loadError}</p>}
            {periodMessage && <p className="text-emerald-600 text-sm mt-2 font-bold">{periodMessage}</p>}
            {activePeriod && (
              <p className="text-sm text-gray-600 mt-1">
                {activePeriod.name}（{activePeriod.status}）
              </p>
            )}
          </div>

          <div className="flex flex-wrap gap-2 p-3 bg-white rounded-xl border border-gray-200 shadow-sm">
            <button
              type="button"
              onClick={() => navigate('/import')}
              className="px-4 py-2.5 text-sm bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-bold"
            >
              Excel取込
            </button>
            <button
              type="button"
              onClick={handleExportSchedule}
              disabled={!activePeriodId}
              className="px-4 py-2.5 text-sm bg-emerald-700 hover:bg-emerald-800 disabled:opacity-40 text-white rounded-lg font-bold"
            >
              時間割DL
            </button>
          </div>
        </header>

        <WorkflowGuide
          steps={summary?.workflow_steps ?? DEFAULT_WORKFLOW_STEPS}
          onNavigate={navigate}
        />

        {summary && (
          <div className="space-y-6 mb-8">
            <RolePanel
              roleLabel="生徒"
              roleKey="students"
              data={summary.students}
              openDays={summary.open_days}
            />
            <RolePanel
              roleLabel="講師"
              roleKey="teachers"
              data={summary.teachers}
              openDays={summary.open_days}
            />
          </div>
        )}

        {!summary && !loadError && activePeriodId && (
          <p className="text-gray-500 py-12 text-center">読み込み中...</p>
        )}

        {changeRequests.length > 0 && (
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-5">
            <h3 className="text-base font-bold text-gray-900 mb-1">
              変更申請（承認待ち）
              <span className="ml-2 text-amber-600">{summary?.pending_change_count ?? 0} 件</span>
            </h3>
            <div className="space-y-2 mt-4">
              {changeRequests.map((req) => (
                <div key={req.id} className="flex flex-wrap items-center justify-between gap-3 p-3 bg-amber-50 border border-amber-200 rounded-xl">
                  <div className="text-sm">
                    <span className="font-bold">{req.entity_name}</span>
                    <span className="text-gray-500 ml-2">({req.role === 'teacher' ? '講師' : '生徒'})</span>
                    <div className="text-gray-700 mt-0.5 text-xs">
                      {req.request_type === 'RESUBMIT' ? (
                        <span>スケジュール変更申請（承認後: {req.role === 'student' ? '割当リセット＋再提出' : '再提出'}）</span>
                      ) : (
                        <>
                          {req.date} · {req.slot}コマ:
                          {' '}{req.current_symbol || '空'} → {req.requested_symbol || '空'}
                        </>
                      )}
                      {req.reason && <span className="text-gray-500 ml-2">— {req.reason}</span>}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button type="button" onClick={() => handleResolveChange(req.id, 'approve')} className="px-3 py-1 bg-emerald-600 text-white rounded-lg text-xs font-bold">承認</button>
                    <button type="button" onClick={() => handleResolveChange(req.id, 'reject')} className="px-3 py-1 bg-gray-500 text-white rounded-lg text-xs font-bold">却下</button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
