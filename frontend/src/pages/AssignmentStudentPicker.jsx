import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAdminSession } from '../hooks/useAdminSession';
import { AdminSidebar } from '../components/AdminSidebar';

const LEVEL_COLUMNS = [
  { key: 'elementary', title: '小学生', accent: 'bg-emerald-600' },
  { key: 'middle', title: '中学生', accent: 'bg-blue-600' },
  { key: 'high', title: '高校生', accent: 'bg-violet-600' },
];

function groupBySchoolLevel(students) {
  const cols = { elementary: [], middle: [], high: [] };
  for (const s of students) {
    const level = s.school_level || 'middle';
    if (cols[level]) cols[level].push(s);
  }
  for (const level of Object.keys(cols)) {
    cols[level].sort((a, b) => {
      const g = (b.grade_year || 0) - (a.grade_year || 0);
      if (g !== 0) return g;
      return (a.name || '').localeCompare(b.name || '', 'ja');
    });
  }
  return cols;
}

function formatStudentPlans(student) {
  const plans = Array.isArray(student.subject_plans) ? student.subject_plans : [];
  const subjects = Array.isArray(student.subjects) ? student.subjects : [];
  if (plans.length > 0) {
    return plans.map((p) => `${p.subject}×${p.slot_count}`).join('、');
  }
  if (subjects.length > 0) {
    return subjects.join('、');
  }
  return null;
}

function TeacherCard({ teacher, onPublish, publishing }) {
  const canPublish = !teacher.schedule_published;
  const isPublishing = publishing === teacher.id;

  return (
    <div className="bg-white border-2 border-gray-200 rounded-xl p-3">
      <div className="flex items-center gap-2">
        <span
          className="w-3 h-3 rounded-full shrink-0"
          style={{ backgroundColor: teacher.color || '#94a3b8' }}
        />
        <h4 className="font-bold text-gray-900 truncate">{teacher.name}</h4>
      </div>
      <div className="mt-2 flex gap-2 flex-wrap items-center">
        {teacher.schedule_published ? (
          <span className="text-xs font-bold bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full">
            送信済
          </span>
        ) : (
          <span className="text-xs font-bold bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
            未送信
          </span>
        )}
      </div>
      {canPublish && (
        <button
          type="button"
          disabled={isPublishing}
          onClick={() => onPublish(teacher.id)}
          className="mt-3 w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white text-sm font-bold py-2.5 rounded-xl shadow-sm transition-colors"
        >
          {isPublishing ? '送信中...' : '確定して講師に送信'}
        </button>
      )}
      {teacher.schedule_published && (
        <p className="mt-2 text-[11px] text-blue-700 font-bold">
          講師画面にスケジュールを送付済みです
        </p>
      )}
    </div>
  );
}

function StudentCard({ student, onOpen, onPublish, publishing }) {
  const planSummary = formatStudentPlans(student);
  const canPublish = student.pending_count === 0 && !student.schedule_published;
  const isPublishing = publishing === student.id;

  return (
    <div className="bg-white border-2 border-gray-200 hover:border-blue-300 rounded-xl p-3 transition-all w-full">
      <button
        type="button"
        onClick={() => onOpen(student.id)}
        className="text-left w-full"
      >
        <div className="flex items-baseline gap-2">
          {student.grade_label && (
            <span className="text-xs font-bold text-gray-500 shrink-0">{student.grade_label}</span>
          )}
          <h4 className="font-bold text-gray-900 truncate">{student.name}</h4>
        </div>
        {planSummary && (
          <p className="text-xs text-gray-500 truncate mt-0.5">
            希望: {planSummary}
          </p>
        )}
        <p className="text-xs text-blue-600 font-bold mt-2">割当を編集 →</p>
      </button>

      <div className="mt-2 flex gap-2 flex-wrap items-center">
        {student.pending_count > 0 ? (
          <span className="text-xs font-bold bg-amber-100 text-amber-800 px-2 py-0.5 rounded-full">
            未割当 {student.pending_count}
          </span>
        ) : (
          <span className="text-xs font-bold bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full">
            割当済
          </span>
        )}
        {student.schedule_published && (
          <span className="text-xs font-bold bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full">
            送信済
          </span>
        )}
      </div>

      {canPublish && (
        <button
          type="button"
          disabled={isPublishing}
          onClick={() => onPublish(student.id)}
          className="mt-3 w-full bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-400 text-white text-sm font-bold py-2.5 rounded-xl shadow-sm transition-colors"
        >
          {isPublishing ? '送信中...' : '確定して生徒に送信'}
        </button>
      )}
      {student.pending_count > 0 && !student.schedule_published && (
        <p className="mt-2 text-[11px] text-amber-700 font-bold">
          未割当をすべて埋めてから確定できます
        </p>
      )}
      {student.schedule_published && (
        <p className="mt-2 text-[11px] text-blue-700 font-bold">
          生徒画面にスケジュールを送付済みです
        </p>
      )}
    </div>
  );
}

