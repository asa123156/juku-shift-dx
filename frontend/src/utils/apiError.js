/** FastAPI のエラーレスポンスをユーザー向けメッセージに変換する */
export async function parseApiError(res, fallback = 'リクエストに失敗しました') {
  if (res.status === 404) {
    return 'APIに接続できません。バックエンドが起動しているか確認してください（cd backend && uvicorn main:app --reload --port 8000）';
  }
  if (res.status >= 502) {
    return 'バックエンドに接続できません。サーバーが起動しているか確認してください';
  }
  try {
    const body = await res.json();
    const detail = body?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      return detail.map((d) => d.msg || JSON.stringify(d)).join(' / ');
    }
    if (detail && typeof detail === 'object') return JSON.stringify(detail);
    return fallback;
  } catch {
    return fallback;
  }
}
