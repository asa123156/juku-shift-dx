import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAdminSession } from '../hooks/useAdminSession';
import { AdminSidebar } from './AdminDashboard';

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

  const pickFile = (file, mode) => {
    if (!file) return;
    const name = file.name.toLowerCase();
    if (mode === 'assignments' && !name.endsWith('.csv')) {
      setError('CSV ファイルを選択してください');
      return;
    }
    if (mode === 'shifts' && !name.endsWith('.xlsx') && !name.endsWith('.csv')) {
      setError('Excel (.xlsx) または CSV を選択してください');
      return;
    }
    if (mode === 'assignments') setSelectedFile(file);
    else setShiftFile(file);
    setError(null);
    setResult(null);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    pickFile(e.dataTransfer.files?.[0], importMode);
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
      <AdminSidebar navigate={navigate} current="import" />

      <div className="flex-1 p-8">
        <header className="mb-8">
          <h2 className="text-3xl font-bold text-gray-800">データインポート</h2>
          <p className="text-gray-500 mt-1">通常授業（◎）は Excel。シフト確定後にダッシュボードへ反映されます。</p>
        </header>

        <div className="bg-white p-10 rounded-2xl shadow-sm border border-gray-200 max-w-2xl space-y-6">
          <div className="flex gap-2">
            <button type="button" onClick={() => setImportMode('assignments')} className={`px-4 py-2 rounded-lg font-bold ${importMode === 'assignments' ? 'bg-blue-600 text-white' : 'bg-gray-100'}`}>割当リクエスト (CSV)</button>
            <button type="button" onClick={() => setImportMode('shifts')} className={`px-4 py-2 rounded-lg font-bold ${importMode === 'shifts' ? 'bg-blue-600 text-white' : 'bg-gray-100'}`}>通常授業 ◎ (Excel)</button>
          </div>

          {importMode === 'shifts' && (
            <div className="flex items-center gap-3">
              <label className="text-sm font-bold text-gray-700">募集期間 ID</label>
              <input type="number" min={1} value={periodId} onChange={(e) => setPeriodId(Number(e.target.value))} className="border rounded-lg px-3 py-2 w-24" />
            </div>
          )}

          <div className="p-4 bg-blue-50 border border-blue-100 rounded-lg text-sm text-blue-800">
            <p className="font-bold mb-1">{importMode === 'assignments' ? 'CSV 形式' : 'Excel 列'}</p>
            <code className="text-xs block whitespace-pre">{importMode === 'assignments'
              ? `date,student_id,student_name,subject\n2026-06-11,1,近大太郎,数学I`
              : `role | entity_id | date | slot | symbol\nteacher | 1 | 2026-06-10 | 1 | ◎`}</code>
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
            <h3 className="text-lg font-bold text-gray-700 mb-2">
              {importMode === 'shifts' ? 'Excel (.xlsx) をドロップ' : 'CSV をドロップ'}
            </h3>
            <label className="bg-white border border-gray-300 text-gray-700 px-6 py-2 rounded-lg font-bold shadow-sm cursor-pointer hover:bg-gray-50 inline-block mt-4">
              ファイルを選択
              <input
                type="file"
                className="hidden"
                accept={importMode === 'shifts' ? '.xlsx,.csv' : '.csv'}
                onChange={(e) => pickFile(e.target.files?.[0], importMode)}
              />
            </label>
          </div>

          {error && <p className="text-red-500 text-sm">{error}</p>}

          {result && (
            <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-800">
              <p className="font-bold">{result.message}</p>
            </div>
          )}

          {(importMode === 'assignments' ? selectedFile : shiftFile) && (
            <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-lg flex items-center justify-between">
              <span className="text-emerald-700 font-bold">📄 {(importMode === 'assignments' ? selectedFile : shiftFile).name}</span>
              <button type="button" onClick={handleImport} disabled={isUploading} className="bg-emerald-600 text-white px-4 py-2 rounded-lg font-bold disabled:bg-emerald-400">
                {isUploading ? '取り込み中...' : 'インポート実行'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
