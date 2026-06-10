import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { loadSession, clearSession } from '../utils/session';

const WEEKDAYS = ['日', '月', '火', '水', '木', '金', '土'];

const EMPTY_SLOTS = { 1: 'blank', 2: 'blank', 3: 'blank', 4: 'blank' };

const DEFAULT_TIME_SLOTS = [
  { slot: 1, start: '13:00', end: '14:20' },
  { slot: 2, start: '14:30', end: '15:50' },
  { slot: 3, start: '16:00', end: '17:20' },
  { slot: 4, start: '17:30', end: '18:50' },
];

function parseDateTab(isoDate) {
  const d = new Date(`${isoDate}T12:00:00`);
  return { day: WEEKDAYS[d.getDay()], date: String(d.getDate()) };
}

function apiSlotsToState(slots) {
  const normalize = (v) => (v === 'priority' ? 'regular_class' : v);
  return {
    1: normalize(slots['1']) ?? 'blank',
    2: normalize(slots['2']) ?? 'blank',
    3: normalize(slots['3']) ?? 'blank',
    4: normalize(slots['4']) ?? 'blank',
  };
}

function stateToApiSlots(slots) {
  return {
    '1': slots[1],
    '2': slots[2],
    '3': slots[3],
    '4': slots[4],
  };
}

const DateSelector = ({ isoDate, isActive, onClick }) => {
  const { day, date } = parseDateTab(isoDate);
  return (
    <button
      type="button"
      onClick={onClick}
      className={`min-w-[60px] rounded-xl p-2 text-center transition-all ${isActive ? 'bg-blue-600 text-white shadow-md' : 'bg-white text-gray-500 border border-gray-200 hover:bg-gray-50'}`}
    >
      <div className="text-xs">{day}</div>
      <div className="text-xl font-bold">{date}</div>
    </button>
  );
};

const TimeSlot = ({ period, time, status, onStatusChange, disabled }) => (
  <div className={`bg-white p-4 rounded-2xl shadow-sm border flex items-center justify-between transition-colors ${status === 'blank' ? 'border-blue-300 ring-2 ring-blue-100' : 'border-gray-100'}`}>
    <div>
      <div className="text-xs text-gray-400 font-bold">{period}コマ目</div>
      <div className="text-lg font-bold text-gray-800">
        {time.start} <span className="text-sm font-normal text-gray-500">~ {time.end}</span>
      </div>
    </div>
    <div className="flex bg-gray-100 rounded-lg p-1 gap-1">
      <button
        type="button"
        disabled={disabled}
        onClick={() => onStatusChange('regular_class')}
        className={`w-11 h-10 rounded-md font-bold text-sm transition-all disabled:opacity-50 ${status === 'regular_class' ? 'bg-slate-500 text-white shadow-sm' : 'text-gray-400 hover:bg-gray-200'}`}
        title="通常授業で入れない"
      >
        ◎
      </button>
      <button
        type="button"
        disabled={disabled}
        onClick={() => onStatusChange('available')}
        className={`w-11 h-10 rounded-md font-bold text-sm transition-all disabled:opacity-50 ${status === 'available' ? 'bg-emerald-500 text-white shadow-sm ring-2 ring-emerald-300' : 'text-gray-400 hover:bg-gray-200 border border-dashed border-gray-300'}`}
        title="空いている"
      >
        空
      </button>
      <button
        type="button"
        disabled={disabled}
        onClick={() => onStatusChange('unavailable')}
        className={`w-11 h-10 rounded-md font-bold transition-all disabled:opacity-50 ${status === 'unavailable' ? 'bg-red-500 text-white shadow-sm' : 'text-gray-400 hover:bg-gray-200'}`}
        title="無理"
      >
        ×
      </button>
    </div>
  </div>
);

