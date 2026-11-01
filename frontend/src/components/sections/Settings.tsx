import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { FaCog, FaShieldAlt, FaToggleOn, FaToggleOff, FaGlobe, FaTrash, FaUser, FaTimes, FaCamera, FaUserCircle } from 'react-icons/fa';
import { useTheme } from '../../context/useTheme';
import { useLanguage } from '../../context/useLanguage';
import { useUser } from '../../context/useUser';
import { useNotifications } from '../../context/useNotifications';
import { useSettings } from '../../hooks/useSettings';
import PasswordRequirements from '../PasswordRequirements';

export default function Settings() {
  const { isDarkMode, toggleDarkMode } = useTheme();
  const { language, setLanguage, t } = useLanguage();
  const { user, updateUser, token, logout } = useUser();
  const { refreshNotifications } = useNotifications();
  const { updateSettings, isLoading: settingsLoading } = useSettings();
  const navigate = useNavigate();

  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [passwordForm, setPasswordForm] = useState({
    currentPassword: '',
    newPassword: '',
    confirmNewPassword: ''
  });
  const [passwordError, setPasswordError] = useState('');
  const [isChangingPassword, setIsChangingPassword] = useState(false);

  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteEmail, setDeleteEmail] = useState('');
  const [isDeletingAccount, setIsDeletingAccount] = useState(false);

  const [userForm, setUserForm] = useState({
    firstName: '',
    lastName: '',
    companyName: ''
  });

  const [profileImage, setProfileImage] = useState<string | null>(null);
  const [isUploadingImage, setIsUploadingImage] = useState(false);

  useEffect(() => {
    if (user) {
      setUserForm({
        firstName: user.first_name || '',
        lastName: user.last_name || '',
        companyName: user.company_name || ''
      });
      setProfileImage(user.profile_image_url || null);
    }
  }, [user]);

  const isGoogleUser = profileImage?.includes('googleusercontent.com') || false;

  const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      console.error(t('settings.invalidImageFile'));
      return;
    }

    if (file.size > 2 * 1024 * 1024) {
      console.error(t('settings.imageTooLarge'));
      return;
    }

    const reader = new FileReader();
    reader.onload = (event) => {
      const img = new Image();
      img.onload = () => {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');

        let width = img.width;
        let height = img.height;
        const maxDimension = 800;

        if (width > height && width > maxDimension) {
          height = (height * maxDimension) / width;
          width = maxDimension;
        } else if (height > maxDimension) {
          width = (width * maxDimension) / height;
          height = maxDimension;
        }

        canvas.width = width;
        canvas.height = height;

        ctx?.drawImage(img, 0, 0, width, height);

        const base64String = canvas.toDataURL('image/jpeg', 0.85);
        handleUploadImage(base64String);
      };
      img.src = event.target?.result as string;
    };
    reader.readAsDataURL(file);
  };

  const handleUploadImage = async (imageData: string) => {
    if (!token) return;

    setIsUploadingImage(true);

    try {
      const response = await fetch('/api/auth/me', {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          profile_image_url: imageData
        }),
      });

      if (response.ok) {
        const updatedUser = await response.json();
        updateUser(updatedUser);
        setProfileImage(imageData);
        refreshNotifications();
      } else {
        const errorData = await response.json().catch(() => ({}));
        console.error(t('settings.photoUpdateError'), errorData.detail);
      }
    } catch (error) {
      console.error('Error uploading image:', error);
    } finally {
      setIsUploadingImage(false);
    }
  };

  const handleRemoveImage = async () => {
    if (!token || isGoogleUser) return;

    setIsUploadingImage(true);

    try {
      const response = await fetch('/api/auth/me', {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          profile_image_url: ''
        }),
      });

      if (response.ok) {
        const updatedUser = await response.json();
        updateUser(updatedUser);
        setProfileImage(null);
        refreshNotifications();
      } else {
        console.error(t('settings.photoDeleteError'));
      }
    } catch {
      console.error(t('settings.photoDeleteError'));
    } finally {
      setIsUploadingImage(false);
    }
  };

  const handleUpdateUser = async () => {
    if (!token) return;

    try {
      const response = await fetch('/api/auth/me', {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          first_name: userForm.firstName,
          last_name: userForm.lastName,
          company_name: userForm.companyName
        }),
      });

      if (response.ok) {
        const updatedUser = await response.json();
        updateUser(updatedUser);
        refreshNotifications();
      } else {
        console.error(t('settings.infoUpdateError'));
      }
    } catch {
      console.error(t('settings.infoUpdateError'));
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordError('');

    if (!passwordForm.currentPassword || !passwordForm.newPassword || !passwordForm.confirmNewPassword) {
      setPasswordError(t('settings.allFieldsRequired'));
      return;
    }

    if (passwordForm.newPassword.length < 8) {
      setPasswordError(t('settings.passwordMinLength'));
      return;
    }

    if (passwordForm.newPassword !== passwordForm.confirmNewPassword) {
      setPasswordError(t('settings.passwordsNotMatch'));
      return;
    }

    setIsChangingPassword(true);

    try {
      const response = await fetch('/api/auth/change-password', {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          current_password: passwordForm.currentPassword,
          new_password: passwordForm.newPassword,
        }),
      });

      if (response.ok) {
        setShowPasswordModal(false);
        setPasswordForm({ currentPassword: '', newPassword: '', confirmNewPassword: '' });
      } else {
        const error = await response.json();
        if (error.detail?.includes('incorrect')) {
          setPasswordError(t('settings.incorrectPassword'));
        } else {
          setPasswordError(t('settings.passwordChangeFailed'));
        }
      }
    } catch {
      setPasswordError(t('settings.passwordChangeFailed'));
    } finally {
      setIsChangingPassword(false);
    }
  };

  const handleDeleteAccount = async () => {
    if (deleteEmail.toLowerCase() !== user?.email.toLowerCase()) {
      console.error(t('settings.emailMismatch'));
      return;
    }

    setIsDeletingAccount(true);

    try {
      const response = await fetch('/api/auth/delete-account', {
        method: 'DELETE',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ email: deleteEmail })
      });

      if (response.ok) {
        setShowDeleteModal(false);
        logout();
        navigate('/signin');
      } else {
        const data = await response.json();
        console.error('Error eliminando cuenta:', data.detail || t('settings.accountDeleteFailed'));
        setIsDeletingAccount(false);
      }
    } catch {
      console.error('Error eliminando cuenta:', t('settings.accountDeleteFailed'));
      setIsDeletingAccount(false);
    }
  };

  const handleThemeToggle = async () => {
    const newTheme = isDarkMode ? 'light' : 'dark';
    toggleDarkMode();
    await updateSettings({ theme: newTheme });
  };

  const handleLanguageChange = async (newLanguage: 'es' | 'en' | 'fr' | 'de' | 'pt') => {
    setLanguage(newLanguage);
    await updateSettings({ language: newLanguage });
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8 bg-dark-50 dark:bg-dark-900 min-h-screen">
      <div className="max-w-4xl mx-auto">
        <div className="mb-6 sm:mb-8">
          <h1 className="text-2xl sm:text-3xl font-bold text-dark-900 dark:text-white flex items-center gap-2 sm:gap-3">
            <FaCog className="w-6 h-6 sm:w-8 sm:h-8 text-primary-600" />
            {t('settings.title')}
          </h1>
          <p className="text-dark-500 dark:text-dark-400 mt-2">{t('settings.subtitle')}</p>
        </div>

        <div className="bg-white dark:bg-dark-800 rounded-xl shadow-sm mb-6 overflow-hidden border border-dark-100 dark:border-dark-700">
          <div className="px-6 py-4 border-b border-dark-200 dark:border-dark-700 bg-white dark:bg-dark-700 flex items-center gap-3">
            <FaUser className="w-5 h-5 text-primary-600 dark:text-primary-400" />
            <h2 className="text-lg sm:text-xl font-bold text-dark-900 dark:text-white">{t('settings.accountInfo')}</h2>
          </div>
          <div className="p-6 space-y-4">
            <div className="space-y-2">
              <label className="block text-sm font-semibold text-dark-700 dark:text-dark-300">
                {t('settings.profilePhoto')}
              </label>
              <div className="flex items-center gap-4">
                <div className="relative">
                  {profileImage ? (
                    <img
                      src={profileImage}
                      alt="Profile"
                      referrerPolicy="no-referrer"
                      className="w-20 h-20 rounded-full object-cover border-2 border-dark-300 dark:border-dark-600"
                    />
                  ) : (
                    <FaUserCircle className="w-20 h-20 text-dark-400 dark:text-dark-500" />
                  )}
                  {!isGoogleUser && profileImage && (
                    <button
                      onClick={handleRemoveImage}
                      disabled={isUploadingImage}
                      className="absolute -top-1 -right-1 bg-red-500 hover:bg-red-600 text-white rounded-full p-1.5 transition-colors disabled:opacity-50"
                      title={t('settings.removePhoto')}
                    >
                      <FaTimes className="w-3 h-3" />
                    </button>
                  )}
                </div>

                <div className="flex-1">
                  {isGoogleUser ? (
                    <p className="text-sm text-dark-500 dark:text-dark-400">
                      {t('settings.googlePhotoNotice')}
                    </p>
                  ) : (
                    <div className="space-y-2">
                      <label
                        htmlFor="profile-image-input"
                        className={`inline-flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors cursor-pointer ${isUploadingImage ? 'opacity-50 cursor-not-allowed' : ''
                          }`}
                      >
                        <FaCamera className="w-4 h-4" />
                        <span>{profileImage ? t('settings.changePhoto') : t('settings.uploadPhoto')}</span>
                      </label>
                      <input
                        id="profile-image-input"
                        type="file"
                        accept="image/*"
                        onChange={handleImageSelect}
                        disabled={isUploadingImage}
                        className="hidden"
                      />
                      <p className="text-xs text-dark-500 dark:text-dark-400">
                        {t('settings.photoFormats')}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <label className="block text-sm font-semibold text-dark-700 dark:text-dark-300">
                {t('settings.firstName') || 'Nombre'}
              </label>
              <input
                type="text"
                value={userForm.firstName}
                onChange={(e) => setUserForm(prev => ({ ...prev, firstName: e.target.value }))}
                className="w-full px-4 py-3 border border-dark-300 dark:border-dark-600 rounded-lg bg-white dark:bg-dark-700 text-dark-900 dark:text-white placeholder-dark-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                placeholder={t('settings.firstNamePlaceholder')}
              />
            </div>

            <div className="space-y-2">
              <label className="block text-sm font-semibold text-dark-700 dark:text-dark-300">
                {t('settings.lastName') || 'Apellido'}
              </label>
              <input
                type="text"
                value={userForm.lastName}
                onChange={(e) => setUserForm(prev => ({ ...prev, lastName: e.target.value }))}
                className="w-full px-4 py-3 border border-dark-300 dark:border-dark-600 rounded-lg bg-white dark:bg-dark-700 text-dark-900 dark:text-white placeholder-dark-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                placeholder={t('settings.lastNamePlaceholder')}
              />
            </div>

            <div className="space-y-2">
              <label className="block text-sm font-semibold text-dark-700 dark:text-dark-300">
                {t('settings.email')}
              </label>
              <input
                type="email"
                value={user?.email || ''}
                disabled
                className="w-full px-4 py-3 border border-dark-300 dark:border-dark-600 rounded-lg bg-dark-100 dark:bg-dark-900 text-dark-500 dark:text-dark-500 cursor-not-allowed"
                placeholder={t('settings.emailPlaceholder')}
              />
            </div>

            <div className="space-y-2">
              <label className="block text-sm font-semibold text-dark-700 dark:text-dark-300">
                {t('settings.companyName')}
              </label>
              <input
                type="text"
                value={userForm.companyName}
                onChange={(e) => setUserForm(prev => ({ ...prev, companyName: e.target.value }))}
                className="w-full px-4 py-3 border border-dark-300 dark:border-dark-600 rounded-lg bg-white dark:bg-dark-700 text-dark-900 dark:text-white placeholder-dark-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                placeholder={t('settings.companyNamePlaceholder')}
              />
            </div>

            <div className="pt-4">
              <button
                onClick={handleUpdateUser}
                className="w-full px-6 py-3 bg-primary-600 hover:bg-primary-700 dark:hover:bg-primary-500 text-white rounded-lg transition-colors font-medium"
              >
                {t('settings.save')}
              </button>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-dark-800 rounded-xl shadow-sm mb-6 overflow-hidden border border-dark-100 dark:border-dark-700">
          <div className="px-6 py-4 border-b border-dark-200 dark:border-dark-700 bg-white dark:bg-dark-700">
            <h2 className="text-lg sm:text-xl font-bold text-dark-900 dark:text-white">{t('settings.appearance')}</h2>
          </div>
          <div className="p-6 space-y-4">
            <div className="flex items-center justify-between p-4 border border-dark-200 dark:border-dark-700 rounded-lg hover:bg-dark-50 dark:hover:bg-dark-700 transition-colors">
              <div>
                <p className="font-semibold text-dark-900 dark:text-white">{t('settings.theme')}</p>
                <p className="text-sm text-dark-500 dark:text-dark-400">{t('settings.themeDesc')}</p>
              </div>
              <button
                onClick={handleThemeToggle}
                disabled={settingsLoading}
                className="transition-colors disabled:opacity-50"
              >
                {isDarkMode ? (
                  <FaToggleOn className="w-6 h-6 text-primary-600" />
                ) : (
                  <FaToggleOff className="w-6 h-6 text-dark-400 dark:text-dark-500" />
                )}
              </button>
            </div>

            <div className="p-4 border border-dark-200 dark:border-dark-700 rounded-lg hover:bg-dark-50 dark:hover:bg-dark-700 transition-colors">
              <label className="flex items-center gap-3 mb-2">
                <FaGlobe className="w-4 h-4 text-primary-600" />
                <span className="font-semibold text-dark-900 dark:text-white">{t('settings.language')}</span>
              </label>
              <p className="text-sm text-dark-500 dark:text-dark-400 mb-3">{t('settings.languageDesc')}</p>
              <select
                value={language}
                onChange={(e) => handleLanguageChange(e.target.value as 'es' | 'en' | 'fr' | 'de' | 'pt')}
                disabled={settingsLoading}
                className="w-full px-4 py-2 border border-dark-300 dark:border-dark-600 rounded-lg bg-white dark:bg-dark-700 text-dark-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:opacity-50"
              >
                <option value="es">Español</option>
                <option value="en">English</option>
                <option value="fr">Français</option>
                <option value="de">Deutsch</option>
                <option value="pt">Português</option>
              </select>
            </div>


          </div>
        </div>

        {/* Suscripción oculta por ahora */}

        {/* Notificaciones ocultas por ahora */}

        <div className="bg-white dark:bg-dark-800 rounded-xl shadow-sm overflow-hidden border border-dark-100 dark:border-dark-700">
          <div className="px-6 py-4 border-b border-dark-200 dark:border-dark-700 bg-white dark:bg-dark-700 flex items-center gap-3">
            <FaShieldAlt className="w-5 h-5 text-primary-600 dark:text-primary-400" />
            <h2 className="text-xl font-bold text-dark-900 dark:text-white">{t('settings.privacy')}</h2>
          </div>
          <div className="p-6 space-y-4">
            {/* Opción de analítica oculta por ahora */}
            <button
              onClick={() => setShowPasswordModal(true)}
              className="w-full mt-4 px-6 py-3 border border-red-300 dark:border-red-700 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950 rounded-lg transition-colors font-medium"
            >
              {t('settings.changePassword')}
            </button>
            <button
              onClick={() => setShowDeleteModal(true)}
              className="w-full px-6 py-3 border border-red-300 dark:border-red-700 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950 rounded-lg transition-colors font-medium flex items-center justify-center gap-2"
            >
              <FaTrash className="w-4 h-4" />
              {t('settings.deleteAccount')}
            </button>
          </div>
        </div>
      </div>

      {showPasswordModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-dark-800 rounded-xl shadow-2xl w-full max-w-md p-6">
            <h2 className="text-2xl font-bold text-dark-900 dark:text-white mb-4">
              {t('settings.changePassword')}
            </h2>

            {passwordError && (
              <div className="mb-4 p-3 bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-200 rounded-lg text-sm">
                {passwordError}
              </div>
            )}

            <form onSubmit={handleChangePassword} className="space-y-4">
              <div>
                <label className="block text-sm font-semibold text-dark-700 dark:text-dark-300 mb-2">
                  {t('settings.currentPassword')}
                </label>
                <input
                  type="password"
                  value={passwordForm.currentPassword}
                  onChange={(e) => setPasswordForm(prev => ({ ...prev, currentPassword: e.target.value }))}
                  className="w-full px-4 py-3 border border-dark-300 dark:border-dark-600 rounded-lg bg-white dark:bg-dark-700 text-dark-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  disabled={isChangingPassword}
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-dark-700 dark:text-dark-300 mb-2">
                  {t('settings.newPassword')}
                </label>
                <input
                  type="password"
                  value={passwordForm.newPassword}
                  onChange={(e) => setPasswordForm(prev => ({ ...prev, newPassword: e.target.value }))}
                  className="w-full px-4 py-3 border border-dark-300 dark:border-dark-600 rounded-lg bg-white dark:bg-dark-700 text-dark-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  disabled={isChangingPassword}
                  minLength={8}
                  required
                />
                <PasswordRequirements password={passwordForm.newPassword} />
              </div>

              <div>
                <label className="block text-sm font-semibold text-dark-700 dark:text-dark-300 mb-2">
                  {t('settings.confirmNewPassword')}
                </label>
                <input
                  type="password"
                  value={passwordForm.confirmNewPassword}
                  onChange={(e) => setPasswordForm(prev => ({ ...prev, confirmNewPassword: e.target.value }))}
                  className="w-full px-4 py-3 border border-dark-300 dark:border-dark-600 rounded-lg bg-white dark:bg-dark-700 text-dark-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  disabled={isChangingPassword}
                  minLength={8}
                  required
                />
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  type="button"
                  onClick={() => {
                    setShowPasswordModal(false);
                    setPasswordForm({ currentPassword: '', newPassword: '', confirmNewPassword: '' });
                    setPasswordError('');
                  }}
                  disabled={isChangingPassword}
                  className="flex-1 px-4 py-2 border border-dark-300 dark:border-dark-600 text-dark-700 dark:text-dark-300 rounded-lg hover:bg-dark-100 dark:hover:bg-dark-600 disabled:opacity-50 transition-colors font-medium"
                >
                  {t('settings.cancel')}
                </button>
                <button
                  type="submit"
                  disabled={isChangingPassword}
                  className="flex-1 px-4 py-2 bg-primary-600 hover:bg-primary-700 dark:hover:bg-primary-500 text-white rounded-lg disabled:opacity-50 transition-colors font-medium"
                >
                  {isChangingPassword ? t('settings.changing') : t('settings.save')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showDeleteModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white dark:bg-dark-800 rounded-xl shadow-2xl w-full max-w-md p-8">
            <h2 className="text-2xl font-bold text-red-600 dark:text-red-400 mb-2">
              {t('settings.deleteAccountTitle')}
            </h2>
            <p className="text-dark-700 dark:text-dark-300 mb-4 font-semibold">
              {t('settings.deleteAccountWarning')}
            </p>
            <p className="text-dark-600 dark:text-dark-400 mb-6 text-sm">
              {t('settings.deleteAccountDescription')}
            </p>

            <div className="bg-yellow-50 dark:bg-yellow-900/20 border-l-4 border-yellow-400 p-4 mb-6">
              <p className="text-sm text-yellow-800 dark:text-yellow-200">
                ⚠️ {t('settings.deleteAccountConfirm')}
              </p>
            </div>

            <div className="mb-6">
              <input
                type="email"
                value={deleteEmail}
                onChange={(e) => setDeleteEmail(e.target.value)}
                placeholder={user?.email}
                className="w-full px-4 py-3 border border-dark-300 dark:border-dark-600 rounded-lg bg-white dark:bg-dark-700 text-dark-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent"
                disabled={isDeletingAccount}
              />
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => {
                  setShowDeleteModal(false);
                  setDeleteEmail('');
                }}
                className="flex-1 px-4 py-3 border border-dark-300 dark:border-dark-600 text-dark-700 dark:text-dark-300 hover:bg-dark-100 dark:hover:bg-dark-600 rounded-lg transition-colors font-medium"
                disabled={isDeletingAccount}
              >
                {t('settings.cancel')}
              </button>
              <button
                onClick={handleDeleteAccount}
                disabled={isDeletingAccount || deleteEmail.toLowerCase() !== user?.email.toLowerCase()}
                className="flex-1 px-4 py-3 bg-red-600 hover:bg-red-700 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
              >
                {isDeletingAccount ? t('settings.deleting') : t('settings.deleteAccountButton')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
