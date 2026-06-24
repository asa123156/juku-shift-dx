import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useAdminSession } from '../hooks/useAdminSession';
import { AdminSidebar } from '../components/AdminSidebar';
import { DEFAULT_MATCH_RULES, MatchRulesPanel, collectSubjects } from '../components/MatchRulesPanel';

function familyName(fullName) {
  if (!fullName) return '';
  const parts = fullName.trim().split(/\s+/);
  if (parts.length > 1) return parts[0];
  return fullName.trim().slice(0, 2);
}

function subjectAbbr(subject) {
  if (typeof subject !== 'string' || !subject) return '';
  const map = {
    数学I: '数', 数学II: '数', 数学: '数',
    英語: '英', 国語: '国', 理科: '理', 社会: '社',
  };
  return map[subject] ?? subject.slice(0, 2);
}

function PaperSheet({ title, entityName, subtitle, children }) {
  return (
    <div className="flex-1 min-w-0 bg-white border-2 border-gray-800 rounded-sm shadow-md flex flex-col">
      <div className="border-b-2 border-gray-800 px-4 py-3 bg-gray-50">
        <div className="text-xs text-gray-500 tracking-widest">{title}</div>
        <div className="flex justify-between items-baseline mt-1 gap-2 flex-wrap">
          <h3 className="text-lg font-bold text-gray-900">{entityName}</h3>
          {subtitle && <span className="text-sm font-bold text-gray-700">{subtitle}</span>}
        </div>
      </div>
      <div className="flex-1 overflow-auto p-2">{children}</div>
    </div>
  );
}

function StudentSlotCell({ slot, pendingSubjects, onCancel }) {
  const a = slot?.assignment;
  if (a) {
    return (
      <button
        type="button"
        onClick={() => onCancel?.(a)}
        title="クリックで割当解除"
        className="w-full text-center py-1 px-0.5 hover:bg-red-50 rounded transition-colors"
      >
        <div className="text-base font-bold text-blue-800">{subjectAbbr(a.subject)}</div>
      </button>
    );
  }
  const avail = typeof slot?.availability === 'string' ? slot.availability : '';
  if (avail === '◎') {
    const hint = pendingSubjects?.length === 1 ? subjectAbbr(pendingSubjects[0]) : '';
    return (
      <div className="text-center py-1">
        <div className="text-lg font-bold text-rose-600">◎</div>
        {hint && <div className="text-xs font-bold text-gray-700">{hint}</div>}
      </div>
    );
  }
  if (avail === '×') {
    return <div className="text-center py-1 text-lg font-bold text-gray-400">×</div>;
  }
  return <div className="text-center py-1 text-[11px] font-bold text-emerald-600">空き</div>;
}

