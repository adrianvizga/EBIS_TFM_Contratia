import { createContext } from 'react';

export interface UserData {
  id?: string;
  email: string;
  first_name?: string;
  last_name?: string;
  firstName?: string;
  lastName?: string;
  company_name?: string;
  name?: string;
  role?: string | number;
  is_active?: boolean;
  profile_image_url?: string;
  created_at?: string;
  updated_at?: string;
}

export interface UserContextType {
  user: UserData | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string, rememberMe?: boolean) => Promise<void>;
  loginWithGoogle: (googleToken: string, rememberMe?: boolean, legalConsent?: { terms_accepted: true; terms_version: string; privacy_version: string }) => Promise<void>;
  register: (data: UserData & { password: string; terms_accepted: true; terms_version: string; privacy_version: string }) => Promise<void>;
  logout: () => void;
  updateUser: (data: Partial<UserData>) => void;
  refreshAccessToken: () => Promise<void>;
}

export const UserContext = createContext<UserContextType | undefined>(undefined);
