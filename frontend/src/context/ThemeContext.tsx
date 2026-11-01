import { useCallback, useEffect, useState } from 'react';
import { ThemeContext } from './themeContextValue';

const getInitialDarkMode = () => localStorage.getItem('theme') === 'dark';

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [isDarkMode, setIsDarkModeState] = useState(getInitialDarkMode);

  useEffect(() => {
    document.documentElement.classList.toggle('dark', isDarkMode);
  }, [isDarkMode]);

  const setDarkMode = useCallback((value: boolean) => {
    setIsDarkModeState(value);
    localStorage.setItem('theme', value ? 'dark' : 'light');
  }, []);

  const toggleDarkMode = useCallback(() => {
    setDarkMode(!isDarkMode);
  }, [isDarkMode, setDarkMode]);

  return (
    <ThemeContext.Provider value={{ isDarkMode, toggleDarkMode, setDarkMode }}>
      {children}
    </ThemeContext.Provider>
  );
}
