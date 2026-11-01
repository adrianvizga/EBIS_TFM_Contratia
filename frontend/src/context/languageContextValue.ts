import { createContext } from 'react';
import type { LanguageContextType } from './languageTypes';

export const LanguageContext = createContext<LanguageContextType | undefined>(undefined);
