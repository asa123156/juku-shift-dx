import React, { useEffect } from 'react';

/**
 * 画面下部固定のトースト。message が変わるたびに表示し、数秒後に onClose で消える。
 * 長いページでも操作結果が視界に入るようにする（インライン表示の補完）。
 */
export function Toast({ message, type = 'success', duration = 4000, onClose }) {
  useEffect(() => {
    if (!message) return undefined;
    const timer = window.setTimeout(onClose, duration);
    return () => window.clearTimeout(timer);
  }, [message, duration, onClose]);

  if (!message) return null;

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-[70] px-4 w-full max-w-md pointer-events-none">
      <div
        role="status"
        aria-live="polite"
        className={`pointer-events-auto flex items-start gap-2 rounded-xl shadow-lg px-4 py-3 text-sm font-bold text-white ${
          type === 'error' ? 'bg-red-600' : 'bg-gray-900'
        }`}
      >
        <span aria-hidden="true">{type === 'error' ? '⚠️' : '✓'}</span>
        <span className="flex-1">{message}</span>
        <button
          type="button"
          onClick={onClose}
          aria-label="閉じる"
          className="shrink-0 -m-1 p-1 text-white/70 hover:text-white"
        >
          ×
        </button>
      </div>
    </div>
  );
}
