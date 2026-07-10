import { clearSession, loadSession } from './session';

/** ログインセッションの JWT を自動付与する fetch ラッパー。401 が返ったらセッションを破棄してログイン画面へ戻す。 */
export async function apiFetch(path, options = {}) {
  const session = loadSession();
  const headers = new Headers(options.headers || {});
  if (session?.token) {
    headers.set('Authorization', `Bearer ${session.token}`);
  }
  const res = await fetch(path, { ...options, headers });
  if (res.status === 401) {
    clearSession();
    if (typeof window !== 'undefined' && window.location.pathname !== '/') {
      window.location.href = '/';
    }
  }
  return res;
}
