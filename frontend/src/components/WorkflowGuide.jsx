import React from 'react';

/** 講習期間が未作成でも表示する固定の手順説明（進捗は API 取得時に上書き） */
export const DEFAULT_WORKFLOW_STEPS = [
  {
    id: 1,
    title: '講習作成・希望設定',
    description: '講習期間を作成し、生徒の希望科目を設定',
    path: '/admin/manage',
    alt_path: '/admin/student-plans',
    status: 'active',
    detail: '教室管理から講習・生徒・講師を登録',
  },
  {
    id: 2,
    title: '通常授業の入力',
    description: 'Excel取込 または 時間割表で通常授業を入力',
    path: '/import',
    alt_path: '/admin/schedule-grid',
    status: 'pending',
  },
  {
    id: 3,
    title: '提案書を送付',
    description: '生徒・講師に講習の日程提案書を配布',
    path: '/admin/assignments',
    status: 'pending',
  },
  {
    id: 4,
    title: 'スケジュール提出',
    description: '生徒・講師が空き / × を提出',
    path: '/admin',
    status: 'pending',
  },
  {
    id: 5,
    title: '割当・時間割調整',
    description: '生徒を講師に割り当て、時間割表で調整',
    path: '/admin/assignments',
    alt_path: '/admin/schedule-grid',
    status: 'pending',
  },
  {
    id: 6,
    title: '確定・送信',
    description: '確定スケジュールを生徒・講師に送信',
    path: '/admin/assignments',
    status: 'pending',
  },
];

const STATUS_STYLE = {
  done: {
    ring: 'border-emerald-400 bg-emerald-50',
    badge: 'bg-emerald-600 text-white',
    dot: 'bg-emerald-500',
  },
  active: {
    ring: 'border-blue-400 bg-blue-50 shadow-md shadow-blue-100',
    badge: 'bg-blue-600 text-white',
    dot: 'bg-blue-500 animate-pulse',
  },
  pending: {
    ring: 'border-gray-200 bg-white',
    badge: 'bg-gray-200 text-gray-600',
    dot: 'bg-gray-300',
  },
};

function StepCard({ step, onNavigate }) {
  const style = STATUS_STYLE[step.status] || STATUS_STYLE.pending;
  const isClickable = step.status === 'active' || step.status === 'done';

  return (
    <button
      type="button"
      onClick={() => isClickable && step.path && onNavigate(step.path)}
      disabled={!isClickable || !step.path}
      className={`text-left rounded-2xl border-2 p-4 transition-all ${style.ring} ${
        isClickable && step.path ? 'hover:scale-[1.01] cursor-pointer' : 'cursor-default'
      }`}
    >
      <div className="flex items-start gap-3">
        <span className={`shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${style.badge}`}>
          {step.status === 'done' ? '✓' : step.id}
        </span>
        <div className="min-w-0 flex-1">
          <p className="font-bold text-gray-900 text-sm">{step.title}</p>
          <p className="text-xs text-gray-600 mt-1 leading-relaxed">{step.description}</p>
          {step.detail && (
            <p className="text-xs font-bold text-gray-500 mt-2">{step.detail}</p>
          )}
          {step.alt_path && step.status !== 'pending' && (
            <p className="text-[10px] text-blue-600 mt-1">
              Excel不要の場合は時間割表から手入力も可
            </p>
          )}
        </div>
        <span className={`shrink-0 w-2 h-2 rounded-full mt-2 ${style.dot}`} />
      </div>
    </button>
  );
}

export function WorkflowGuide({ steps, onNavigate }) {
  if (!steps?.length) return null;

  const activeStep = steps.find((s) => s.status === 'active') ?? steps.find((s) => s.status === 'pending');

  return (
    <section className="mb-8 bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-100 bg-gradient-to-r from-slate-50 to-blue-50/50">
        <h3 className="text-lg font-bold text-gray-900">講習の進め方</h3>
        <p className="text-xs text-gray-600 mt-1">
          Excel を使う場合・使わない場合のどちらでも同じ流れです。
          {activeStep && (
            <span className="ml-1 font-bold text-blue-700">現在: ステップ {activeStep.id}</span>
          )}
        </p>
      </div>
      <div className="p-4 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
        {steps.map((step) => (
          <StepCard key={step.id} step={step} onNavigate={onNavigate} />
        ))}
      </div>
    </section>
  );
}
