// src/pages/AdminDashboard.jsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

export default function AdminDashboard() {
  const navigate = useNavigate();
  const [selectedDate, setSelectedDate] = useState('2026-06-10');
  const [teachers, setTeachers] = useState([]);
  
  // ★追加：自動割当の計算中かどうかを判定するState
  const [isCalculating, setIsCalculating] = useState(false);
  
  // ★追加：微調整ポップアップ（モーダル）用のState
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedCell, setSelectedCell] = useState(null);

  useEffect(() => {
    // 初期データの読み込み（モック）
    const mockData = [
      { id: 1, name: '田中 先生', color: 'bg-blue-100 text-blue-600', s1: '確定', s2: '確定', s3: '不可', s4: '不可' },
      { id: 2, name: '佐藤 先生', color: 'bg-pink-100 text-pink-600', s1: '不可', s2: '待機', s3: '不足', s4: '未提出' },
      { id: 3, name: '鈴木 先生', color: 'bg-green-100 text-green-600', s1: '待機', s2: '待機', s3: '確定', s4: '待機' },
    ];
    setTeachers(mockData);
  }, [selectedDate]);

  // ステータスに応じたデザイン設定
  const getStatusStyle = (status) => {
    switch (status) {
      case '確定': return 'bg-emerald-100 text-emerald-700 border-emerald-200';
      case '待機': return 'bg-white text-blue-600 border-blue-400 border-2 hover:bg-blue-50';
      case '不可': return 'bg-gray-100 text-gray-400 border-gray-100';
      case '不足': return 'bg-yellow-100 text-yellow-700 border-yellow-300 animate-pulse';
      case 'AI提案': return 'bg-purple-100 text-purple-700 border-purple-400 border-2 shadow-[0_0_10px_rgba(168,85,247,0.4)]';
      default: return 'bg-white text-gray-400 border-gray-200';
    }
  };

  // ★追加：自動割当ボタンを押した時の処理（API通信のシミュレーション）
  const handleAutoAssign = () => {
    setIsCalculating(true); // ローディング開始
    
    // バックエンドの計算時間を想定し、2.5秒後に結果を反映する
    setTimeout(() => {
      setTeachers(prev => prev.map(t => {
        if (t.id === 2) return { ...t, s3: 'AI提案' }; // 佐藤先生の不足枠をAI提案に変更
        if (t.id === 3) return { ...t, s1: 'AI提案' }; // 鈴木先生の待機枠をAI提案に変更
        return t;
      }));
      setIsCalculating(false); // ローディング終了
    }, 2500);
  };

  // ★追加：セルをクリックしてポップアップを開く処理
  const handleCellClick = (teacherName, period, currentStatus) => {
    if (currentStatus === '不可' || currentStatus === '未提出') return; // 変更不可のセルは何もしない
    setSelectedCell({ teacherName, period, currentStatus });
    setModalOpen(true);
  };

  return (
    <div className="min-h-screen bg-gray-50 flex font-sans relative">
      {/* 画面全体を覆うローディングオーバーレイ */}
      {isCalculating && (
        <div className="absolute inset-0 bg-white/70 backdrop-blur-sm z-50 flex flex-col items-center justify-center">
          <div className="w-16 h-16 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin mb-4"></div>
          <h2 className="text-2xl font-bold text-blue-800">最適シフトを計算中...</h2>
          <p className="text-gray-500 mt-2">条件に合致する講師をマッチングしています</p>
        </div>
      )}

      {/* 微調整用モーダル（ポップアップ） */}
      {modalOpen && selectedCell && (
        <div className="absolute inset-0 bg-black/50 z-40 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-md w-full">
            <h3 className="text-xl font-bold text-gray-800 mb-2">シフトの個別調整</h3>
            <p className="text-gray-500 mb-6">{selectedCell.period}コマ目 - {selectedCell.teacherName} ({selectedCell.currentStatus})</p>
            
            <div className="space-y-3 mb-8">
              <p className="text-sm font-bold text-gray-700">代替可能な講師候補（AIスコア順）</p>
              <button className="w-full text-left p-3 border-2 border-emerald-500 bg-emerald-50 rounded-xl font-bold text-emerald-800 flex justify-between">
                <span>👨‍🏫 高橋 先生 (数学)</span>
                <span className="text-emerald-600">マッチ度: 95%</span>
              </button>
              <button className="w-full text-left p-3 border border-gray-200 hover:bg-gray-50 rounded-xl text-gray-700 flex justify-between">
                <span>👩‍🏫 伊藤 先生 (理系全般)</span>
                <span className="text-gray-400">マッチ度: 70%</span>
              </button>
            </div>
            
            <div className="flex gap-3">
              <button onClick={() => setModalOpen(false)} className="flex-1 py-3 bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-xl font-bold transition-colors">キャンセル</button>
              <button onClick={() => setModalOpen(false)} className="flex-1 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-bold shadow-md transition-colors">変更を確定</button>
            </div>
          </div>
        </div>
      )}

      <div className="w-64 bg-gray-900 text-white p-6 flex flex-col">
        <h1 className="text-2xl font-bold mb-10 text-blue-400 flex items-center gap-2"><span>🎓</span> JUKU-SHIFT</h1>
        <nav className="flex-1 space-y-2">
          <button className="w-full text-left bg-gray-800 px-4 py-3 rounded-lg font-bold">ダッシュボード</button>
          <button onClick={() => navigate('/import')} className="w-full text-left hover:bg-gray-800 px-4 py-3 rounded-lg text-gray-400 transition-colors">データインポート</button>
        </nav>
        <button onClick={() => navigate('/')} className="text-gray-400 hover:text-white text-left text-sm">← ログアウト</button>
      </div>

      <div className="flex-1 p-8 overflow-y-auto">
        <header className="mb-8 flex justify-between items-center">
          <div>
            <h2 className="text-3xl font-bold text-gray-800">ダッシュボード</h2>
            <div className="flex items-center gap-3 mt-3">
              <input type="date" value={selectedDate} onChange={(e) => setSelectedDate(e.target.value)} className="bg-white border border-gray-300 text-gray-700 px-3 py-2 rounded-lg font-bold shadow-sm focus:ring-2 focus:ring-blue-500 outline-none cursor-pointer" />
              <p className="text-gray-500 font-bold">のシフト状況</p>
            </div>
          </div>
          <div className="flex gap-3">
            {/* ★自動割当実行ボタン */}
            <button onClick={handleAutoAssign} disabled={isCalculating} className="bg-purple-600 hover:bg-purple-700 text-white px-6 py-3 rounded-xl font-bold shadow-md transition-all active:scale-95 flex items-center gap-2">
              ✨ AI自動割当を実行
            </button>
            <button className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-xl font-bold shadow-md transition-all active:scale-95">
              シフトを確定する
            </button>
          </div>
        </header>

        <div className="grid grid-cols-3 gap-6 mb-8">
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex items-center justify-between">
            <div><p className="text-sm text-gray-500 font-bold mb-1">未提出の講師</p><p className="text-3xl font-bold text-red-500">3 <span className="text-lg text-gray-400 font-normal">名</span></p></div>
          </div>
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex items-center justify-between">
            <div><p className="text-sm text-gray-500 font-bold mb-1">不足しているコマ</p><p className="text-3xl font-bold text-yellow-500">5 <span className="text-lg text-gray-400 font-normal">枠</span></p></div>
          </div>
        </div>

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
              {teachers.map((t) => (
                <tr key={t.id} className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
                  <td className="p-4 border-r border-gray-200 font-bold flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${t.color}`}>{t.name.charAt(0)}</div>{t.name}
                  </td>
                  {/* ★セルをクリック可能にし、状態を渡す */}
                  <td className="p-3 text-center" onClick={() => handleCellClick(t.name, 1, t.s1)}>
                    <div className={`py-2 rounded-lg text-sm font-bold border cursor-pointer ${getStatusStyle(t.s1)}`}>{t.s1}</div>
                  </td>
                  <td className="p-3 text-center" onClick={() => handleCellClick(t.name, 2, t.s2)}>
                    <div className={`py-2 rounded-lg text-sm font-bold border cursor-pointer ${getStatusStyle(t.s2)}`}>{t.s2}</div>
                  </td>
                  <td className="p-3 text-center" onClick={() => handleCellClick(t.name, 3, t.s3)}>
                    <div className={`py-2 rounded-lg text-sm font-bold border cursor-pointer ${getStatusStyle(t.s3)}`}>{t.s3}</div>
                  </td>
                  <td className="p-3 text-center" onClick={() => handleCellClick(t.name, 4, t.s4)}>
                    <div className={`py-2 rounded-lg text-sm font-bold border cursor-pointer ${getStatusStyle(t.s4)}`}>{t.s4}</div>
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