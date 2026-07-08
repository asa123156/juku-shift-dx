import React from 'react';

const PHASES = [
  { key: 'proposal', label: '提案書', sub: '日程を確認' },
  { key: 'submit', label: '提出', sub: '空き / ×' },
  { key: 'revision', label: '修正', sub: '変更提案' },
  { key: 'final', label: '確定', sub: '閲覧のみ' },
];

function resolvePhase({ readonly, scheduleRequested, schedulePublished, proposalMode, periodStatus }) {
  if (proposalMode) return 'revision';
  if (readonly || schedulePublished || periodStatus === 'FINALIZED') return 'final';
  if (scheduleRequested) return 'submit';
  return 'proposal';
}

export function UserPhaseStepper({
  role = 'student',
  readonly,
  scheduleRequested,
  schedulePublished,
  proposalMode,
  periodStatus,
}) {
  const current = resolvePhase({
    readonly,
    scheduleRequested,
    schedulePublished,
    proposalMode,
    periodStatus,
  });
  const accent = role === 'student' ? 'emerald' : 'blue';
  const activeBg = accent === 'emerald' ? 'bg-emerald-600' : 'bg-blue-600';
  const doneBg = accent === 'emerald' ? 'bg-emerald-100 text-emerald-800' : 'bg-blue-100 text-blue-800';

  const order = ['proposal', 'submit', 'revision', 'final'];
  const currentIdx = order.indexOf(current);

  return (
    <div className="mb-4 p-3 bg-white border border-gray-200 rounded-2xl">
      <div className="flex items-center justify-between gap-1">
        {PHASES.map((phase, idx) => {
          const isDone = idx < currentIdx;
          const isActive = phase.key === current;
          return (
            <div key={phase.key} className="flex-1 flex flex-col items-center min-w-0">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold mb-1 ${
                  isActive
                    ? `${activeBg} text-white shadow-md`
                    : isDone
                      ? doneBg
                      : 'bg-gray-100 text-gray-400'
                }`}
              >
                {isDone ? '✓' : idx + 1}
              </div>
              <span className={`text-[10px] font-bold truncate w-full text-center ${
                isActive ? 'text-gray-900' : 'text-gray-500'
              }`}
              >
                {phase.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function SubjectPlansCard({ plans }) {
  if (!plans?.length) return null;
  return (
    <div className="mb-4 p-4 bg-indigo-50 border border-indigo-200 rounded-2xl">
      <p className="text-xs font-bold text-indigo-800 tracking-wide">希望科目</p>
      <div className="flex flex-wrap gap-2 mt-2">
        {plans.map((p) => (
          <span
            key={p.subject}
            className="text-sm font-bold bg-white text-indigo-900 px-3 py-1 rounded-full border border-indigo-200"
          >
            {p.subject} × {p.slot_count}コマ
          </span>
        ))}
      </div>
    </div>
  );
}
