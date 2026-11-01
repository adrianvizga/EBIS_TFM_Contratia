
import { FaCheck, FaTimes } from 'react-icons/fa';
import { useLanguage } from '../context/useLanguage';

interface PasswordRequirementsProps {
  password: string;
}

export default function PasswordRequirements({ password }: PasswordRequirementsProps) {
  const { t } = useLanguage();

  const requirements = [
    {
      id: 'length',
      label: t('auth.passwordReq.minLength'),
      check: password.length >= 8,
    },
    {
      id: 'uppercase',
      label: t('auth.passwordReq.uppercase'),
      check: /[A-Z]/.test(password),
    },
    {
      id: 'lowercase',
      label: t('auth.passwordReq.lowercase'),
      check: /[a-z]/.test(password),
    },
    {
      id: 'number',
      label: t('auth.passwordReq.number'),
      check: /[0-9]/.test(password),
    },
    {
      id: 'special',
      label: t('auth.passwordReq.special'),
      check: /[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?]/.test(password),
    },
  ];

  if (!password) {
    return null;
  }

  return (
    <div className="mt-3 p-4 bg-gray-50 dark:bg-dark-700 rounded-lg border border-gray-200 dark:border-dark-600">
      <p className="text-sm font-semibold text-dark-700 dark:text-dark-300 mb-3">
        {t('auth.passwordReq.title')}
      </p>
      <div className="space-y-2">
        {requirements.map((req) => (
          <div
            key={req.id}
            className="flex items-center gap-2 text-sm"
          >
            {req.check ? (
              <FaCheck className="w-4 h-4 text-green-500 flex-shrink-0" />
            ) : (
              <FaTimes className="w-4 h-4 text-red-400 flex-shrink-0" />
            )}
            <span className={req.check ? 'text-green-700 dark:text-green-400' : 'text-gray-600 dark:text-dark-400'}>
              {req.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
