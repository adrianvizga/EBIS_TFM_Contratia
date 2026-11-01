import { FaCheckCircle, FaClock, FaExclamationCircle } from 'react-icons/fa';

type Translate = (key: string) => string;

export function ContractStatusBadge({ status, t }: { status: string; t: Translate }) {
  const variants: Record<string, { className: string; label: string; icon?: 'check' | 'clock' | 'spinner' | 'error' }> = {
    completed: { className: 'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300', label: 'analyze.completed', icon: 'check' },
    pending: { className: 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300', label: 'analyze.pending', icon: 'clock' },
    analyzing: { className: 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300', label: 'analyze.processing', icon: 'spinner' },
    error: { className: 'bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300', label: 'analyze.failed', icon: 'error' },
    failed: { className: 'bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300', label: 'analyze.failed', icon: 'error' },
  };
  const variant = variants[status];
  if (!variant) return null;
  return (
    <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium ${variant.className}`}>
      {variant.icon === 'check' && <FaCheckCircle className="w-3 h-3" />}
      {variant.icon === 'clock' && <FaClock className="w-3 h-3" />}
      {variant.icon === 'error' && <FaExclamationCircle className="w-3 h-3" />}
      {variant.icon === 'spinner' && <span className="w-3 h-3 border-2 border-blue-700 dark:border-blue-300 border-t-transparent rounded-full animate-spin" />}
      {t(variant.label)}
    </span>
  );
}

export function ContractRiskBadge({ level, status, t }: { level: string; status?: string; t: Translate }) {
  if (status !== 'completed') return null;
  const variants: Record<string, { className: string; label: string }> = {
    high: { className: 'bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300', label: 'analyze.riskHigh' },
    medium: { className: 'bg-yellow-100 dark:bg-yellow-900 text-yellow-700 dark:text-yellow-300', label: 'analyze.riskMedium' },
    low: { className: 'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300', label: 'analyze.riskLow' },
  };
  const variant = variants[level];
  return variant ? <span className={`px-3 py-1 rounded-full text-sm font-medium ${variant.className}`}>{t(variant.label)}</span> : null;
}
