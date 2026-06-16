const SLOT_NUMS = [1, 2, 3, 4, 5, 6];

const DEFAULT_STUDENT_SUBJECTS = ['数学', '英語', '国語', '理科', '社会'];

export function parseStudentSlot(value) {
  if (value === '◎') return { kind: '◎', subject: '' };
  if (value === '×') return { kind: '×', subject: '' };
  if (!value) return { kind: '', subject: '' };
  if (value.startsWith('通常:')) return { kind: '通常', subject: value.slice(3) };
  if (value.startsWith('講習:')) return { kind: '講習', subject: value.slice(3) };
  return { kind: '', subject: '' };
}

export function encodeStudentSlot(kind, subject = '') {
  if (kind === '×') return '×';
  const sub = subject.trim();
  if (kind === '通常') return sub ? `通常:${sub}` : '';
  if (kind === '講習') return sub ? `講習:${sub}` : '';
  return '';
}

export function studentSlotLabel(status) {
  const parsed = parseStudentSlot(status);
  if (parsed.kind === '◎') return { text: '◎ 通常授業', cls: 'bg-slate-100 text-slate-700 border-slate-300' };
  if (parsed.kind === '×') return { text: '× 不可', cls: 'bg-red-50 text-red-700 border-red-200' };
  if (parsed.kind === '通常') {
    return {
      text: parsed.subject ? `通常 ${parsed.subject}` : '通常',
      cls: 'bg-slate-50 text-slate-800 border-slate-300',
    };
  }
  if (parsed.kind === '講習') {
    return {
      text: parsed.subject ? `講習 ${parsed.subject}` : '講習',
      cls: 'bg-blue-50 text-blue-800 border-blue-200',
    };
  }
  return { text: '未選択', cls: 'bg-gray-50 text-gray-500 border-gray-200' };
}

export function apiSlotsToState(slots) {
  return Object.fromEntries(SLOT_NUMS.map((n) => [n, slots?.[String(n)] ?? '']));
}

export function stateToApiSlots(slots) {
  return Object.fromEntries(SLOT_NUMS.map((n) => [String(n), slots[n] ?? '']));
}

export const EMPTY_SLOTS = Object.fromEntries(SLOT_NUMS.map((n) => [n, '']));

function formatPeriodRange(start, end) {
  if (!start || !end) return '';
  const s = start.slice(5).replace('-', '/');
  const e = end.slice(5).replace('-', '/');
  return `${s}〜${e}`;
}

function slotLabel(status, role = 'teacher') {
  if (role === 'student') return studentSlotLabel(status);
  if (status === '◎') return { text: '◎ 通常授業', cls: 'bg-slate-100 text-slate-700 border-slate-300' };
  if (status === '×') return { text: '× 不可', cls: 'bg-red-50 text-red-700 border-red-200' };
  return { text: '空き', cls: 'bg-emerald-50 text-emerald-700 border-emerald-200' };
}

export function PeriodBanner({ periodName, periodStart, periodEnd, periodStatus, schedulePublished }) {
  if (!periodName) return null;
  const range = formatPeriodRange(periodStart, periodEnd);
  return (
    <div className="mb-4 p-4 bg-white border border-gray-200 rounded-2xl shadow-sm">
      <p className="text-xs text-gray-400 font-bold tracking-wide">対象講習</p>
      <p className="text-base font-bold text-gray-900 mt-1">{periodName}</p>
      {range && <p className="text-sm text-gray-500 mt-0.5">{range}</p>}
      <div className="flex flex-wrap gap-2 mt-2">
        <span className="text-xs px-2 py-1 rounded-full bg-gray-100 text-gray-700 font-bold">{periodStatus}</span>
        {schedulePublished && (
          <span className="text-xs px-2 py-1 rounded-full bg-blue-100 text-blue-800 font-bold">送付済み</span>
        )}
      </div>
    </div>
  );
}

