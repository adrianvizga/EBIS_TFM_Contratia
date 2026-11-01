
import { useState, useEffect, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useLanguage } from '../context/useLanguage';
import { useUser } from '../context/useUser';
import { googleConfig } from '../config/google';

export default function SignIn() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showForgotPassword, setShowForgotPassword] = useState(false);
  const [resetEmail, setResetEmail] = useState('');
  const [resetSuccess, setResetSuccess] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const navigate = useNavigate();
  const { t } = useLanguage();
  const { login, loginWithGoogle, isAuthenticated } = useUser();
  const googleButtonRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/panel', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  useEffect(() => {
    const savedEmail = localStorage.getItem('rememberedEmail');
    const savedRememberMe = localStorage.getItem('rememberMeChecked');

    if (savedEmail) {
      setEmail(savedEmail);
    }

    if (savedRememberMe === 'true') {
      setRememberMe(true);
    }
  }, []);

  useEffect(() => {
    if (!googleConfig.isConfigured || !window.google || !googleButtonRef.current) {
      return;
    }

    const handleCredentialResponse = async (response: GoogleCredentialResponse) => {
      setError('');
      setIsLoading(true);
      try {
        if (!response.credential) {
          setError('Google authentication failed');
          setIsLoading(false);
          return;
        }
        await loginWithGoogle(response.credential, rememberMe);
        navigate('/panel');
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'auth.loginFailed';
        setError(errorMessage.startsWith('auth.') ? t(errorMessage) : errorMessage);
        console.error('Google login error:', err);
      } finally {
        setIsLoading(false);
      }
    };

    try {
      const clientId = googleConfig.clientId.trim();

      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: handleCredentialResponse,
        auto_select: false,
        cancel_on_tap_outside: false,
        itp_support: false,
      });

      window.google.accounts.id.cancel();

      window.google.accounts.id.renderButton(googleButtonRef.current, {
        type: 'standard',
        size: 'large',
        text: 'signin_with',
        locale: 'es',
        theme: 'outline',
      });
    } catch (err) {
      console.error('Failed to initialize Google Sign-In:', err);
    }
  }, [loginWithGoogle, navigate, rememberMe, t]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!email.trim()) {
      setError(t('auth.emailRequired'));
      return;
    }

    if (!password.trim()) {
      setError(t('auth.passwordRequired'));
      return;
    }

    setIsLoading(true);
    try {
      await login(email, password, rememberMe);
      navigate('/panel');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'auth.loginFailed';
      setError(errorMessage.startsWith('auth.') ? t(errorMessage) : errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleForgotPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsResetting(true);

    try {
      const response = await fetch('/api/auth/forgot-password', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email: resetEmail }),
      });

      if (response.ok) {
        await response.json();
        setResetSuccess(true);
        setError('');
      } else {
        const data = await response.json();
        if (data.detail && typeof data.detail === 'string') {
          if (data.detail.includes('No existe una cuenta') || data.detail.includes('No account exists')) {
            setError(t('auth.emailNotFound'));
          } else {
            setError(data.detail);
          }
        } else {
          setError(t('auth.passwordResetFailed'));
        }
      }
    } catch (err) {
      console.error('Error in forgot password:', err);
      setError(t('auth.passwordResetFailed'));
    } finally {
      setIsResetting(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-400 via-primary-500 to-primary-600 flex items-center justify-center p-4">
      <div className="bg-white dark:bg-dark-800 rounded-2xl shadow-2xl w-full max-w-md p-8">
        <div className="text-center mb-8">
          <div className="flex items-center justify-center mb-6">
            <img src="/logo.png" alt="ContratIA" className="h-20 sm:h-24 w-auto object-contain dark:hidden" />
            <img src="/logo-dark.png" alt="ContratIA" className="h-20 sm:h-24 w-auto object-contain hidden dark:block" />
          </div>
          <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-dark-800 dark:text-dark-100">
            {t('auth.signIn')}
          </h2>
        </div>

        {error && (
          <div className="mb-6 p-3 bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-200 rounded-lg text-sm">
            {error}
          </div>
        )}

        {googleConfig.isConfigured ? (
          <div ref={googleButtonRef} className="w-full flex justify-center mb-6"></div>
        ) : null}

        <div className="relative mb-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-dark-300 dark:border-dark-600"></div>
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-4 bg-white dark:bg-dark-800 text-dark-500 dark:text-dark-400">
              {t('auth.or')}
            </span>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-semibold text-dark-700 dark:text-dark-300 mb-2">
              {t('auth.email')}
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder={t('auth.emailPlaceholder')}
              className="w-full px-4 py-3 border border-dark-300 dark:border-dark-600 rounded-lg bg-white dark:bg-dark-700 text-dark-900 dark:text-white placeholder-dark-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:opacity-50"
              disabled={isLoading}
              required
            />
          </div>

          <div>
            <label className="block text-sm font-semibold text-dark-700 dark:text-dark-300 mb-2">
              {t('auth.password')}
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={t('auth.passwordPlaceholder')}
              className="w-full px-4 py-3 border border-dark-300 dark:border-dark-600 rounded-lg bg-white dark:bg-dark-700 text-dark-900 dark:text-white placeholder-dark-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:opacity-50"
              disabled={isLoading}
              required
            />
          </div>

          <div className="flex items-center justify-between text-sm">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={rememberMe}
                onChange={(e) => {
                  const checked = e.target.checked;
                  setRememberMe(checked);
                  localStorage.setItem('rememberMeChecked', checked.toString());
                }}
                className="w-4 h-4 text-primary-600 border-dark-300 rounded focus:ring-primary-500 disabled:opacity-50"
                disabled={isLoading}
              />
              <span className="text-dark-600 dark:text-dark-400">
                {t('auth.rememberMe')}
              </span>
            </label>
            <a
              href="#"
              onClick={(e) => {
                e.preventDefault();
                setShowForgotPassword(true);
                setError('');
              }}
              className="text-primary-600 hover:text-primary-700 font-medium"
            >
              {t('auth.forgotPassword')}
            </a>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-primary-600 hover:bg-primary-700 dark:hover:bg-primary-500 text-white font-semibold py-3 rounded-lg transition-colors flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? 'Loading...' : t('auth.continue')}
            <span>▸</span>
          </button>
        </form>

        <p className="text-center text-sm text-dark-600 dark:text-dark-400 mt-6">
          {t('auth.noAccount')}{' '}
          <Link to="/signup" className="text-primary-600 hover:text-primary-700 font-semibold">
            {t('auth.signUp')}
          </Link>
        </p>
      </div>

      {showForgotPassword && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white dark:bg-dark-800 rounded-xl shadow-2xl w-full max-w-md p-8">
            <h2 className="text-2xl font-bold text-dark-900 dark:text-white mb-2">
              {t('auth.resetPasswordTitle')}
            </h2>
            <p className="text-dark-600 dark:text-dark-400 mb-6 text-sm">
              {t('auth.resetPasswordDesc')}
            </p>

            {resetSuccess ? (
              <div className="space-y-4">
                <div className="p-4 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded-lg">
                  <p className="font-semibold mb-1">{t('auth.resetLinkSent')}</p>
                  <p className="text-sm">{t('auth.resetLinkSentDesc')}</p>
                </div>
                <button
                  onClick={() => {
                    setShowForgotPassword(false);
                    setResetSuccess(false);
                    setResetEmail('');
                    setError('');
                  }}
                  className="w-full bg-primary-600 hover:bg-primary-700 dark:hover:bg-primary-500 text-white font-semibold py-3 rounded-lg transition-colors"
                >
                  {t('auth.backToLogin')}
                </button>
              </div>
            ) : (
              <form onSubmit={handleForgotPassword} className="space-y-4">
                {error && (
                  <div className="p-3 bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-200 rounded-lg text-sm">
                    {error}
                  </div>
                )}

                <div>
                  <label className="block text-sm font-semibold text-dark-700 dark:text-dark-300 mb-2">
                    {t('auth.email')}
                  </label>
                  <input
                    type="email"
                    value={resetEmail}
                    onChange={(e) => setResetEmail(e.target.value)}
                    placeholder={t('auth.emailPlaceholder')}
                    className="w-full px-4 py-3 border border-dark-300 dark:border-dark-600 rounded-lg bg-white dark:bg-dark-700 text-dark-900 dark:text-white placeholder-dark-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:opacity-50"
                    disabled={isResetting}
                    required
                  />
                </div>

                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={() => {
                      setShowForgotPassword(false);
                      setError('');
                      setResetEmail('');
                    }}
                    className="flex-1 border border-dark-300 dark:border-dark-600 text-dark-700 dark:text-dark-300 hover:bg-dark-100 dark:hover:bg-dark-600 font-semibold py-3 rounded-lg transition-colors disabled:opacity-50"
                    disabled={isResetting}
                  >
                    {t('auth.cancel')}
                  </button>
                  <button
                    type="submit"
                    disabled={isResetting}
                    className="flex-1 bg-primary-600 hover:bg-primary-700 text-white font-semibold py-3 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isResetting ? 'Loading...' : t('auth.sendResetLink')}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