function TeacherSlotCell({ slot, onAssign, onCancel }) {
  const lanes = slot?.lanes?.length === 2
    ? slot.lanes
    : null;
  const list = slot?.assignments?.length ? slot.assignments : (slot?.assignment ? [slot.assignment] : []);
  const canAssign = slot?.assignable;

  function LaneBox({ lane, idx }) {
    if (lane?.blocked) {
      return (
        <div className="w-full min-h-[40px] rounded border border-gray-200 bg-gray-100 relative overflow-hidden">
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div className="w-full h-px bg-gray-400 rotate-45 scale-150" />
          </div>
        </div>
      );
    }
    if (lane?.occupied && lane.lesson_kind === '通常') {
      return (
        <div className="w-full min-h-[40px] rounded border border-rose-200 bg-rose-50 p-1 text-center">
          <div className="text-[10px] font-bold text-rose-700">通常</div>
          <div className="text-sm font-bold text-rose-600">◎</div>
        </div>
      );
    }
    if (lane?.assignment) {
      const a = lane.assignment;
      return (
        <button
          type="button"
          onClick={() => onCancel?.(a)}
          title="クリックで割当解除"
          className="w-full min-h-[40px] rounded border border-emerald-200 bg-emerald-50 hover:bg-red-50 p-1 text-center"
        >
          <div className="text-[10px] font-bold text-emerald-800 leading-tight">
            {familyName(a.student_name)}
          </div>
          <div className="text-[10px] text-emerald-700">{subjectAbbr(a.subject)}</div>
        </button>
      );
    }
    if (canAssign) {
      return (
        <button
          type="button"
          onClick={onAssign}
          className="w-full min-h-[40px] rounded border border-dashed border-gray-300 hover:bg-blue-50 hover:border-blue-300 text-[10px] font-bold text-gray-400"
        >
          空き
        </button>
      );
    }
    return (
      <div className="w-full min-h-[40px] rounded border border-gray-100 bg-gray-50 text-[10px] text-gray-300 flex items-center justify-center">
        —
      </div>
    );
  }

  if (lanes) {
    return (
      <div className="flex flex-col gap-0.5 min-h-[40px]">
        {lanes.map((lane, idx) => (
          <LaneBox key={lane.lane ?? idx} lane={lane} idx={idx} />
        ))}
      </div>
    );
  }

  // fallback（旧形式）
  const blocked = slot?.availability === '◎' || slot?.availability === '×';
  if (list.length > 0) {
    return (
      <div className="flex flex-col gap-0.5 min-h-[36px]">
        {list.map((a) => (
          <button
            key={`${a.student_id}-${a.subject}`}
            type="button"
            onClick={() => onCancel?.(a)}
            title="クリックで割当解除"
            className="w-full text-center py-0.5 px-0.5 bg-emerald-50 hover:bg-red-50 rounded transition-colors"
          >
            <div className="text-[11px] font-bold text-emerald-800 leading-tight">
              {familyName(a.student_name)} {subjectAbbr(a.subject)}
            </div>
          </button>
        ))}
        {canAssign && (
          <button
            type="button"
            onClick={onAssign}
            className="w-full text-center py-0.5 text-[10px] font-bold text-gray-400 hover:bg-blue-50 hover:text-blue-600 rounded"
          >
            ＋
          </button>
        )}
      </div>
    );
  }
  if (blocked && !canAssign) {
    return (
      <div className="text-center py-1 bg-gray-100 rounded relative overflow-hidden min-h-[36px]">
        {slot.availability === '×' && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div className="w-full h-px bg-gray-400 rotate-45 scale-150" />
          </div>
        )}
        <span className={`text-lg font-bold relative ${slot.availability === '◎' ? 'text-rose-600' : ''}`}>
          {slot.availability === '◎' ? '◎' : ''}
        </span>
      </div>
    );
  }
  return (
    <button
      type="button"
      onClick={onAssign}
      className="w-full text-center py-1 text-[11px] font-bold text-gray-400 hover:bg-blue-50 hover:text-blue-600 rounded min-h-[36px]"
    >
      空き
    </button>
  );
}

