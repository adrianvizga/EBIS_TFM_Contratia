import type { TranslationCatalog } from '../context/languageTypes';
import es from './translations/es';
import en from './translations/en';
import fr from './translations/fr';
import de from './translations/de';
import pt from './translations/pt';

const rawTranslations: TranslationCatalog = { es, en, fr, de, pt };
const spanishKeys = Object.keys(es);

export const translations: TranslationCatalog = Object.fromEntries(
  Object.entries(rawTranslations).map(([language, catalog]) => [
    language,
    language === 'es'
      ? { ...catalog }
      : Object.fromEntries(spanishKeys.map(key => [key, catalog[key] ?? es[key]])),
  ]),
) as TranslationCatalog;
