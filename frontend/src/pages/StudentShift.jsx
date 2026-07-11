import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { loadSession, clearSession } from '../utils/session';
import { apiFetch } from '../utils/apiClient';
import { confirmDialog } from '../utils/confirmDialog';
import {
  apiSlotsToState,
  EMPTY_SLOTS,
  ScheduleLegend,
  stateToApiSlots,
  TimeSlotRow,
  PeriodBanner,
  DateTabs,
  DayScheduleOverview,
  collectProposalChanges,
  submitChangeProposal,
} from '../components/ScheduleEditor';
import { UserPhaseStepper } from '../components/UserPhaseStepper';
import { PasswordChangeModal } from '../components/PasswordChangeModal';
import {
  fetchScheduleContext,
  formatMonthLabel,
  monthScheduleQuery,
  shiftMonth,
} from '../utils/scheduleContext';

export default function StudentShift() {
  const navigate = useNavigate();

  const [teacherId, setTeacherId] = useState(null);
  const [teacherName, setTeacherName] = useState('');
  const [dates, setDates] = useState([]);
  const [selectedDate, setSelectedDate] = useState(null);
  const [scheduleByDate, setScheduleByDate] = useState({});
  const [lockedByDate, setLockedByDate] = useState({});
  const [lessonsByDate, setLessonsByDate] = useState({});
  const [teacherLanesByDate, setTeacherLanesByDate] = useState({});
  const [scheduleMode, setScheduleMode] = useState('regular');
  const [calendarYear, setCalendarYear] = useState(null);
  const [calendarMonth, setCalendarMonth] = useState(null);
  const [periodId, setPeriodId] = useState(null);
  const [periodName, setPeriodName] = useState('');
  const [periodStart, setPeriodStart] = useState('');
  const [periodEnd, setPeriodEnd] = useState('');
  const [periodStatus, setPeriodStatus] = useState(null);
  const [submissionDeadline, setSubmissionDeadline] = useState(null);
  const [scheduleRequested, setScheduleRequested] = useState(false);
  const [schedulePublished, setSchedulePublished] = useState(false);
  const [readonly, setReadonly] = useState(false);
  const [scheduleMessage, setScheduleMessage] = useState(null);
  const [timeSlots, setTimeSlots] = useState([]);
  const [pendingRequests, setPendingRequests] = useState([]);

  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [proposalMode, setProposalMode] = useState(false);
  const [proposalByDate, setProposalByDate] = useState({});
  const [proposalReason, setProposalReason] = useState('');

  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [submissionComplete, setSubmissionComplete] = useState(false);
  const [resubmitPending, setResubmitPending] = useState(false);
  const [error, setError] = useState(null);
  const [submitMessage, setSubmitMessage] = useState(null);

  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  useEffect(() => {
    if (!hasUnsavedChanges) return undefined;
    const onBeforeUnload = (e) => {
      e.preventDefault();
      e.returnValue = '';
    };
    window.addEventListener('beforeunload', onBeforeUnload);
    return () => window.removeEventListener('beforeunload', onBeforeUnload);
  }, [hasUnsavedChanges]);

  const handleLogout = async () => {
    if (!(await confirmDialog({ title: 'ログアウトしますか？', message: '提出していない変更は保存されません。', confirmLabel: 'ログアウト' }))) return;
    clearSession();
    navigate('/');
  };

  const canRequestChanges = readonly && (schedulePublished || periodStatus === 'FINALIZED');

  useEffect(() => {
    const s = loadSession();
    if (!s || s.role !== 'teacher' || !s.teacher_id) {
      navigate('/');
      return;
    }
    setTeacherId(s.teacher_id);
    setTeacherName(s.name ?? '講師');
  }, [navigate]);

  const loadPendingRequests = useCallback(async (pid, tid) => {
    const res = await apiFetch(`/api/admin/change-requests?period_id=${pid}&status=PENDING`);
    if (!res.ok) return;
    const data = await res.json();
    setPendingRequests(
      (data.requests ?? []).filter((r) => r.role === 'teacher' && r.entity_id === tid),
    );
  }, []);

  const loadSchedule = useCallback(async (tid, pid, ctx) => {
    setIsLoading(true);
    setError(null);
    try {
      const monthQuery = ctx ? monthScheduleQuery(ctx) : '';
      const res = await apiFetch(
        `/api/shifts/my-schedule?role=teacher&entity_id=${tid}&period_id=${pid}${monthQuery}`,
      );
      if (!res.ok) throw new Error('スケジュールの取得に失敗しました');
      const sched = await res.json();
      setPeriodStatus(sched.period_status);
      setSubmissionDeadline(sched.submission_deadline ?? null);
      setPeriodName(sched.period_name ?? '');
      setPeriodStart(sched.period_start_date ?? '');
      setPeriodEnd(sched.period_end_date ?? '');
      setScheduleRequested(Boolean(sched.schedule_requested));
      setSchedulePublished(Boolean(sched.schedule_published));
      setSubmissionComplete(Boolean(sched.submission_complete));
      setResubmitPending(Boolean(sched.resubmit_pending));
      setSubmitted(Boolean(sched.submission_complete));
      setReadonly(sched.readonly);
      setScheduleMessage(sched.message);
      setTimeSlots(sched.time_slots ?? []);

      const byDate = {};
      const locked = {};
      const lessons = {};
      const teacherLanes = {};
      sched.dates.forEach((d) => {
        byDate[d.date] = apiSlotsToState(d.slots);
        locked[d.date] = d.locked_slots ?? {};
        lessons[d.date] = d.confirmed_lessons ?? [];
        teacherLanes[d.date] = d.teacher_slot_lanes ?? [];
      });
      setScheduleByDate(byDate);
      setLockedByDate(locked);
      setLessonsByDate(lessons);
      setTeacherLanesByDate(teacherLanes);
      setDates(sched.dates.map((d) => d.date));
      setSelectedDate((prev) => prev ?? sched.dates[0]?.date ?? null);
      await loadPendingRequests(pid, tid);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }, [loadPendingRequests]);

  useEffect(() => {
    if (!teacherId) return;
    fetchScheduleContext()
      .then((ctx) => {
        setPeriodId(ctx.period_id);
        setScheduleMode(ctx.mode);
        setCalendarYear(ctx.calendar_year);
        setCalendarMonth(ctx.month);
        loadSchedule(teacherId, ctx.period_id, ctx);
      })
      .catch((err) => {
        setError(err.message);
        setIsLoading(false);
      });
  }, [teacherId, loadSchedule]);

  const handleMonthChange = (delta) => {
    if (!teacherId || !periodId || scheduleMode !== 'regular') return;
    const next = shiftMonth({ calendar_year: calendarYear, month: calendarMonth }, delta);
    const ctx = { mode: 'regular', calendar_year: next.calendar_year, month: next.month };
    setCalendarYear(next.calendar_year);
    setCalendarMonth(next.month);
    setSelectedDate(null);
    loadSchedule(teacherId, periodId, ctx);
  };

  useEffect(() => {
    if (!teacherId || !periodId || schedulePublished || readonly) return undefined;
    if (!submissionComplete && !resubmitPending) return undefined;
    const ctx =
      scheduleMode === 'regular'
        ? { mode: 'regular', calendar_year: calendarYear, month: calendarMonth }
        : null;
    const timer = window.setInterval(
      () => loadSchedule(teacherId, periodId, ctx),
      15000,
    );
    return () => window.clearInterval(timer);
  }, [
    teacherId,
    periodId,
    submissionComplete,
    resubmitPending,
    schedulePublished,
    readonly,
    loadSchedule,
    scheduleMode,
    calendarYear,
    calendarMonth,
  ]);

  const startProposal = () => {
    setProposalByDate(JSON.parse(JSON.stringify(scheduleByDate)));
    setProposalReason('');
    setProposalMode(true);
    setSubmitMessage(null);
    setError(null);
  };

  const cancelProposal = () => {
    setHasUnsavedChanges(false);
    setProposalMode(false);
    setProposalByDate({});
    setProposalReason('');
  };

  const proposalChanges = useMemo(
    () => collectProposalChanges(scheduleByDate, proposalByDate, lockedByDate),
    [scheduleByDate, proposalByDate, lockedByDate],
  );

  const handleProposalSlotChange = (slotNum, symbol) => {
    if (!selectedDate) return;
    setHasUnsavedChanges(true);
    setProposalByDate((prev) => {
      const day = { ...(prev[selectedDate] ?? EMPTY_SLOTS) };
      day[slotNum] = day[slotNum] === symbol ? '' : symbol;
      return { ...prev, [selectedDate]: day };
    });
  };

  const handleSubmitProposal = async () => {
    if (!teacherId || !periodId || proposalChanges.length === 0) {
      setError('変更がありません');
      return;
    }
    setIsSubmitting(true);
    setError(null);
    try {
      const { results, errors } = await submitChangeProposal({
        periodId,
        role: 'teacher',
        entityId: teacherId,
        changes: proposalChanges,
        reason: proposalReason,
      });
      if (errors.length && !results.length) {
        throw new Error(errors[0]);
      }
      setSubmitMessage(
        errors.length
          ? `${results.length} 件送信（${errors.length} 件はスキップ）`
          : `変更提案書を ${results.length} 件送信しました。教室長の承認をお待ちください。`,
      );
      setProposalMode(false);
      setHasUnsavedChanges(false);
      await loadPendingRequests(periodId, teacherId);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleStatusChange = async (slotNum, symbol) => {
    if (!teacherId || !selectedDate || isSaving || readonly) return;
    const locked = lockedByDate[selectedDate]?.[String(slotNum)];
    if (locked) return;
    const daySlots = scheduleByDate[selectedDate] ?? EMPTY_SLOTS;
    const next = daySlots[slotNum] === symbol ? '' : symbol;
    const prev = { ...scheduleByDate };
    setSubmitted(false);
    setScheduleByDate((m) => ({ ...m, [selectedDate]: { ...daySlots, [slotNum]: next } }));
    setIsSaving(true);
    try {
      const res = await apiFetch('/api/shifts', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          teacher_id: teacherId,
          date: selectedDate,
          slot: slotNum,
          status: next,
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || '更新に失敗しました');
      }
    } catch (err) {
      setScheduleByDate(prev);
      setError(err.message);
    } finally {
      setIsSaving(false);
    }
  };

  const handleBulkSubmit = async () => {
    if (!teacherId || !periodId || readonly) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const submissions = dates.map((date) => ({
        date,
        slots: stateToApiSlots(scheduleByDate[date] ?? EMPTY_SLOTS),
      }));
      const res = await apiFetch('/api/shifts/bulk', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          role: 'teacher',
          entity_id: teacherId,
          period_id: periodId,
          submissions,
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || '提出に失敗しました');
      }
      setSubmitMessage((await res.json()).message);
      setSubmitted(true);
      setHasUnsavedChanges(false);
      setSubmissionComplete(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRequestChange = async () => {
    if (!teacherId || !periodId || resubmitPending) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const res = await apiFetch('/api/shifts/resubmit-request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          period_id: periodId,
          role: 'teacher',
          entity_id: teacherId,
          reason: '',
        }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(body.detail || '変更申請に失敗しました');
      setResubmitPending(true);
      setSubmitMessage(body.message);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const shiftData = selectedDate
    ? (proposalMode ? proposalByDate[selectedDate] : scheduleByDate[selectedDate]) ?? EMPTY_SLOTS
    : EMPTY_SLOTS;
  const originalDay = selectedDate ? scheduleByDate[selectedDate] ?? EMPTY_SLOTS : EMPTY_SLOTS;
  const lockedSlots = selectedDate ? lockedByDate[selectedDate] ?? {} : {};
  const confirmedLessons = selectedDate ? lessonsByDate[selectedDate] ?? [] : [];
  const teacherSlotLanes = selectedDate ? teacherLanesByDate[selectedDate] ?? [] : [];
  const pendingBySlot = {};
  pendingRequests.forEach((r) => {
    if (r.date === selectedDate) pendingBySlot[r.slot] = r;
  });

  if (!teacherId) return null;

  const isWaitingForFinal =
    scheduleRequested && !schedulePublished && !readonly && submissionComplete && !proposalMode;

  return (
    <div className="min-h-screen bg-slate-100 flex justify-center p-0 sm:p-4 font-sans">
      <div className="w-full max-w-lg bg-white sm:rounded-3xl sm:shadow-xl overflow-hidden flex flex-col min-h-[100vh] sm:min-h-[90vh]">
        <header className="bg-gradient-to-br from-blue-700 to-blue-900 text-white px-5 pt-8 pb-5">
          <div className="flex items-center justify-between mb-4">
            <button type="button" onClick={handleLogout} className="text-sm bg-white/15 hover:bg-white/25 px-3 py-1.5 rounded-lg">ログアウト</button>
            <button type="button" onClick={() => setShowPasswordModal(true)} className="text-sm bg-white/15 hover:bg-white/25 px-3 py-1.5 rounded-lg">パスワード変更</button>
            {!proposalMode && canRequestChanges && (
              <button type="button" onClick={startProposal} className="text-sm bg-amber-400 hover:bg-amber-300 text-amber-950 px-3 py-1.5 rounded-lg font-bold">
                変更の提案書作成
              </button>
            )}
            {proposalMode && (
              <button type="button" onClick={cancelProposal} className="text-sm bg-white/15 hover:bg-white/25 px-3 py-1.5 rounded-lg">キャンセル</button>
            )}
          </div>
          <h1 className="text-xl font-bold">{proposalMode ? '変更提案書' : '講師スケジュール'}</h1>
          <p className="text-blue-200 text-sm mt-1">{teacherName}</p>
        </header>

        <main className="flex-1 overflow-y-auto p-3 sm:p-4 bg-slate-50">
          {!isWaitingForFinal && (
            <>
          <PeriodBanner
            periodName={periodName}
            periodStart={periodStart}
            periodEnd={periodEnd}
            periodStatus={periodStatus}
            submissionDeadline={submissionDeadline}
            scheduleRequested={scheduleRequested}
            schedulePublished={schedulePublished}
          />

          {scheduleMode === 'regular' && calendarYear && calendarMonth && (
            <div className="flex items-center justify-between mb-3 px-1">
              <button
                type="button"
                onClick={() => handleMonthChange(-1)}
                className="px-3 py-1.5 rounded-lg border border-gray-200 bg-white text-sm font-bold hover:bg-gray-50"
              >
                ←
              </button>
              <span className="text-sm font-bold text-gray-700">
                {formatMonthLabel(calendarYear, calendarMonth)}
              </span>
              <button
                type="button"
                onClick={() => handleMonthChange(1)}
                className="px-3 py-1.5 rounded-lg border border-gray-200 bg-white text-sm font-bold hover:bg-gray-50"
              >
                →
              </button>
            </div>
          )}

          {scheduleMode === 'cram' && (
            <UserPhaseStepper
              role="teacher"
              readonly={readonly}
              scheduleRequested={scheduleRequested}
              schedulePublished={schedulePublished}
              proposalMode={proposalMode}
              periodStatus={periodStatus}
            />
          )}
            </>
          )}

          {error && <p className="text-red-600 text-sm mb-3 p-3 bg-red-50 rounded-xl">{error}</p>}
          {submitMessage && !isWaitingForFinal && (
            <p className="text-emerald-700 text-sm mb-3 p-3 bg-emerald-50 rounded-xl font-bold">{submitMessage}</p>
          )}

          {isWaitingForFinal ? (
            <div className="flex flex-col items-center justify-center min-h-[50vh] text-center px-6">
              <p className="text-3xl font-bold text-gray-900">提出完了</p>
              {resubmitPending ? (
                <p className="text-sm text-amber-800 mt-6 font-bold leading-relaxed">
                  変更申請中です。
                  <br />
                  教室長の承認をお待ちください。
                </p>
              ) : (
                <button
                  type="button"
                  onClick={handleRequestChange}
                  disabled={isSubmitting}
                  className="mt-10 px-8 py-3 rounded-2xl border-2 border-gray-300 bg-white hover:bg-gray-50 text-gray-800 font-bold shadow-sm disabled:opacity-50"
                >
                  {isSubmitting ? '送信中...' : '変更'}
                </button>
              )}
            </div>
          ) : (
            <>
          {proposalMode && (
            <div className="mb-4 p-4 bg-amber-50 border border-amber-200 rounded-2xl text-sm text-amber-900">
              <p className="font-bold">変更したい都合を編集してください</p>
              <p className="mt-1 text-amber-800">通常授業は変更できません。送信後、教室長が承認します。</p>
              {proposalChanges.length > 0 && (
                <p className="mt-2 font-bold text-amber-950">{proposalChanges.length} コマに変更があります</p>
              )}
            </div>
          )}

          {!proposalMode && scheduleMessage && (
            <div className={`mb-4 p-4 rounded-2xl text-sm border ${
              readonly
                ? 'bg-blue-50 border-blue-200 text-blue-900'
                : 'bg-white border-blue-200 text-blue-900'
            }`}>
              {scheduleMessage}
            </div>
          )}

          <DateTabs dates={dates} selectedDate={selectedDate} onSelect={setSelectedDate} accent="blue" />

          {isLoading ? (
            <p className="text-gray-500 text-center py-12">読み込み中...</p>
          ) : proposalMode ? (
            <>
              <ScheduleLegend />
              <div className="space-y-3">
                {(timeSlots.length ? timeSlots : [1, 2, 3, 4, 5, 6].map((s) => ({ slot: s, start: '', end: '' }))).map(({ slot, start, end }) => (
                  <TimeSlotRow
                    key={slot}
                    period={slot}
                    time={{ start, end }}
                    status={shiftData[slot]}
                    locked={lockedSlots[String(slot)]}
                    readonly={false}
                    disabled={isSubmitting}
                    changed={originalDay[slot] !== shiftData[slot]}
                    onStatusChange={(sym) => handleProposalSlotChange(slot, sym)}
                  />
                ))}
              </div>
            </>
          ) : readonly ? (
            <DayScheduleOverview
              timeSlots={timeSlots}
              slots={shiftData}
              lessons={confirmedLessons}
              lockedSlots={lockedSlots}
              role="teacher"
              pendingBySlot={pendingBySlot}
              teacherSlotLanes={teacherSlotLanes}
            />
          ) : (
            <>
              <ScheduleLegend />
              <div className="space-y-3">
                {(timeSlots.length ? timeSlots : [1, 2, 3, 4, 5, 6].map((s) => ({ slot: s, start: '', end: '' }))).map(({ slot, start, end }) => (
                  <TimeSlotRow
                    key={slot}
                    period={slot}
                    time={{ start, end }}
                    status={shiftData[slot]}
                    locked={lockedSlots[String(slot)]}
                    readonly={false}
                    disabled={isSaving || isSubmitting}
                    confirmedLesson={confirmedLessons.find((l) => l.slot === slot)}
                    onStatusChange={(sym) => handleStatusChange(slot, sym)}
                  />
                ))}
              </div>
            </>
          )}
            </>
          )}
        </main>

        <footer className="p-4 bg-white border-t border-gray-100 space-y-3">
          {isWaitingForFinal ? null : proposalMode ? (
            <>
              <label className="block">
                <span className="text-xs font-bold text-gray-600">変更理由（任意）</span>
                <textarea
                  value={proposalReason}
                  onChange={(e) => setProposalReason(e.target.value)}
                  rows={2}
                  placeholder="例: 6/12午後のみ都合が悪くなりました"
                  className="mt-1 w-full border border-gray-300 rounded-xl px-3 py-2 text-sm"
                />
              </label>
              <button
                type="button"
                onClick={handleSubmitProposal}
                disabled={isSubmitting || proposalChanges.length === 0}
                className="w-full bg-amber-500 hover:bg-amber-600 disabled:bg-amber-300 text-amber-950 font-bold py-4 rounded-2xl shadow-lg"
              >
                {isSubmitting ? '送信中...' : '修正した提案書を送信'}
              </button>
            </>
          ) : scheduleMode === 'cram' && !readonly && !scheduleRequested && periodStatus === 'COLLECTING' ? (
            <p className="text-center text-sm text-gray-500 py-2">
              教室長から提案書が届くまでお待ちください
            </p>
          ) : !readonly && (
            <button
              type="button"
              onClick={handleBulkSubmit}
              disabled={isLoading || isSubmitting || submitted}
              className={`w-full font-bold py-4 rounded-2xl shadow-lg text-white ${
                submitted
                  ? 'bg-blue-500 disabled:opacity-100'
                  : 'bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400'
              }`}
            >
              {submitted ? '提出完了' : isSubmitting ? '提出中...' : '講習日程を提出する'}
            </button>
          )}
        </footer>
      </div>
      <PasswordChangeModal open={showPasswordModal} onClose={() => setShowPasswordModal(false)} />
    </div>
  );
}
