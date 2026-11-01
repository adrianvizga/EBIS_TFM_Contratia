import { createContext } from 'react';

export interface NotificationsContextType {
  refreshTrigger: number;
  refreshNotifications: () => void;
}

export const NotificationsContext = createContext<NotificationsContextType | undefined>(undefined);
