
import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { useLanguage } from '../context/useLanguage';
import PasswordRequirements from '../components/PasswordRequirements';

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  const { t } = useLanguage();
  const token = searchParams.get('token');

  useEffect(() => {
    if (!token) {
      setError(t('auth.invalidResetToken'));
    }
  }, [token, t]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!password.trim()) {
      setError(t('auth.passwordRequired'));
      return;
    }

    if (password.length < 8) {
      setError(t('auth.passwordMinLength'));
      return;
    }

    if (password !== confirmPassword) {
      setError(t('auth.passwordMismatch'));
      return;
    }

    if (!token) {
      setError(t('auth.invalidResetToken'));
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch('/api/auth/reset-password', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          token: token,
          new_password: password,
        }),
      });

      if (response.ok) {
        setSuccess(true);
        setTimeout(() => {
          navigate('/signin');
        }, 3000);
      } else {
        const data = await response.json();
        if (data.detail?.includes('Invalid or expired')) {
          setError(t('auth.invalidResetToken'));
        } else {
          setError(data.detail || t('auth.passwordResetFailed'));
        }
      }
    } catch {
      setError(t('auth.passwordResetFailed'));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-400 via-primary-500 to-primary-600 flex items-center justify-center p-4">
      <div className="bg-white dark:bg-dark-800 rounded-2xl shadow-2xl w-full max-w-md p-8">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-primary-500 rounded-full mb-4">
            <span className="text-3xl font-bold text-white">C</span>
          </div>
          <h1 className="text-3xl font-bold text-dark-900 dark:text-white mb-2">
            {t('auth.resetPasswordTitle')}
          </h1>
          <p className="text-dark-600 dark:text-dark-400">
            {t('auth.enterNewPassword')}
          </p>
        </div>

        {success ? (
          <div className="space-y-4">
            <div className="p-4 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded-lg">
              <p className="font-semibold mb-1">{t('auth.passwordResetSuccess')}</p>
              <p className="text-sm">{t('auth.redirecting')}...</p>
            </div>
            <Link
              to="/signin"
              className="block w-full text-center bg-primary-600 hover:bg-primary-700 dark:hover:bg-primary-500 text-white font-semibold py-3 rounded-lg transition-colors"
            >
              {t('auth.backToLogin')}
            </Link>
          </div>
        ) : (
          <>
            {error && (
              <div className="mb-6 p-3 bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-200 rounded-lg text-sm">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-semibold text-dark-700 dark:text-dark-300 mb-2">
                  {t('auth.newPassword')}
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder={t('auth.passwordPlaceholder')}
                  className="w-full px-4 py-3 border border-dark-300 dark:border-dark-600 rounded-lg bg-white dark:bg-dark-700 text-dark-900 dark:text-white placeholder-dark-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:opacity-50"
                  disabled={isLoading || !token}
                  required
                />
                {password && <PasswordRequirements password={password} />}
              </div>

              <div>
                <label className="block text-sm font-semibold text-dark-700 dark:text-dark-300 mb-2">
                  {t('auth.confirmPassword')}
                </label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder={t('auth.confirmPasswordPlaceholder')}
                  className="w-full px-4 py-3 border border-dark-300 dark:border-dark-600 rounded-lg bg-white dark:bg-dark-700 text-dark-900 dark:text-white placeholder-dark-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:opacity-50"
                  disabled={isLoading || !token}
                  required
                />
              </div>

              <button
                type="submit"
                disabled={isLoading || !token}
                className="w-full bg-primary-600 hover:bg-primary-700 text-white font-semibold py-3 rounded-lg transition-colors flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? 'Loading...' : t('auth.resetPassword')}
              </button>
            </form>

            <p className="text-center text-sm text-dark-600 dark:text-dark-400 mt-6">
              <Link to="/signin" className="text-primary-600 hover:text-primary-700 font-semibold">
                {t('auth.backToLogin')}
              </Link>
            </p>
          </>
        )}
      </div>
    </div>
  );
}
