import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAdminSession } from '../hooks/useAdminSession';
import { AdminSidebar } from '../components/AdminSidebar';

const LEVEL_OPTIONS = [
  { value: 'elementary', label: '小学部' },
  { value: 'middle', label: '中学部' },
  { value: 'high', label: '高校部' },
];

const LEVEL_ORDER = { elementary: 0, middle: 1, high: 2 };

const SUBJECT_PRESETS = ['国語', '数学', '数学I', '数学II', '英語', '理科', '社会'];

function formatPlanSummary(plans) {
  if (!plans?.length) return '未設定';
  return plans.map((p) => `${p.subject}×${p.slot_count}`).join('、');
}

function emptyPlanRow() {
  return { subject: '数学', slot_count: 1 };
}

const WEEKDAY_JA = ['日', '月', '火', '水', '木', '金', '土'];

function candidateOpenDates(start, end) {
  if (!start || !end || end < start) return [];
  const dates = [];
  const cursor = new Date(`${start}T12:00:00`);
  const last = new Date(`${end}T12:00:00`);
  while (cursor <= last) {
    if (cursor.getDay() !== 0) {
      const y = cursor.getFullYear();
      const m = String(cursor.getMonth() + 1).padStart(2, '0');
      const d = String(cursor.getDate()).padStart(2, '0');
      dates.push(`${y}-${m}-${d}`);
    }
    cursor.setDate(cursor.getDate() + 1);
  }
  return dates;
}

function formatDateLabel(iso) {
  const d = new Date(`${iso}T12:00:00`);
  return `${d.getMonth() + 1}/${d.getDate()}(${WEEKDAY_JA[d.getDay()]})`;
}

function Section({ title, children }) {
  return (
    <section className="bg-white rounded-2xl border shadow-sm p-6 mb-6">
      <h3 className="text-lg font-bold text-gray-800 mb-4">{title}</h3>
      {children}
    </section>
  );
}

function groupStudents(students) {
  const buckets = {};
  for (const s of students) {
    const key = `${s.school_level}-${s.grade_year}`;
    if (!buckets[key]) {
      buckets[key] = {
        school_level: s.school_level,
        level_label: s.level_label,
        grade_label: s.grade_label,
        students: [],
      };
    }
    buckets[key].students.push(s);
  }
  return Object.values(buckets).sort((a, b) => {
    const lo = (LEVEL_ORDER[a.school_level] ?? 9) - (LEVEL_ORDER[b.school_level] ?? 9);
    if (lo !== 0) return lo;
    return b.grade_year - a.grade_year;
  });
}

