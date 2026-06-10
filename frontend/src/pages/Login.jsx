import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { saveSession } from '../utils/session';

export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('teacher@example.com');
  const [password, setPassword] = useState('demo');
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleLogin = async (expectedRole) => {
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
      if (data.role !== expectedRole) {
        throw new Error(
          expectedRole === 'teacher'
            ? '講師アカウントでログインしてください'
            : expectedRole === 'student'
              ? '生徒アカウントでログインしてください'
              : '教室長アカウントでログインしてください',
        );
      }
      saveSession(data);
      navigate(data.redirect);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-xl overflow-hidden">
        <div className="bg-blue-800 p-6 text-center">
          <h1 className="text-2xl font-bold text-white">JUKU-SHIFT DX</h1>
          <p className="text-blue-200 text-sm mt-2">シフト管理システム</p>
        </div>

        <div className="p-8">
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-bold text-gray-700 mb-2">メールアドレス</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                placeholder="email@example.com"
              />
            </div>
            <div>
              <label className="block text-sm font-bold text-gray-700 mb-2">パスワード</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                placeholder="••••••••"
              />
            </div>
          </div>

          {error && <p className="mt-4 text-red-500 text-sm">{error}</p>}

          <div className="mt-8 flex flex-col gap-4">
            <button
              type="button"
              onClick={() => handleLogin('teacher')}
              disabled={isLoading}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-bold py-3 rounded-xl shadow-md transition-all active:scale-95"
            >
              講師としてログイン
            </button>
            <button
              type="button"
              onClick={() => handleLogin('student')}
              disabled={isLoading}
              className="w-full bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-400 text-white font-bold py-3 rounded-xl shadow-md transition-all active:scale-95"
            >
              生徒としてログイン
            </button>
            <button
              type="button"
              onClick={() => handleLogin('admin')}
              disabled={isLoading}
              className="w-full bg-gray-800 hover:bg-gray-900 disabled:bg-gray-600 text-white font-bold py-3 rounded-xl shadow-md transition-all active:scale-95"
            >
              教室長としてログイン
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
