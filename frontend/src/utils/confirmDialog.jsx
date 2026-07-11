import React, { useEffect, useRef } from 'react';
import { createRoot } from 'react-dom/client';

function ConfirmDialog({ title, message, confirmLabel, destructive, onResolve }) {
  const cancelRef = useRef(null);

  useEffect(() => {
    cancelRef.current?.focus();
    const onKeyDown = (e) => {
      if (e.key === 'Escape') onResolve(false);
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [onResolve]);

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40 p-4"
      onClick={() => onResolve(false)}
    >
      <div
        role="alertdialog"
        aria-modal="true"
        aria-label={title}
        className="w-full max-w-sm bg-white rounded-2xl shadow-xl p-5"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-base font-bold text-gray-900">{title}</h2>
        {message && (
          <p className="text-sm text-gray-600 mt-2 whitespace-pre-line">{message}</p>
        )}
        <div className="flex gap-2 mt-5">
          <button
            ref={cancelRef}
            type="button"
            onClick={() => onResolve(false)}
            className="flex-1 py-2.5 rounded-xl border border-gray-300 bg-white text-gray-700 font-bold text-sm hover:bg-gray-50"
          >
            キャンセル
          </button>
          <button
            type="button"
            onClick={() => onResolve(true)}
            className={`flex-1 py-2.5 rounded-xl text-white font-bold text-sm ${
              destructive ? 'bg-red-600 hover:bg-red-700' : 'bg-blue-600 hover:bg-blue-700'
            }`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * window.confirm の置き換え。await confirmDialog({...}) で true/false を返す。
 * 削除などの破壊的操作は destructive: true で確認ボタンを赤にする。
 */
export function confirmDialog({ title, message = '', confirmLabel = 'OK', destructive = false }) {
  return new Promise((resolve) => {
    const host = document.createElement('div');
    document.body.appendChild(host);
    const root = createRoot(host);
    const onResolve = (result) => {
      root.unmount();
      host.remove();
      resolve(result);
    };
    root.render(
      <ConfirmDialog
        title={title}
        message={message}
        confirmLabel={confirmLabel}
        destructive={destructive}
        onResolve={onResolve}
      />,
    );
  });
}
