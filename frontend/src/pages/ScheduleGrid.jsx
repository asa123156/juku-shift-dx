import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAdminSession } from '../hooks/useAdminSession';
import { AdminSidebar } from '../components/AdminSidebar';
import { apiFetch } from '../utils/apiClient';
import { confirmDialog } from '../utils/confirmDialog';
import { parseApiError } from '../utils/apiError';

const WEEKDAY_JA = ['日', '月', '火', '水', '木', '金', '土'];
const SUBJECT_OPTIONS = ['国語', '数学', '英語', '理科', '社会'];
const TEACHERS_PER_PAGE = 6;
const TEACHER_COL_WIDTH_PX = 140;
const TIME_COL_WIDTH_PX = 80;

function formatDayLabel(iso) {
  if (!iso) return '';
  const d = new Date(`${iso}T12:00:00`);
  return `${d.getMonth() + 1}/${d.getDate()}（${WEEKDAY_JA[d.getDay()]}）`;
}

function isRegularAssignment(a) {
  return Boolean(a?.is_fixed || a?.lesson_kind === '通常');
}

function isRegularLane(lane) {
  if (lane?.blocked) return false;
  if (lane?.lesson_kind === '通常' && lane?.occupied) return true;
  return isRegularAssignment(lane?.assignment);
}

function isBlockedCell(slotInfo) {
  const avail = slotInfo?.availability ?? '';
  if (avail === '×' || avail === '不可') return true;
  return (slotInfo?.lanes ?? []).some((l) => l.blocked);
}

function formatRegularSubject(subject) {
  const trimmed = (subject || '').trim();
  return trimmed || '通常';
}

function FixedSlot({ onCancel, assignment }) {
  const subject = formatRegularSubject(assignment?.subject);
  return (
    <button
      type="button"
      onClick={() => assignment && onCancel(assignment)}
      title={assignment ? 'クリックで解除' : undefined}
      className={`w-full h-12 rounded-lg border-2 flex flex-col items-center justify-center transition-colors px-1 ${
        assignment
          ? 'border-amber-300 bg-amber-50 hover:bg-red-50 cursor-pointer'
          : 'border-amber-200 bg-amber-50/80'
      }`}
    >
      <span className="text-xs font-bold text-amber-900 leading-tight truncate max-w-full">{subject}</span>
      {assignment?.student_name && (
        <span className="text-xs text-amber-800/80 truncate max-w-full">{assignment.student_name}</span>
      )}
    </button>
  );
}

function TutoringSlot({ lane, onCancel }) {
  const a = lane?.assignment;
  if (!a) {
    return (
      <div className="h-12 rounded-lg border border-dashed border-gray-200 bg-gray-50/80 flex items-center justify-center">
        <span className="text-xs text-gray-400 font-medium">空き</span>
      </div>
    );
  }
  return (
    <button
      type="button"
      onClick={() => onCancel(a)}
      title="クリックで解除"
      className="w-full h-12 rounded-lg border border-sky-200 bg-sky-50 hover:bg-red-50 px-2 text-left transition-colors"
    >
      <p className="text-xs font-bold text-sky-900 leading-tight truncate">{a.subject}</p>
      <p className="text-xs text-gray-600 truncate">{a.student_name}</p>
    </button>
  );
}

