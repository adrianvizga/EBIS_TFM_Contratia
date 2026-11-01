import { createContext, useState, useCallback, type ReactNode } from 'react';

export type ToastType = 'error' | 'success' | 'warning';

interface ToastItem {
  id: string;
  message: string;
  type: ToastType;
}

interface ToastContextValue {
  showToast: (message: string, type?: ToastType) => void;
}

export const ToastContext = createContext<ToastContextValue>({ showToast: () => {} });

const STYLES: Record<ToastType, string> = {
  error:   'bg-red-600 text-white',
  success: 'bg-green-600 text-white',
  warning: 'bg-amber-500 text-white',
};

const ICONS: Record<ToastType, string> = {
  error:   '✕',
  success: '✓',
  warning: '⚠',
};

function ToastList({ toasts, onClose }: { toasts: ToastItem[]; onClose: (id: string) => void }) {
  if (toasts.length === 0) return null;
  return (
    <div
      aria-live="assertive"
      className="fixed bottom-5 right-5 z-[9999] flex flex-col gap-3 max-w-sm w-full pointer-events-none"
    >
      {toasts.map((toast) => (
        <div
          key={toast.id}
          role="alert"
          className={`pointer-events-auto flex items-start gap-3 rounded-xl px-4 py-3 shadow-lg
            ${STYLES[toast.type]} animate-slide-in`}
        >
          <span className="mt-0.5 text-base font-bold shrink-0">{ICONS[toast.type]}</span>
          <p className="flex-1 text-sm leading-snug">{toast.message}</p>
          <button
            onClick={() => onClose(toast.id)}
            aria-label="Cerrar notificación"
            className="shrink-0 ml-1 opacity-80 hover:opacity-100 text-lg leading-none"
          >
            ×
          </button>
        </div>
      ))}
    </div>
  );
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const showToast = useCallback(
    (message: string, type: ToastType = 'error') => {
      const id = crypto.randomUUID();
      setToasts((prev) => [...prev, { id, message, type }]);
      setTimeout(() => removeToast(id), 5000);
    },
    [removeToast],
  );

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <ToastList toasts={toasts} onClose={removeToast} />
    </ToastContext.Provider>
  );
}