export function DateTabs({ dates, selectedDate, onSelect, accent = 'blue' }) {
  const active = accent === 'emerald'
    ? 'bg-emerald-600 text-white shadow-md'
    : 'bg-blue-600 text-white shadow-md';
  return (
    <div className="flex gap-2 mb-4 overflow-x-auto pb-1 -mx-1 px-1">
      {dates.map((isoDate) => {
        const d = new Date(`${isoDate}T12:00:00`);
        const day = ['日', '月', '火', '水', '木', '金', '土'][d.getDay()];
        return (
          <button
            key={isoDate}
            type="button"
            onClick={() => onSelect(isoDate)}
            className={`shrink-0 min-w-[64px] rounded-xl p-2.5 text-center transition-all border ${
              selectedDate === isoDate ? active : 'bg-white text-gray-600 border-gray-200 hover:border-gray-300'
            }`}
          >
            <div className="text-xs opacity-90">{day}</div>
            <div className="text-lg font-bold leading-tight">{d.getDate()}</div>
          </button>
        );
      })}
    </div>
  );
}

/** 1日分を一覧表示（確定授業 + 都合を見やすく） */
export function DayScheduleOverview({
  timeSlots,
  slots,
  lessons,
  lockedSlots,
  role,
  pendingBySlot = {},
  teacherSlotLanes = [],
}) {
  const rows = (timeSlots.length ? timeSlots : SLOT_NUMS.map((s) => ({ slot: s, start: '', end: '' })));
  const lanesBySlot = Object.fromEntries(
    (teacherSlotLanes ?? []).map((entry) => [entry.slot, entry.lanes ?? []]),
  );

  function LaneCell({ lane, slotStatus }) {
    if (lane?.blocked) {
      return (
        <div className="w-full rounded-xl border border-gray-200 bg-gray-100 p-2 text-center min-h-[52px] flex flex-col justify-center">
          <span className="text-lg font-bold text-gray-400">×</span>
        </div>
      );
    }
    if (lane?.occupied && lane.lesson_kind === '通常') {
      return (
        <div className="w-full rounded-xl border border-slate-300 bg-slate-50 p-2 text-center min-h-[52px] flex flex-col justify-center">
          <span className="text-xs font-bold text-slate-600">通常</span>
          <span className="text-sm font-bold text-slate-800 mt-0.5">◎ 通常授業</span>
        </div>
      );
    }
    if (lane?.occupied && lane.student_name) {
      return (
        <div className="w-full rounded-xl border border-blue-200 bg-blue-50/80 p-2 min-h-[52px]">
          <p className="text-sm font-bold text-blue-900">{lane.subject}</p>
          <p className="text-xs text-gray-700 mt-0.5">{lane.student_name} さん</p>
        </div>
      );
    }
    const badge = slotLabel(slotStatus);
    return (
      <div className={`w-full rounded-xl border p-2 text-center min-h-[52px] flex flex-col justify-center text-sm font-bold ${badge.cls}`}>
        {badge.text}
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {rows.map(({ slot, start, end }) => {
        const status = slots[slot] ?? '';
        const locked = lockedSlots[String(slot)] || status === '◎';
        const lesson = lessons.find((l) => l.slot === slot);
        const pending = pendingBySlot[slot];
        const badge = slotLabel(status, role);
        const lanes = lanesBySlot[slot];
        const useSplit = role === 'teacher' && lanes?.length === 2;

        if (useSplit) {
          return (
            <div key={slot} className="rounded-2xl border p-4 bg-white border-gray-200">
              <div className="flex items-center gap-2 flex-wrap mb-2">
                <span className="text-sm font-bold text-gray-800">{slot}コマ</span>
                {start && (
                  <span className="text-xs text-gray-500">{start}〜{end}</span>
                )}
                {pending && (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 font-bold">
                    変更申請中
                  </span>
                )}
              </div>
              <div className="flex flex-col gap-2">
                <div>
                  <p className="text-[10px] font-bold text-gray-400 mb-1">①</p>
                  <LaneCell lane={lanes[0]} slotStatus={status} />
                  </div>
                <div>
                  <p className="text-[10px] font-bold text-gray-400 mb-1">②</p>
                  <LaneCell lane={lanes[1]} slotStatus={status} />
                </div>
              </div>
            </div>
          );
        }

        return (
          <div
            key={slot}
            className={`rounded-2xl border p-4 ${lesson ? 'bg-blue-50/60 border-blue-200' : 'bg-white border-gray-200'}`}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-bold text-gray-800">{slot}コマ</span>
                  {start && (
                    <span className="text-xs text-gray-500">{start}〜{end}</span>
                  )}
                  {pending && (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 font-bold">
                      変更申請中
                    </span>
                  )}
                </div>
                {lesson ? (
                  <div className="mt-2">
                    <p className="text-lg font-bold text-blue-900">{lesson.subject}</p>
                    <p className="text-sm text-gray-700 mt-0.5">
                      {role === 'teacher'
                        ? `${lesson.student_name} さん`
                        : `${lesson.teacher_name} 先生`}
                    </p>
                  </div>
                ) : (
                  <p className="text-sm text-gray-400 mt-2">授業割当なし</p>
                )}
              </div>
              <div className={`shrink-0 px-3 py-2 rounded-xl border text-sm font-bold ${badge.cls}`}>
                {locked && status === '◎' ? '◎ 通常授業' : badge.text}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function StudentSlotRow({
  period,
  time,
  status,
  locked,
  readonly,
  onStatusChange,
  disabled,
  changed,
  subjectPlans = [],
}) {
  const lockedSlot = locked || status === '◎';
  const readOnly = readonly || lockedSlot;
  const parsed = parseStudentSlot(status);
  const badge = studentSlotLabel(status);
  const subjects = subjectPlans.length
    ? subjectPlans.map((p) => p.subject)
    : DEFAULT_STUDENT_SUBJECTS;

  const setKind = (kind) => {
    if (kind === '×') {
      onStatusChange('×');
      return;
    }
    const current = parseStudentSlot(status);
    const subject = current.kind === kind && current.subject
      ? current.subject
      : subjects[0] ?? '';
    onStatusChange(encodeStudentSlot(kind, subject));
  };

  const setSubject = (subject) => {
    if (parsed.kind !== '通常' && parsed.kind !== '講習') return;
    onStatusChange(encodeStudentSlot(parsed.kind, subject));
  };

  return (
    <div className={`rounded-2xl border p-4 transition-all ${
      changed ? 'border-amber-400 bg-amber-50/50 ring-2 ring-amber-200' : 'border-gray-200 bg-white'
    }`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold text-gray-800">{period}コマ</span>
            {changed && <span className="text-xs text-amber-700 font-bold">変更</span>}
          </div>
          {time?.start && (
            <div className="text-sm text-gray-500 mt-0.5">{time.start}〜{time.end}</div>
          )}
        </div>
        {readOnly ? (
          <div className={`shrink-0 px-4 py-2 rounded-xl border text-sm font-bold ${badge.cls}`}>
            {lockedSlot && status === '◎' ? '◎ 通常授業' : badge.text}
          </div>
        ) : (
          <div className="flex flex-col items-end gap-2 shrink-0">
            <div className="flex bg-gray-100 rounded-xl p-1 gap-1">
              <button
                type="button"
                disabled={disabled}
                onClick={() => setKind('通常')}
                className={`px-3 h-11 rounded-lg font-bold text-sm transition-all disabled:opacity-50 ${
                  parsed.kind === '通常' ? 'bg-slate-600 text-white shadow-sm' : 'text-gray-600 hover:bg-gray-200'
                }`}
              >
                通常
              </button>
              <button
                type="button"
                disabled={disabled}
                onClick={() => setKind('講習')}
                className={`px-3 h-11 rounded-lg font-bold text-sm transition-all disabled:opacity-50 ${
                  parsed.kind === '講習' ? 'bg-blue-600 text-white shadow-sm' : 'text-gray-600 hover:bg-gray-200'
                }`}
              >
                講習
              </button>
              <button
                type="button"
                disabled={disabled}
                onClick={() => setKind('×')}
                className={`w-12 h-11 rounded-lg font-bold text-sm transition-all disabled:opacity-50 ${
                  parsed.kind === '×' ? 'bg-red-500 text-white shadow-sm' : 'text-gray-500 hover:bg-gray-200'
                }`}
              >
                ×
              </button>
            </div>
            {(parsed.kind === '通常' || parsed.kind === '講習') && (
              <select
                value={parsed.subject || subjects[0] || ''}
                disabled={disabled}
                onChange={(e) => setSubject(e.target.value)}
                className="text-sm border border-gray-300 rounded-lg px-2 py-1.5 bg-white font-bold text-gray-800 max-w-[140px]"
              >
                {subjects.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export function TimeSlotRow({
  period,
  time,
  status,
  locked,
  readonly,
  onStatusChange,
  disabled,
  changed,
}) {
  const lockedSlot = locked || status === '◎';
  const readOnly = readonly || lockedSlot;
  const badge = slotLabel(status);

  return (
    <div className={`rounded-2xl border p-4 transition-all ${
      changed ? 'border-amber-400 bg-amber-50/50 ring-2 ring-amber-200' : 'border-gray-200 bg-white'
    }`}>
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold text-gray-800">{period}コマ</span>
            {changed && <span className="text-xs text-amber-700 font-bold">変更</span>}
          </div>
          {time?.start && (
            <div className="text-sm text-gray-500 mt-0.5">{time.start}〜{time.end}</div>
          )}
        </div>
        {readOnly ? (
          <div className={`px-4 py-2 rounded-xl border text-sm font-bold ${badge.cls}`}>
            {lockedSlot && status === '◎' ? '◎ 通常授業' : badge.text}
          </div>
        ) : (
          <div className="flex bg-gray-100 rounded-xl p-1 gap-1">
            <button
              type="button"
              disabled={disabled}
              onClick={() => onStatusChange('')}
              className={`w-16 h-11 rounded-lg font-bold text-sm transition-all disabled:opacity-50 ${
                status === '' ? 'bg-emerald-500 text-white shadow-sm' : 'text-gray-500 hover:bg-gray-200'
              }`}
            >
              空
            </button>
            <button
              type="button"
              disabled={disabled}
              onClick={() => onStatusChange('×')}
              className={`w-16 h-11 rounded-lg font-bold text-sm transition-all disabled:opacity-50 ${
                status === '×' ? 'bg-red-500 text-white shadow-sm' : 'text-gray-500 hover:bg-gray-200'
              }`}
            >
              ×
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export function StudentScheduleLegend() {
  return (
    <div className="flex flex-wrap justify-center gap-x-4 gap-y-1 mb-4 text-xs text-gray-500">
      <span><span className="text-slate-600 font-bold">◎</span> 通常授業（変更不可）</span>
      <span><span className="text-slate-600 font-bold">通常</span> ＋教科</span>
      <span><span className="text-blue-600 font-bold">講習</span> ＋教科</span>
      <span><span className="text-red-500 font-bold">×</span> 都合つかない</span>
    </div>
  );
}

export function ScheduleLegend() {
  return (
    <div className="flex flex-wrap justify-center gap-x-4 gap-y-1 mb-4 text-xs text-gray-500">
      <span><span className="text-slate-600 font-bold">◎</span> 通常授業（変更不可）</span>
      <span><span className="text-emerald-600 font-bold">空</span> 都合つく</span>
      <span><span className="text-red-500 font-bold">×</span> 都合つかない</span>
    </div>
  );
}

/** 変更提案の差分を集計 */
export function collectProposalChanges(originalByDate, proposalByDate, lockedByDate) {
  const changes = [];
  Object.keys(proposalByDate).forEach((date) => {
    const original = originalByDate[date] ?? EMPTY_SLOTS;
    const proposal = proposalByDate[date] ?? EMPTY_SLOTS;
    const locked = lockedByDate[date] ?? {};
    SLOT_NUMS.forEach((slot) => {
      if (locked[String(slot)] || original[slot] === '◎') return;
      if (original[slot] !== proposal[slot]) {
        changes.push({ date, slot, from: original[slot] ?? '', to: proposal[slot] ?? '' });
      }
    });
  });
  return changes;
}

export async function submitChangeProposal({
  periodId,
  role,
  entityId,
  changes,
  reason,
}) {
  const results = [];
  const errors = [];
  for (const ch of changes) {
    const res = await fetch('/api/shifts/change-requests', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        period_id: periodId,
        role,
        entity_id: entityId,
        date: ch.date,
        slot: ch.slot,
        requested_symbol: ch.to,
        reason,
      }),
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) {
      errors.push(body.detail || `${ch.date} ${ch.slot}コマ`);
    } else {
      results.push(body.request);
    }
  }
  return { results, errors };
}
