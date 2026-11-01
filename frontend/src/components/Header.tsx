
import { useState, useEffect, useCallback } from 'react';
import { FaBell, FaCheck, FaTimes, FaBars, FaTrash } from 'react-icons/fa';
import { useLanguage } from '../context/useLanguage';
import { formatRelative } from '../utils/formatDate';
import { useUser } from '../context/useUser';
import { useNotifications } from '../context/useNotifications';
import { useAuthFetch } from '../hooks/useAuthFetch';

interface HeaderProps {
  title: string;
  subtitle?: string;
  onMenuClick?: () => void;
}

interface Notification {
  id: string;
  title: string;
  message: string;
  created_at: string;
  is_read: boolean;
  notification_type: 'info' | 'warning' | 'success' | 'error';
}

export default function Header({ title, subtitle, onMenuClick }: HeaderProps) {
  const [isNotificationOpen, setIsNotificationOpen] = useState(false);
  const [isFullNotificationViewOpen, setIsFullNotificationViewOpen] = useState(false);
  const { t, language } = useLanguage();
  const { user, token } = useUser();
  const { refreshTrigger } = useNotifications();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [, setIsLoadingNotifications] = useState(false);
  const authFetch = useAuthFetch();

  const loadNotifications = useCallback(async () => {
    if (!token) return;

    setIsLoadingNotifications(true);
    try {
      const response = await authFetch('/api/notifications');

      if (response.ok) {
        const data = await response.json();
        setNotifications(data);
      }
    } catch (error) {
      console.error('Error loading notifications:', error);
    } finally {
      setIsLoadingNotifications(false);
    }
  }, [authFetch, token]);

  useEffect(() => {
    if (user && token) {
      loadNotifications();
    }
  }, [loadNotifications, token, user]);

  useEffect(() => {
    if (user && token) {
      loadNotifications();
    }
  }, [loadNotifications, refreshTrigger, token, user]);

  const unreadCount = notifications.filter(n => !n.is_read).length;

  const markAllAsRead = async () => {
    if (!token) return;

    try {
      const response = await authFetch('/api/notifications/mark-all-read', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        setNotifications(notifications.map(n => ({ ...n, is_read: true })));
      }
    } catch (error) {
      console.error('Error marking notifications as read:', error);
    }
  };

  const markAsRead = async (notificationId: string) => {
    if (!token) return;

    try {
      const response = await authFetch(`/api/notifications/${notificationId}/read`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        setNotifications(
          notifications.map(n =>
            n.id === notificationId ? { ...n, is_read: true } : n
          )
        );
      }
    } catch (error) {
      console.error('Error marking notification as read:', error);
    }
  };

  const deleteNotification = async (notificationId: string) => {
    if (!token) return;

    try {
      const response = await authFetch(`/api/notifications/${notificationId}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        setNotifications(notifications.filter(n => n.id !== notificationId));
      }
    } catch (error) {
      console.error('Error deleting notification:', error);
    }
  };

  const deleteAllNotifications = async () => {
    if (!token) return;

    try {
      const response = await authFetch('/api/notifications/delete-all', {
        method: 'DELETE',
      });

      if (response.ok) {
        setNotifications([]);
      }
    } catch (error) {
      console.error('Error deleting all notifications:', error);
    }
  };

  const formatDate = (dateString: string) => formatRelative(dateString, language, t);

  const getNotificationColor = (type: string) => {
    switch (type) {
      case 'success':
        return 'border-l-green-500';
      case 'warning':
        return 'border-l-yellow-500';
      case 'error':
        return 'border-l-red-500';
      default:
        return 'border-l-blue-500';
    }
  };

  return (
    <>
      <div className="bg-white dark:bg-dark-800 border-b border-dark-200 dark:border-dark-700">
        <div className="px-4 sm:px-6 lg:px-8 py-3 sm:py-[14px]">
          <div className="flex items-center justify-between gap-3">
            <button
              onClick={onMenuClick}
              className="lg:hidden p-2 -ml-2 rounded-lg text-dark-600 dark:text-dark-400 hover:bg-dark-100 dark:hover:bg-dark-700 transition-colors flex-shrink-0"
              aria-label="Abrir menú"
            >
              <FaBars className="w-5 h-5" />
            </button>

            <div className="flex-1 min-w-0">
              <h1 className="text-lg sm:text-xl lg:text-2xl xl:text-3xl font-bold text-dark-900 dark:text-white leading-tight truncate">
                {title}
              </h1>
              {subtitle && (
                <p className="text-dark-500 dark:text-dark-400 mt-0.5 sm:mt-1 text-xs sm:text-sm leading-tight truncate">
                  {subtitle}
                </p>
              )}
            </div>

            <div className="relative flex-shrink-0 flex items-center gap-2">
              <button
                onClick={() => setIsNotificationOpen(!isNotificationOpen)}
                className="p-2 sm:p-3 rounded-lg text-dark-400 dark:text-dark-500 hover:bg-dark-100 dark:hover:bg-dark-700 hover:text-dark-600 dark:hover:text-dark-300 transition-all duration-200 relative z-50"
                aria-label={t('header.notifications')}
              >
                <FaBell className={`w-5 h-5 sm:w-6 sm:h-6 ${unreadCount > 0 ? 'animate-[ring_2s_ease-in-out_infinite]' : ''}`} />
                {unreadCount > 0 && (
                  <span className="absolute top-1 right-1 w-2.5 h-2.5 sm:w-3 sm:h-3 bg-red-500 rounded-full border-2 border-white dark:border-dark-800 animate-pulse"></span>
                )}
              </button>

              {isNotificationOpen && (
                <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-white dark:bg-dark-800 rounded-lg shadow-2xl z-50 border border-dark-200 dark:border-dark-700 max-h-[calc(100vh-100px)] overflow-hidden top-full">
                  <div className="px-4 py-4 border-b border-dark-200 dark:border-dark-700">
                    <h3 className="font-bold text-dark-900 dark:text-white text-base mb-3">{t('header.notifications')}</h3>
                    <div className="flex items-center gap-2">
                      {notifications.length > 0 && (
                        <button
                          onClick={deleteAllNotifications}
                          className="text-xs text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 font-medium flex items-center gap-1 px-3 py-1.5 rounded bg-red-50 dark:bg-red-900/20 hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors"
                          title={t('header.deleteAll') || 'Borrar todas'}
                        >
                          <FaTrash className="w-3 h-3" />
                          <span className="hidden sm:inline">{t('header.deleteAll') || 'Borrar todas'}</span>
                        </button>
                      )}
                      {unreadCount > 0 && (
                        <button
                          onClick={markAllAsRead}
                          className="text-xs text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300 font-medium flex items-center gap-1 px-3 py-1.5 rounded bg-primary-50 dark:bg-primary-900/20 hover:bg-primary-100 dark:hover:bg-primary-900/30 transition-colors"
                        >
                          <FaCheck className="w-3 h-3" />
                          <span className="hidden sm:inline">{t('header.markAllRead')}</span>
                          <span className="sm:hidden">{t('header.markRead')}</span>
                        </button>
                      )}
                    </div>
                  </div>

                  <div className="max-h-96 overflow-y-auto">
                    {notifications.length === 0 ? (
                      <div className="px-4 py-8 text-center text-dark-500">
                        <p>{t('header.noNotifications')}</p>
                      </div>
                    ) : (
                      notifications.map(notification => (
                        <div
                          key={notification.id}
                          className={`px-4 py-3 border-b border-dark-100 dark:border-dark-700 border-l-4 hover:bg-dark-50 dark:hover:bg-dark-700 transition-colors cursor-pointer ${
                            !notification.is_read ? 'bg-primary-50 dark:bg-primary-900/20' : ''
                          } ${getNotificationColor(notification.notification_type)}`}
                          onClick={() => !notification.is_read && markAsRead(notification.id)}
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div className="flex-1">
                              <div className="flex items-center gap-2">
                                <p className="font-semibold text-dark-900 dark:text-white">{notification.title}</p>
                                {!notification.is_read && (
                                  <span className="w-2 h-2 bg-primary-600 rounded-full"></span>
                                )}
                              </div>
                              <p className="text-sm text-dark-600 dark:text-dark-300 mt-1">{notification.message}</p>
                              <p className="text-xs text-dark-400 mt-2">{formatDate(notification.created_at)}</p>
                            </div>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                deleteNotification(notification.id);
                              }}
                              className="text-dark-400 hover:text-red-600 transition-colors flex-shrink-0"
                              title={t('header.close')}
                            >
                              <FaTimes className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                      ))
                    )}
                  </div>

                  {notifications.length > 0 && (
                    <div className="px-4 py-3 border-t border-dark-200 text-center">
                      <button 
                        onClick={() => {
                          setIsFullNotificationViewOpen(true);
                          setIsNotificationOpen(false);
                        }}
                        className="text-primary-600 hover:text-primary-700 text-sm font-medium"
                      >
                        {t('header.viewAll')}
                      </button>
                    </div>
                  )}
                </div>
              )}

            </div>
          </div>
        </div>
      </div>

      {isNotificationOpen && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setIsNotificationOpen(false)}
        ></div>
      )}

      {isFullNotificationViewOpen && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white dark:bg-dark-800 rounded-xl shadow-2xl w-full max-w-2xl max-h-screen overflow-hidden flex flex-col">
            <div className="px-6 py-4 border-b border-dark-200 dark:border-dark-700 flex items-center justify-between">
              <h2 className="text-2xl font-bold text-dark-900 dark:text-white">{t('header.allNotifications')}</h2>
              <button
                onClick={() => setIsFullNotificationViewOpen(false)}
                className="text-dark-400 hover:text-dark-600 dark:hover:text-dark-300 transition-colors"
                title={t('header.close')}
              >
                <FaTimes className="w-6 h-6" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto">
              {notifications.length === 0 ? (
                <div className="px-6 py-12 text-center text-dark-500">
                  <FaBell className="w-12 h-12 mx-auto mb-4 opacity-30" />
                  <p className="text-lg">{t('header.noNotifications')}</p>
                </div>
              ) : (
                <div className="divide-y divide-dark-100 dark:divide-dark-700">
                  {notifications.map(notification => (
                    <div
                      key={notification.id}
                      className={`px-6 py-4 border-l-4 hover:bg-dark-50 dark:hover:bg-dark-700 transition-colors cursor-pointer ${
                        !notification.is_read ? 'bg-primary-50 dark:bg-primary-900/20' : ''
                      } ${getNotificationColor(notification.notification_type)}`}
                      onClick={() => !notification.is_read && markAsRead(notification.id)}
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <p className="font-semibold text-dark-900 dark:text-white text-lg">{notification.title}</p>
                            {!notification.is_read && (
                              <span className="w-2 h-2 bg-primary-600 rounded-full"></span>
                            )}
                          </div>
                          <p className="text-dark-600 dark:text-dark-300 mb-3">{notification.message}</p>
                          <p className="text-sm text-dark-400">{formatDate(notification.created_at)}</p>
                        </div>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            deleteNotification(notification.id);
                          }}
                          className="text-dark-400 hover:text-red-600 transition-colors flex-shrink-0 mt-1"
                          title={t('header.close')}
                        >
                          <FaTimes className="w-5 h-5" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {notifications.length > 0 && (
              <div className="px-4 sm:px-6 py-3 sm:py-4 border-t border-dark-200 dark:border-dark-700 flex flex-col sm:flex-row gap-3">
                {unreadCount > 0 && (
                  <button
                    onClick={markAllAsRead}
                    className="flex-1 bg-primary-600 hover:bg-primary-700 dark:hover:bg-primary-500 text-white font-medium py-2 px-4 rounded-lg transition-colors flex items-center justify-center gap-2 text-sm sm:text-base"
                  >
                    <FaCheck className="w-3 h-3 sm:w-4 sm:h-4" />
                    <span>{t('header.markAllRead')}</span>
                  </button>
                )}
                <button
                  onClick={deleteAllNotifications}
                  className="flex-1 bg-red-600 hover:bg-red-700 dark:hover:bg-red-500 text-white font-medium py-2 px-4 rounded-lg transition-colors flex items-center justify-center gap-2 text-sm sm:text-base"
                >
                  <FaTrash className="w-3 h-3 sm:w-4 sm:h-4" />
                  <span>{t('header.deleteAll') || 'Borrar todas'}</span>
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}

