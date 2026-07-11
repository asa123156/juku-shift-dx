import React, { useState, useEffect } from 'react';
import { periodStatusLabel } from '../components/ScheduleEditor';
import { useNavigate } from 'react-router-dom';
import { useAdminSession } from '../hooks/useAdminSession';
import { AdminSidebar } from '../components/AdminSidebar';
import { apiFetch } from '../utils/apiClient';

const MODES = {
  juku: {
    key: 'juku',
    label: '時間割 (白庭台 xlsx)',
    accept: '.xlsx,.xlsm',
    hint: '1ヶ月分の Excel をそのまま取り込みます。時間割シート（週次・日次）のみ読み込み、参照・講師シフト等は触りません。',
  },
  google: {
    key: 'google',
    label: 'Google スプレッドシート',
    accept: null,
    hint: '共有済みスプレッドシートから月次時間割を取り込み。日付省略時は時間割シートを一括取込します。',
  },
  assignments: {
    key: 'assignments',
    label: '割当リクエスト (CSV)',
    accept: '.csv',
    hint: 'date,student_id,student_name,subject',
  },
  shifts: {
    key: 'shifts',
    label: '固定枠 ◎ (Excel/CSV)',
    accept: '.xlsx,.csv',
    hint: 'role,entity_id,date,slot,symbol',
  },
};

