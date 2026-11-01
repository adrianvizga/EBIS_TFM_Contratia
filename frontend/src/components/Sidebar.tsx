
import { useState } from 'react';
import {
  FaHome,
  FaFileContract,
  FaSearch,
  FaRobot,
  FaChevronDown,
  FaSignOutAlt,
  FaCog,
  FaUserCircle,
} from 'react-icons/fa';
import { useLanguage } from '../context/useLanguage';
import { useUser } from '../context/useUser';

interface SidebarProps {
  activeSection: string;
  onSectionChange: (section: string) => void;
}

const getRoleLabel = (role?: string | number, t?: (key: string) => string): string => {
  const tr = t || ((k: string) => k);
  if (role === '0' || role === 0) return tr('sidebar.roleAdmin');
  if (role === '1' || role === 1) return tr('sidebar.roleFree');
  if (role === '2' || role === 2) return tr('sidebar.rolePlus');
  if (role === '3' || role === 3) return tr('sidebar.rolePro');
  return tr('sidebar.roleUser');
};

export default function Sidebar({ activeSection, onSectionChange }: SidebarProps) {
  const [isProfileMenuOpen, setIsProfileMenuOpen] = useState(false);
  const { t } = useLanguage();
  const { logout, user } = useUser();

  const menuItems = [
    { id: 'dashboard', label: t('sidebar.dashboard'), icon: FaHome, disabled: false },
    { id: 'generate', label: t('sidebar.generate'), icon: FaFileContract, disabled: false },
    { id: 'analyze', label: t('sidebar.analyze'), icon: FaSearch, disabled: false },
    { id: 'agent', label: t('sidebar.agent'), icon: FaRobot, disabled: false },
  ];

  const profileMenuItems = [
    { label: t('sidebar.settings'), icon: FaCog, id: 'settings' },
    { label: t('sidebar.logout'), icon: FaSignOutAlt, id: 'logout' },
  ];

  const handleProfileMenuClick = (id: string) => {
    if (id === 'settings') {
      onSectionChange('settings');
      setIsProfileMenuOpen(false);
    } else if (id === 'logout') {
      logout();
      setIsProfileMenuOpen(false);
    }
  };

  return (
    <aside className="w-64 bg-dark-800 dark:bg-dark-950 text-white h-screen flex flex-col shadow-lg">
      <div className="p-4 sm:p-6 border-b border-dark-700 dark:border-dark-800">
        <div className="flex items-center justify-center">
          <img src="/logo-dark.png" alt="ContratIA Logo" className="h-14 sm:h-16 w-auto object-contain" />
        </div>
      </div>

      <nav className="flex-1 px-4 py-6 space-y-2">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeSection === item.id;
          const isDisabled = item.disabled;
          return (
            <button
              key={item.id}
              onClick={() => {
                if (!isDisabled) {
                  onSectionChange(item.id);
                }
              }}
              disabled={isDisabled}
              title={isDisabled ? t('sidebar.disabledSection') : ''}
              className={`w-full flex items-center px-4 py-3 rounded-lg transition-all duration-200 group ${isDisabled
                ? 'opacity-50 cursor-not-allowed text-dark-400'
                : isActive
                  ? 'bg-primary-600 text-white'
                  : 'text-dark-300 hover:bg-dark-700 hover:text-white'
                }`}
            >
              <Icon className={`w-5 h-5 ${isActive && !isDisabled ? 'text-white' : 'text-dark-400 group-hover:text-white'}`} />
              <span className="ml-3 font-medium">{item.label}</span>
            </button>
          );
        })}
      </nav>

      <div className="border-t border-dark-700 p-4">
        <div className="relative">
          <button
            onClick={() => setIsProfileMenuOpen(!isProfileMenuOpen)}
            className="w-full flex items-center px-3 py-2 rounded-lg hover:bg-dark-700 transition-all duration-200 group"
          >
            {user?.profile_image_url ? (
              <img
                src={user.profile_image_url}
                alt="Profile"
                referrerPolicy="no-referrer"
                className="w-8 h-8 rounded-full object-cover"
              />
            ) : (
              <FaUserCircle className="w-8 h-8 text-primary-400" />
            )}
            <div className="ml-3 text-left flex-1">
              <p className="text-sm font-medium text-white">
                {user ? `${user.first_name || ''} ${user.last_name || ''}`.trim() || user.email : t('sidebar.userFallback')}
              </p>
              <p className="text-xs text-dark-400">{getRoleLabel(user?.role, t)}</p>
            </div>
            <FaChevronDown
              className={`w-4 h-4 text-dark-400 transition-transform duration-200 ${isProfileMenuOpen ? 'rotate-180' : ''
                }`}
            />
          </button>

          {isProfileMenuOpen && (
            <div className="absolute bottom-16 left-0 right-0 bg-dark-700 rounded-lg shadow-lg z-50">
              {profileMenuItems.map((item, index) => {
                const Icon = item.icon;
                return (
                  <button
                    key={index}
                    onClick={() => handleProfileMenuClick(item.id)}
                    className="w-full flex items-center px-4 py-2 text-sm text-dark-300 hover:text-white hover:bg-dark-600 transition-colors duration-200 first:rounded-t-lg last:rounded-b-lg"
                  >
                    <Icon className="w-4 h-4 mr-3" />
                    {item.label}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
