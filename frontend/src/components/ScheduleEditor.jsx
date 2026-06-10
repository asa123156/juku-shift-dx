const EMPTY = { 1: '', 2: '', 3: '', 4: '' };

export function apiSlotsToState(slots) {
  return {
    1: slots?.['1'] ?? '',
    2: slots?.['2'] ?? '',
    3: slots?.['3'] ?? '',
    4: slots?.['4'] ?? '',
  };
}

export function stateToApiSlots(slots) {
  return { '1': slots[1], '2': slots[2], '3': slots[3], '4': slots[4] };
}

export { EMPTY as EMPTY_SLOTS };

export function TimeSlotRow({ period, time, status, locked, readonly, onStatusChange, disabled }) {
  const lockedSlot = locked || status === '◎';
  const readOnly = readonly || lockedSlot;

  return (
    <div className={`bg-white p-4 rounded-2xl shadow-sm border flex items-center justify-between transition-colors ${status === '' && !readOnly ? 'border-blue-300 ring-2 ring-blue-100' : 'border-gray-100'}`}>
      <div>
        <div className="text-xs text-gray-400 font-bold">{period}コマ目</div>
        <div className="text-lg font-bold text-gray-800">
          {time?.start} <span className="text-sm font-normal text-gray-500">~ {time?.end}</span>
        </div>
      </div>
      {readOnly ? (
        <div className="px-4 py-2 rounded-lg bg-gray-100 text-gray-700 font-bold text-sm">
          {status === '◎' ? '◎ 通常授業' : status === '×' ? '× 無理' : '空き'}
        </div>
      ) : (
        <div className="flex bg-gray-100 rounded-lg p-1 gap-1">
          <button
            type="button"
            disabled={disabled}
            onClick={() => onStatusChange('')}
            className={`w-14 h-10 rounded-md font-bold text-sm transition-all disabled:opacity-50 ${status === '' ? 'bg-emerald-500 text-white shadow-sm ring-2 ring-emerald-300' : 'text-gray-400 hover:bg-gray-200 border border-dashed border-gray-300'}`}
            title="空いている"
          >
            空
          </button>
          <button
            type="button"
            disabled={disabled}
            onClick={() => onStatusChange('×')}
            className={`w-14 h-10 rounded-md font-bold transition-all disabled:opacity-50 ${status === '×' ? 'bg-red-500 text-white shadow-sm' : 'text-gray-400 hover:bg-gray-200'}`}
            title="無理"
          >
            ×
          </button>
        </div>
      )}
    </div>
  );
}

export function ScheduleLegend() {
  return (
    <div className="flex justify-center gap-4 mb-4 text-xs text-gray-500">
      <span><span className="text-slate-600 font-bold">◎</span> 通常授業（固定）</span>
      <span><span className="text-emerald-600 font-bold">空</span> 空いてる</span>
      <span><span className="text-red-500 font-bold">×</span> 無理</span>
    </div>
  );
}
