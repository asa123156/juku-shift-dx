import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAdminSession } from '../hooks/useAdminSession';
import { clearSession } from '../utils/session';

export default function DataImport() {
  const navigate = useNavigate();
  const isReady = useAdminSession();
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [shiftFile, setShiftFile] = useState(null);
  const [periodId, setPeriodId] = useState(1);
  const [importMode, setImportMode] = useState('assignments');
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const handleDragOver = (e) => { e.preventDefault(); setIsDragging(true); };
  const handleDragLeave = () => { setIsDragging(false); };

  const pickFile = (file) => {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.csv')) {
      setError('CSV ファイルを選択してください');
      return;
    }
    setSelectedFile(file);
    setError(null);
    setResult(null);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    pickFile(e.dataTransfer.files?.[0]);
  };

  const handleImport = async () => {
    const file = importMode === 'assignments' ? selectedFile : shiftFile;
    if (!file || isUploading) return;

    setIsUploading(true);
    setError(null);
    setResult(null);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const url = importMode === 'assignments'
        ? '/api/admin/assignment-requests/import'
        : `/api/admin/shifts/import-excel?period_id=${periodId}`;
      const res = await fetch(url, { method: 'POST', body: formData });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(body.detail || 'インポートに失敗しました');
      setResult(body);
      if (importMode === 'assignments') setSelectedFile(null);
      else setShiftFile(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsUploading(false);
    }
  };

  if (!isReady) return null;

  return (
    <div className="min-h-screen bg-gray-50 flex font-sans">
      <div className="w-64 bg-gray-900 text-white p-6 flex flex-col">
        <h1 className="text-2xl font-bold mb-10 text-blue-400 flex items-center gap-2">
          <span>🎓</span> JUKU-SHIFT
        </h1>
        <nav className="flex-1 space-y-2">
          <button type="button" onClick={() => navigate('/admin')} className="w-full text-left hover:bg-gray-800 px-4 py-3 rounded-lg text-gray-400 transition-colors">ダッシュボード</button>
          <button type="button" className="w-full text-left bg-gray-800 px-4 py-3 rounded-lg font-bold">データインポート</button>
        </nav>
        <button type="button" onClick={() => { clearSession(); navigate('/'); }} className="text-gray-400 hover:text-white text-left text-sm">← ログアウト</button>
      </div>

      <div className="flex-1 p-8">
        <header className="mb-8">
          <h2 className="text-3xl font-bold text-gray-800">CSVデータインポート</h2>
          <p className="text-gray-500 mt-1">iPadのExcelから書き出した授業情報をシステムに取り込みます</p>
        </header>

        <div className="bg-white p-10 rounded-2xl shadow-sm border border-gray-200 max-w-2xl space-y-6">
          <div className="flex gap-2">
            <button type="button" onClick={() => setImportMode('assignments')} className={`px-4 py-2 rounded-lg font-bold ${importMode === 'assignments' ? 'bg-blue-600 text-white' : 'bg-gray-100'}`}>割当リクエスト</button>
            <button type="button" onClick={() => setImportMode('shifts')} className={`px-4 py-2 rounded-lg font-bold ${importMode === 'shifts' ? 'bg-blue-600 text-white' : 'bg-gray-100'}`}>通常授業（◎）</button>
          </div>

          {importMode === 'shifts' && (
            <div className="flex items-center gap-3">
              <label className="text-sm font-bold text-gray-700">募集期間 ID</label>
              <input type="number" min={1} value={periodId} onChange={(e) => setPeriodId(Number(e.target.value))} className="border rounded-lg px-3 py-2 w-24" />
            </div>
          )}

          <div className="p-4 bg-blue-50 border border-blue-100 rounded-lg text-sm text-blue-800">
            <p className="font-bold mb-1">CSV 形式</p>
            <code className="text-xs block whitespace-pre">{importMode === 'assignments'
              ? `date,student_id,student_name,subject\n2026-06-11,1,近大太郎,数学I`
              : `role,entity_id,date,slot,symbol\nteacher,1,2026-06-10,1,◎`}</code>
          </div>

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
              <input
                type="file"
                className="hidden"
                accept=".csv"
                onChange={(e) => (importMode === 'assignments' ? pickFile(e.target.files?.[0]) : (setShiftFile(e.target.files?.[0]), setError(null), setResult(null)))}
              />
            </label>
          </div>

          {error && <p className="mt-4 text-red-500 text-sm">{error}</p>}

          {result && (
            <div className="mt-6 p-4 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-800">
              <p className="font-bold">{result.message}</p>
              {Object.keys(result.by_date ?? {}).length > 0 && (
                <ul className="mt-2 text-sm list-disc list-inside">
                  {Object.entries(result.by_date).map(([date, count]) => (
                    <li key={date}>{date}: {count} 件追加</li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {(importMode === 'assignments' ? selectedFile : shiftFile) && (
            <div className="mt-6 p-4 bg-emerald-50 border border-emerald-200 rounded-lg flex items-center justify-between">
              <div className="flex items-center gap-3 text-emerald-700 font-bold">
                <span>📄</span> {(importMode === 'assignments' ? selectedFile : shiftFile).name}
              </div>
              <button
                type="button"
                onClick={handleImport}
                disabled={isUploading}
                className="bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-400 text-white px-4 py-2 rounded-lg font-bold shadow-md transition-all active:scale-95"
              >
                {isUploading ? '取り込み中...' : 'インポート実行'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
