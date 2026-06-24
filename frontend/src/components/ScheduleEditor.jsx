const SLOT_NUMS = [1, 2, 3, 4, 5, 6];

/** 生徒提出: 空き（""）/ × / ◎（教室長設定・変更不可）のみ */
export function parseStudentSlot(value) {
  if (value === '◎') return { kind: '◎' };
  if (value === '×') return { kind: '×' };
  return { kind: '空き' };
}

export function studentSlotLabel(status) {
  const parsed = parseStudentSlot(status);
  if (parsed.kind === '◎') return { text: '◎ 通常授業', cls: 'bg-slate-100 text-slate-700 border-slate-300' };
  if (parsed.kind === '×') return { text: '× 不可', cls: 'bg-red-50 text-red-700 border-red-200' };
  return { text: '空き', cls: 'bg-emerald-50 text-emerald-700 border-emerald-200' };
}

function lessonKindBadge(kind) {
  if (kind === '通常') {
    return { text: '通常', cls: 'bg-slate-50 text-slate-800 border-slate-300' };
  }
  return { text: '講習', cls: 'bg-blue-50 text-blue-800 border-blue-200' };
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
  confirmedLesson = null,
  pending = false,
}) {
  const lockedSlot = locked || status === '◎';
  const readOnly = readonly || lockedSlot;
  const badge = studentSlotLabel(status);
  const kindBadge = confirmedLesson ? lessonKindBadge(confirmedLesson.lesson_kind) : null;

  return (
    <div className={`rounded-2xl border p-4 transition-all ${
      changed ? 'border-amber-400 bg-amber-50/50 ring-2 ring-amber-200'
        : confirmedLesson ? 'bg-blue-50/60 border-blue-200'
          : 'border-gray-200 bg-white'
    }`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-bold text-gray-800">{period}コマ</span>
            {time?.start && (
              <span className="text-xs text-gray-500">{time.start}〜{time.end}</span>
            )}
            {changed && <span className="text-xs text-amber-700 font-bold">変更</span>}
            {pending && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 font-bold">
                変更申請中
              </span>
            )}
          </div>

          {readOnly && confirmedLesson && (
            <div className="mt-2">
              <p className="text-lg font-bold text-blue-900">{confirmedLesson.subject}</p>
              <p className="text-sm text-gray-700 mt-0.5">
                {confirmedLesson.teacher_name?.includes('先生')
                  ? confirmedLesson.teacher_name
                  : `${confirmedLesson.teacher_name} 先生`}
              </p>
            </div>
          )}
        </div>

        {lockedSlot && status === '◎' ? (
          <div className="shrink-0 px-3 py-2 rounded-xl border text-sm font-bold bg-slate-100 text-slate-700 border-slate-300">
            ◎ 通常授業
          </div>
        ) : readOnly && confirmedLesson && kindBadge ? (
          <span className={`shrink-0 px-2.5 py-1 rounded-lg border text-xs font-bold ${kindBadge.cls}`}>
            {kindBadge.text}
          </span>
        ) : readOnly ? (
          <div className={`shrink-0 px-3 py-2 rounded-xl border text-sm font-bold ${badge.cls}`}>
            {badge.text}
          </div>
        ) : (
          <div className="flex bg-gray-100 rounded-xl p-1 gap-1 shrink-0">
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
      <span><span className="text-emerald-600 font-bold">空</span> 都合つく</span>
      <span><span className="text-red-500 font-bold">×</span> 都合つかない</span>
      <span className="text-gray-400">確定後は左に科目・右に通常/講習</span>
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