export default function StudentShift() {
  const navigate = useNavigate();

  const [teacherId, setTeacherId] = useState(null);
  const [teacherName, setTeacherName] = useState('');
  const [availableDates, setAvailableDates] = useState([]);
  const [selectedDate, setSelectedDate] = useState(null);
  const [shiftData, setShiftData] = useState(EMPTY_SLOTS);
  const [timeSlots, setTimeSlots] = useState(DEFAULT_TIME_SLOTS);

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

  useEffect(() => {
    if (!teacherId) return;

    const init = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const datesRes = await fetch('/api/shifts/dates');
        if (!datesRes.ok) throw new Error('日付一覧の取得に失敗しました');
        const datesData = await datesRes.json();
        setAvailableDates(datesData.dates);
        setSelectedDate((prev) => prev ?? datesData.default_date);

        const dashRes = await fetch(`/api/shifts?date=${encodeURIComponent(datesData.default_date)}`);
        if (dashRes.ok) {
          const dash = await dashRes.json();
          if (dash.time_slots?.length) {
            setTimeSlots(dash.time_slots.map(({ slot, start, end }) => ({ slot, start, end })));
          }
        }
      } catch (err) {
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    };

    init();
  }, [teacherId]);

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
    } catch (err) {
      setError(err.message);
      setShiftData(EMPTY_SLOTS);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!teacherId || !selectedDate) return;
    fetchMyShift(selectedDate, teacherId);
  }, [teacherId, selectedDate, fetchMyShift]);

  const handleStatusChange = async (slotNum, newStatus) => {
    if (!teacherId || !selectedDate || isSaving) return;

    const nextStatus = shiftData[slotNum] === newStatus ? 'blank' : newStatus;
    const prev = shiftData;
    setShiftData((s) => ({ ...s, [slotNum]: nextStatus }));
    setIsSaving(true);
    setError(null);

    try {
      const res = await fetch('/api/shifts', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          teacher_id: teacherId,
          date: selectedDate,
          slot: slotNum,
          status: nextStatus,
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

  const handleSubmit = async () => {
    if (!teacherId || !selectedDate || isSubmitting) return;

    setIsSubmitting(true);
    setError(null);
    setSubmitMessage(null);
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
      const data = await res.json();
      setSubmitMessage(data.message);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleLogout = () => {
    clearSession();
    navigate('/');
  };

  if (!teacherId) return null;

  return (
    <div className="min-h-screen bg-gray-100 flex justify-center p-4 font-sans">
      <div className="w-full max-w-[400px] bg-gray-50 rounded-[2rem] shadow-xl overflow-hidden border-4 border-white flex flex-col relative h-[800px]">
        <header className="bg-blue-800 text-white pt-10 pb-4 px-6 rounded-b-3xl shadow-md z-10 flex justify-between items-center">
          <button type="button" onClick={handleLogout} className="text-sm bg-white/20 px-3 py-1 rounded-lg">← 戻る</button>
          <div className="text-center">
            <h1 className="text-lg font-bold">シフト入力</h1>
            <p className="text-xs text-blue-200">{teacherName}</p>
          </div>
          <div className="w-8 h-8" />
        </header>

        <main className="flex-1 overflow-y-auto p-4 hide-scrollbar">
          {error && <p className="text-red-500 text-sm mb-4 text-center">{error}</p>}
          {submitMessage && <p className="text-emerald-600 text-sm mb-4 text-center font-bold">{submitMessage}</p>}

          <div className="flex gap-2 mb-4 overflow-x-auto pb-2">
            {availableDates.map((isoDate) => (
              <DateSelector
                key={isoDate}
                isoDate={isoDate}
                isActive={selectedDate === isoDate}
                onClick={() => setSelectedDate(isoDate)}
              />
            ))}
          </div>

          <div className="flex justify-center gap-4 mb-4 text-xs text-gray-500">
            <span><span className="text-slate-600 font-bold">◎</span> 通常授業</span>
            <span><span className="text-emerald-600 font-bold">空</span> 空いてる</span>
            <span><span className="text-red-500 font-bold">×</span> 無理</span>
          </div>

          {isLoading ? (
            <p className="text-gray-500 text-center py-8">読み込み中...</p>
          ) : (
            <div className="space-y-3">
              {timeSlots.map(({ slot, start, end }) => (
                <TimeSlot
                  key={slot}
                  period={slot}
                  time={{ start, end }}
                  status={shiftData[slot]}
                  disabled={isSaving || isSubmitting}
                  onStatusChange={(status) => handleStatusChange(slot, status)}
                />
              ))}
            </div>
          )}
        </main>

        <footer className="bg-white p-4 border-t border-gray-100">
          <button
            type="button"
            onClick={handleSubmit}
            disabled={isLoading || isSubmitting || isSaving}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-bold py-4 rounded-xl shadow-lg transition-transform active:scale-95"
          >
            {isSubmitting ? '提出中...' : '提出する'}
          </button>
        </footer>
      </div>
    </div>
  );
}
