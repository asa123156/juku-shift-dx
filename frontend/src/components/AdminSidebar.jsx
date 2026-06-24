import { clearSession } from '../utils/session';

export function AdminSidebar({ navigate, current }) {
  const link = (path, label, key) => (
    <button
      type="button"
      onClick={() => navigate(path)}
      className={`w-full text-left px-4 py-3 rounded-lg transition-colors ${
        current === key ? 'bg-gray-800 font-bold' : 'hover:bg-gray-800 text-gray-400'
      }`}
    >
      {label}
    </button>
  );

  return (
    <div className="w-64 bg-gray-900 text-white p-6 flex flex-col shrink-0">
      <h1 className="text-2xl font-bold mb-10 text-blue-400 flex items-center gap-2">
        <span>🎓</span> JUKU-SHIFT
      </h1>
      <nav className="flex-1 space-y-2">
        {link('/admin', 'ダッシュボード', 'dashboard')}
        {link('/admin/manage', '教室管理', 'manage')}
        {link('/admin/student-plans', '講習希望設定', 'student-plans')}
        {link('/admin/assignments', '生徒の割り当て', 'assignments')}
        {link('/import', 'データインポート', 'import')}
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
