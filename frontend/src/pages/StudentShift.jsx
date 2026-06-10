import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { loadSession, clearSession } from '../utils/session';
import {
  apiSlotsToState,
  ScheduleLegend,
  stateToApiSlots,
  TimeSlotRow,
} from '../components/ScheduleEditor';

const WEEKDAYS = ['日', '月', '火', '水', '木', '金', '土'];
const DEFAULT_TIME_SLOTS = [
  { slot: 1, start: '13:30', end: '14:50' },
  { slot: 2, start: '15:00', end: '16:20' },
  { slot: 3, start: '16:30', end: '17:50' },
  { slot: 4, start: '18:00', end: '19:20' },
];

function parseDateTab(isoDate) {
  const d = new Date(`${isoDate}T12:00:00`);
  return { day: WEEKDAYS[d.getDay()], date: String(d.getDate()) };
}

export default function StudentShift() {
  const navigate = useNavigate();

  const [teacherId, setTeacherId] = useState(null);
  const [teacherName, setTeacherName] = useState('');
  const [availableDates, setAvailableDates] = useState([]);
  const [selectedDate, setSelectedDate] = useState(null);
  const [shiftData, setShiftData] = useState({ 1: '', 2: '', 3: '', 4: '' });
  const [lockedSlots, setLockedSlots] = useState({});
  const [periodId, setPeriodId] = useState(null);
  const [periodStatus, setPeriodStatus] = useState(null);
  const [readonly, setReadonly] = useState(false);
  const [timeSlots, setTimeSlots] = useState(DEFAULT_TIME_SLOTS);
  const [allSchedules, setAllSchedules] = useState({});

  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [submitMessage, setSubmitMessage] = useState(null);

  useEffect(() => {
    const s = loadSession();
    if (!s || s.role !== 'teacher' || !s.teacher_id) {
      navigate('/');
      return;
    }
    setTeacherId(s.teacher_id);
    setTeacherName(s.name ?? '講師');
  }, [navigate]);

  const fetchMyShift = useCallback(async (date, tid) => {
    setIsLoading(true);
    setError(null);
    setSubmitMessage(null);
    try {
      const res = await fetch(
        `/api/shifts/me?teacher_id=${tid}&date=${encodeURIComponent(date)}`,
      );
      if (!res.ok) throw new Error('シフトデータの取得に失敗しました');
      const data = await res.json();
      setShiftData(apiSlotsToState(data.slots));
      setLockedSlots(data.locked_slots ?? {});
      setPeriodId(data.period_id ?? null);
      setPeriodStatus(data.period_status ?? null);
      setReadonly(Boolean(data.readonly));
    } catch (err) {
      setError(err.message);
      setShiftData({ 1: '', 2: '', 3: '', 4: '' });
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!teacherId) return;
    const init = async () => {
      try {
        const periodsRes = await fetch('/api/admin/periods');
        if (periodsRes.ok) {
          const pdata = await periodsRes.json();
          const pid = pdata.active_period_id ?? pdata.periods[0]?.id;
          if (pid) {
            setPeriodId(pid);
            const schedRes = await fetch(
              `/api/shifts/my-schedule?role=teacher&entity_id=${teacherId}&period_id=${pid}`,
            );
            if (schedRes.ok) {
              const sched = await schedRes.json();
              setPeriodStatus(sched.period_status);
              setReadonly(sched.readonly);
              const map = {};
              sched.dates.forEach((d) => { map[d.date] = apiSlotsToState(d.slots); });
              setAllSchedules(map);
              setAvailableDates(sched.dates.map((d) => d.date));
              setSelectedDate(sched.dates[0]?.date ?? null);
              const dashRes = await fetch(`/api/shifts?date=${sched.dates[0]?.date}`);
              if (dashRes.ok) {
                const dash = await dashRes.json();
                if (dash.time_slots?.length) {
                  setTimeSlots(dash.time_slots.map(({ slot, start, end }) => ({ slot, start, end })));
                }
              }
              return;
            }
          }
        }
        const datesRes = await fetch('/api/shifts/dates');
        const datesData = await datesRes.json();
        setAvailableDates(datesData.dates);
        setSelectedDate(datesData.default_date);
      } catch (err) {
        setError(err.message);
      }
    };
    init();
  }, [teacherId]);

  useEffect(() => {
    if (!teacherId || !selectedDate) return;
    if (allSchedules[selectedDate]) {
      setShiftData(allSchedules[selectedDate]);
      fetchMyShift(selectedDate, teacherId);
    } else {
      fetchMyShift(selectedDate, teacherId);
    }
  }, [teacherId, selectedDate, fetchMyShift, allSchedules]);

  const handleStatusChange = async (slotNum, symbol) => {
    if (!teacherId || !selectedDate || isSaving || readonly || lockedSlots[String(slotNum)]) return;
    const next = shiftData[slotNum] === symbol ? '' : symbol;
    const prev = shiftData;
    setShiftData((s) => ({ ...s, [slotNum]: next }));
    setAllSchedules((m) => ({ ...m, [selectedDate]: { ...shiftData, [slotNum]: next } }));
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
      if (!res.ok) throw new Error('コマの更新に失敗しました');
    } catch (err) {
      setShiftData(prev);
      setError(err.message);
    } finally {
      setIsSaving(false);
    }
  };

  const handleSubmitDay = async () => {
    if (!teacherId || !selectedDate || isSubmitting || readonly) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const res = await fetch('/api/shifts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          teacher_id: teacherId,
          date: selectedDate,
          slots: stateToApiSlots(shiftData),
        }),
      });
      if (!res.ok) throw new Error('提出に失敗しました');
      setSubmitMessage((await res.json()).message);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleBulkSubmit = async () => {
    if (!teacherId || !periodId || readonly) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const submissions = availableDates.map((date) => ({
        date,
        slots: stateToApiSlots(allSchedules[date] ?? shiftData),
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
        throw new Error(body.detail || '一括提出に失敗しました');
      }
      setSubmitMessage((await res.json()).message);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!teacherId) return null;

  return (
    <div className="min-h-screen bg-gray-100 flex justify-center p-4 font-sans">
      <div className="w-full max-w-[400px] bg-gray-50 rounded-[2rem] shadow-xl overflow-hidden border-4 border-white flex flex-col relative min-h-[800px]">
        <header className="bg-blue-800 text-white pt-10 pb-4 px-6 rounded-b-3xl shadow-md flex justify-between items-center">
          <button type="button" onClick={() => { clearSession(); navigate('/'); }} className="text-sm bg-white/20 px-3 py-1 rounded-lg">← 戻る</button>
          <div className="text-center">
            <h1 className="text-lg font-bold">シフト入力</h1>
            <p className="text-xs text-blue-200">{teacherName}</p>
            {periodStatus && <p className="text-xs text-blue-300">{periodStatus}{readonly ? '（閲覧のみ）' : ''}</p>}
          </div>
          <div className="w-8" />
        </header>

        <main className="flex-1 overflow-y-auto p-4">
          {error && <p className="text-red-500 text-sm mb-4 text-center">{error}</p>}
          {submitMessage && <p className="text-emerald-600 text-sm mb-4 text-center font-bold">{submitMessage}</p>}

          <div className="flex gap-2 mb-4 overflow-x-auto pb-2">
            {availableDates.map((isoDate) => {
              const { day, date } = parseDateTab(isoDate);
              return (
                <button
                  key={isoDate}
                  type="button"
                  onClick={() => setSelectedDate(isoDate)}
                  className={`min-w-[60px] rounded-xl p-2 text-center transition-all ${selectedDate === isoDate ? 'bg-blue-600 text-white shadow-md' : 'bg-white text-gray-500 border border-gray-200'}`}
                >
                  <div className="text-xs">{day}</div>
                  <div className="text-xl font-bold">{date}</div>
                </button>
              );
            })}
          </div>

          <ScheduleLegend />

          {isLoading ? (
            <p className="text-gray-500 text-center py-8">読み込み中...</p>
          ) : (
            <div className="space-y-3">
              {timeSlots.map(({ slot, start, end }) => (
                <TimeSlotRow
                  key={slot}
                  period={slot}
                  time={{ start, end }}
                  status={shiftData[slot]}
                  locked={lockedSlots[String(slot)]}
                  readonly={readonly}
                  disabled={isSaving || isSubmitting}
                  onStatusChange={(sym) => handleStatusChange(slot, sym)}
                />
              ))}
            </div>
          )}
        </main>

        {!readonly && (
          <footer className="bg-white p-4 border-t border-gray-100 space-y-2">
            {periodStatus === 'COLLECTING' && periodId && (
              <button
                type="button"
                onClick={handleBulkSubmit}
                disabled={isLoading || isSubmitting}
                className="w-full bg-purple-600 hover:bg-purple-700 disabled:bg-purple-400 text-white font-bold py-3 rounded-xl shadow-lg"
              >
                期間を一括提出する
              </button>
            )}
            <button
              type="button"
              onClick={handleSubmitDay}
              disabled={isLoading || isSubmitting || isSaving}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-bold py-3 rounded-xl shadow-lg"
            >
              {isSubmitting ? '提出中...' : 'この日を提出する'}
            </button>
          </footer>
        )}
      </div>
    </div>
  );
}
