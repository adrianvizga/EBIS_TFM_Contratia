
import { useState, useEffect, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useLanguage } from '../context/useLanguage';
import { useUser } from '../context/useUser';
import PasswordRequirements from '../components/PasswordRequirements';
import LegalModal from '../components/LegalModal';
import { googleConfig } from '../config/google';
import { PRIVACY_VERSION, TERMS_VERSION } from '../config/legal';

export default function SignUp() {
  const [formData, setFormData] = useState({
    firstName: '',
    lastName: '',
    email: '',
    password: '',
    confirmPassword: '',
    acceptTerms: false,
  });
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [legalModal, setLegalModal] = useState<'terms' | 'privacy' | null>(null);
  const navigate = useNavigate();
  const { t } = useLanguage();
  const { register, loginWithGoogle, isAuthenticated } = useUser();
  const googleButtonRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/panel', { replace: true });
    }
  }, [isAuthenticated, navigate]);

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
        await loginWithGoogle(response.credential, false, {
          terms_accepted: true,
          terms_version: TERMS_VERSION,
          privacy_version: PRIVACY_VERSION,
        });
        navigate('/panel');
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'auth.registrationFailed';
        setError(errorMessage.startsWith('auth.') ? t(errorMessage) : errorMessage);
        console.error('Google signup error:', err);
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
        text: 'signup_with',
        locale: 'es',
        theme: 'outline',
      });
    } catch (err) {
      console.error('Failed to initialize Google Sign-In:', err);
    }
  }, [formData.acceptTerms, loginWithGoogle, navigate, t]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!formData.firstName.trim()) {
      setError(t('auth.firstNameRequired'));
      return;
    }
    if (!formData.lastName.trim()) {
      setError(t('auth.lastNameRequired'));
      return;
    }
    if (!formData.email.trim()) {
      setError(t('auth.emailRequired'));
      return;
    }
    if (formData.password.length < 8) {
      setError(t('auth.passwordMinLength'));
      return;
    }
    if (formData.password !== formData.confirmPassword) {
      setError(t('auth.passwordMismatch'));
      return;
    }
    if (!formData.acceptTerms) {
      setError(t('auth.acceptTermsRequired'));
      return;
    }

    setIsLoading(true);
    try {
      await register({
        firstName: formData.firstName,
        lastName: formData.lastName,
        email: formData.email,
        password: formData.password,
        company_name: '',
        terms_accepted: true as const,
        terms_version: TERMS_VERSION,
        privacy_version: PRIVACY_VERSION,
      });

      navigate('/panel');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'auth.registrationFailed';
      setError(errorMessage.startsWith('auth.') ? t(errorMessage) : errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-400 via-primary-500 to-primary-600 flex items-center justify-center p-4">
      <LegalModal type={legalModal} onClose={() => setLegalModal(null)} />
      <div className="bg-white dark:bg-dark-800 rounded-2xl shadow-2xl w-full max-w-md p-8">
        <div className="text-center mb-8">
          <div className="flex items-center justify-center mb-6">
            <img src="/logo.png" alt="ContratIA" className="h-20 sm:h-24 w-auto object-contain dark:hidden" />
            <img src="/logo-dark.png" alt="ContratIA" className="h-20 sm:h-24 w-auto object-contain hidden dark:block" />
          </div>
          <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-dark-800 dark:text-dark-100">
            {t('auth.createAccount')}
          </h2>
        </div>

        {error && (
          <div className="mb-6 p-3 bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-200 rounded-lg text-sm">
            {error}
          </div>
        )}

        {googleConfig.isConfigured ? (
          <div className="mb-6">
            <div ref={googleButtonRef} className="w-full flex justify-center mb-4"></div>
            <p className="text-center text-xs text-dark-400 dark:text-dark-500 leading-relaxed">
              {t('auth.googleSignupConsent')}{' '}
              <button type="button" onClick={() => setLegalModal('terms')} className="text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300">
                {t('auth.termsOfService')}
              </button>{' '}
              {t('auth.and')}{' '}
              <button type="button" onClick={() => setLegalModal('privacy')} className="text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300">
                {t('auth.privacyPolicy')}
              </button>
            </p>
          </div>
        ) : (
          <div className="w-full mb-6 p-3 bg-gray-100 dark:bg-dark-700 rounded-lg text-center text-sm text-gray-600 dark:text-gray-400">
            Google Sign-In not configured
          </div>
        )}

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
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-semibold text-dark-700 dark:text-dark-300 mb-2">
                {t('auth.firstName')}
              </label>
              <input
                type="text"
                name="firstName"
                value={formData.firstName}
                onChange={handleChange}
                placeholder={t('auth.firstNamePlaceholder')}
                className="w-full px-4 py-3 border border-dark-300 dark:border-dark-600 rounded-lg bg-white dark:bg-dark-700 text-dark-900 dark:text-white placeholder-dark-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:opacity-50"
                disabled={isLoading}
                required
              />
            </div>
            <div>
              <label className="block text-sm font-semibold text-dark-700 dark:text-dark-300 mb-2">
                {t('auth.lastName')}
              </label>
              <input
                type="text"
                name="lastName"
                value={formData.lastName}
                onChange={handleChange}
                placeholder={t('auth.lastNamePlaceholder')}
                className="w-full px-4 py-3 border border-dark-300 dark:border-dark-600 rounded-lg bg-white dark:bg-dark-700 text-dark-900 dark:text-white placeholder-dark-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:opacity-50"
                disabled={isLoading}
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-semibold text-dark-700 dark:text-dark-300 mb-2">
              {t('auth.email')}
            </label>
            <input
              type="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
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
              name="password"
              value={formData.password}
              onChange={handleChange}
              placeholder={t('auth.passwordPlaceholder')}
              className="w-full px-4 py-3 border border-dark-300 dark:border-dark-600 rounded-lg bg-white dark:bg-dark-700 text-dark-900 dark:text-white placeholder-dark-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:opacity-50"
              disabled={isLoading}
              required
            />
            <PasswordRequirements password={formData.password} />
          </div>

          <div>
            <label className="block text-sm font-semibold text-dark-700 dark:text-dark-300 mb-2">
              {t('auth.confirmPassword')}
            </label>
            <input
              type="password"
              name="confirmPassword"
              value={formData.confirmPassword}
              onChange={handleChange}
              placeholder={t('auth.confirmPasswordPlaceholder')}
              className="w-full px-4 py-3 border border-dark-300 dark:border-dark-600 rounded-lg bg-white dark:bg-dark-700 text-dark-900 dark:text-white placeholder-dark-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:opacity-50"
              disabled={isLoading}
              required
            />
          </div>

          <div className="flex items-start gap-2">
            <input
              type="checkbox"
              name="acceptTerms"
              checked={formData.acceptTerms}
              onChange={handleChange}
              className="w-4 h-4 mt-1 text-primary-600 border-dark-300 rounded focus:ring-primary-500 disabled:opacity-50"
              disabled={isLoading}
              required
            />
            <label className="text-sm text-dark-600 dark:text-dark-400">
              {t('auth.acceptTerms')}{' '}
              <button type="button" onClick={() => setLegalModal('terms')} className="text-primary-600 hover:text-primary-700 font-medium focus:outline-none focus:ring-2 focus:ring-primary-500 rounded">
                {t('auth.termsOfService')}
              </button>{' '}
              {t('auth.and')}{' '}
              <button type="button" onClick={() => setLegalModal('privacy')} className="text-primary-600 hover:text-primary-700 font-medium focus:outline-none focus:ring-2 focus:ring-primary-500 rounded">
                {t('auth.privacyPolicy')}
              </button>
            </label>
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
          {t('auth.hasAccount')}{' '}
          <Link to="/signin" className="text-primary-600 hover:text-primary-700 font-semibold">
            {t('auth.signIn')}
          </Link>
        </p>
      </div>
    </div>
  );
}
