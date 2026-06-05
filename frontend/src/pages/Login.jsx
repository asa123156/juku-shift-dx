// src/pages/Login.jsx
import React from 'react';
import { useNavigate } from 'react-router-dom';

export default function Login() {
  const navigate = useNavigate();

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
              <input type="email" className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all" placeholder="email@example.com" />
            </div>
            <div>
              <label className="block text-sm font-bold text-gray-700 mb-2">パスワード</label>
              <input type="password" className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all" placeholder="••••••••" />
            </div>
          </div>

          <div className="mt-8 flex flex-col gap-4">
            <button 
              onClick={() => navigate('/student')}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 rounded-xl shadow-md transition-all active:scale-95"
            >
              講師・生徒としてログイン
            </button>
            <button 
              onClick={() => navigate('/admin')}
              className="w-full bg-gray-800 hover:bg-gray-900 text-white font-bold py-3 rounded-xl shadow-md transition-all active:scale-95"
            >
              教室長としてログイン
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}