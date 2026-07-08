import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { saveSession } from '../utils/session';

const ROLES = [
  {
    id: 'student',
    title: '生徒',
    desc: '講習日程の提案書を確認し、空き / × を提出。確定後はスケジュールを閲覧。',
    demo: 'student@example.com',
  },
  {
    id: 'teacher',
    title: '講師',
    desc: '講習日程の提案書を確認し、空き / × を提出。確定後はスケジュールを閲覧。',
    demo: 'teacher@example.com',
  },
  {
    id: 'admin',
    title: '教室長',
    desc: '講習作成・時間割管理・提案書送付・割当・確定送付。',
    demo: 'admin@example.com',
  },
];

const BTN = {
  student: 'bg-emerald-600 hover:bg-emerald-700',
  teacher: 'bg-blue-600 hover:bg-blue-700',
  admin: 'bg-gray-800 hover:bg-gray-900',
};

const CARD_RING = {
  student: 'hover:border-emerald-300 hover:shadow-emerald-100',
  teacher: 'hover:border-blue-300 hover:shadow-blue-100',
  admin: 'hover:border-gray-400 hover:shadow-gray-200',
};

const ACCENT = {
  student: 'text-emerald-700 focus:ring-emerald-500',
  teacher: 'text-blue-700 focus:ring-blue-500',
  admin: 'text-gray-800 focus:ring-gray-500',
};

export default function Login() {
  const navigate = useNavigate();
  const [step, setStep] = useState('select');
  const [selectedRole, setSelectedRole] = useState(null);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('demo');
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const roleMeta = ROLES.find((r) => r.id === selectedRole);

  const chooseRole = (roleId) => {
    const role = ROLES.find((r) => r.id === roleId);
    setSelectedRole(roleId);
    setEmail(role?.demo ?? '');
    setPassword('demo');
    setError(null);
    setStep('login');
  };

  const goBack = () => {
    setStep('select');
    setSelectedRole(null);
    setError(null);
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    if (!selectedRole) return;
    setError(null);
    setIsLoading(true);
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || 'ログインに失敗しました');
      }
      const data = await res.json();
      if (data.role !== selectedRole) {
        throw new Error(
          selectedRole === 'teacher'
            ? '講師アカウントでログインしてください'
            : selectedRole === 'student'
              ? '生徒アカウントでログインしてください'
              : '教室長アカウントでログインしてください',
        );
      }
      saveSession(data);
      const redirect = data.role === 'teacher' && data.redirect === '/student'
        ? '/teacher'
        : data.redirect;
      navigate(redirect);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-100 to-blue-50 flex items-center justify-center p-4">
      <div className="max-w-4xl w-full">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">JUKU-SHIFT DX</h1>
          <p className="text-gray-600 mt-2">講習シフト管理 — Excel あり・なしどちらでも使えます</p>
        </div>

        {step === 'select' && (
          <>
            <p className="text-center text-sm text-gray-600 mb-5">ログインする立場を選んでください</p>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              {ROLES.map((role) => (
                <button
                  key={role.id}
                  type="button"
                  onClick={() => chooseRole(role.id)}
                  className={`text-left bg-white rounded-2xl border border-gray-200 p-5 shadow-sm transition-all hover:shadow-md ${CARD_RING[role.id]}`}
                >
                  <h2 className="font-bold text-lg text-gray-900">{role.title}</h2>
                  <p className="text-xs text-gray-600 mt-2 leading-relaxed min-h-[3rem]">{role.desc}</p>
                  <span
                    className={`inline-block w-full mt-4 text-white text-center font-bold py-3 rounded-xl shadow-md ${BTN[role.id]}`}
                  >
                    {role.title}としてログイン
                  </span>
                </button>
              ))}
            </div>
          </>
        )}

        {step === 'login' && roleMeta && (
          <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-6 max-w-md mx-auto">
            <button
              type="button"
              onClick={goBack}
              className="text-sm text-gray-500 hover:text-gray-800 mb-4"
            >
              ← 立場の選択に戻る
            </button>
            <h2 className={`text-xl font-bold ${ACCENT[selectedRole].split(' ')[0]}`}>
              {roleMeta.title}ログイン
            </h2>
            <p className="text-xs text-gray-500 mt-1 mb-5">{roleMeta.desc}</p>

            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="block text-sm font-bold text-gray-700 mb-1">メールアドレス</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="username"
                  autoFocus
                  required
                  className={`w-full px-4 py-2.5 rounded-lg border border-gray-300 focus:ring-2 focus:outline-none ${ACCENT[selectedRole]}`}
                  placeholder="email@example.com"
                />
              </div>
              <div>
                <label className="block text-sm font-bold text-gray-700 mb-1">パスワード</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  required
                  className={`w-full px-4 py-2.5 rounded-lg border border-gray-300 focus:ring-2 focus:outline-none ${ACCENT[selectedRole]}`}
                />
              </div>
              {error && <p className="text-red-500 text-sm">{error}</p>}
              <button
                type="submit"
                disabled={isLoading}
                className={`w-full text-white font-bold py-3 rounded-xl shadow-md transition-all disabled:opacity-60 ${BTN[selectedRole]}`}
              >
                {isLoading ? 'ログイン中…' : 'ログイン'}
              </button>
            </form>
            <p className="text-[11px] text-gray-400 mt-4 text-center">
              デモ: {roleMeta.demo}（パスワード demo）
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