function LevelColumn({ title, accent, students, onOpen, onPublish, publishing }) {
  return (
    <div className="flex flex-col min-w-0 flex-1">
      <div className={`${accent} text-white text-center font-bold py-2.5 rounded-t-xl text-sm`}>
        {title}
        <span className="font-normal opacity-90 ml-1">({students.length}名)</span>
      </div>
      <div className="flex-1 bg-white border-2 border-t-0 border-gray-200 rounded-b-xl p-3 space-y-2 min-h-[200px]">
        {students.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-8">該当なし</p>
        ) : (
          students.map((s) => (
            <StudentCard
              key={s.id}
              student={s}
              onOpen={onOpen}
              onPublish={onPublish}
              publishing={publishing}
            />
          ))
        )}
      </div>
    </div>
  );
}

export default function AssignmentStudentPicker() {
  const navigate = useNavigate();
  const isReady = useAdminSession();
  const [periods, setPeriods] = useState([]);
  const [periodId, setPeriodId] = useState(null);
  const [sheets, setSheets] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [message, setMessage] = useState(null);
  const [publishingId, setPublishingId] = useState(null);
  const [publishingTeacherId, setPublishingTeacherId] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  const loadSheets = useCallback(async (pid) => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const res = await fetch(`/api/admin/assignments/sheets?period_id=${pid}`);
      if (!res.ok) throw new Error('生徒一覧の取得に失敗しました');
      setSheets(await res.json());
    } catch (err) {
      setLoadError(err.message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isReady) return;
    fetch('/api/admin/periods')
      .then((r) => r.json())
      .then((data) => {
        setPeriods(data.periods ?? []);
        setPeriodId(data.active_period_id ?? data.periods?.[0]?.id ?? null);
      })
      .catch(() => setLoadError('期間の取得に失敗しました'));
  }, [isReady]);

  useEffect(() => {
    if (!periodId) {
      setIsLoading(false);
      return;
    }
    loadSheets(periodId);
  }, [periodId, loadSheets]);

  const students = sheets?.students ?? [];
  const teachers = sheets?.teachers ?? [];
  const publishStats = useMemo(() => {
    const published = students.filter((s) => s.schedule_published).length;
    const ready = students.filter((s) => s.pending_count === 0 && !s.schedule_published).length;
    const pending = students.filter((s) => s.pending_count > 0).length;
    return { published, ready, pending, total: students.length };
  }, [students]);

  const teacherPublishStats = useMemo(() => {
    const published = teachers.filter((t) => t.schedule_published).length;
    return { published, total: teachers.length };
  }, [teachers]);

  const handlePublish = async (studentId) => {
    if (!periodId || publishingId) return;
    setPublishingId(studentId);
    setMessage(null);
    setLoadError(null);
    try {
      const res = await fetch('/api/admin/assignments/publish-schedule', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ period_id: periodId, student_id: studentId }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || 'スケジュール送信に失敗しました');
      setSheets(data.sheets);
      setMessage(data.message);
    } catch (err) {
      setLoadError(err.message);
    } finally {
      setPublishingId(null);
    }
  };

  const handlePublishTeacher = async (teacherId) => {
    if (!periodId || publishingTeacherId) return;
    setPublishingTeacherId(teacherId);
    setMessage(null);
    setLoadError(null);
    try {
      const res = await fetch('/api/admin/assignments/publish-teacher-schedule', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ period_id: periodId, teacher_id: teacherId }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || '講師への送信に失敗しました');
      setSheets(data.sheets);
      setMessage(data.message);
    } catch (err) {
      setLoadError(err.message);
    } finally {
      setPublishingTeacherId(null);
    }
  };

  const byLevel = useMemo(() => groupBySchoolLevel(students), [students]);
  const openDays = sheets?.dates?.length ?? 0;

  if (!isReady) return null;

  return (
    <div className="min-h-screen bg-gray-50 flex font-sans">
      <AdminSidebar navigate={navigate} current="assignments" />

      <div className="flex-1 p-8 overflow-y-auto">
        <header className="mb-6">
          <h2 className="text-3xl font-bold text-gray-800">生徒の割り当て</h2>
          <p className="text-sm text-gray-500 mt-2">
            {sheets?.period_name ?? '—'} — 紙・スケジュール {openDays} 日分（日曜除く）
          </p>
          {students.length > 0 && (
            <p className="text-sm text-gray-600 mt-2">
              送信済み <span className="font-bold text-blue-700">{publishStats.published}</span>
              / {publishStats.total} 名
              {publishStats.ready > 0 && (
                <span className="ml-3 text-emerald-700 font-bold">確定可能 {publishStats.ready} 名</span>
              )}
              {publishStats.pending > 0 && (
                <span className="ml-3 text-amber-700 font-bold">未割当あり {publishStats.pending} 名</span>
              )}
            </p>
          )}
          {periods.length > 1 && (
            <select
              value={periodId ?? ''}
              onChange={(e) => setPeriodId(Number(e.target.value))}
              className="mt-3 border rounded-lg px-3 py-2 font-bold bg-white"
            >
              {periods.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          )}
        </header>

        {loadError && <p className="text-red-500 mb-4">{loadError}</p>}
        {message && <p className="text-emerald-600 font-bold mb-4">{message}</p>}

        {!periodId && !isLoading && (
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-6">
            <p className="text-amber-900 font-bold mb-2">講習がまだありません</p>
            <button type="button" onClick={() => navigate('/admin/manage')} className="text-blue-600 font-bold hover:underline">
              教室管理で講習を作成 →
            </button>
          </div>
        )}

        {isLoading ? (
          <p className="text-gray-500">読み込み中...</p>
        ) : students.length === 0 && periodId ? (
          <p className="text-gray-500">
            生徒が登録されていません。
            <button type="button" onClick={() => navigate('/admin/manage')} className="text-blue-600 font-bold ml-1">教室管理で追加</button>
          </p>
        ) : (
          <>
            <div className="mb-4 p-4 bg-white border border-gray-200 rounded-xl text-sm text-gray-700">
              <p className="font-bold text-gray-800">確定の流れ</p>
              <ol className="mt-2 list-decimal list-inside space-y-1 text-gray-600">
                <li>生徒を選んで割当を完成させる（未割当 0 になるまで）</li>
                <li>「確定して生徒に送信」を押すと、生徒画面にスケジュールが届きます</li>
                <li>送付後は生徒は変更申請のみ可能です</li>
              </ol>
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 items-start">
              {LEVEL_COLUMNS.map((col) => (
                <LevelColumn
                  key={col.key}
                  title={col.title}
                  accent={col.accent}
                  students={byLevel[col.key] ?? []}
                  onOpen={(id) => navigate(`/admin/assignments/${id}`)}
                  onPublish={handlePublish}
                  publishing={publishingId}
                />
              ))}
            </div>

            {teachers.length > 0 && (
              <section className="mt-10">
                <h3 className="text-xl font-bold text-gray-800 mb-2">講師への送付</h3>
                <p className="text-sm text-gray-600 mb-4">
                  送信済み <span className="font-bold text-blue-700">{teacherPublishStats.published}</span>
                  / {teacherPublishStats.total} 名
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                  {teachers.map((t) => (
                    <TeacherCard
                      key={t.id}
                      teacher={t}
                      onPublish={handlePublishTeacher}
                      publishing={publishingTeacherId}
                    />
                  ))}
                </div>
              </section>
            )}
          </>
        )}
      </div>
    </div>
  );
}
