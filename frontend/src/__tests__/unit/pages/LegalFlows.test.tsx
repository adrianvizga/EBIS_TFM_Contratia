import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { vi } from 'vitest';

import LegalDocument from '../../../pages/LegalDocument';
import SignUp from '../../../pages/SignUp';

const register = vi.fn();
vi.mock('../../../context/useUser', () => ({
  useUser: () => ({ register, loginWithGoogle: vi.fn(), isAuthenticated: false }),
}));
vi.mock('../../../context/useLanguage', () => ({
  useLanguage: () => ({ t: (key: string) => ({
    'auth.termsOfService': 'Términos de Servicio',
    'auth.privacyPolicy': 'Política de Privacidad',
    'auth.acceptTerms': 'He leído y acepto los',
    'auth.and': 'y la',
    'auth.acceptTermsRequired': 'Debes aceptar los términos y condiciones',
  }[key] || key) }),
}));

describe('legal registration flow', () => {
  it('renders accessible versioned legal documents', () => {
    render(<MemoryRouter><LegalDocument type="terms" /></MemoryRouter>);
    expect(screen.getByRole('heading', { level: 1, name: 'Términos de Servicio' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Volver al registro' })).toHaveAttribute('href', '/signup');
  });

  it('uses real keyboard-accessible links without replacing the form tab', async () => {
    render(<MemoryRouter><SignUp /></MemoryRouter>);
    const terms = screen.getByRole('link', { name: 'Términos de Servicio' });
    const privacy = screen.getByRole('link', { name: 'Política de Privacidad' });
    expect(terms).toHaveAttribute('href', '/terms');
    expect(terms).toHaveAttribute('target', '_blank');
    expect(privacy).toHaveAttribute('href', '/privacy');
    expect(privacy).toHaveAttribute('target', '_blank');
    await userEvent.tab();
    expect(document.activeElement).not.toBe(document.body);
  });
});
