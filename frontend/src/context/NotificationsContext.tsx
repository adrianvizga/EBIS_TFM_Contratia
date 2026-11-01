import React, { useState, useCallback } from 'react';
import type { ReactNode } from 'react';
import { NotificationsContext } from './notificationsContextValue';

export const NotificationsProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const refreshNotifications = useCallback(() => {
    setRefreshTrigger(prev => prev + 1);
  }, []);

  return (
    <NotificationsContext.Provider value={{ refreshTrigger, refreshNotifications }}>
      {children}
    </NotificationsContext.Provider>
  );
};

