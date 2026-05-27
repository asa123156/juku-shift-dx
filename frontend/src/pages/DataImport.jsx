// src/pages/DataImport.jsx
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

export default function DataImport() {
  const navigate = useNavigate();
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);

  // ドラッグ＆ドロップの処理
  const handleDragOver = (e) => { e.preventDefault(); setIsDragging(true); };
  const handleDragLeave = () => { setIsDragging(false); };
  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setSelectedFile(e.dataTransfer.files[0].name);
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
          <button onClick={() => navigate('/admin')} className="w-full text-left hover:bg-gray-800 px-4 py-3 rounded-lg text-gray-400 transition-colors">ダッシュボード</button>
          <button className="w-full text-left bg-gray-800 px-4 py-3 rounded-lg font-bold">データインポート</button>
        </nav>
        <button onClick={() => navigate('/')} className="text-gray-400 hover:text-white text-left text-sm">← ログアウト</button>
      </div>

      {/* メインコンテンツ */}
      <div className="flex-1 p-8">
        <header className="mb-8">
          <h2 className="text-3xl font-bold text-gray-800">CSVデータインポート</h2>
          <p className="text-gray-500 mt-1">iPadのExcelから書き出した授業情報をシステムに取り込みます</p>
        </header>

        <div className="bg-white p-10 rounded-2xl shadow-sm border border-gray-200 max-w-2xl">
          {/* ドロップエリア */}
          <div 
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={`border-4 border-dashed rounded-xl p-12 text-center transition-all ${
              isDragging ? 'border-blue-500 bg-blue-50' : 'border-gray-300 bg-gray-50 hover:bg-gray-100'
            }`}
          >
            <div className="text-5xl mb-4 text-blue-400">📁</div>
            <h3 className="text-lg font-bold text-gray-700 mb-2">CSVファイルをここにドロップ</h3>
            <p className="text-gray-500 text-sm mb-6">または</p>
            <label className="bg-white border border-gray-300 text-gray-700 px-6 py-2 rounded-lg font-bold shadow-sm cursor-pointer hover:bg-gray-50">
              ファイルを選択
              <input type="file" className="hidden" accept=".csv" onChange={(e) => setSelectedFile(e.target.files[0]?.name)} />
            </label>
          </div>

          {/* 選択されたファイルの表示 */}
          {selectedFile && (
            <div className="mt-6 p-4 bg-emerald-50 border border-emerald-200 rounded-lg flex items-center justify-between">
              <div className="flex items-center gap-3 text-emerald-700 font-bold">
                <span>📄</span> {selectedFile}
              </div>
              <button 
                onClick={() => alert('バックエンドAPIへCSVを送信します！')}
                className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-lg font-bold shadow-md transition-all active:scale-95"
              >
                インポート実行
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}