import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { LoadingSpinner } from '../components/ScheduleEditor';
import { useNavigate } from 'react-router-dom';
import { useAdminSession } from '../hooks/useAdminSession';
import { apiFetch } from '../utils/apiClient';
import { parseApiError } from '../utils/apiError';

const DAY_LABELS = ['日', '月', '火', '水', '木', '金', '土'];

function formatDate(isoDate) {
  const d = new Date(`${isoDate}T12:00:00`);
  return `${d.getMonth() + 1}/${d.getDate()}(${DAY_LABELS[d.getDay()]})`;
}

function teacherLabel(name) {
  if (!name) return '';
  return name.includes('先生') ? name : `${name} 先生`;
}

/** 生徒1人分のコンパクトな予定カード */
function StudentCard({ student, periodName, timeByStot }) {
  return (
    <div className="print-card border border-gray-400 rounded-lg overflow-hidden bg-white">
      <div className="px-3 py-2 bg-gray-100 border-b border-gray-400 flex items-baseline justify-between gap-2">
        <span className="text-base font-bold text-gray-900">{student.name}</span>
        <span className="text-[10px] text-gray-500 truncate">{periodName}</span>
      </div>
      <table className="w-full text-[11px] leading-tight">
        <thead>
          <tr className="border-b border-gray-300 text-gray-600">
            <th className="px-2 py-1 text-left font-bold w-16">日付</th>
            <th className="px-2 py-1 text-left font-bold w-20">時間</th>
            <th className="px-2 py-1 text-left font-bold">教科</th>
            <th className="px-2 py-1 text-left font-bold">担当</th>
          </tr>
        </thead>
        <tbody>
          {student.lessons.map((lesson, i) => {
            const time = timeByStot[lesson.slot];
            const isRegular = lesson.lesson_kind === '通常' || lesson.is_fixed;
            return (
              <tr key={`${lesson.date}-${lesson.slot}-${i}`} className="border-b border-gray-200 last:border-b-0">
                <td className="px-2 py-1 whitespace-nowrap font-bold text-gray-800">{formatDate(lesson.date)}</td>
                <td className="px-2 py-1 whitespace-nowrap text-gray-700">
                  {lesson.slot}コマ {time ? `${time.start}〜` : ''}
                </td>
                <td className="px-2 py-1 font-bold text-gray-900">
                  {lesson.subject}
                  {isRegular && <span className="ml-1 font-normal text-gray-500">(通常)</span>}
                </td>
                <td className="px-2 py-1 text-gray-700 whitespace-nowrap">{teacherLabel(lesson.teacher_name)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default function PrintStudentSchedules() {
  const navigate = useNavigate();
  const isReady = useAdminSession();
  const [periods, setPeriods] = useState([]);
  const [periodId, setPeriodId] = useState(null);
  const [schedule, setSchedule] = useState(null);
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedIds, setSelectedIds] = useState(null); // null = 未初期化（全員選択予定）

  useEffect(() => {
    if (!isReady) return;
    apiFetch('/api/admin/periods')
      .then((r) => r.json())
      .then((data) => {
        setPeriods(data.periods ?? []);
        setPeriodId(data.active_period_id ?? data.periods?.[0]?.id ?? null);
      })
      .catch(() => setError('講習一覧の取得に失敗しました'));
  }, [isReady]);

  const loadSchedule = useCallback(async (pid) => {
    if (!pid) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await apiFetch(`/api/admin/schedule/full?period_id=${pid}`);
      if (!res.ok) throw new Error(await parseApiError(res, '時間割の取得に失敗しました'));
      setSchedule(await res.json());
    } catch (err) {
      setError(err.message);
      setSchedule(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (periodId) loadSchedule(periodId);
  }, [periodId, loadSchedule]);

  const timeByStot = useMemo(() => {
    const map = {};
    (schedule?.time_slots ?? []).forEach((t) => { map[t.slot] = t; });
    return map;
  }, [schedule]);

  const students = useMemo(() => {
    const byStudent = new Map();
    (schedule?.schedules ?? []).forEach((row) => {
      if (!row.student_id) return;
      if (!byStudent.has(row.student_id)) {
        byStudent.set(row.student_id, { id: row.student_id, name: row.student_name, lessons: [] });
      }
      byStudent.get(row.student_id).lessons.push(row);
    });
    const list = [...byStudent.values()];
    list.forEach((s) => s.lessons.sort((a, b) => (a.date === b.date ? a.slot - b.slot : a.date < b.date ? -1 : 1)));
    list.sort((a, b) => a.name.localeCompare(b.name, 'ja'));
    return list;
  }, [schedule]);

  // 講習を切り替えて生徒リストが変わったら、まず全員を選択状態にする
  useEffect(() => {
    if (students.length) {
      setSelectedIds(new Set(students.map((s) => s.id)));
    } else {
      setSelectedIds(new Set());
    }
  }, [students]);

  const toggleStudent = (id) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectedStudents = useMemo(
    () => students.filter((s) => selectedIds?.has(s.id)),
    [students, selectedIds],
  );

  if (!isReady) return null;

  return (
    <div className="min-h-screen bg-gray-100 print:bg-white">
      <style>{`
        @page { size: A4 portrait; margin: 10mm; }
        @media print {
          .print-card { break-inside: avoid; page-break-inside: avoid; }
        }
      `}</style>

      {/* 操作バー（印刷時は非表示） */}
      <div className="print:hidden sticky top-0 z-10 bg-white border-b border-gray-200 shadow-sm px-4 py-3 flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={() => navigate('/admin')}
          className="text-sm text-gray-500 hover:text-gray-800"
        >
          ← ダッシュボード
        </button>
        <h1 className="text-lg font-bold text-gray-900">印刷用ビュー（生徒別時間割）</h1>
        <select
          value={periodId ?? ''}
          onChange={(e) => setPeriodId(Number(e.target.value))}
          className="border rounded-lg px-3 py-1.5 text-sm bg-white"
        >
          {periods.map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
        <button
          type="button"
          onClick={() => window.print()}
          disabled={!selectedStudents.length}
          className="ml-auto px-5 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white rounded-lg text-sm font-bold"
        >
          🖨 印刷する（{selectedStudents.length}名）
        </button>
      </div>

      {/* 生徒の選択（印刷時は非表示） */}
      {students.length > 0 && (
        <div className="print:hidden max-w-5xl mx-auto px-4 pt-4">
          <div className="bg-white border border-gray-200 rounded-xl p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-bold text-gray-700">印刷する生徒を選択</span>
              <div className="flex gap-3 text-xs font-bold">
                <button
                  type="button"
                  onClick={() => setSelectedIds(new Set(students.map((s) => s.id)))}
                  className="text-blue-600 hover:underline"
                >
                  すべて選択
                </button>
                <button
                  type="button"
                  onClick={() => setSelectedIds(new Set())}
                  className="text-gray-500 hover:underline"
                >
                  すべて解除
                </button>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              {students.map((s) => {
                const checked = selectedIds?.has(s.id) ?? false;
                return (
                  <label
                    key={s.id}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-sm cursor-pointer select-none ${
                      checked ? 'bg-blue-50 border-blue-300 text-blue-900' : 'bg-gray-50 border-gray-200 text-gray-500'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggleStudent(s.id)}
                      className="rounded border-gray-300"
                    />
                    {s.name}
                  </label>
                );
              })}
            </div>
          </div>
        </div>
      )}

      <div className="max-w-5xl mx-auto p-4 print:p-0 print:max-w-none">
        {error && <p className="text-red-500 text-sm mb-4 print:hidden">{error}</p>}
        {isLoading && <div className="print:hidden"><LoadingSpinner /></div>}
        {!isLoading && schedule && students.length === 0 && (
          <p className="text-gray-500 text-sm py-12 text-center print:hidden">
            この講習にはまだ割当がありません
          </p>
        )}
        {!isLoading && students.length > 0 && selectedStudents.length === 0 && (
          <p className="text-gray-500 text-sm py-12 text-center print:hidden">
            生徒が選択されていません
          </p>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 print:grid-cols-2 gap-4 print:gap-3">
          {selectedStudents.map((s) => (
            <StudentCard key={s.id} student={s} periodName={schedule?.period_name ?? ''} timeByStot={timeByStot} />
          ))}
        </div>
      </div>
    </div>
  );
}
