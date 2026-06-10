import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { loadSession, clearSession } from '../utils/session';
import { useStudentSession } from '../hooks/useStudentSession';
import {
  apiSlotsToState,
  ScheduleLegend,
  stateToApiSlots,
  TimeSlotRow,
} from '../components/ScheduleEditor';

const WEEKDAYS = ['日', '月', '火', '水', '木', '金', '土'];

function parseDateTab(isoDate) {
  const d = new Date(`${isoDate}T12:00:00`);
  return { day: WEEKDAYS[d.getDay()], date: String(d.getDate()) };
}

export default function StudentSchedule() {
  const navigate = useNavigate();
  const isReady = useStudentSession();
  const session = loadSession();

  const [studentId, setStudentId] = useState(null);
  const [studentName, setStudentName] = useState('');
  const [periodId, setPeriodId] = useState(null);
  const [periodStatus, setPeriodStatus] = useState(null);
  const [readonly, setReadonly] = useState(false);
  const [scheduleMessage, setScheduleMessage] = useState(null);
  const [dates, setDates] = useState([]);
  const [selectedDate, setSelectedDate] = useState(null);
  const [scheduleByDate, setScheduleByDate] = useState({});
  const [lockedByDate, setLockedByDate] = useState({});
  const [lessonsByDate, setLessonsByDate] = useState({});
  const [timeSlots, setTimeSlots] = useState([]);

  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    if (!session?.student_id) return;
    setStudentId(session.student_id);
    setStudentName(session.name ?? '生徒');
  }, [session]);

  const fetchSchedule = useCallback(async (sid, pid) => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(
        `/api/shifts/my-schedule?role=student&entity_id=${sid}&period_id=${pid}`,
      );
      if (!res.ok) throw new Error('スケジュールの取得に失敗しました');
      const data = await res.json();
      setPeriodStatus(data.period_status);
      setReadonly(data.readonly);
      setScheduleMessage(data.message);
      setTimeSlots(data.time_slots ?? []);
      const byDate = {};
      const locked = {};
      const lessons = {};
      const dateList = data.dates.map((d) => {
        byDate[d.date] = apiSlotsToState(d.slots);
        locked[d.date] = d.locked_slots;
        lessons[d.date] = d.confirmed_lessons ?? [];
        return d.date;
      });
      setScheduleByDate(byDate);
      setLockedByDate(locked);
      setLessonsByDate(lessons);
      setDates(dateList);
      setSelectedDate((prev) => prev ?? dateList[0] ?? null);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!studentId) return;
    const init = async () => {
      const res = await fetch('/api/admin/periods');
      if (!res.ok) return;
      const data = await res.json();
      const pid = data.active_period_id ?? data.periods[0]?.id;
      if (pid) {
        setPeriodId(pid);
        await fetchSchedule(studentId, pid);
      } else {
        setError('募集期間が設定されていません');
        setIsLoading(false);
      }
    };
    init();
  }, [studentId, fetchSchedule]);

  const shiftData = selectedDate ? scheduleByDate[selectedDate] ?? { 1: '', 2: '', 3: '', 4: '' } : {};
  const lockedSlots = selectedDate ? lockedByDate[selectedDate] ?? {} : {};
  const confirmedLessons = selectedDate ? lessonsByDate[selectedDate] ?? [] : [];

  const handleStatusChange = (slotNum, symbol) => {
    if (readonly || lockedSlots[String(slotNum)]) return;
    setScheduleByDate((prev) => ({
      ...prev,
      [selectedDate]: {
        ...prev[selectedDate],
        [slotNum]: prev[selectedDate][slotNum] === symbol ? '' : symbol,
      },
    }));
  };

  const handleBulkSubmit = async () => {
    if (!studentId || !periodId || readonly) return;
    setIsSubmitting(true);
    setError(null);
    setMessage(null);
    try {
      const submissions = dates.map((date) => ({
        date,
        slots: stateToApiSlots(scheduleByDate[date] ?? { 1: '', 2: '', 3: '', 4: '' }),
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
      const data = await res.json();
      setMessage(data.message);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isReady || !studentId) return null;

  return (
    <div className="min-h-screen bg-gray-100 flex justify-center p-4 font-sans">
      <div className="w-full max-w-[400px] bg-gray-50 rounded-[2rem] shadow-xl overflow-hidden border-4 border-white flex flex-col relative min-h-[800px]">
        <header className="bg-emerald-800 text-white pt-10 pb-4 px-6 rounded-b-3xl shadow-md flex justify-between items-center">
          <button type="button" onClick={() => { clearSession(); navigate('/'); }} className="text-sm bg-white/20 px-3 py-1 rounded-lg">← 戻る</button>
          <div className="text-center">
            <h1 className="text-lg font-bold">生徒スケジュール</h1>
            <p className="text-xs text-emerald-200">{studentName}</p>
            {periodStatus && <p className="text-xs text-emerald-300 mt-1">{periodStatus}{readonly ? '（確定済み）' : ''}</p>}
          </div>
          <div className="w-8" />
        </header>

        <main className="flex-1 overflow-y-auto p-4">
          {error && <p className="text-red-500 text-sm mb-4 text-center">{error}</p>}
          {message && <p className="text-emerald-600 text-sm mb-4 text-center font-bold">{message}</p>}
          {scheduleMessage && readonly && (
            <div className="bg-emerald-100 border border-emerald-300 rounded-xl p-4 mb-4 text-emerald-800 text-sm font-bold text-center">
              {scheduleMessage}
            </div>
          )}

          <div className="flex gap-2 mb-4 overflow-x-auto pb-2">
            {dates.map((isoDate) => {
              const { day, date } = parseDateTab(isoDate);
              return (
                <button
                  key={isoDate}
                  type="button"
                  onClick={() => setSelectedDate(isoDate)}
                  className={`min-w-[60px] rounded-xl p-2 text-center transition-all ${selectedDate === isoDate ? 'bg-emerald-600 text-white shadow-md' : 'bg-white text-gray-500 border border-gray-200'}`}
                >
                  <div className="text-xs">{day}</div>
                  <div className="text-xl font-bold">{date}</div>
                </button>
              );
            })}
          </div>

          {!readonly && <ScheduleLegend />}

          {readonly && confirmedLessons.length > 0 && (
            <div className="mb-4 space-y-2">
              <p className="text-sm font-bold text-gray-700">確定した授業</p>
              {confirmedLessons.map((lesson) => (
                <div key={lesson.slot} className="bg-white border border-emerald-200 rounded-xl p-3 shadow-sm">
                  <div className="text-xs text-gray-400">{lesson.slot}コマ目</div>
                  <div className="font-bold text-emerald-800">{lesson.subject}</div>
                  <div className="text-sm text-gray-600">{lesson.teacher_name} 先生</div>
                </div>
              ))}
            </div>
          )}

          {isLoading ? (
            <p className="text-gray-500 text-center py-8">読み込み中...</p>
          ) : (
            <div className="space-y-3">
              {(timeSlots.length ? timeSlots : [{ slot: 1, start: '13:30', end: '14:50' }]).map(({ slot, start, end }) => (
                <TimeSlotRow
                  key={slot}
                  period={slot}
                  time={{ start, end }}
                  status={shiftData[slot]}
                  locked={lockedSlots[String(slot)]}
                  readonly={readonly}
                  disabled={isSubmitting}
                  onStatusChange={(sym) => handleStatusChange(slot, sym)}
                />
              ))}
            </div>
          )}
        </main>

        {!readonly && periodStatus === 'COLLECTING' && (
          <footer className="bg-white p-4 border-t border-gray-100">
            <button
              type="button"
              onClick={handleBulkSubmit}
              disabled={isLoading || isSubmitting}
              className="w-full bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-400 text-white font-bold py-4 rounded-xl shadow-lg"
            >
              {isSubmitting ? '提出中...' : '期間を一括提出する'}
            </button>
          </footer>
        )}
      </div>
    </div>
  );
}
