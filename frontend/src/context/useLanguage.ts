import { useContext } from 'react';
import { LanguageContext } from './languageContextValue';
import type { LanguageContextType } from './languageTypes';

export function useLanguage(): LanguageContextType {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
}
