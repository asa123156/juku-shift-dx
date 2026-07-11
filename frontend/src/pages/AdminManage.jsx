import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAdminSession } from '../hooks/useAdminSession';
import { AdminSidebar } from '../components/AdminSidebar';
import { apiFetch } from '../utils/apiClient';
import { confirmDialog } from '../utils/confirmDialog';
import { parseApiError } from '../utils/apiError';
import { periodStatusLabel } from '../components/ScheduleEditor';
import { Toast } from '../components/Toast';

const LEVEL_OPTIONS = [
  { value: 'elementary', label: '小学部' },
  { value: 'middle', label: '中学部' },
  { value: 'high', label: '高校部' },
];

const LEVEL_ORDER = { elementary: 0, middle: 1, high: 2 };

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
  const [deletedPeriods, setDeletedPeriods] = useState([]);
  const [activePeriodId, setActivePeriodId] = useState(null);
  const [students, setStudents] = useState([]);
  const [teachers, setTeachers] = useState([]);

  const [periodForm, setPeriodForm] = useState({ name: '', start_date: '', end_date: '', location_slug: 'hakutei', submission_deadline: '' });
  const [locationOptions, setLocationOptions] = useState([]);
  const [openDateSelection, setOpenDateSelection] = useState([]);
  const [studentForm, setStudentForm] = useState({ name: '', school_level: 'middle', grade_year: 2 });
  const [teacherForm, setTeacherForm] = useState({ name: '' });
  const [editingStudentId, setEditingStudentId] = useState(null);
  const [editingTeacherId, setEditingTeacherId] = useState(null);

  const loadAll = useCallback(async () => {
    setError(null);
    try {
      const [pRes, pdRes, sRes, tRes] = await Promise.all([
        apiFetch('/api/admin/periods'),
        apiFetch('/api/admin/periods/deleted'),
        apiFetch('/api/admin/students'),
        apiFetch('/api/admin/teachers'),
      ]);
      if (!pRes.ok) throw new Error(await parseApiError(pRes, '講習一覧の取得に失敗しました'));
      if (!sRes.ok) throw new Error(await parseApiError(sRes, '生徒一覧の取得に失敗しました'));
      if (!tRes.ok) throw new Error(await parseApiError(tRes, '講師一覧の取得に失敗しました'));
      const pData = await pRes.json();
      const pdData = pdRes.ok ? await pdRes.json() : { periods: [] };
      const sData = await sRes.json();
      const tData = await tRes.json();
      setPeriods(pData.periods ?? []);
      setDeletedPeriods(pdData.periods ?? []);
      const pid = pData.active_period_id;
      setActivePeriodId(pid);
      setStudents(sData.students ?? []);
      setTeachers(tData.teachers ?? []);
      apiFetch('/api/export/locations')
        .then((r) => r.json())
        .then((data) => {
          const locs = data.locations ?? [];
          setLocationOptions(locs);
          const def = locs.find((l) => l.default) ?? locs[0];
          if (def) {
            setPeriodForm((prev) => ({ ...prev, location_slug: prev.location_slug || def.slug }));
          }
        })
        .catch(() => {});
    } catch (err) {
      setError(err.message);
    }
  }, []);

  useEffect(() => {
    if (isReady) loadAll();
  }, [isReady, loadAll]);

  const studentGroups = useMemo(() => groupStudents(students), [students]);

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
    if (!periodForm.start_date || !periodForm.end_date) {
      setError('開始日と終了日を入力してください');
      return;
    }
    if (periodForm.end_date < periodForm.start_date) {
      setError('終了日は開始日以降にしてください');
      return;
    }
    const effectiveOpen = openDateSelection.length > 0 ? openDateSelection : periodCandidates;
    if (effectiveOpen.length === 0) {
      setError('開校日がありません。期間内に日曜以外の日を含めてください');
      return;
    }
    const closed_dates = periodCandidates.filter((d) => !effectiveOpen.includes(d));
    try {
      const res = await apiFetch('/api/admin/periods', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...periodForm,
          submission_deadline: periodForm.submission_deadline || null,
          closed_dates,
        }),
      });
      if (!res.ok) throw new Error(await parseApiError(res, '講習の作成に失敗しました'));
      const data = await res.json();
      setMessage(data.message);
      setPeriodForm({ name: '', start_date: '', end_date: '', location_slug: periodForm.location_slug || 'hakutei', submission_deadline: '' });
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
      const res = await apiFetch(`/api/admin/periods/${periodId}/activate`, { method: 'PATCH' });
      if (!res.ok) throw new Error('講習の選択に失敗しました');
      const data = await res.json();
      setMessage(data.message);
      await loadAll();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDeletePeriod = async (period) => {
    if (!(await confirmDialog({ title: `講習「${period.name}」を削除しますか？`, message: 'あとで復元できます。', confirmLabel: '削除する', destructive: true }))) return;
    setMessage(null);
    setError(null);
    try {
      const res = await apiFetch(`/api/admin/periods/${period.id}`, { method: 'DELETE' });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || '講習の削除に失敗しました');
      setMessage(data.message || `講習「${period.name}」を削除しました`);
      await loadAll();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleRestorePeriod = async (period) => {
    setMessage(null);
    setError(null);
    try {
      const res = await apiFetch(`/api/admin/periods/${period.id}/restore`, { method: 'PATCH' });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || '講習の復元に失敗しました');
      setMessage(data.message || `講習「${period.name}」を復元しました`);
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
      const res = await apiFetch(
        isEdit ? `/api/admin/students/${editingStudentId}` : '/api/admin/students',
        {
          method: isEdit ? 'PATCH' : 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(studentForm),
        },
      );
      if (!res.ok) throw new Error(await parseApiError(res, (isEdit ? '生徒の更新に失敗しました' : '生徒の追加に失敗しました')));
      const data = await res.json();
      if (isEdit) {
        setMessage(`生徒「${data.name}」を更新しました`);
      } else {
        setMessage(
          `生徒「${data.name}」を追加しました（ID: ${data.login_id || '-'} / PW: ${data.password || '-'}）`,
        );
      }
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

  const handleResetStudentPassword = async (s) => {
    if (!(await confirmDialog({ title: `「${s.name}」のパスワードを再発行しますか？`, message: '現在のパスワードは使えなくなります。', confirmLabel: '再発行する' }))) return;
    setMessage(null);
    setError(null);
    try {
      const res = await apiFetch(`/api/admin/students/${s.id}/reset-password`, { method: 'POST' });
      if (!res.ok) throw new Error(await parseApiError(res, 'パスワードの再発行に失敗しました'));
      const data = await res.json();
      setMessage(`生徒「${data.name}」のパスワードを再発行しました（ID: ${data.login_id || '-'} / PW: ${data.password || '-'}）`);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDeleteStudent = async (s) => {
    if (!(await confirmDialog({ title: `「${s.name}」を削除しますか？`, message: '割当・希望データも削除されます。', confirmLabel: '削除する', destructive: true }))) return;
    setMessage(null);
    setError(null);
    try {
      const res = await apiFetch(`/api/admin/students/${s.id}`, { method: 'DELETE' });
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
      const res = await apiFetch(
        isEdit ? `/api/admin/teachers/${editingTeacherId}` : '/api/admin/teachers',
        {
          method: isEdit ? 'PATCH' : 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(teacherForm),
        },
      );
      if (!res.ok) throw new Error(await parseApiError(res, (isEdit ? '講師の更新に失敗しました' : '講師の追加に失敗しました')));
      const data = await res.json();
      if (isEdit) {
        setMessage(`講師「${data.name}」を更新しました`);
      } else {
        setMessage(
          `講師「${data.name}」を追加しました（ID: ${data.login_id || '-'} / PW: ${data.password || '-'}）`,
        );
      }
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

  const handleResetTeacherPassword = async (t) => {
    if (!(await confirmDialog({ title: `「${t.name}」のパスワードを再発行しますか？`, message: '現在のパスワードは使えなくなります。', confirmLabel: '再発行する' }))) return;
    setMessage(null);
    setError(null);
    try {
      const res = await apiFetch(`/api/admin/teachers/${t.id}/reset-password`, { method: 'POST' });
      if (!res.ok) throw new Error(await parseApiError(res, 'パスワードの再発行に失敗しました'));
      const data = await res.json();
      setMessage(`講師「${data.name}」のパスワードを再発行しました（ID: ${data.login_id || '-'} / PW: ${data.password || '-'}）`);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDeleteTeacher = async (t) => {
    if (!(await confirmDialog({ title: `「${t.name}」を削除しますか？`, confirmLabel: '削除する', destructive: true }))) return;
    setMessage(null);
    setError(null);
    try {
      const res = await apiFetch(`/api/admin/teachers/${t.id}`, { method: 'DELETE' });
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

        <Toast message={error} type="error" onClose={() => setError(null)} />
        <Toast message={message} onClose={() => setMessage(null)} />

        {activePeriodId && (
          <div className="mb-6 p-4 bg-violet-50 border border-violet-200 rounded-2xl flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-violet-900">
              生徒ごとの講習教科・コマ数は「講習希望設定」ページで編集できます。
            </p>
            <button
              type="button"
              onClick={() => navigate('/admin/student-plans')}
              className="text-sm font-bold bg-violet-600 hover:bg-violet-700 text-white px-4 py-2 rounded-xl"
            >
              講習希望設定へ →
            </button>
          </div>
        )}

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
            <label className="block">
              <span className="text-sm font-bold text-gray-600">提出期限（任意）</span>
              <input
                type="date"
                value={periodForm.submission_deadline}
                onChange={(e) => setPeriodForm({ ...periodForm, submission_deadline: e.target.value })}
                className="mt-1 w-full border rounded-lg px-3 py-2"
              />
              <span className="text-xs text-gray-400">期限後も提出は可能（画面に「期限超過」と表示）</span>
            </label>
            {locationOptions.length > 0 && (
              <label className="block sm:col-span-2">
                <span className="text-sm font-bold text-gray-600">出力形式（拠点）</span>
                <select
                  value={periodForm.location_slug}
                  onChange={(e) => setPeriodForm({ ...periodForm, location_slug: e.target.value })}
                  className="mt-1 w-full border rounded-lg px-3 py-2 bg-white"
                >
                  {locationOptions.map((loc) => (
                    <option key={loc.slug} value={loc.slug}>{loc.name}</option>
                  ))}
                </select>
              </label>
            )}
            {periodForm.start_date && periodForm.end_date && periodCandidates.length === 0 && (
              <p className="sm:col-span-2 text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
                終了日は開始日以降にしてください。日曜以外の開校日が1日以上必要です。
              </p>
            )}
            {periodForm.start_date && periodForm.end_date && periodCandidates.length > 0 && (
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
                    <span className="text-xs ml-2 px-2 py-0.5 rounded-full bg-gray-100">{periodStatusLabel(p.status)}</span>
                  </div>
                  {p.id !== activePeriodId && (
                    <div className="flex items-center gap-3">
                      <button type="button" onClick={() => handleActivatePeriod(p.id)} className="text-sm font-bold text-blue-600 hover:underline">
                        選択
                      </button>
                      <button type="button" onClick={() => handleDeletePeriod(p)} className="text-sm font-bold text-red-600 hover:underline">
                        削除
                      </button>
                    </div>
                  )}
                  {p.id === activePeriodId && (
                    <div className="flex items-center gap-3">
                      <span className="text-xs font-bold text-blue-600">使用中</span>
                      <button type="button" onClick={() => handleDeletePeriod(p)} className="text-sm font-bold text-red-600 hover:underline">
                        削除
                      </button>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
          {deletedPeriods.length > 0 && (
            <div className="mt-4">
              <p className="text-sm font-bold text-gray-600 mb-2">削除済み講習（復元可能）</p>
              <ul className="space-y-2">
                {deletedPeriods.map((p) => (
                  <li key={p.id} className="flex items-center justify-between p-3 rounded-xl border border-amber-200 bg-amber-50">
                    <div>
                      <span className="font-bold text-amber-900">{p.name}</span>
                      <span className="text-sm text-amber-800 ml-2">{p.start_date} 〜 {p.end_date}</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleRestorePeriod(p)}
                      className="text-sm font-bold text-amber-700 hover:underline"
                    >
                      復元
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </Section>

        <Section title={editingStudentId ? '生徒を編集' : '生徒を追加'}>
          {activePeriodId && (
            <p className="text-sm text-gray-600 mb-4">
              講習の教科・コマ数は
              <button
                type="button"
                onClick={() => navigate('/admin/student-plans')}
                className="mx-1 font-bold text-violet-700 hover:underline"
              >
                講習希望設定
              </button>
              ページで設定できます。
            </p>
          )}
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
                          <p className="text-xs text-gray-500 mt-0.5">
                            ID: <span className="font-mono">{s.login_id || '-'}</span>
                          </p>
                        </div>
                        <div className="flex gap-2 shrink-0">
                          <button type="button" onClick={() => handleResetStudentPassword(s)} className="text-xs font-bold text-emerald-600 hover:underline">PW再発行</button>
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
                  <div className="flex items-center gap-2 text-sm min-w-0">
                    <span className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${t.color}`}>{t.name.charAt(0)}</span>
                    <div className="min-w-0">
                      <p className="font-medium text-gray-800">{t.name}</p>
                      <p className="text-xs text-gray-500 mt-0.5">
                        ID: <span className="font-mono">{t.login_id || '-'}</span>
                      </p>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button type="button" onClick={() => handleResetTeacherPassword(t)} className="text-xs font-bold text-emerald-600 hover:underline">PW再発行</button>
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
