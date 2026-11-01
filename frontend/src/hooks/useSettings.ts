import { useState, useEffect, useCallback } from 'react';
import { useUser } from '../context/useUser';
import { useTheme } from '../context/useTheme';
import { useLanguage } from '../context/useLanguage';
import { API_BASE_URL } from '../config/api';


export interface UserSettings {
  id: string;
  user_id: string;
  theme: 'light' | 'dark';
  language: 'es' | 'en' | 'fr' | 'de' | 'pt';
  currency: 'EUR' | 'USD' | 'GBP' | 'JPY' | 'CNY' | 'CHF' | 'CAD' | 'AUD';
  email_notifications: boolean;
  push_notifications: boolean;
  allow_analytics: boolean;
  created_at: string;
  updated_at: string;
}

export interface UserSettingsUpdate {
  theme?: 'light' | 'dark';
  language?: 'es' | 'en' | 'fr' | 'de' | 'pt';
  currency?: 'EUR' | 'USD' | 'GBP' | 'JPY' | 'CNY' | 'CHF' | 'CAD' | 'AUD';
  email_notifications?: boolean;
  push_notifications?: boolean;
  allow_analytics?: boolean;
}

export const useSettings = () => {
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { token, isLoading: contextIsLoading } = useUser();
  const { setDarkMode } = useTheme();
  const { setLanguage } = useLanguage();

  const loadSettings = useCallback(async () => {
    if (!token) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/settings`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Error loading settings');
      }

      const data: UserSettings = await response.json();
      setSettings(data);

      if (data.theme === 'dark') {
        setDarkMode(true);
      } else {
        setDarkMode(false);
      }
      setLanguage(data.language);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      console.error('Error loading settings:', err);
    } finally {
      setIsLoading(false);
    }
  }, [setDarkMode, setLanguage, token]);

  const updateSettings = async (updates: UserSettingsUpdate) => {
    if (!token) {
      setError('No authentication token');
      return false;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/settings`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updates),
      });

      if (!response.ok) {
        throw new Error('Error updating settings');
      }

      const data: UserSettings = await response.json();
      setSettings(data);

      if (updates.theme !== undefined) {
        setDarkMode(updates.theme === 'dark');
      }
      if (updates.language !== undefined) {
        setLanguage(updates.language);
      }

      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (!contextIsLoading && token) {
      loadSettings();
    }
  }, [token, contextIsLoading, loadSettings]);

  return {
    settings,
    isLoading,
    error,
    loadSettings,
    updateSettings,
  };
};
