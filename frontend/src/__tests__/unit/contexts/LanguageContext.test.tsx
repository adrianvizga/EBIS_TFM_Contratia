import { describe, it, expect } from 'vitest';
import { render, act } from '@testing-library/react';
import { LanguageProvider } from '../../../context/LanguageContext';
import { useLanguage } from '../../../context/useLanguage';

function TestConsumer({ onContext }: { onContext: (ctx: ReturnType<typeof useLanguage>) => void }) {
  const ctx = useLanguage();
  onContext(ctx);
  return null;
}

function getContext() {
  let ctx: ReturnType<typeof useLanguage> | null = null;
  render(
    <LanguageProvider>
      <TestConsumer onContext={(c) => { ctx = c; }} />
    </LanguageProvider>,
  );
  return ctx!;
}

describe('LanguageContext', () => {
  it('restores a valid stored language', () => {
    localStorage.setItem('language', 'de');
    expect(getContext().language).toBe('de');
  });

  it('falls back to Spanish for an invalid stored language', () => {
    localStorage.setItem('language', 'invalid');
    expect(getContext().language).toBe('es');
  });

  it('throws when useLanguage is rendered without its provider', () => {
    const Consumer = () => { useLanguage(); return null; };
    expect(() => render(<Consumer />)).toThrow('useLanguage must be used within a LanguageProvider');
  });

  it('t_returns_translation — t() returns correct Spanish translation', () => {
    const ctx = getContext();
    expect(ctx.language).toBe('es');
    expect(ctx.t('auth.signIn')).toBe('Iniciar sesión');
  });

  it('t_missing_key_returns_key — t() with unknown key returns the key itself', () => {
    const ctx = getContext();
    expect(ctx.t('nonexistent.key.xyz')).toBe('nonexistent.key.xyz');
  });

  it('switch_language — changing language updates translations', () => {
    let ctx: ReturnType<typeof useLanguage> | null = null;
    render(
      <LanguageProvider>
        <TestConsumer onContext={(c) => { ctx = c; }} />
      </LanguageProvider>,
    );

    act(() => {
      ctx!.setLanguage('en');
    });

    expect(ctx!.language).toBe('en');
    expect(ctx!.t('auth.signIn')).toBe('Sign In');
  });

  it('persistence_localStorage — changing language persists to localStorage', () => {
    let ctx: ReturnType<typeof useLanguage> | null = null;
    render(
      <LanguageProvider>
        <TestConsumer onContext={(c) => { ctx = c; }} />
      </LanguageProvider>,
    );

    act(() => {
      ctx!.setLanguage('fr');
    });

    expect(localStorage.getItem('language')).toBe('fr');
  });

  it('5_languages_exist — all 5 languages have translations', () => {
    const languages: Array<'es' | 'en' | 'fr' | 'de' | 'pt'> = ['es', 'en', 'fr', 'de', 'pt'];
    const testKey = 'auth.signIn';

    let ctx: ReturnType<typeof useLanguage> | null = null;
    render(
      <LanguageProvider>
        <TestConsumer onContext={(c) => { ctx = c; }} />
      </LanguageProvider>,
    );

    for (const lang of languages) {
      act(() => {
        ctx!.setLanguage(lang);
      });
      const translation = ctx!.t(testKey);
      expect(translation).toBeTruthy();
      expect(translation).not.toBe(testKey);
    }
  });
});