export default function DataImport() {
  const navigate = useNavigate();
  const isReady = useAdminSession();
  const [isDragging, setIsDragging] = useState(false);
  const [file, setFile] = useState(null);
  const [importMode, setImportMode] = useState('juku');
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const [periods, setPeriods] = useState([]);
  const [activePeriodId, setActivePeriodId] = useState(1);
  const [importDate, setImportDate] = useState('');
  const [sheetName, setSheetName] = useState('');
  const [spreadsheetRef, setSpreadsheetRef] = useState('');
  const [googleConfigured, setGoogleConfigured] = useState(null);
  const [serviceAccountEmail, setServiceAccountEmail] = useState('');
  const [importAllSheets, setImportAllSheets] = useState(true);

  useEffect(() => {
    if (!isReady) return;
    apiFetch('/api/admin/periods')
      .then((r) => r.json())
      .then((data) => {
        setPeriods(data.periods ?? []);
        const active = data.active_period_id ?? data.periods?.[0]?.id ?? 1;
        setActivePeriodId(active);
        const period = (data.periods ?? []).find((p) => p.id === active);
        if (period?.start_date) setImportDate(period.start_date);
      })
      .catch(() => {});
    apiFetch('/api/google/status')
      .then((r) => r.json())
      .then((data) => {
        setGoogleConfigured(data.configured);
        setServiceAccountEmail(data.service_account_email || '');
      })
      .catch(() => {
        setGoogleConfigured(false);
        setServiceAccountEmail('');
      });
  }, [isReady]);

  const handleDragOver = (e) => { e.preventDefault(); setIsDragging(true); };
  const handleDragLeave = () => { setIsDragging(false); };

  const pickFile = (next) => {
    if (!next) return;
    setFile(next);
    setError(null);
    setResult(null);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    pickFile(e.dataTransfer.files?.[0]);
  };

  const buildImportUrl = () => {
    if (importMode === 'assignments') return '/api/admin/assignment-requests/import';
    if (importMode === 'shifts') return `/api/admin/shifts/import-excel?period_id=${activePeriodId}`;
    return `/api/import/juku-grid?period_id=${activePeriodId}`;
  };

  const handleGoogleImport = async () => {
    if (isUploading || !spreadsheetRef.trim()) {
      setError('スプレッドシート URL または ID を入力してください');
      return;
    }
    if (!importAllSheets && !importDate) {
      setError('単日取込の場合は取り込み日を指定してください');
      return;
    }

    setIsUploading(true);
    setError(null);
    setResult(null);
    try {
      const body = {
        period_id: activePeriodId,
        spreadsheet_ref: spreadsheetRef.trim(),
      };
      if (!importAllSheets) {
        body.date = importDate;
        if (sheetName.trim()) body.sheet_name = sheetName.trim();
      }
      const res = await apiFetch('/api/google/import', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || 'Google 取込に失敗しました');
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsUploading(false);
    }
  };

  const handleImport = async () => {
    if (importMode === 'google') {
      await handleGoogleImport();
      return;
    }
    if (!file || isUploading) return;

    setIsUploading(true);
    setError(null);
    setResult(null);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await apiFetch(buildImportUrl(), { method: 'POST', body: formData });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(body.detail || 'インポートに失敗しました');
      setResult(body);
      setFile(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsUploading(false);
    }
  };

  if (!isReady) return null;

  const mode = MODES[importMode];

  return (
    <div className="min-h-screen bg-gray-50 flex font-sans">
      <AdminSidebar navigate={navigate} current="import" />

      <div className="flex-1 p-8">
        <header className="mb-8">
          <h2 className="text-3xl font-bold text-gray-800">データインポート</h2>
          <p className="text-gray-500 mt-1">白庭台形式の時間割 xlsx から講師・生徒・割当リクエストを取り込めます。</p>
        </header>

        <div className="bg-white p-10 rounded-2xl shadow-sm border border-gray-200 max-w-2xl space-y-6">
          <div className="flex flex-wrap gap-2">
            {Object.values(MODES).map((m) => (
              <button
                key={m.key}
                type="button"
                onClick={() => { setImportMode(m.key); setFile(null); setResult(null); setError(null); }}
                className={`px-4 py-2 rounded-lg font-bold text-sm ${importMode === m.key ? 'bg-blue-600 text-white' : 'bg-gray-100'}`}
              >
                {m.label}
              </button>
            ))}
          </div>

          {(importMode === 'juku' || importMode === 'shifts' || importMode === 'google') && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <label className="block">
                <span className="text-sm font-bold text-gray-700">講習期間</span>
                <select
                  value={activePeriodId}
                  onChange={(e) => {
                    const id = Number(e.target.value);
                    setActivePeriodId(id);
                    const p = periods.find((x) => x.id === id);
                    if (p?.start_date) setImportDate(p.start_date);
                  }}
                  className="mt-1 w-full border rounded-lg px-3 py-2"
                >
                  {periods.map((p) => (
                    <option key={p.id} value={p.id}>{p.name}（{periodStatusLabel(p.status)}）</option>
                  ))}
                </select>
              </label>
              {importMode === 'google' && (
                <>
                  <label className="block sm:col-span-2">
                    <span className="text-sm font-bold text-gray-700">スプレッドシート URL / ID</span>
                    <input
                      type="text"
                      value={spreadsheetRef}
                      onChange={(e) => setSpreadsheetRef(e.target.value)}
                      placeholder="https://docs.google.com/spreadsheets/d/..."
                      className="mt-1 w-full border rounded-lg px-3 py-2"
                    />
                  </label>
                  <label className="flex items-center gap-2 sm:col-span-2">
                    <input
                      type="checkbox"
                      checked={importAllSheets}
                      onChange={(e) => setImportAllSheets(e.target.checked)}
                    />
                    <span className="text-sm font-bold text-gray-700">時間割シートを一括取込（推奨）</span>
                  </label>
                  {!importAllSheets && (
                    <>
                      <label className="block">
                        <span className="text-sm font-bold text-gray-700">取り込み日</span>
                        <input
                          type="date"
                          value={importDate}
                          onChange={(e) => setImportDate(e.target.value)}
                          className="mt-1 w-full border rounded-lg px-3 py-2"
                        />
                      </label>
                      <label className="block">
                        <span className="text-sm font-bold text-gray-700">シート名（任意）</span>
                        <input
                          type="text"
                          value={sheetName}
                          onChange={(e) => setSheetName(e.target.value)}
                          placeholder="例: 6月29日"
                          className="mt-1 w-full border rounded-lg px-3 py-2"
                        />
                      </label>
                    </>
                  )}
                  {googleConfigured === false && (
                    <p className="sm:col-span-2 text-amber-700 text-sm bg-amber-50 border border-amber-200 rounded-lg p-3">
                      Google 連携が未設定です。サーバーに GOOGLE_SERVICE_ACCOUNT_FILE を設定し、
                      スプレッドシートをサービスアカウントのメールに「編集者」で共有してください。
                    </p>
                  )}
                  {googleConfigured === true && (
                    <div className="sm:col-span-2 text-emerald-700 text-sm bg-emerald-50 border border-emerald-200 rounded-lg p-3 space-y-1">
                      <p className="font-bold">Google 連携: 利用可能</p>
                      {serviceAccountEmail && (
                        <p>
                          共有先サービスアカウント:
                          <span className="ml-1 font-mono text-emerald-900">{serviceAccountEmail}</span>
                        </p>
                      )}
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          <div className="p-4 bg-blue-50 border border-blue-100 rounded-lg text-sm text-blue-800">
            <p className="font-bold mb-1">{mode.label}</p>
            <p>{mode.hint}</p>
            {importMode === 'assignments' && (
              <code className="text-xs block whitespace-pre mt-2">date,student_id,student_name,subject</code>
            )}
          </div>

          {importMode !== 'google' && (
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={`border-4 border-dashed rounded-xl p-12 text-center transition-all ${
              isDragging ? 'border-blue-500 bg-blue-50' : 'border-gray-300 bg-gray-50 hover:bg-gray-100'
            }`}
          >
            <div className="text-5xl mb-4 text-blue-400">📁</div>
            <h3 className="text-lg font-bold text-gray-700 mb-2">ファイルをドロップ</h3>
            <label className="bg-white border border-gray-300 text-gray-700 px-6 py-2 rounded-lg font-bold shadow-sm cursor-pointer hover:bg-gray-50 inline-block mt-4">
              ファイルを選択
              <input
                type="file"
                className="hidden"
                accept={mode.accept}
                onChange={(e) => pickFile(e.target.files?.[0])}
              />
            </label>
          </div>
          )}

          {importMode === 'google' && (
            <button
              type="button"
              onClick={handleGoogleImport}
              disabled={isUploading || !spreadsheetRef.trim()}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white px-6 py-3 rounded-xl font-bold"
            >
              {isUploading ? 'Google から取り込み中...' : 'Google スプレッドシートから取り込む'}
            </button>
          )}

          {error && <p className="text-red-500 text-sm">{error}</p>}

          {result && (
            <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-800">
              <p className="font-bold">{result.message}</p>
            </div>
          )}

          {file && importMode !== 'google' && (
            <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-lg flex items-center justify-between gap-4 flex-wrap">
              <span className="text-emerald-700 font-bold">📄 {file.name}</span>
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