function MultiDayTable({ timeSlots, dates, renderCell }) {
  return (
    <table className="w-full border-collapse text-sm min-w-[600px]">
      <thead>
        <tr className="border-b-2 border-gray-800">
          <th className="p-1.5 text-left font-bold w-20 border-r border-gray-300 bg-gray-50 sticky left-0 z-10">時間</th>
          {dates.map((d) => (
            <th key={d.date} className="p-1 text-center font-bold min-w-[52px] text-xs">
              <div>{d.label}</div>
              <div className="font-normal text-gray-500">({d.weekday})</div>
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {timeSlots.map((ts) => (
          <tr key={ts.slot} className="border-b border-gray-200">
            <td className="p-1.5 border-r border-gray-200 bg-gray-50 sticky left-0 z-10 align-middle">
              <div className="font-bold text-xs">{ts.slot}コマ</div>
              <div className="text-[10px] text-gray-500 whitespace-nowrap">{ts.start}〜</div>
            </td>
            {dates.map((d) => (
              <td key={d.date} className="p-0.5 align-middle border-r border-gray-100 last:border-r-0">
                {renderCell(d.date, ts.slot)}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function TeacherSwitcher({ teachers, selectedIdx, onSelect }) {
  if (!teachers.length) return null;
  const prev = () => onSelect((selectedIdx - 1 + teachers.length) % teachers.length);
  const next = () => onSelect((selectedIdx + 1) % teachers.length);

  return (
    <div className="flex items-center gap-2 mb-3 flex-wrap">
      <span className="text-xs font-bold text-gray-500">講師</span>
      <button type="button" onClick={prev} className="px-2 py-1 rounded border border-gray-300 bg-white hover:bg-gray-100 text-sm font-bold">◀</button>
      <div className="flex gap-1 flex-wrap">
        {teachers.map((t, idx) => (
          <button
            key={t.id}
            type="button"
            onClick={() => onSelect(idx)}
            className={`px-3 py-1 rounded-full text-sm font-bold border transition-colors ${
              idx === selectedIdx ? 'bg-gray-800 text-white border-gray-800' : 'bg-white text-gray-700 border-gray-300 hover:border-gray-500'
            }`}
          >
            {t.name}
          </button>
        ))}
      </div>
      <button type="button" onClick={next} className="px-2 py-1 rounded border border-gray-300 bg-white hover:bg-gray-100 text-sm font-bold">▶</button>
      <span className="text-xs text-gray-400">{selectedIdx + 1}/{teachers.length}</span>
    </div>
  );
}

export default function AssignmentBoard() {
  const navigate = useNavigate();
  const { studentId } = useParams();
  const isReady = useAdminSession();
  const [periodId, setPeriodId] = useState(null);
  const [sheets, setSheets] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAutoAssigning, setIsAutoAssigning] = useState(false);
  const [message, setMessage] = useState(null);
  const [teacherIdx, setTeacherIdx] = useState(0);
  const [manualOpen, setManualOpen] = useState(false);
  const [manualTarget, setManualTarget] = useState(null);
  const [selectedRequestIdx, setSelectedRequestIdx] = useState(0);
  const [matchRules, setMatchRules] = useState(DEFAULT_MATCH_RULES);
  const [isPublishing, setIsPublishing] = useState(false);

  const fetchSheets = useCallback(async (pid) => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const res = await fetch(`/api/admin/assignments/sheets?period_id=${pid}`);
      if (!res.ok) throw new Error('スケジュールの取得に失敗しました');
      setSheets(await res.json());
    } catch (err) {
      setLoadError(err.message);
      setSheets(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isReady) return;
    (async () => {
      try {
        const periodsRes = await fetch('/api/admin/periods');
        if (!periodsRes.ok) throw new Error('期間の取得に失敗しました');
        const periodsData = await periodsRes.json();
        const pid = periodsData.active_period_id ?? periodsData.periods?.[0]?.id;
        if (!pid) throw new Error('募集期間がありません');
        setPeriodId(pid);
        await fetchSheets(pid);
      } catch (err) {
        setLoadError(err.message);
        setIsLoading(false);
      }
    })();
  }, [isReady, fetchSheets]);

  if (!isReady) return null;

  const sid = Number(studentId);
  const dates = sheets?.dates ?? [];
  const timeSlots = sheets?.time_slots ?? [];
  const students = sheets?.students ?? [];
  const teachers = sheets?.teachers ?? [];
  const currentStudent = students.find((s) => s.id === sid) ?? null;
  const currentTeacher = teachers[teacherIdx] ?? null;
  const manualPending = manualTarget ? (sheets?.pending_by_date?.[manualTarget.date] ?? []) : [];
  const ruleSubjects = collectSubjects(students, matchRules.weekly_limits);
  const studentPending = currentStudent?.pending_count ?? 0;
  const schedulePublished = currentStudent?.schedule_published ?? false;

  const handleAutoAssign = async () => {
    if (!periodId) return;
    setIsAutoAssigning(true);
    setMessage(null);
    setLoadError(null);
    try {
      const res = await fetch('/api/admin/auto-assign-period', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ period_id: periodId, rules: matchRules }),
      });
      if (!res.ok) throw new Error('自動割当に失敗しました');
      const data = await res.json();
      setSheets(data.sheets);
      setMessage(data.message);
    } catch (err) {
      setLoadError(err.message);
    } finally {
      setIsAutoAssigning(false);
    }
  };

  const openManual = (date, teacherId, teacherName, slot) => {
    setManualTarget({ date, teacherId, teacherName, slot });
    setSelectedRequestIdx(0);
    setManualOpen(true);
  };

  const handleManualAssign = async () => {
    const pending = sheets?.pending_by_date?.[manualTarget?.date] ?? [];
    const req = pending[selectedRequestIdx];
    if (!req || !manualTarget) return;
    try {
      const res = await fetch('/api/admin/assignments/manual', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          date: manualTarget.date,
          student_id: req.student_id,
          student_name: req.student_name,
          subject: req.subject,
          teacher_id: manualTarget.teacherId,
          slot: manualTarget.slot,
          period_id: periodId,
          rules: matchRules,
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || '手動割当に失敗しました');
      }
      await fetchSheets(periodId);
      setManualOpen(false);
      setMessage(`${req.student_name} を ${manualTarget.teacherName} ${manualTarget.slot}コマ（${manualTarget.date}）に割当しました`);
    } catch (err) {
      setLoadError(err.message);
    }
  };

  const handleCancel = async (assignment) => {
    if (!periodId || !assignment) return;
    if (!window.confirm(`${assignment.student_name} の ${assignment.subject} 割当を解除しますか？`)) return;
    try {
      const res = await fetch('/api/admin/assignments/cancel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          date: assignment.date,
          teacher_id: assignment.teacher_id,
          slot: assignment.slot,
          period_id: periodId,
          student_id: assignment.student_id,
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || '割当解除に失敗しました');
      }
      const data = await res.json();
      setSheets(data.sheets);
      setMessage(data.message);
    } catch (err) {
      setLoadError(err.message);
    }
  };

  const handlePublishSchedule = async () => {
    const publishStudentId = Number(studentId);
    if (!periodId || !publishStudentId || studentPending > 0 || isPublishing) return;
    setIsPublishing(true);
    setMessage(null);
    setLoadError(null);
    try {
      const res = await fetch('/api/admin/assignments/publish-schedule', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ period_id: periodId, student_id: publishStudentId }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || 'スケジュール送信に失敗しました');
      }
      const data = await res.json();
      setSheets(data.sheets);
      setMessage(data.message);
    } catch (err) {
      setLoadError(err.message);
    } finally {
      setIsPublishing(false);
    }
  };

  if (!isLoading && !currentStudent && sheets) {
    return (
      <div className="min-h-screen bg-gray-50 flex font-sans">
        <AdminSidebar navigate={navigate} current="assignments" />
        <div className="flex-1 p-8">
          <p className="text-red-500 mb-4">生徒 ID={studentId} が見つかりません</p>
          <button type="button" onClick={() => navigate('/admin/assignments')} className="text-blue-600 font-bold">← 生徒一覧へ</button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100 flex font-sans relative">
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
              {manualTarget.teacherName} — {manualTarget.date} {manualTarget.slot}コマ
            </p>
            {manualPending.length === 0 ? (
              <p className="text-gray-500 text-sm mb-6">この日の未割当リクエストがありません。</p>
            ) : (
              <div className="space-y-2 mb-6 max-h-48 overflow-y-auto">
                {manualPending.map((r, idx) => (
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
              <button type="button" onClick={handleManualAssign} disabled={!manualPending.length} className="flex-1 py-3 bg-blue-600 text-white rounded-xl font-bold disabled:bg-blue-300">割当する</button>
            </div>
          </div>
        </div>
      )}

      <AdminSidebar navigate={navigate} current="assignments" />

      <div className="flex-1 p-4 lg:p-6 overflow-y-auto min-w-0">
        <header className="mb-4 flex justify-between items-start flex-wrap gap-3">
          <div>
            <button type="button" onClick={() => navigate('/admin/assignments')} className="text-sm text-blue-600 font-bold mb-2 hover:underline">
              ← 生徒の割り当て
            </button>
            <h2 className="text-2xl font-bold text-gray-800">
              {currentStudent?.name ?? '…'}
              {currentStudent?.grade_label && (
                <span className="text-base font-normal text-gray-500 ml-2">{currentStudent.grade_label}</span>
              )}
              の割当
            </h2>
            <p className="text-sm text-gray-500 mt-1">
              {sheets?.period_name} — {dates.length}日分（日曜除く）
              {(studentPending ?? 0) > 0 && (
                <span className="ml-2 text-amber-600 font-bold">未割当 {studentPending} 件</span>
              )}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={handlePublishSchedule}
              disabled={isLoading || isPublishing || !periodId || schedulePublished || studentPending > 0}
              title={studentPending > 0 ? `未割当が ${studentPending} 件残っています` : undefined}
              className="bg-emerald-600 hover:bg-emerald-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white px-5 py-2.5 rounded-xl font-bold shadow-md text-sm"
            >
              {schedulePublished
                ? '✓ 送信済み'
                : isPublishing
                  ? '送信中...'
                  : studentPending > 0
                    ? '未割当のため確定不可'
                    : '確定して生徒に送信'}
            </button>
            <button
              type="button"
              onClick={handleAutoAssign}
              disabled={isAutoAssigning || isLoading || !periodId}
              className="bg-purple-600 hover:bg-purple-700 text-white px-5 py-2.5 rounded-xl font-bold shadow-md text-sm"
            >
              ✨ 期間一括 自動マッチング
            </button>
          </div>
        </header>

        {loadError && <p className="text-red-500 mb-3">{loadError}</p>}
        {message && <p className="text-emerald-600 font-bold mb-3 text-sm">{message}</p>}

        <MatchRulesPanel rules={matchRules} onChange={setMatchRules} subjects={ruleSubjects} />

        {isLoading ? (
          <p className="p-8 text-center text-gray-500">読み込み中...</p>
        ) : (
          <div className="flex gap-3 items-start flex-col xl:flex-row">
            <div className="w-full xl:w-1/2 flex flex-col min-h-[360px]">
              <PaperSheet title="授業希望表" entityName={currentStudent?.name ?? ''} subtitle={`${dates.length}日分`}>
                <MultiDayTable
                  timeSlots={timeSlots}
                  dates={dates}
                  renderCell={(isoDate, slotNum) => {
                    const day = currentStudent?.days?.[isoDate];
                    const slot = day?.slots?.find((s) => s.slot === slotNum);
                    return (
                      <StudentSlotCell
                        slot={slot}
                        pendingSubjects={day?.pending_subjects ?? []}
                        onCancel={handleCancel}
                      />
                    );
                  }}
                />
              </PaperSheet>
            </div>

            <div className="w-full xl:w-1/2 flex flex-col min-h-[360px]">
              <TeacherSwitcher teachers={teachers} selectedIdx={teacherIdx} onSelect={setTeacherIdx} />
              {currentTeacher ? (
                <PaperSheet title="講師スケジュール" entityName={currentTeacher.name} subtitle={`${dates.length}日分`}>
                  <p className="text-[10px] text-gray-500 mb-1 px-1">①② = 2レーン（通常◎があっても片方に追加割当可）</p>
                  <MultiDayTable
                    timeSlots={timeSlots}
                    dates={dates}
                    renderCell={(isoDate, slotNum) => {
                      const day = currentTeacher.days?.[isoDate];
                      const slot = day?.slots?.find((s) => s.slot === slotNum);
                      return (
                        <TeacherSlotCell
                          slot={slot}
                          onAssign={() => openManual(isoDate, currentTeacher.id, currentTeacher.name, slotNum)}
                          onCancel={handleCancel}
                        />
                      );
                    }}
                  />
                </PaperSheet>
              ) : (
                <div className="flex-1 bg-white border-2 border-dashed border-gray-300 rounded-sm flex items-center justify-center text-gray-400 p-8">
                  講師データがありません
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
