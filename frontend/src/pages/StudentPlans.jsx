import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAdminSession } from '../hooks/useAdminSession';
import { AdminSidebar } from '../components/AdminSidebar';

const SUBJECT_PRESETS = ['数学', '算数', '理科', '物理', '化学', '国語', '社会', '英語'];

const LEVEL_ORDER = { elementary: 0, middle: 1, high: 2 };

function formatPlanSummary(plans) {
  if (!plans?.length) return '未設定';
  return plans
    .map((p) => {
      const teacher = p.teacher_name ? `→${p.teacher_name}` : '';
      return `${p.subject}×${p.slot_count}${teacher}`;
    })
    .join('、');
}

function emptyPlanRow() {
  return { subject: '', slot_count: 1, teacher_id: null };
}

function totalSlots(plans) {
  return (plans ?? []).reduce((sum, p) => sum + (p.slot_count || 0), 0);
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

export default function StudentPlans() {
  const navigate = useNavigate();
  const isReady = useAdminSession();

  const [periods, setPeriods] = useState([]);
  const [periodId, setPeriodId] = useState(null);
  const [students, setStudents] = useState([]);
  const [teachers, setTeachers] = useState([]);
  const [periodPlans, setPeriodPlans] = useState([]);
  const [selectedStudentId, setSelectedStudentId] = useState(null);
  const [planRows, setPlanRows] = useState([emptyPlanRow()]);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');

  const activePeriod = periods.find((p) => p.id === periodId);
  const readonly = activePeriod?.status === 'FINALIZED';

  const plansByStudentId = useMemo(() => {
    const map = {};
    periodPlans.forEach((entry) => {
      map[entry.student_id] = entry.plans ?? [];
    });
    return map;
  }, [periodPlans]);

  const loadPlans = useCallback(async (pid) => {
    if (!pid) {
      setPeriodPlans([]);
      return;
    }
    const planRes = await fetch(`/api/admin/periods/${pid}/student-plans`);
    if (!planRes.ok) throw new Error('希望データの取得に失敗しました');
    const planData = await planRes.json();
    setPeriodPlans(planData.students ?? []);
  }, []);

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
      setStudents(sData.students ?? []);
      setTeachers(tData.teachers ?? []);
      const pid = pData.active_period_id ?? pData.periods?.[0]?.id ?? null;
      setPeriodId(pid);
    } catch (err) {
      setError(err.message);
    }
  }, []);

  useEffect(() => {
    if (isReady) loadAll();
  }, [isReady, loadAll]);

  useEffect(() => {
    if (!periodId || !isReady) return;
    loadPlans(periodId).catch((err) => setError(err.message));
  }, [periodId, isReady, loadPlans]);

  const selectStudent = (student) => {
    setSelectedStudentId(student.id);
    setMessage(null);
    setError(null);
    const existing = plansByStudentId[student.id] ?? [];
    setPlanRows(
      existing.length
        ? existing.map((p) => ({
            subject: p.subject,
            slot_count: p.slot_count,
            teacher_id: p.teacher_id ?? null,
          }))
        : [emptyPlanRow()],
    );
  };

  const handlePeriodChange = (e) => {
    const pid = Number(e.target.value);
    setPeriodId(pid);
    setSelectedStudentId(null);
    setMessage(null);
  };

  const handleSave = async (e) => {
    e.preventDefault();
    if (!periodId || selectedStudentId == null || isSaving || readonly) return;
    setIsSaving(true);
    setMessage(null);
    setError(null);
    try {
      const res = await fetch(
        `/api/admin/periods/${periodId}/students/${selectedStudentId}/plans`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            plans: planRows
              .filter((r) => r.subject?.trim() && r.slot_count > 0)
              .map((r) => ({
                subject: r.subject.trim(),
                slot_count: r.slot_count,
                teacher_id: r.teacher_id || null,
              })),
          }),
        },
      );
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || '希望の保存に失敗しました');
      const student = students.find((s) => s.id === selectedStudentId);
      setMessage(
        `${student?.name ?? '生徒'}の希望を保存しました（割当リクエスト ${data.synced_request_count} 件）`,
      );
      await loadPlans(periodId);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSaving(false);
    }
  };

  const studentGroups = useMemo(() => groupStudents(students), [students]);

  const filteredGroups = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return studentGroups;
    return studentGroups
      .map((g) => ({
        ...g,
        students: g.students.filter(
          (s) =>
            s.name.toLowerCase().includes(q)
            || formatPlanSummary(plansByStudentId[s.id]).toLowerCase().includes(q),
        ),
      }))
      .filter((g) => g.students.length > 0);
  }, [studentGroups, search, plansByStudentId]);

  const selectedStudent = students.find((s) => s.id === selectedStudentId);
  const configuredCount = students.filter((s) => (plansByStudentId[s.id]?.length ?? 0) > 0).length;

  if (!isReady) return null;

  return (
    <div className="min-h-screen bg-gray-50 flex font-sans">
      <AdminSidebar navigate={navigate} current="student-plans" />

      <div className="flex-1 flex flex-col min-w-0">
        <header className="bg-white border-b px-6 py-5 shrink-0">
          <h2 className="text-2xl font-bold text-gray-800">講習希望設定</h2>
          <p className="text-sm text-gray-500 mt-1">
            生徒ごとに教科・コマ数・担当講師を設定します。担当講師を指定すると自動割当・候補抽出でその講師のみ使われます。
          </p>
          <div className="mt-4 flex flex-wrap gap-3 items-end">
            <label className="min-w-[220px]">
              <span className="text-xs font-bold text-gray-600">対象講習</span>
              <select
                value={periodId ?? ''}
                onChange={handlePeriodChange}
                className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
              >
                {periods.length === 0 && <option value="">講習がありません</option>}
                {periods.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}（{p.status}）
                  </option>
                ))}
              </select>
            </label>
            {activePeriod && (
              <p className="text-sm text-gray-600 pb-2">
                {activePeriod.start_date} 〜 {activePeriod.end_date}
                <span className="ml-3 font-bold text-violet-700">
                  設定済み {configuredCount} / {students.length} 名
                </span>
              </p>
            )}
          </div>
          {error && <p className="mt-3 text-red-600 text-sm">{error}</p>}
          {message && <p className="mt-3 text-emerald-700 text-sm font-bold">{message}</p>}
        </header>

        {!periodId ? (
          <div className="flex-1 flex items-center justify-center text-gray-500">
            先に「教室管理」で講習期間を作成してください。
          </div>
        ) : (
          <div className="flex-1 flex min-h-0">
            <aside className="w-80 shrink-0 border-r bg-white flex flex-col min-h-0">
              <div className="p-3 border-b">
                <input
                  type="search"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="名前・教科で検索"
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                />
              </div>
              <div className="flex-1 overflow-y-auto p-3 space-y-4">
                {filteredGroups.map((g) => (
                  <div key={`${g.school_level}-${g.grade_label}`}>
                    <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wide mb-2 px-1">
                      {g.level_label} {g.grade_label}
                    </h3>
                    <ul className="space-y-1">
                      {g.students.map((s) => {
                        const plans = plansByStudentId[s.id] ?? [];
                        const active = s.id === selectedStudentId;
                        return (
                          <li key={s.id}>
                            <button
                              type="button"
                              onClick={() => selectStudent(s)}
                              className={`w-full text-left rounded-xl px-3 py-2.5 border transition-all ${
                                active
                                  ? 'border-violet-500 bg-violet-50 ring-2 ring-violet-200'
                                  : 'border-gray-100 bg-gray-50 hover:bg-white hover:border-gray-200'
                              }`}
                            >
                              <p className="font-bold text-gray-900 text-sm truncate">{s.name}</p>
                              <p className={`text-xs mt-0.5 truncate ${plans.length ? 'text-violet-700' : 'text-gray-400'}`}>
                                {formatPlanSummary(plans)}
                                {plans.length > 0 && (
                                  <span className="text-gray-500 ml-1">（計{totalSlots(plans)}コマ）</span>
                                )}
                              </p>
                            </button>
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                ))}
                {filteredGroups.length === 0 && (
                  <p className="text-sm text-gray-400 text-center py-8">該当する生徒がいません</p>
                )}
              </div>
            </aside>

            <main className="flex-1 overflow-y-auto p-6 min-w-0">
              {!selectedStudent ? (
                <div className="h-full flex flex-col items-center justify-center text-gray-400">
                  <p className="text-lg font-bold">← 左の一覧から生徒を選んでください</p>
                  <p className="text-sm mt-2">教科・コマ数・担当講師を設定できます</p>
                </div>
              ) : (
                <div className="max-w-2xl">
                  <div className="mb-6">
                    <h3 className="text-xl font-bold text-gray-900">{selectedStudent.name}</h3>
                    <p className="text-sm text-gray-500 mt-0.5">
                      {selectedStudent.level_label} {selectedStudent.grade_label}
                    </p>
                  </div>

                  {readonly ? (
                    <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-amber-900 text-sm">
                      <p className="font-bold">確定済みの講習期間のため編集できません。</p>
                      <ul className="mt-3 space-y-2">
                        {(plansByStudentId[selectedStudentId] ?? []).map((p) => (
                          <li key={p.subject} className="flex justify-between gap-3 border-b border-amber-100 pb-2">
                            <span className="font-bold">{p.subject}</span>
                            <span className="text-right">
                              {p.slot_count} コマ
                              {p.teacher_name && (
                                <span className="block text-xs text-amber-800/80">担当: {p.teacher_name}</span>
                              )}
                            </span>
                          </li>
                        ))}
                        {(plansByStudentId[selectedStudentId] ?? []).length === 0 && (
                          <li className="text-amber-700">未設定</li>
                        )}
                      </ul>
                    </div>
                  ) : (
                    <form onSubmit={handleSave} className="space-y-4">
                      {planRows.map((row, idx) => (
                        <div
                          key={idx}
                          className="flex flex-wrap gap-3 items-end p-4 bg-white rounded-2xl border border-gray-200 shadow-sm"
                        >
                          <label className="flex-1 min-w-[140px]">
                            <span className="text-xs font-bold text-gray-600">教科</span>
                            <select
                              value={row.subject}
                              onChange={(e) => {
                                const next = [...planRows];
                                next[idx] = { ...next[idx], subject: e.target.value };
                                setPlanRows(next);
                              }}
                              className="mt-1 w-full border rounded-lg px-3 py-2 bg-white"
                            >
                              <option value="">教科を選択</option>
                              {row.subject && !SUBJECT_PRESETS.includes(row.subject) && (
                                <option value={row.subject}>{row.subject}</option>
                              )}
                              {SUBJECT_PRESETS.map((sub) => (
                                <option key={sub} value={sub}>{sub}</option>
                              ))}
                            </select>
                          </label>
                          <label className="w-28">
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
                          <label className="flex-1 min-w-[160px]">
                            <span className="text-xs font-bold text-gray-600">担当講師</span>
                            <select
                              value={row.teacher_id ?? ''}
                              onChange={(e) => {
                                const next = [...planRows];
                                const raw = e.target.value;
                                next[idx] = {
                                  ...next[idx],
                                  teacher_id: raw ? Number(raw) : null,
                                };
                                setPlanRows(next);
                              }}
                              className="mt-1 w-full border rounded-lg px-3 py-2 bg-white"
                            >
                              <option value="">指定なし</option>
                              {teachers.map((t) => (
                                <option key={t.id} value={t.id}>{t.name}</option>
                              ))}
                            </select>
                          </label>
                          <button
                            type="button"
                            onClick={() => setPlanRows(planRows.filter((_, i) => i !== idx))}
                            disabled={planRows.length <= 1}
                            className="text-sm font-bold text-red-600 px-2 py-2.5 disabled:opacity-30"
                          >
                            削除
                          </button>
                        </div>
                      ))}

                      <div className="flex flex-wrap gap-2 pt-2">
                        <button
                          type="button"
                          onClick={() => setPlanRows([...planRows, emptyPlanRow()])}
                          className="text-sm font-bold text-gray-600 border border-gray-300 rounded-xl px-4 py-2.5 hover:bg-gray-50"
                        >
                          ＋ 教科を追加
                        </button>
                        <button
                          type="submit"
                          disabled={isSaving}
                          className="bg-violet-600 hover:bg-violet-700 disabled:bg-violet-300 text-white px-6 py-2.5 rounded-xl font-bold shadow-sm"
                        >
                          {isSaving ? '保存中...' : '保存してリクエスト反映'}
                        </button>
                      </div>

                      <p className="text-xs text-gray-500 leading-relaxed">
                        未割当は希望コマ数と時間割表の割当数の差分として計算されます。
                        担当講師を指定すると、その教科は自動割当・手動割当候補でその講師に限定されます。
                        合計 {totalSlots(planRows.filter((r) => r.subject?.trim() && r.slot_count > 0))} コマ
                      </p>
                    </form>
                  )}
                </div>
              )}
            </main>
          </div>
        )}
      </div>
    </div>
  );
}
