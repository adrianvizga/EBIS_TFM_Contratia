import React, { useState, useEffect } from 'react';
import type { ReactNode } from 'react';
import { API_BASE_URL } from '../config/api';
import { setAccessToken } from '../services/authTokenStore';
import { UserContext, type UserData } from './userContextValue';

const mapBackendError = (errorMessage: string): string => {
  const lowerError = errorMessage.toLowerCase();
  
  if (lowerError.includes('already registered') || lowerError.includes('already exists')) {
    return 'auth.emailAlreadyRegistered';
  }
  if (lowerError.includes('invalid') && lowerError.includes('password')) {
    return 'auth.invalidCredentials';
  }
  if (lowerError.includes('invalid')) {
    return 'auth.invalidCredentials';
  }
  if (lowerError.includes('account not found') || lowerError.includes('please sign up')) {
    return 'auth.emailNotFound';
  }
  if (lowerError.includes('not found')) {
    return 'auth.invalidCredentials';
  }
  if (lowerError.includes('registration')) {
    return 'auth.registrationFailed';
  }
  if (lowerError.includes('login')) {
    return 'auth.loginFailed';
  }
  
  return errorMessage;
};

export const UserProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserData | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true); 

  useEffect(() => {
    const initializeSession = async () => {
      const savedUser = sessionStorage.getItem('userData');

      try {
        const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
          method: 'POST',
          credentials: 'include',
        });

        if (response.ok) {
          const data = await response.json();
          setToken(data.access_token);
          setAccessToken(data.access_token);

          const verifyResponse = await fetch(`${API_BASE_URL}/auth/me`, {
            headers: { 'Authorization': `Bearer ${data.access_token}` },
            credentials: 'include',
          });

          if (verifyResponse.ok) {
            const freshUser = await verifyResponse.json();
            setUser(freshUser);
            sessionStorage.setItem('userData', JSON.stringify(freshUser));
          } else if (savedUser) {
            setUser(JSON.parse(savedUser));
          } else {
            setToken(null);
            setAccessToken(null);
          }
        } else {
          setAccessToken(null);
          sessionStorage.removeItem('userData');
        }
      } catch {
        setAccessToken(null);
        sessionStorage.removeItem('userData');
      }
      
      setIsLoading(false);
    };

    initializeSession();
  }, []);

  const login = async (email: string, password: string, rememberMe: boolean = false) => {
    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password, remember_me: rememberMe }),
      });

      if (!response.ok) {
        const error = await response.json();
        const errorMessage = error.detail || 'auth.loginFailed';
        const translationKey = mapBackendError(errorMessage);
        throw new Error(translationKey);
      }

      const data = await response.json();
      const userData = data.user;
      
      setToken(data.access_token);
      setAccessToken(data.access_token);
      setUser(userData);
      
      sessionStorage.setItem('userData', JSON.stringify(userData));
      localStorage.setItem('rememberedEmail', email);
      
      if (rememberMe) {
        localStorage.setItem('isRemembered', 'true');
      } else {
        localStorage.setItem('isRemembered', 'false');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const loginWithGoogle = async (googleToken: string, rememberMe: boolean = false, legalConsent?: { terms_accepted: true; terms_version: string; privacy_version: string }) => {
    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/auth/google-login`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ token: googleToken, remember_me: rememberMe, ...legalConsent }),
      });

      if (!response.ok) {
        const error = await response.json();
        const errorMessage = error.detail || 'auth.loginFailed';
        const translationKey = mapBackendError(errorMessage);
        throw new Error(translationKey);
      }

      const data = await response.json();
      const userData = data.user;
      
      setToken(data.access_token);
      setAccessToken(data.access_token);
      setUser(userData);
      
      sessionStorage.setItem('userData', JSON.stringify(userData));
      
      if (rememberMe) {
        localStorage.setItem('isRemembered', 'true');
      } else {
        localStorage.setItem('isRemembered', 'false');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (data: UserData & { password: string; terms_accepted: true; terms_version: string; privacy_version: string }) => {
    setIsLoading(true);
    try {
      const payload = {
        email: data.email,
        password: data.password,
        first_name: data.firstName,
        last_name: data.lastName,
        company_name: data.company_name || null,
        terms_accepted: data.terms_accepted,
        terms_version: data.terms_version,
        privacy_version: data.privacy_version,
      };

      const response = await fetch(`${API_BASE_URL}/auth/register`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const error = await response.json();
        const errorMessage = error.detail || 'auth.registrationFailed';
        const translationKey = mapBackendError(errorMessage);
        throw new Error(translationKey);
      }

      const responseData = await response.json();
      const userData = responseData.user;
      
      setToken(responseData.access_token);
      setAccessToken(responseData.access_token);
      setUser(userData);
      
      sessionStorage.setItem('userData', JSON.stringify(userData));
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    try {
      await fetch(`${API_BASE_URL}/auth/logout`, {
        method: 'POST',
        credentials: 'include',
        headers: token ? { 'Authorization': `Bearer ${token}` } : undefined,
      });
    } catch {
      // Aunque falle la red, la sesión local debe quedar cerrada.
    }
    
    setUser(null);
    setToken(null);
    setAccessToken(null);
    sessionStorage.removeItem('userData');
    localStorage.removeItem('isRemembered');
  };

  const refreshAccessToken = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: 'POST',
        credentials: 'include',
      });

      if (!response.ok) {
        logout();
        throw new Error('Token refresh failed');
      }

      const data = await response.json();
      setToken(data.access_token);
      setAccessToken(data.access_token);
    } catch (error) {
      logout();
      throw error;
    }
  };

  const updateUser = (newData: Partial<UserData>) => {
    setUser(prev => {
      if (!prev) return null;
      const updated = { ...prev, ...newData };
      sessionStorage.setItem('userData', JSON.stringify(updated));
      return updated;
    });
  };

  return (
    <UserContext.Provider value={{
      user,
      token,
      isAuthenticated: !!token,
      isLoading,
      login,
      loginWithGoogle,
      register,
      logout,
      updateUser,
      refreshAccessToken,
    }}>
      {children}
    </UserContext.Provider>
  );
};

