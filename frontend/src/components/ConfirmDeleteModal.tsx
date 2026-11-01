
import { FaExclamationTriangle, FaTimes } from 'react-icons/fa';
import { useLanguage } from '../context/useLanguage';

interface ConfirmDeleteModalProps {
  isOpen: boolean;
  contractName: string;
  onConfirm: () => void;
  onCancel: () => void;
  isLoading?: boolean;
  title?: string;
  description?: string;
  warningItems?: string[];
  confirmNote?: string;
}

export default function ConfirmDeleteModal({
  isOpen,
  contractName,
  onConfirm,
  onCancel,
  isLoading = false,
  title,
  description,
  warningItems,
  confirmNote,
}: ConfirmDeleteModalProps) {
  const { t } = useLanguage();
  const resolvedTitle = title || t('delete.title');
  const resolvedDescription = description || t('delete.description');
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-dark-800 rounded-xl shadow-2xl max-w-md w-full overflow-hidden">
        <div className="px-6 py-4 border-b border-dark-200 dark:border-dark-700 bg-red-50 dark:bg-red-950 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <FaExclamationTriangle className="w-6 h-6 text-red-600 dark:text-red-400" />
            <h2 className="text-lg font-bold text-red-900 dark:text-red-300">{resolvedTitle}</h2>
          </div>
          <button
            type="button"
            onClick={onCancel}
            className="text-dark-400 dark:text-dark-500 hover:text-dark-600 dark:hover:text-dark-400 transition-colors"
            title={t('delete.close')}
          >
            <FaTimes className="w-5 h-5" />
          </button>
        </div>

        <div className="px-6 py-6">
          <p className="text-dark-900 dark:text-white font-semibold mb-4">
            {resolvedDescription}
          </p>
          <p className="text-dark-700 dark:text-dark-300 text-sm mb-4">
            <strong>{t('delete.file')}</strong> {contractName}
          </p>
          <div className="bg-red-50 dark:bg-red-950 border-l-4 border-l-red-500 p-4 rounded mb-6">
            <p className="text-sm text-dark-900 dark:text-red-300 mb-2">
              <strong>{t('delete.importantWarning')}</strong>
            </p>
            <ul className="text-sm text-dark-700 dark:text-dark-300 space-y-2">
              {(warningItems || [
                t('delete.warning1'),
                t('delete.warning2'),
                t('delete.warning3')
              ]).map((item, i) => (
                <li key={i}>• {item}</li>
              ))}
            </ul>
          </div>
          <p className="text-xs text-dark-500 dark:text-dark-400">
            {confirmNote || t('delete.confirmNote')}
          </p>
        </div>

        <div className="px-6 py-4 border-t border-dark-200 dark:border-dark-700 bg-dark-50 dark:bg-dark-700 flex gap-3 justify-end">
          <button
            type="button"
            onClick={onCancel}
            disabled={isLoading}
            className="px-4 py-2 border border-dark-300 dark:border-dark-600 text-dark-700 dark:text-dark-300 rounded-lg hover:bg-dark-100 dark:hover:bg-dark-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
          >
            {t('delete.cancel')}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isLoading}
            className="px-4 py-2 bg-red-600 hover:bg-red-700 dark:hover:bg-red-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
          >
            {isLoading ? t('delete.deleting') : t('delete.confirm')}
          </button>
        </div>
      </div>
    </div>
  );
}