export default function AdminManage() {
  const navigate = useNavigate();
  const isReady = useAdminSession();
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);

  const [periods, setPeriods] = useState([]);
  const [activePeriodId, setActivePeriodId] = useState(null);
  const [students, setStudents] = useState([]);
  const [teachers, setTeachers] = useState([]);

  const [periodForm, setPeriodForm] = useState({ name: '', start_date: '', end_date: '' });
  const [openDateSelection, setOpenDateSelection] = useState([]);
  const [studentForm, setStudentForm] = useState({ name: '', school_level: 'middle', grade_year: 2 });
  const [teacherForm, setTeacherForm] = useState({ name: '' });
  const [editingStudentId, setEditingStudentId] = useState(null);
  const [editingTeacherId, setEditingTeacherId] = useState(null);
  const [periodPlans, setPeriodPlans] = useState([]);
  const [planStudentId, setPlanStudentId] = useState(null);
  const [planRows, setPlanRows] = useState([emptyPlanRow()]);
  const [isSavingPlans, setIsSavingPlans] = useState(false);

  const loadAll = useCallback(async () => {
    setError(null);
    try {
      const [pRes, sRes, tRes] = await Promise.all([
        fetch('/api/admin/periods'),
        fetch('/api/admin/students'),
        fetch('/api/admin/teachers'),
      ]);
      if (!pRes.ok || !sRes.ok || !tRes.ok) throw new Error('データの取得に失敗しました');
      const pData = await pRes.json();
      const sData = await sRes.json();
      const tData = await tRes.json();
      setPeriods(pData.periods ?? []);
      const pid = pData.active_period_id;
      setActivePeriodId(pid);
      setStudents(sData.students ?? []);
      setTeachers(tData.teachers ?? []);
      if (pid) {
        const planRes = await fetch(`/api/admin/periods/${pid}/student-plans`);
        if (planRes.ok) {
          const planData = await planRes.json();
          setPeriodPlans(planData.students ?? []);
        } else {
          setPeriodPlans([]);
        }
      } else {
        setPeriodPlans([]);
      }
    } catch (err) {
      setError(err.message);
    }
  }, []);

  useEffect(() => {
    if (isReady) loadAll();
  }, [isReady, loadAll]);

  const studentGroups = useMemo(() => groupStudents(students), [students]);

  const plansByStudentId = useMemo(() => {
    const map = {};
    periodPlans.forEach((entry) => {
      map[entry.student_id] = entry.plans ?? [];
    });
    return map;
  }, [periodPlans]);

  const activePeriod = periods.find((p) => p.id === activePeriodId);
  const plansReadonly = activePeriod?.status === 'FINALIZED';

  const periodCandidates = useMemo(
    () => candidateOpenDates(periodForm.start_date, periodForm.end_date),
    [periodForm.start_date, periodForm.end_date],
  );

  useEffect(() => {
    setOpenDateSelection(periodCandidates);
  }, [periodCandidates]);

  const resetStudentForm = () => {
    setStudentForm({ name: '', school_level: 'middle', grade_year: 2 });
    setEditingStudentId(null);
  };

  const resetTeacherForm = () => {
    setTeacherForm({ name: '' });
    setEditingTeacherId(null);
  };

  const handleCreatePeriod = async (e) => {
    e.preventDefault();
    setMessage(null);
    setError(null);
    if (openDateSelection.length === 0) {
      setError('開校日を1日以上選んでください');
      return;
    }
    const closed_dates = periodCandidates.filter((d) => !openDateSelection.includes(d));
    try {
      const res = await fetch('/api/admin/periods', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...periodForm, closed_dates }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || '講習の作成に失敗しました');
      }
      const data = await res.json();
      setMessage(data.message);
      setPeriodForm({ name: '', start_date: '', end_date: '' });
      setOpenDateSelection([]);
      await loadAll();
    } catch (err) {
      setError(err.message);
    }
  };

  const toggleOpenDate = (iso) => {
    setOpenDateSelection((prev) => (
      prev.includes(iso) ? prev.filter((d) => d !== iso) : [...prev, iso].sort()
    ));
  };

  const handleActivatePeriod = async (periodId) => {
    setMessage(null);
    setError(null);
    try {
      const res = await fetch(`/api/admin/periods/${periodId}/activate`, { method: 'PATCH' });
      if (!res.ok) throw new Error('講習の選択に失敗しました');
      const data = await res.json();
      setMessage(data.message);
      await loadAll();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleSaveStudent = async (e) => {
    e.preventDefault();
    setMessage(null);
    setError(null);
    try {
      const isEdit = editingStudentId != null;
      const res = await fetch(
        isEdit ? `/api/admin/students/${editingStudentId}` : '/api/admin/students',
        {
          method: isEdit ? 'PATCH' : 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(studentForm),
        },
      );
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || (isEdit ? '生徒の更新に失敗しました' : '生徒の追加に失敗しました'));
      }
      const data = await res.json();
      setMessage(isEdit ? `生徒「${data.name}」を更新しました` : `生徒「${data.name}」を追加しました`);
      resetStudentForm();
      await loadAll();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleEditStudent = (s) => {
    setEditingStudentId(s.id);
    setStudentForm({ name: s.name, school_level: s.school_level, grade_year: s.grade_year });
    setEditingTeacherId(null);
    resetTeacherForm();
  };

  const openPlanEditor = (s) => {
    setPlanStudentId(s.id);
    const existing = plansByStudentId[s.id] ?? [];
    setPlanRows(existing.length ? existing.map((p) => ({ ...p })) : [emptyPlanRow()]);
    setEditingStudentId(null);
    setEditingTeacherId(null);
  };

  const handleSavePlans = async (e) => {
    e.preventDefault();
    if (!activePeriodId || planStudentId == null || isSavingPlans) return;
    setIsSavingPlans(true);
    setMessage(null);
    setError(null);
    try {
      const res = await fetch(
        `/api/admin/periods/${activePeriodId}/students/${planStudentId}/plans`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ plans: planRows.filter((r) => r.subject?.trim() && r.slot_count > 0) }),
        },
      );
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || '希望の保存に失敗しました');
      const student = students.find((s) => s.id === planStudentId);
      setMessage(
        `${student?.name ?? '生徒'}の希望を保存しました（割当リクエスト ${data.synced_request_count} 件）`,
      );
      setPlanStudentId(null);
      await loadAll();
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSavingPlans(false);
    }
  };

  const handleDeleteStudent = async (s) => {
    if (!window.confirm(`「${s.name}」を削除しますか？\n割当・希望データも削除されます。`)) return;
    setMessage(null);
    setError(null);
    try {
      const res = await fetch(`/api/admin/students/${s.id}`, { method: 'DELETE' });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || '生徒の削除に失敗しました');
      }
      if (editingStudentId === s.id) resetStudentForm();
      setMessage(`生徒「${s.name}」を削除しました`);
      await loadAll();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleSaveTeacher = async (e) => {
    e.preventDefault();
    setMessage(null);
    setError(null);
    try {
      const isEdit = editingTeacherId != null;
      const res = await fetch(
        isEdit ? `/api/admin/teachers/${editingTeacherId}` : '/api/admin/teachers',
        {
          method: isEdit ? 'PATCH' : 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(teacherForm),
        },
      );
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || (isEdit ? '講師の更新に失敗しました' : '講師の追加に失敗しました'));
      }
      const data = await res.json();
      setMessage(isEdit ? `講師「${data.name}」を更新しました` : `講師「${data.name}」を追加しました`);
      resetTeacherForm();
      await loadAll();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleEditTeacher = (t) => {
    setEditingTeacherId(t.id);
    setTeacherForm({ name: t.name });
    setEditingStudentId(null);
    resetStudentForm();
  };

  const handleDeleteTeacher = async (t) => {
    if (!window.confirm(`「${t.name}」を削除しますか？`)) return;
    setMessage(null);
    setError(null);
    try {
      const res = await fetch(`/api/admin/teachers/${t.id}`, { method: 'DELETE' });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || '講師の削除に失敗しました');
      }
      if (editingTeacherId === t.id) resetTeacherForm();
      setMessage(`講師「${t.name}」を削除しました`);
      await loadAll();
    } catch (err) {
      setError(err.message);
    }
  };

  if (!isReady) return null;

  const maxGrade = studentForm.school_level === 'elementary' ? 6 : 3;

  return (
    <div className="min-h-screen bg-gray-50 flex font-sans">
      <AdminSidebar navigate={navigate} current="manage" />

      <div className="flex-1 p-8 overflow-y-auto max-w-4xl">
        <header className="mb-8">
          <h2 className="text-3xl font-bold text-gray-800">教室管理</h2>
          <p className="text-sm text-gray-500 mt-2">講習の作成・生徒・講師の登録。日曜は自動で休校。開校する日を個別に選べます。</p>
        </header>

        {error && <p className="text-red-500 mb-4">{error}</p>}
        {message && <p className="text-emerald-600 font-bold mb-4">{message}</p>}

        <Section title="講習（期間）を作成">
          <form onSubmit={handleCreatePeriod} className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
            <label className="block sm:col-span-2">
              <span className="text-sm font-bold text-gray-600">講習名</span>
              <input
                required
                value={periodForm.name}
                onChange={(e) => setPeriodForm({ ...periodForm, name: e.target.value })}
                placeholder="例: 2026年 夏期講習"
                className="mt-1 w-full border rounded-lg px-3 py-2"
              />
            </label>
            <label className="block">
              <span className="text-sm font-bold text-gray-600">開始日</span>
              <input
                required
                type="date"
                value={periodForm.start_date}
                onChange={(e) => setPeriodForm({ ...periodForm, start_date: e.target.value })}
                className="mt-1 w-full border rounded-lg px-3 py-2"
              />
            </label>
            <label className="block">
              <span className="text-sm font-bold text-gray-600">終了日</span>
              <input
                required
                type="date"
                value={periodForm.end_date}
                onChange={(e) => setPeriodForm({ ...periodForm, end_date: e.target.value })}
                className="mt-1 w-full border rounded-lg px-3 py-2"
              />
            </label>
            {periodCandidates.length > 0 && (
              <div className="sm:col-span-2 border rounded-xl p-4 bg-gray-50">
                <div className="flex items-center justify-between mb-3 gap-2 flex-wrap">
                  <span className="text-sm font-bold text-gray-700">開校日（チェックを外すと休校）</span>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setOpenDateSelection([...periodCandidates])}
                      className="text-xs font-bold text-blue-600 hover:underline"
                    >
                      すべて選択
                    </button>
                    <button
                      type="button"
                      onClick={() => setOpenDateSelection([])}
                      className="text-xs font-bold text-gray-500 hover:underline"
                    >
                      すべて解除
                    </button>
                  </div>
                </div>
                <p className="text-xs text-gray-500 mb-3">
                  日曜は表示されません。{openDateSelection.length} / {periodCandidates.length} 日を開校
                </p>
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2 max-h-48 overflow-y-auto">
                  {periodCandidates.map((iso) => (
                    <label key={iso} className="flex items-center gap-2 text-sm bg-white border rounded-lg px-2 py-1.5 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={openDateSelection.includes(iso)}
                        onChange={() => toggleOpenDate(iso)}
                      />
                      <span>{formatDateLabel(iso)}</span>
                    </label>
                  ))}
                </div>
              </div>
            )}
            <button type="submit" className="sm:col-span-2 bg-blue-600 hover:bg-blue-700 text-white py-3 rounded-xl font-bold">
              講習を作成（紙・スケジュールを生成）
            </button>
          </form>
          {periods.length > 0 && (
            <ul className="space-y-2">
              {periods.map((p) => (
                <li key={p.id} className={`flex items-center justify-between p-3 rounded-xl border ${p.id === activePeriodId ? 'border-blue-500 bg-blue-50' : 'border-gray-200'}`}>
                  <div>
                    <span className="font-bold">{p.name}</span>
                    <span className="text-sm text-gray-500 ml-2">{p.start_date} 〜 {p.end_date}</span>
                    <span className="text-xs ml-2 px-2 py-0.5 rounded-full bg-gray-100">{p.status}</span>
                  </div>
                  {p.id !== activePeriodId && (
                    <button type="button" onClick={() => handleActivatePeriod(p.id)} className="text-sm font-bold text-blue-600 hover:underline">
                      選択
                    </button>
                  )}
                  {p.id === activePeriodId && <span className="text-xs font-bold text-blue-600">使用中</span>}
                </li>
              ))}
            </ul>
          )}
        </Section>

        <Section title={editingStudentId ? '生徒を編集' : '生徒を追加'}>
          <form onSubmit={handleSaveStudent} className="flex flex-wrap gap-3 items-end">
            <label className="flex-1 min-w-[140px]">
              <span className="text-sm font-bold text-gray-600">氏名</span>
              <input required value={studentForm.name} onChange={(e) => setStudentForm({ ...studentForm, name: e.target.value })} className="mt-1 w-full border rounded-lg px-3 py-2" />
            </label>
            <label>
              <span className="text-sm font-bold text-gray-600">部</span>
              <select value={studentForm.school_level} onChange={(e) => setStudentForm({ ...studentForm, school_level: e.target.value, grade_year: 1 })} className="mt-1 border rounded-lg px-3 py-2">
                {LEVEL_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </label>
            <label>
              <span className="text-sm font-bold text-gray-600">学年</span>
              <select value={studentForm.grade_year} onChange={(e) => setStudentForm({ ...studentForm, grade_year: Number(e.target.value) })} className="mt-1 border rounded-lg px-3 py-2">
                {Array.from({ length: maxGrade }, (_, i) => i + 1).map((g) => (
                  <option key={g} value={g}>{g}年</option>
                ))}
              </select>
            </label>
            <button type="submit" className="bg-emerald-600 hover:bg-emerald-700 text-white px-5 py-2.5 rounded-xl font-bold">
              {editingStudentId ? '保存' : '追加'}
            </button>
            {editingStudentId && (
              <button type="button" onClick={resetStudentForm} className="text-sm font-bold text-gray-500 hover:text-gray-700 px-2 py-2.5">
                キャンセル
              </button>
            )}
          </form>

          {studentGroups.length > 0 && (
            <div className="mt-6 space-y-4">
              {studentGroups.map((g) => (
                <div key={`${g.school_level}-${g.grade_label}`}>
                  <h4 className="text-sm font-bold text-gray-500 mb-2">
                    {g.level_label} {g.grade_label}
                  </h4>
                  <ul className="divide-y border rounded-xl overflow-hidden">
                    {g.students.map((s) => (
                      <li key={s.id} className="flex items-center justify-between px-4 py-2.5 bg-gray-50 hover:bg-white gap-2 flex-wrap">
                        <div className="min-w-0">
                          <span className="font-medium text-gray-800">{s.name}</span>
                          <p className="text-xs text-gray-500 mt-0.5 truncate">
                            希望: {formatPlanSummary(plansByStudentId[s.id])}
                          </p>
                        </div>
                        <div className="flex gap-2 shrink-0">
                          {activePeriodId && !plansReadonly && (
                            <button type="button" onClick={() => openPlanEditor(s)} className="text-xs font-bold text-violet-700 hover:underline">
                              希望設定
                            </button>
                          )}
                          <button type="button" onClick={() => handleEditStudent(s)} className="text-xs font-bold text-blue-600 hover:underline">編集</button>
                          <button type="button" onClick={() => handleDeleteStudent(s)} className="text-xs font-bold text-red-600 hover:underline">削除</button>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          )}
        </Section>

        {activePeriodId && (
          <Section title={`講習希望（教科・コマ数）— ${activePeriod?.name ?? ''}`}>
            <p className="text-sm text-gray-600 mb-4">
              生徒ごとに「取りたい教科」と「講習期間中のコマ数」を設定します。保存すると割当ボード用の未割当リクエストが自動生成されます。
              {plansReadonly && <span className="block mt-1 text-amber-700 font-bold">確定済みのため編集できません。</span>}
            </p>
            {planStudentId != null ? (
              <form onSubmit={handleSavePlans} className="space-y-3">
                <p className="font-bold text-gray-800">
                  {students.find((s) => s.id === planStudentId)?.name ?? '生徒'} の希望
                </p>
                {planRows.map((row, idx) => (
                  <div key={idx} className="flex flex-wrap gap-2 items-end">
                    <label className="flex-1 min-w-[120px]">
                      <span className="text-xs font-bold text-gray-600">教科</span>
                      <input
                        list="subject-presets"
                        value={row.subject}
                        onChange={(e) => {
                          const next = [...planRows];
                          next[idx] = { ...next[idx], subject: e.target.value };
                          setPlanRows(next);
                        }}
                        className="mt-1 w-full border rounded-lg px-3 py-2"
                        placeholder="例: 数学"
                      />
                    </label>
                    <label className="w-24">
                      <span className="text-xs font-bold text-gray-600">コマ数</span>
                      <input
                        type="number"
                        min={0}
                        max={60}
                        value={row.slot_count}
                        onChange={(e) => {
                          const next = [...planRows];
                          next[idx] = { ...next[idx], slot_count: Number(e.target.value) };
                          setPlanRows(next);
                        }}
                        className="mt-1 w-full border rounded-lg px-3 py-2"
                      />
                    </label>
                    <button
                      type="button"
                      onClick={() => setPlanRows(planRows.filter((_, i) => i !== idx))}
                      className="text-xs font-bold text-red-600 px-2 py-2.5"
                    >
                      削除
                    </button>
                  </div>
                ))}
                <datalist id="subject-presets">
                  {SUBJECT_PRESETS.map((sub) => (
                    <option key={sub} value={sub} />
                  ))}
                </datalist>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => setPlanRows([...planRows, emptyPlanRow()])}
                    className="text-sm font-bold text-gray-600 border rounded-lg px-3 py-2"
                  >
                    ＋ 教科を追加
                  </button>
                  <button
                    type="submit"
                    disabled={isSavingPlans}
                    className="bg-violet-600 hover:bg-violet-700 disabled:bg-violet-300 text-white px-5 py-2 rounded-xl font-bold"
                  >
                    {isSavingPlans ? '保存中...' : '保存してリクエスト反映'}
                  </button>
                  <button
                    type="button"
                    onClick={() => setPlanStudentId(null)}
                    className="text-sm font-bold text-gray-500 px-3 py-2"
                  >
                    キャンセル
                  </button>
                </div>
              </form>
            ) : (
              <p className="text-sm text-gray-500">生徒一覧の「希望設定」から編集してください。</p>
            )}
          </Section>
        )}

        <Section title={editingTeacherId ? '講師を編集' : '講師を追加'}>
          <form onSubmit={handleSaveTeacher} className="flex gap-3 items-end flex-wrap">
            <label className="flex-1 min-w-[140px]">
              <span className="text-sm font-bold text-gray-600">氏名</span>
              <input required value={teacherForm.name} onChange={(e) => setTeacherForm({ name: e.target.value })} placeholder="例: 山本 先生" className="mt-1 w-full border rounded-lg px-3 py-2" />
            </label>
            <button type="submit" className="bg-emerald-600 hover:bg-emerald-700 text-white px-5 py-2.5 rounded-xl font-bold">
              {editingTeacherId ? '保存' : '追加'}
            </button>
            {editingTeacherId && (
              <button type="button" onClick={resetTeacherForm} className="text-sm font-bold text-gray-500 hover:text-gray-700 px-2 py-2.5">
                キャンセル
              </button>
            )}
          </form>
          {teachers.length > 0 && (
            <ul className="mt-4 divide-y border rounded-xl overflow-hidden">
              {teachers.map((t) => (
                <li key={t.id} className="flex items-center justify-between px-4 py-2.5 bg-gray-50 hover:bg-white">
                  <div className="flex items-center gap-2 text-sm">
                    <span className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${t.color}`}>{t.name.charAt(0)}</span>
                    <span className="font-medium text-gray-800">{t.name}</span>
                  </div>
                  <div className="flex gap-2">
                    <button type="button" onClick={() => handleEditTeacher(t)} className="text-xs font-bold text-blue-600 hover:underline">編集</button>
                    <button type="button" onClick={() => handleDeleteTeacher(t)} className="text-xs font-bold text-red-600 hover:underline">削除</button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Section>
      </div>
    </div>
  );
}
