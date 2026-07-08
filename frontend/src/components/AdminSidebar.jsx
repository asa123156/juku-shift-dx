import { clearSession } from '../utils/session';

const NAV_ITEMS = [
  { path: '/admin', key: 'dashboard', step: null, label: 'ダッシュボード', sub: '進捗確認' },
  { path: '/admin/manage', key: 'manage', step: 1, label: '教室管理', sub: '講習・生徒・講師' },
  { path: '/admin/student-plans', key: 'student-plans', step: 1, label: '講習希望設定', sub: '希望科目' },
  { path: '/import', key: 'import', step: 2, label: 'Excel取込', sub: '任意' },
  { path: '/admin/schedule-grid', key: 'schedule-grid', step: 2, label: '時間割表', sub: '手入力も可' },
  { path: '/admin/assignments', key: 'assignments', step: '3-6', label: '割当・送付', sub: '提案→確定' },
];

export function AdminSidebar({ navigate, current }) {
  return (
    <div className="w-64 bg-gray-900 text-white p-6 flex flex-col shrink-0">
      <h1 className="text-2xl font-bold mb-2 text-blue-400 flex items-center gap-2">
        <span>🎓</span> JUKU-SHIFT
      </h1>
      <p className="text-xs text-gray-500 mb-8">教室長メニュー</p>
      <nav className="flex-1 space-y-1">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.key}
            type="button"
            onClick={() => navigate(item.path)}
            className={`w-full text-left px-4 py-3 rounded-lg transition-colors ${
              current === item.key ? 'bg-gray-800 font-bold' : 'hover:bg-gray-800 text-gray-400'
            }`}
          >
            <div className="flex items-center gap-2">
              {item.step && (
                <span className="text-[10px] font-bold bg-gray-700 text-gray-300 px-1.5 py-0.5 rounded">
                  {item.step}
                </span>
              )}
              <span className={current === item.key ? 'text-white' : ''}>{item.label}</span>
            </div>
            <p className="text-[10px] text-gray-500 mt-0.5 ml-0">{item.sub}</p>
          </button>
        ))}
      </nav>
      <button
        type="button"
        onClick={() => { clearSession(); navigate('/'); }}
        className="text-gray-400 hover:text-white text-left text-sm"
      >
        ← ログアウト
      </button>
    </div>
  );
}
