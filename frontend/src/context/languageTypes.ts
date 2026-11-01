export const supportedLanguages = ['es', 'en', 'fr', 'de', 'pt'] as const;

export type Language = (typeof supportedLanguages)[number];
export type TranslationCatalog = Record<Language, Record<string, string>>;

export interface LanguageContextType {
  language: Language;
  setLanguage: (language: Language) => void;
  t: (key: string) => string;
}

export function isLanguage(value: string | null): value is Language {
  return value !== null && supportedLanguages.some(language => language === value);
}
