import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { loadSession, clearSession } from '../utils/session';
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
  const [periodId, setPeriodId] = useState(null);
  const [periodName, setPeriodName] = useState('');
  const [periodStart, setPeriodStart] = useState('');
  const [periodEnd, setPeriodEnd] = useState('');
  const [periodStatus, setPeriodStatus] = useState(null);
  const [schedulePublished, setSchedulePublished] = useState(false);
  const [readonly, setReadonly] = useState(false);
  const [scheduleMessage, setScheduleMessage] = useState(null);
  const [timeSlots, setTimeSlots] = useState([]);
  const [pendingRequests, setPendingRequests] = useState([]);

  const [proposalMode, setProposalMode] = useState(false);
  const [proposalByDate, setProposalByDate] = useState({});
  const [proposalReason, setProposalReason] = useState('');

  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [submitMessage, setSubmitMessage] = useState(null);

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
    const res = await fetch(`/api/admin/change-requests?period_id=${pid}&status=PENDING`);
    if (!res.ok) return;
    const data = await res.json();
    setPendingRequests(
      (data.requests ?? []).filter((r) => r.role === 'teacher' && r.entity_id === tid),
    );
  }, []);

  const loadSchedule = useCallback(async (tid, pid) => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(
        `/api/shifts/my-schedule?role=teacher&entity_id=${tid}&period_id=${pid}`,
      );
      if (!res.ok) throw new Error('スケジュールの取得に失敗しました');
      const sched = await res.json();
      setPeriodStatus(sched.period_status);
      setPeriodName(sched.period_name ?? '');
      setPeriodStart(sched.period_start_date ?? '');
      setPeriodEnd(sched.period_end_date ?? '');
      setSchedulePublished(Boolean(sched.schedule_published));
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
    fetch('/api/admin/periods')
      .then((r) => r.json())
      .then((pdata) => {
        const pid = pdata.active_period_id ?? pdata.periods[0]?.id;
        if (pid) {
          setPeriodId(pid);
          loadSchedule(teacherId, pid);
        }
      });
  }, [teacherId, loadSchedule]);

  const startProposal = () => {
    setProposalByDate(JSON.parse(JSON.stringify(scheduleByDate)));
    setProposalReason('');
    setProposalMode(true);
    setSubmitMessage(null);
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

  const handleProposalSlotChange = (slotNum, symbol) => {
    if (!selectedDate) return;
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
    setScheduleByDate((m) => ({ ...m, [selectedDate]: { ...daySlots, [slotNum]: next } }));
    setIsSaving(true);
    try {
      const res = await fetch('/api/shifts', {
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
      const res = await fetch('/api/shifts/bulk', {
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

  return (
    <div className="min-h-screen bg-slate-100 flex justify-center p-4 font-sans">
      <div className="w-full max-w-lg bg-white rounded-3xl shadow-xl overflow-hidden flex flex-col min-h-[90vh]">
        <header className="bg-gradient-to-br from-blue-700 to-blue-900 text-white px-5 pt-8 pb-5">
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
          <h1 className="text-xl font-bold">{proposalMode ? '変更提案書' : '講師スケジュール'}</h1>
          <p className="text-blue-200 text-sm mt-1">{teacherName}</p>
        </header>

        <main className="flex-1 overflow-y-auto p-4 bg-slate-50">
          <PeriodBanner
            periodName={periodName}
            periodStart={periodStart}
            periodEnd={periodEnd}
            periodStatus={periodStatus}
            schedulePublished={schedulePublished}
          />

          {error && <p className="text-red-600 text-sm mb-3 p-3 bg-red-50 rounded-xl">{error}</p>}
          {submitMessage && <p className="text-emerald-700 text-sm mb-3 p-3 bg-emerald-50 rounded-xl font-bold">{submitMessage}</p>}

          {proposalMode && (
            <div className="mb-4 p-4 bg-amber-50 border border-amber-200 rounded-2xl text-sm text-amber-900">
              <p className="font-bold">変更したい都合を編集してください</p>
              <p className="mt-1 text-amber-800">◎ 通常授業は変更できません。送信後、教室長が承認します。</p>
              {proposalChanges.length > 0 && (
                <p className="mt-2 font-bold text-amber-950">{proposalChanges.length} コマに変更があります</p>
              )}
            </div>
          )}

          {!proposalMode && scheduleMessage && readonly && (
            <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-2xl text-sm text-blue-900">
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
                    onStatusChange={(sym) => handleStatusChange(slot, sym)}
                  />
                ))}
              </div>
            </>
          )}
        </main>

        <footer className="p-4 bg-white border-t border-gray-100 space-y-3">
          {proposalMode ? (
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
                {isSubmitting ? '送信中...' : `提案書を送信（${proposalChanges.length}件）`}
              </button>
            </>
          ) : !readonly && periodStatus === 'COLLECTING' && (
            <button
              type="button"
              onClick={handleBulkSubmit}
              disabled={isLoading || isSubmitting}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-bold py-4 rounded-2xl shadow-lg"
            >
              {isSubmitting ? '提出中...' : '期間を一括提出する'}
            </button>
          )}
        </footer>
      </div>
    </div>
  );
}
