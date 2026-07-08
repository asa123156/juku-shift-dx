import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { loadSession, clearSession } from '../utils/session';
import { useStudentSession } from '../hooks/useStudentSession';
import {
  apiSlotsToState,
  EMPTY_SLOTS,
  StudentScheduleLegend,
  stateToApiSlots,
  StudentSlotRow,
  PeriodBanner,
  DateTabs,
  collectProposalChanges,
  submitChangeProposal,
} from '../components/ScheduleEditor';
import { UserPhaseStepper, SubjectPlansCard } from '../components/UserPhaseStepper';
import {
  fetchScheduleContext,
  formatMonthLabel,
  monthScheduleQuery,
  shiftMonth,
} from '../utils/scheduleContext';

export default function StudentSchedule() {
  const navigate = useNavigate();
  const isReady = useStudentSession();
  const session = loadSession();

  const [studentId, setStudentId] = useState(null);
  const [studentName, setStudentName] = useState('');
  const [scheduleMode, setScheduleMode] = useState('regular');
  const [calendarYear, setCalendarYear] = useState(null);
  const [calendarMonth, setCalendarMonth] = useState(null);
  const [periodId, setPeriodId] = useState(null);
  const [periodName, setPeriodName] = useState('');
  const [periodStart, setPeriodStart] = useState('');
  const [periodEnd, setPeriodEnd] = useState('');
  const [periodStatus, setPeriodStatus] = useState(null);
  const [scheduleRequested, setScheduleRequested] = useState(false);
  const [schedulePublished, setSchedulePublished] = useState(false);
  const [readonly, setReadonly] = useState(false);
  const [scheduleMessage, setScheduleMessage] = useState(null);
  const [dates, setDates] = useState([]);
  const [selectedDate, setSelectedDate] = useState(null);
  const [scheduleByDate, setScheduleByDate] = useState({});
  const [lockedByDate, setLockedByDate] = useState({});
  const [lessonsByDate, setLessonsByDate] = useState({});
  const [timeSlots, setTimeSlots] = useState([]);
  const [subjectPlans, setSubjectPlans] = useState([]);
  const [pendingRequests, setPendingRequests] = useState([]);

  const [proposalMode, setProposalMode] = useState(false);
  const [proposalByDate, setProposalByDate] = useState({});
  const [proposalReason, setProposalReason] = useState('');

  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [submissionComplete, setSubmissionComplete] = useState(false);
  const [resubmitPending, setResubmitPending] = useState(false);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);

  const canRequestChanges = readonly && (schedulePublished || periodStatus === 'FINALIZED');

  useEffect(() => {
    if (!session?.student_id) return;
    setStudentId(session.student_id);
    setStudentName(session.name ?? '生徒');
  }, [session]);

  const loadPendingRequests = useCallback(async (pid, sid) => {
    const res = await fetch(`/api/admin/change-requests?period_id=${pid}&status=PENDING`);
    if (!res.ok) return;
    const data = await res.json();
    setPendingRequests(
      (data.requests ?? []).filter((r) => r.role === 'student' && r.entity_id === sid),
    );
  }, []);

  const fetchSchedule = useCallback(async (sid, pid, ctx) => {
    setIsLoading(true);
    setError(null);
    try {
      const monthQuery = ctx ? monthScheduleQuery(ctx) : '';
      const res = await fetch(
        `/api/shifts/my-schedule?role=student&entity_id=${sid}&period_id=${pid}${monthQuery}`,
      );
      if (!res.ok) throw new Error('スケジュールの取得に失敗しました');
      const data = await res.json();
      setPeriodStatus(data.period_status);
      setPeriodName(data.period_name ?? '');
      setPeriodStart(data.period_start_date ?? '');
      setPeriodEnd(data.period_end_date ?? '');
      setScheduleRequested(Boolean(data.schedule_requested));
      setSchedulePublished(Boolean(data.schedule_published));
      setSubmissionComplete(Boolean(data.submission_complete));
      setResubmitPending(Boolean(data.resubmit_pending));
      setSubmitted(Boolean(data.submission_complete));
      setReadonly(data.readonly);
      setScheduleMessage(data.message);
      setTimeSlots(data.time_slots ?? []);
      setSubjectPlans(data.subject_plans ?? []);
      const byDate = {};
      const locked = {};
      const lessons = {};
      const dateList = data.dates.map((d) => {
        const lockedSlots = d.locked_slots ?? {};
        locked[d.date] = lockedSlots;
        byDate[d.date] = apiSlotsToState(d.slots);
        lessons[d.date] = d.confirmed_lessons ?? [];
        return d.date;
      });
      setScheduleByDate(byDate);
      setLockedByDate(locked);
      setLessonsByDate(lessons);
      setDates(dateList);
      setSelectedDate((prev) => prev ?? dateList[0] ?? null);
      await loadPendingRequests(pid, sid);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }, [loadPendingRequests]);

  useEffect(() => {
    if (!studentId) return;
    fetchScheduleContext()
      .then((ctx) => {
        setPeriodId(ctx.period_id);
        setScheduleMode(ctx.mode);
        setCalendarYear(ctx.calendar_year);
        setCalendarMonth(ctx.month);
        fetchSchedule(studentId, ctx.period_id, ctx);
      })
      .catch((err) => {
        setError(err.message);
        setIsLoading(false);
      });
  }, [studentId, fetchSchedule]);

  const handleMonthChange = (delta) => {
    if (!studentId || !periodId || scheduleMode !== 'regular') return;
    const next = shiftMonth({ calendar_year: calendarYear, month: calendarMonth }, delta);
    const ctx = { mode: 'regular', calendar_year: next.calendar_year, month: next.month };
    setCalendarYear(next.calendar_year);
    setCalendarMonth(next.month);
    setSelectedDate(null);
    fetchSchedule(studentId, periodId, ctx);
  };

  useEffect(() => {
    if (!studentId || !periodId || schedulePublished || readonly) return undefined;
    if (!submissionComplete && !resubmitPending) return undefined;
    const ctx =
      scheduleMode === 'regular'
        ? { mode: 'regular', calendar_year: calendarYear, month: calendarMonth }
        : null;
    const timer = window.setInterval(
      () => fetchSchedule(studentId, periodId, ctx),
      15000,
    );
    return () => window.clearInterval(timer);
  }, [
    studentId,
    periodId,
    submissionComplete,
    resubmitPending,
    schedulePublished,
    readonly,
    fetchSchedule,
    scheduleMode,
    calendarYear,
    calendarMonth,
  ]);

  const startProposal = () => {
    setProposalByDate(JSON.parse(JSON.stringify(scheduleByDate)));
    setProposalReason('');
    setProposalMode(true);
    setMessage(null);
    setError(null);
  };

  const cancelProposal = () => {
    setProposalMode(false);
    setProposalByDate({});
    setProposalReason('');
  };

  const proposalChanges = useMemo(
    () => collectProposalChanges(scheduleByDate, proposalByDate, lockedByDate),
    [scheduleByDate, proposalByDate, lockedByDate],
  );

  const handleStatusChange = (slotNum, symbol) => {
    if (readonly || !selectedDate) return;
    const locked = lockedByDate[selectedDate]?.[String(slotNum)];
    if (locked) return;
    setSubmitted(false);
    setScheduleByDate((prev) => ({
      ...prev,
      [selectedDate]: {
        ...prev[selectedDate],
        [slotNum]: symbol,
      },
    }));
  };

  const handleProposalSlotChange = (slotNum, symbol) => {
    if (!selectedDate) return;
    setProposalByDate((prev) => ({
      ...prev,
      [selectedDate]: {
        ...(prev[selectedDate] ?? EMPTY_SLOTS),
        [slotNum]: symbol,
      },
    }));
  };

  const handleSubmitProposal = async () => {
    if (!studentId || !periodId || proposalChanges.length === 0) {
      setError('変更がありません');
      return;
    }
    setIsSubmitting(true);
    setError(null);
    try {
      const { results, errors } = await submitChangeProposal({
        periodId,
        role: 'student',
        entityId: studentId,
        changes: proposalChanges,
        reason: proposalReason,
      });
      if (errors.length && !results.length) {
        throw new Error(errors[0]);
      }
      setMessage(
        errors.length
          ? `${results.length} 件送信（${errors.length} 件はスキップ）`
          : `変更提案書を ${results.length} 件送信しました。教室長の承認をお待ちください。`,
      );
      setProposalMode(false);
      await loadPendingRequests(periodId, studentId);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleBulkSubmit = async () => {
    if (!studentId || !periodId || readonly) return;
    setIsSubmitting(true);
    setError(null);
    setMessage(null);
    try {
      const submissions = dates.map((date) => ({
        date,
        slots: stateToApiSlots(scheduleByDate[date] ?? EMPTY_SLOTS),
      }));
      const res = await fetch('/api/shifts/bulk', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          role: 'student',
          entity_id: studentId,
          period_id: periodId,
          submissions,
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || '提出に失敗しました');
      }
      setMessage((await res.json()).message);
      setSubmitted(true);
      setSubmissionComplete(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRequestChange = async () => {
    if (!studentId || !periodId || resubmitPending) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const res = await fetch('/api/shifts/resubmit-request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          period_id: periodId,
          role: 'student',
          entity_id: studentId,
          reason: '',
        }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(body.detail || '変更申請に失敗しました');
      setResubmitPending(true);
      setMessage(body.message);
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
  const pendingBySlot = {};
  pendingRequests.forEach((r) => {
    if (r.date === selectedDate) pendingBySlot[r.slot] = r;
  });

  if (!isReady || !studentId) return null;

  const isWaitingForFinal =
    scheduleRequested && !schedulePublished && !readonly && submissionComplete && !proposalMode;

  return (
    <div className="min-h-screen bg-slate-100 flex justify-center p-4 font-sans">
      <div className="w-full max-w-lg bg-white rounded-3xl shadow-xl overflow-hidden flex flex-col min-h-[90vh]">
        <header className="bg-gradient-to-br from-emerald-700 to-emerald-900 text-white px-5 pt-8 pb-5">
          <div className="flex items-center justify-between mb-4">
            <button type="button" onClick={() => { clearSession(); navigate('/'); }} className="text-sm bg-white/15 hover:bg-white/25 px-3 py-1.5 rounded-lg">← ログアウト</button>
            {!proposalMode && canRequestChanges && (
              <button type="button" onClick={startProposal} className="text-sm bg-amber-400 hover:bg-amber-300 text-amber-950 px-3 py-1.5 rounded-lg font-bold">
                変更の提案書作成
              </button>
            )}
            {proposalMode && (
              <button type="button" onClick={cancelProposal} className="text-sm bg-white/15 hover:bg-white/25 px-3 py-1.5 rounded-lg">キャンセル</button>
            )}
          </div>
          <h1 className="text-xl font-bold">{proposalMode ? '変更提案書' : '生徒スケジュール'}</h1>
          <p className="text-emerald-200 text-sm mt-1">{studentName}</p>
        </header>

        <main className="flex-1 overflow-y-auto p-4 bg-slate-50">
          {!isWaitingForFinal && (
            <>
          <PeriodBanner
            periodName={periodName}
            periodStart={periodStart}
            periodEnd={periodEnd}
            periodStatus={periodStatus}
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
              role="student"
              readonly={readonly}
              scheduleRequested={scheduleRequested}
              schedulePublished={schedulePublished}
              proposalMode={proposalMode}
              periodStatus={periodStatus}
            />
          )}

          {scheduleMode === 'cram' && <SubjectPlansCard plans={subjectPlans} />}
            </>
          )}

          {error && <p className="text-red-600 text-sm mb-3 p-3 bg-red-50 rounded-xl">{error}</p>}
          {message && !isWaitingForFinal && (
            <p className="text-emerald-700 text-sm mb-3 p-3 bg-emerald-50 rounded-xl font-bold">{message}</p>
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
              <p className="mt-1 text-amber-800">日付タブで日を切り替えて編集できます。送信後、教室長が承認します。</p>
              {proposalChanges.length > 0 && (
                <p className="mt-2 font-bold text-amber-950">{proposalChanges.length} コマに変更があります</p>
              )}
            </div>
          )}

          {!proposalMode && scheduleMessage && (
            <div className={`mb-4 p-4 rounded-2xl text-sm border ${
              readonly
                ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
                : 'bg-white border-emerald-200 text-emerald-900'
            }`}>
              {scheduleMessage}
            </div>
          )}

          <DateTabs dates={dates} selectedDate={selectedDate} onSelect={setSelectedDate} accent="emerald" />

          {isLoading ? (
            <p className="text-gray-500 text-center py-12">読み込み中...</p>
          ) : (
            <>
              {(proposalMode || !readonly) && <StudentScheduleLegend />}
              <div className="space-y-3">
                {(timeSlots.length ? timeSlots : [1, 2, 3, 4, 5, 6].map((s) => ({ slot: s, start: '', end: '' }))).map(({ slot, start, end }) => (
                  <StudentSlotRow
                    key={slot}
                    period={slot}
                    time={{ start, end }}
                    status={shiftData[slot]}
                    locked={lockedSlots[String(slot)]}
                    readonly={!proposalMode && readonly}
                    disabled={isSubmitting}
                    changed={proposalMode && originalDay[slot] !== shiftData[slot]}
                    confirmedLesson={
                      !proposalMode && (readonly || scheduleRequested)
                        ? confirmedLessons.find((l) => l.slot === slot)
                        : null
                    }
                    pending={Boolean(pendingBySlot[slot])}
                    onStatusChange={(sym) => (
                      proposalMode
                        ? handleProposalSlotChange(slot, sym)
                        : handleStatusChange(slot, sym)
                    )}
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
                  placeholder="例: 6/12の3コマ目が都合悪くなりました"
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
                  ? 'bg-emerald-500 disabled:opacity-100'
                  : 'bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-400'
              }`}
            >
              {submitted ? '提出完了' : isSubmitting ? '提出中...' : '講習日程を提出する'}
            </button>
          )}
        </footer>
      </div>
    </div>
  );
}
