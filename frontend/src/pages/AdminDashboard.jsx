// src/pages/AdminDashboard.jsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

export default function AdminDashboard() {
  const navigate = useNavigate();

  // ① データを保持するためのState（箱）
  const [teachers, setTeachers] = useState([]);

  // ② 画面が表示された時に一度だけデータをセットする（将来はここでAPI通信を行います）
  useEffect(() => {
    // チームメンバーが作っている lesson_mock.json などのデータを想定したダミーデータ
    const mockData = [
      { id: 1, name: '田中 先生', color: 'bg-blue-100 text-blue-600', s1: '確定', s2: '確定', s3: '不可', s4: '不可' },
      { id: 2, name: '佐藤 先生', color: 'bg-pink-100 text-pink-600', s1: '不可', s2: '待機', s3: '不足', s4: '未提出' },
      { id: 3, name: '鈴木 先生', color: 'bg-green-100 text-green-600', s1: '待機', s2: '待機', s3: '確定', s4: '待機' },
    ];
    setTeachers(mockData);
  }, []);

  // ステータスに応じてデザイン（色）を変える関数
  const getStatusStyle = (status) => {
    switch (status) {
      case '確定': return 'bg-emerald-100 text-emerald-700 border-emerald-200';
      case '待機': return 'bg-white text-blue-600 border-blue-400 border-2 cursor-pointer hover:bg-blue-50';
      case '不可': return 'bg-gray-100 text-gray-400 border-gray-100';
      case '不足': return 'bg-yellow-100 text-yellow-700 border-yellow-300 animate-pulse';
      default: return 'bg-white text-gray-400 border-gray-200';
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex font-sans">
      {/* サイドバー */}
      <div className="w-64 bg-gray-900 text-white p-6 flex flex-col">
        <h1 className="text-2xl font-bold mb-10 text-blue-400 flex items-center gap-2">
          <span>🎓</span> JUKU-SHIFT
        </h1>
        <nav className="flex-1 space-y-2">
          <button className="w-full text-left bg-gray-800 px-4 py-3 rounded-lg font-bold">ダッシュボード</button>
          <button className="w-full text-left hover:bg-gray-800 px-4 py-3 rounded-lg text-gray-400 transition-colors">データインポート</button>
        </nav>
        <button onClick={() => navigate('/')} className="text-gray-400 hover:text-white text-left text-sm">← ログアウト</button>
      </div>

      {/* メインコンテンツ */}
      <div className="flex-1 p-8 overflow-y-auto">
        <header className="mb-8 flex justify-between items-center">
          <div>
            <h2 className="text-3xl font-bold text-gray-800">ダッシュボード</h2>
            <p className="text-gray-500 mt-1">2026年 6月10日 (月) の状況</p>
          </div>
          <button className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-xl font-bold shadow-md transition-all active:scale-95">
            シフトを確定する
          </button>
        </header>

        {/* メトリクス（警告）パネル */}
        <div className="grid grid-cols-3 gap-6 mb-8">
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 font-bold mb-1">未提出の講師</p>
              <p className="text-3xl font-bold text-red-500">3 <span className="text-lg text-gray-400 font-normal">名</span></p>
            </div>
          </div>
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 font-bold mb-1">不足しているコマ</p>
              <p className="text-3xl font-bold text-yellow-500">5 <span className="text-lg text-gray-400 font-normal">枠</span></p>
            </div>
          </div>
        </div>

        {/* シフト表（マトリクス） */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-gray-100 text-gray-600 text-sm border-b border-gray-200">
                <th className="p-4 font-bold border-r border-gray-200">講師名 \ 時間</th>
                <th className="p-4 font-bold text-center">1コマ (13:00)</th>
                <th className="p-4 font-bold text-center">2コマ (14:30)</th>
                <th className="p-4 font-bold text-center">3コマ (16:00)</th>
                <th className="p-4 font-bold text-center">4コマ (17:30)</th>
              </tr>
            </thead>
            <tbody>
              {/* ③ データの配列を元に、自動で行（<tr>）を繰り返し生成する */}
              {teachers.map((teacher) => (
                <tr key={teacher.id} className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
                  <td className="p-4 border-r border-gray-200 font-bold flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${teacher.color}`}>
                      {teacher.name.charAt(0)}
                    </div>
                    {teacher.name}
                  </td>
                  <td className="p-3 text-center">
                    <div className={`py-2 rounded-lg text-sm font-bold border ${getStatusStyle(teacher.s1)}`}>{teacher.s1}</div>
                  </td>
                  <td className="p-3 text-center">
                    <div className={`py-2 rounded-lg text-sm font-bold border ${getStatusStyle(teacher.s2)}`}>{teacher.s2}</div>
                  </td>
                  <td className="p-3 text-center">
                    <div className={`py-2 rounded-lg text-sm font-bold border ${getStatusStyle(teacher.s3)}`}>{teacher.s3}</div>
                  </td>
                  <td className="p-3 text-center">
                    <div className={`py-2 rounded-lg text-sm font-bold border ${getStatusStyle(teacher.s4)}`}>{teacher.s4}</div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}