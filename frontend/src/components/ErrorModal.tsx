
import { FaExclamationTriangle, FaTimes, FaRedo } from 'react-icons/fa';
import { useLanguage } from '../context/useLanguage';

interface ErrorModalProps {
  isOpen: boolean;
  errorMessage: string;
  filename: string;
  onClose: () => void;
  onRetry: () => void;
}

export default function ErrorModal({ isOpen, errorMessage, filename, onClose, onRetry }: ErrorModalProps) {
  const { t } = useLanguage();

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-fadeIn">
      <div className="bg-white dark:bg-dark-800 rounded-xl shadow-2xl max-w-md w-full overflow-hidden animate-slideUp">
        <div className="px-6 py-4 bg-red-50 dark:bg-red-950 border-b border-red-200 dark:border-red-900">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-red-100 dark:bg-red-900 rounded-lg">
                <FaExclamationTriangle className="w-5 h-5 text-red-600 dark:text-red-400" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-red-900 dark:text-red-300">
                  {t('error.title')}
                </h3>
                <p className="text-sm text-red-700 dark:text-red-400 mt-1">
                  {filename}
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-1 text-red-600 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900 rounded transition-colors"
              title={t('error.close')}
            >
              <FaTimes className="w-5 h-5" />
            </button>
          </div>
        </div>

        <div className="px-6 py-5">
          <div className="mb-4">
            <h4 className="text-sm font-semibold text-dark-900 dark:text-white mb-2">
              {t('error.description')}
            </h4>
            <p className="text-sm text-dark-700 dark:text-dark-300 leading-relaxed">
              {errorMessage}
            </p>
          </div>

        </div>

        <div className="px-6 py-4 bg-dark-50 dark:bg-dark-700 border-t border-dark-200 dark:border-dark-600 flex gap-3 justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-dark-700 dark:text-dark-300 bg-white dark:bg-dark-800 border border-dark-300 dark:border-dark-600 rounded-lg hover:bg-dark-50 dark:hover:bg-dark-600 transition-colors font-medium text-sm"
          >
            {t('error.close')}
          </button>
          <button
            onClick={onRetry}
            className="px-4 py-2 bg-primary-600 hover:bg-primary-700 dark:hover:bg-primary-500 text-white rounded-lg transition-colors font-medium text-sm flex items-center gap-2"
          >
            <FaRedo className="w-3 h-3" />
            {t('error.retry')}
          </button>
        </div>
      </div>
    </div>
  );
}