function ModeToggle({ mode, onChange, disabled }) {
  return (
    <div className="flex rounded-lg overflow-hidden border border-gray-200 text-xs font-bold mb-2">
      {[
        { id: 'tutoring', label: '講習' },
        { id: 'fixed', label: '通常授業' },
      ].map(({ id, label }) => (
        <button
          key={id}
          type="button"
          disabled={disabled}
          onClick={() => onChange(id)}
          className={`flex-1 py-1 transition-colors ${
            mode === id ? 'bg-gray-800 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'
          } disabled:opacity-50`}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

function FormatToggle({ maxLanes, disabled, onChange }) {
  return (
    <div className="flex gap-1 mb-2">
      {[2, 4].map((ml) => (
        <button
          key={ml}
          type="button"
          disabled={disabled}
          onClick={() => onChange(ml)}
          className={`flex-1 text-xs py-0.5 rounded font-bold border transition-colors ${
            maxLanes === ml
              ? 'bg-violet-600 text-white border-violet-600'
              : 'bg-white text-gray-500 border-gray-200 hover:border-violet-300'
          } disabled:opacity-50`}
        >
          {ml === 2 ? '1対2' : '1対4'}
        </button>
      ))}
    </div>
  );
}

function GridCell({
  slotInfo,
  teacherId,
  teacherName,
  slotNum,
  date,
  periodId,
  scheduleMode,
  savingKey,
  onSave,
  onCancel,
  onCapacityChange,
}) {
  const [mode, setMode] = useState('tutoring');
  const [subject, setSubject] = useState('');
  const [studentName, setStudentName] = useState('');
  const key = `${teacherId}-${slotNum}`;
  const isSaving = savingKey === key;
  const blocked = isBlockedCell(slotInfo);
  const lanes = slotInfo?.lanes ?? [];
  const maxLanes = slotInfo?.max_lanes ?? 2;
  const assignable = Boolean(slotInfo?.assignable) && !blocked;

  const regularLane = lanes.find((l) => isRegularLane(l));
  const tutoringLanes = lanes.filter((l) => !isRegularLane(l) && !l.blocked);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const name = studentName.trim();
    const subj = subject.trim();
    if (!name || !subj || isSaving) return;
    const ok = await onSave({
      date,
      teacherId,
      teacherName,
      slot: slotNum,
      subject: subj,
      studentName: name,
      isFixed: mode === 'fixed',
      key,
    });
    if (ok) {
      setSubject('');
      setStudentName('');
    }
  };

  if (blocked) {
    return (
      <td className="border border-gray-200 p-2 align-middle bg-gray-50/60 text-center w-[140px] max-w-[140px]">
        <span className="text-xl font-bold text-gray-300">×</span>
      </td>
    );
  }

  return (
    <td className="border border-gray-200 p-2 align-top w-[140px] max-w-[140px] bg-white">
      <FormatToggle
        maxLanes={maxLanes}
        disabled={isSaving}
        onChange={(ml) => onCapacityChange({ date, teacherId, slot: slotNum, maxLanes: ml, key })}
      />

      {regularLane && (
        <div className="mb-1.5">
          <FixedSlot assignment={regularLane.assignment} onCancel={onCancel} />
        </div>
      )}

      <div className={`flex flex-col gap-1 ${regularLane ? 'mt-1' : ''}`}>
        {tutoringLanes.map((lane, idx) => (
          <TutoringSlot key={lane.lane ?? idx} lane={lane} onCancel={onCancel} />
        ))}
      </div>

      {assignable && (
        <form onSubmit={handleSubmit} className="mt-2 pt-2 border-t border-gray-100 space-y-1.5">
          <ModeToggle mode={mode} onChange={setMode} disabled={isSaving} />
          {mode === 'fixed' && (
            <p className="text-xs text-amber-700 font-medium leading-snug">
              {scheduleMode === 'cram'
                ? '同一曜日・同じコマに講習期間中すべて展開されます'
                : '同一曜日・同じコマに年度内の開校日すべて展開されます'}
            </p>
          )}
          <input
            type="text"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            placeholder="科目"
            list="grid-subject-options"
            disabled={isSaving}
            className={`w-full text-xs border rounded-md px-2 py-1.5 focus:outline-none focus:ring-2 ${
              mode === 'fixed'
                ? 'border-amber-200 focus:ring-amber-300'
                : 'border-gray-200 focus:ring-sky-300'
            }`}
          />
          <input
            type="text"
            value={studentName}
            onChange={(e) => setStudentName(e.target.value)}
            placeholder="生徒名"
            list="grid-student-options"
            disabled={isSaving}
            className={`w-full text-xs border rounded-md px-2 py-1.5 focus:outline-none focus:ring-2 ${
              mode === 'fixed'
                ? 'border-amber-200 focus:ring-amber-300'
                : 'border-gray-200 focus:ring-sky-300'
            }`}
          />
          <button
            type="submit"
            disabled={isSaving || !studentName.trim() || !subject.trim()}
            className={`w-full text-xs py-1.5 rounded-md text-white font-bold disabled:bg-gray-300 ${
              mode === 'fixed' ? 'bg-amber-700 hover:bg-amber-800' : 'bg-gray-800 hover:bg-gray-900'
            }`}
          >
            {isSaving ? '保存中…' : '登録'}
          </button>
        </form>
      )}
    </td>
  );
}

export default function ScheduleGrid() {
  const navigate = useNavigate();
  const isReady = useAdminSession();
  const [selectedDate, setSelectedDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [regularPeriodId, setRegularPeriodId] = useState(null);
  const [cramPeriodId, setCramPeriodId] = useState(null);
  const [scheduleMode, setScheduleMode] = useState('regular');
  const [periodId, setPeriodId] = useState(null);
  const [periodName, setPeriodName] = useState('');
  const [grid, setGrid] = useState(null);
  const [students, setStudents] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [savingKey, setSavingKey] = useState(null);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);
  const [teacherPage, setTeacherPage] = useState(0);

  const fetchGrid = useCallback(async (date) => {
    if (!date) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await apiFetch(`/api/admin/assignments/grid?date=${encodeURIComponent(date)}`);
      if (!res.ok) throw new Error(await parseApiError(res, '時間割の取得に失敗しました'));
      const data = await res.json();
      setGrid(data);
      const ctx = data.period_context;
      if (ctx) {
        setRegularPeriodId(ctx.regular_period_id);
        setCramPeriodId(ctx.cram_period_id);
        setScheduleMode(ctx.mode);
        setPeriodId(ctx.regular_period_id);
        setPeriodName(
          ctx.mode === 'cram' && ctx.cram_period_name
            ? `${ctx.regular_period_name} · ${ctx.cram_period_name}`
            : ctx.regular_period_name,
        );
      }
    } catch (err) {
      setError(err.message);
      setGrid(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isReady) return;
    apiFetch('/api/admin/students')
      .then((r) => r.json())
      .then((data) => setStudents(data.students ?? []))
      .catch(() => {});
  }, [isReady]);

  useEffect(() => {
    if (selectedDate) fetchGrid(selectedDate);
  }, [selectedDate, fetchGrid]);

  useEffect(() => {
    setTeacherPage(0);
  }, [selectedDate]);

  const timeSlots = grid?.time_slots ?? [];
  const teachers = grid?.teachers ?? [];
  const totalTeacherPages = Math.max(1, Math.ceil(teachers.length / TEACHERS_PER_PAGE));
  const visibleTeachers = useMemo(() => {
    const start = teacherPage * TEACHERS_PER_PAGE;
    return teachers.slice(start, start + TEACHERS_PER_PAGE);
  }, [teachers, teacherPage]);
  const tableWidthPx = TIME_COL_WIDTH_PX + visibleTeachers.length * TEACHER_COL_WIDTH_PX;
  const slotByTeacher = useMemo(() => {
    const map = {};
    for (const t of teachers) {
      map[t.id] = Object.fromEntries((t.slots ?? []).map((s) => [s.slot, s]));
    }
    return map;
  }, [teachers]);

  useEffect(() => {
    if (teacherPage >= totalTeacherPages) {
      setTeacherPage(Math.max(0, totalTeacherPages - 1));
    }
  }, [teacherPage, totalTeacherPages]);

  const handleCapacityChange = async ({ date, teacherId, slot, maxLanes, key }) => {
    setSavingKey(key);
    setError(null);
    try {
      const res = await apiFetch('/api/admin/assignments/grid/capacity', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ date, teacher_id: teacherId, slot, max_lanes: maxLanes }),
      });
      if (!res.ok) throw new Error(await parseApiError(res, '授業形態の変更に失敗しました'));
      setGrid(await res.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setSavingKey(null);
    }
  };

  const handleCellSave = async ({ date, teacherId, teacherName, slot, subject, studentName, isFixed, key }) => {
    const targetPeriodId = isFixed ? regularPeriodId : (cramPeriodId ?? regularPeriodId);
    if (!targetPeriodId) {
      setError('年度または講習期間が設定されていません');
      return false;
    }
    setSavingKey(key);
    setError(null);
    try {
      const res = await apiFetch('/api/admin/assignments/manual', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          date,
          student_name: studentName,
          subject,
          teacher_id: teacherId,
          slot,
          period_id: targetPeriodId,
          skip_rules: true,
          is_fixed: isFixed,
        }),
      });
      if (!res.ok) throw new Error(await parseApiError(res, '保存に失敗しました'));
      setGrid(await res.json());
      setMessage(
        isFixed
          ? `${studentName}（${subject}）を同一曜日の開校日すべてに登録しました`
          : `${studentName}（${subject}）を ${teacherName} に登録しました`,
      );
      return true;
    } catch (err) {
      setError(err.message);
      return false;
    } finally {
      setSavingKey(null);
    }
  };

  const handleCancel = async (assignment) => {
    const cancelPeriodId = isRegularAssignment(assignment)
      ? regularPeriodId
      : (cramPeriodId ?? regularPeriodId);
    if (!cancelPeriodId || !assignment) return;
    const label = isRegularAssignment(assignment)
      ? `${assignment.student_name} の通常授業`
      : `${assignment.student_name} の ${assignment.subject}`;
    if (!(await confirmDialog({ title: `${label} を解除しますか？`, confirmLabel: '解除する', destructive: true }))) return;
    try {
      const res = await apiFetch('/api/admin/assignments/cancel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          date: assignment.date || selectedDate,
          teacher_id: assignment.teacher_id,
          slot: assignment.slot,
          period_id: cancelPeriodId,
          student_id: assignment.student_id,
        }),
      });
      if (!res.ok) throw new Error(await parseApiError(res, '割当解除に失敗しました'));
      await fetchGrid(selectedDate);
      setMessage('割当を解除しました');
    } catch (err) {
      setError(err.message);
    }
  };

  const shiftDate = (delta) => {
    if (!selectedDate) return;
    const d = new Date(`${selectedDate}T12:00:00`);
    d.setDate(d.getDate() + delta);
    setSelectedDate(d.toISOString().slice(0, 10));
  };

  if (!isReady) return null;

  return (
    <div className="min-h-screen bg-slate-100 flex font-sans">
      <AdminSidebar navigate={navigate} current="schedule-grid" />

      <datalist id="grid-subject-options">
        {SUBJECT_OPTIONS.map((s) => (
          <option key={s} value={s} />
        ))}
      </datalist>
      <datalist id="grid-student-options">
        {students.map((s) => (
          <option key={s.id} value={s.name} />
        ))}
      </datalist>

      <div className="flex-1 flex flex-col min-w-0">
        <div className="bg-white border-b border-gray-200 px-4 lg:px-6 py-4">
          <div className="flex flex-wrap justify-between items-start gap-3">
            <div>
              <h2 className="text-xl font-bold text-gray-900">時間割表</h2>
              <p className="text-sm text-gray-500 mt-0.5">
                {periodName && `${periodName} · `}
                {selectedDate ? formatDayLabel(selectedDate) : ''}
              </p>
              <p className="text-xs text-gray-400 mt-1">
                正本データベース。通常授業（{scheduleMode === 'cram' ? '年度＋講習' : '年度'}）と講習枠をここで編集します。
              </p>
            </div>
            <div className="flex flex-wrap gap-2 items-center">
              <button type="button" onClick={() => shiftDate(-1)} className="px-2.5 py-1.5 text-sm border rounded-lg bg-white hover:bg-gray-50">←</button>
              <input
                type="date"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                className="border rounded-lg px-2 py-1.5 text-sm font-medium"
              />
              <button type="button" onClick={() => shiftDate(1)} className="px-2.5 py-1.5 text-sm border rounded-lg bg-white hover:bg-gray-50">→</button>
            </div>
          </div>
          {error && <p className="text-red-600 text-sm mt-2">{error}</p>}
          {message && <p className="text-emerald-600 text-sm mt-2 font-bold">{message}</p>}
          <div className="flex flex-wrap gap-4 mt-3 text-xs text-gray-500">
            <span className="flex items-center gap-1"><span className="inline-block w-5 h-5 rounded border-2 border-amber-300 bg-amber-50" /> 通常授業</span>
            <span className="flex items-center gap-1"><span className="inline-block w-5 h-5 rounded border border-sky-200 bg-sky-50" /> 講習</span>
            <span className="flex items-center gap-1"><span className="inline-block w-5 h-5 rounded border border-dashed border-gray-200" /> 空き</span>
          </div>
        </div>

        <div className="flex-1 p-4 lg:p-6 overflow-auto">
          {!regularPeriodId && !isLoading && (
            <p className="text-amber-800 bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm">年度が初期化されていません。ページを再読み込みしてください。</p>
          )}
          {isLoading ? (
            <p className="text-gray-500 py-16 text-center">読み込み中...</p>
          ) : teachers.length === 0 ? (
            <p className="text-gray-500 py-16 text-center">講師が登録されていません。</p>
          ) : (
            <>
              {teachers.length > TEACHERS_PER_PAGE && (
                <div className="flex items-center justify-end gap-2 mb-3">
                  <span className="text-xs text-gray-500 mr-1">
                    講師 {teacherPage * TEACHERS_PER_PAGE + 1}–{Math.min((teacherPage + 1) * TEACHERS_PER_PAGE, teachers.length)} / {teachers.length} 名
                  </span>
                  <button
                    type="button"
                    disabled={teacherPage === 0}
                    onClick={() => setTeacherPage((p) => Math.max(0, p - 1))}
                    className="px-3 py-1.5 rounded-lg border border-gray-300 bg-white hover:bg-gray-50 text-sm font-bold disabled:opacity-40 disabled:cursor-not-allowed"
                    aria-label="前の講師ページ"
                  >
                    ←
                  </button>
                  <span className="text-xs font-bold text-gray-600 min-w-[3rem] text-center">
                    {teacherPage + 1} / {totalTeacherPages}
                  </span>
                  <button
                    type="button"
                    disabled={teacherPage >= totalTeacherPages - 1}
                    onClick={() => setTeacherPage((p) => Math.min(totalTeacherPages - 1, p + 1))}
                    className="px-3 py-1.5 rounded-lg border border-gray-300 bg-white hover:bg-gray-50 text-sm font-bold disabled:opacity-40 disabled:cursor-not-allowed"
                    aria-label="次の講師ページ"
                  >
                    →
                  </button>
                </div>
              )}
              <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white shadow-sm">
              <table
                className="border-collapse text-sm table-fixed"
                style={{ width: `${tableWidthPx}px` }}
              >
                <thead>
                  <tr className="bg-slate-50">
                    <th className="sticky left-0 z-10 bg-slate-50 border-b border-r border-gray-200 px-3 py-2 text-left text-xs font-bold text-gray-600 w-20">時間</th>
                    {visibleTeachers.map((t) => (
                      <th key={t.id} className="border-b border-gray-200 px-2 py-2 text-center w-[140px]">
                        <div className={`mx-auto w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold mb-1 ${t.color || 'bg-gray-200 text-gray-700'}`}>
                          {t.name.charAt(0)}
                        </div>
                        <span className="text-xs font-bold text-gray-800 truncate block">{t.name}</span>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {timeSlots.map((ts) => (
                    <tr key={ts.slot} className="hover:bg-slate-50/50">
                      <td className="sticky left-0 z-10 bg-white border-r border-b border-gray-200 px-3 py-2 w-20">
                        <div className="text-xs font-bold text-gray-800">{ts.start}</div>
                        <div className="text-xs text-gray-400">{ts.end} · {ts.slot}コマ</div>
                      </td>
                      {visibleTeachers.map((t) => (
                        <GridCell
                          key={`${t.id}-${ts.slot}`}
                          slotInfo={slotByTeacher[t.id]?.[ts.slot]}
                          teacherId={t.id}
                          teacherName={t.name}
                          slotNum={ts.slot}
                          date={selectedDate}
                          periodId={periodId}
                          scheduleMode={scheduleMode}
                          savingKey={savingKey}
                          onSave={handleCellSave}
                          onCancel={handleCancel}
                          onCapacityChange={handleCapacityChange}
                        />
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
