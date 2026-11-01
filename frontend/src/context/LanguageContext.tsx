import { useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { translations } from '../config/translations';
import { isLanguage } from './languageTypes';
import type { Language, LanguageContextType } from './languageTypes';
import { LanguageContext } from './languageContextValue';

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = useState<Language>(() => {
    const storedLanguage = localStorage.getItem('language');
    return isLanguage(storedLanguage) ? storedLanguage : 'es';
  });

  useEffect(() => {
    localStorage.setItem('language', language);
  }, [language]);

  const value = useMemo<LanguageContextType>(() => ({
    language,
    setLanguage,
    t: (key: string) => translations[language][key] ?? key,
  }), [language]);

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}
