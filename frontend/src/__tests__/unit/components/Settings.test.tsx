import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import Settings from '../../../components/sections/Settings';

const mockUser = {
  id: 'user-1',
  email: 'user@example.com',
  first_name: 'Test',
  last_name: 'User',
  company_name: 'Acme',
  profile_image_url: null,
};

const mockUpdateUser = vi.fn();
const mockLogout = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => vi.fn(),
  };
});

vi.mock('../../../context/useTheme', () => ({
  useTheme: () => ({ isDarkMode: false, toggleDarkMode: vi.fn() }),
}));

vi.mock('../../../context/useLanguage', () => ({
  useLanguage: () => ({
    language: 'es',
    setLanguage: vi.fn(),
    t: (key: string) => key,
  }),
}));

vi.mock('../../../context/useUser', () => ({
  useUser: () => ({
    user: mockUser,
    updateUser: mockUpdateUser,
    token: 'token',
    logout: mockLogout,
  }),
}));

vi.mock('../../../context/useNotifications', () => ({
  useNotifications: () => ({ refreshNotifications: vi.fn() }),
}));

vi.mock('../../../hooks/useSettings', () => ({
  useSettings: () => ({
    settings: { theme: 'light', language: 'es', currency: 'EUR' },
    updateSettings: vi.fn(),
    isLoading: false,
  }),
}));

vi.mock('../../../components/PasswordRequirements', () => ({
  default: () => null,
}));

describe('Settings', () => {
  it('does not show the currency selector in the settings panel', () => {
    render(
      <MemoryRouter>
        <Settings />
      </MemoryRouter>,
    );

    expect(screen.queryByText('settings.currency')).not.toBeInTheDocument();
    expect(screen.queryByText('settings.currencyDesc')).not.toBeInTheDocument();
    expect(screen.queryByText('settings.currencyEUR')).not.toBeInTheDocument();
  });
});
