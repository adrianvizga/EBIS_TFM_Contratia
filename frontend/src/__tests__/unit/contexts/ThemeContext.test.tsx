import { describe, it, expect } from 'vitest';
import { render, act } from '@testing-library/react';
import { ThemeProvider } from '../../../context/ThemeContext';
import { useTheme } from '../../../context/useTheme';

function TestConsumer({ onContext }: { onContext: (ctx: ReturnType<typeof useTheme>) => void }) {
  const ctx = useTheme();
  onContext(ctx);
  return null;
}

describe('ThemeContext', () => {
  it('toggle_dark_mode — toggleDarkMode() flips isDarkMode', () => {
    let ctx: ReturnType<typeof useTheme> | null = null;
    render(
      <ThemeProvider>
        <TestConsumer onContext={(c) => { ctx = c; }} />
      </ThemeProvider>,
    );

    expect(ctx!.isDarkMode).toBe(false);

    act(() => {
      ctx!.toggleDarkMode();
    });

    expect(ctx!.isDarkMode).toBe(true);

    act(() => {
      ctx!.toggleDarkMode();
    });

    expect(ctx!.isDarkMode).toBe(false);
  });

  it('dark_class_on_html — dark mode adds "dark" class to document.documentElement', () => {
    let ctx: ReturnType<typeof useTheme> | null = null;
    render(
      <ThemeProvider>
        <TestConsumer onContext={(c) => { ctx = c; }} />
      </ThemeProvider>,
    );

    expect(document.documentElement.classList.contains('dark')).toBe(false);

    act(() => {
      ctx!.setDarkMode(true);
    });

    expect(document.documentElement.classList.contains('dark')).toBe(true);

    act(() => {
      ctx!.setDarkMode(false);
    });

    expect(document.documentElement.classList.contains('dark')).toBe(false);
  });

  it('persistence — theme change is persisted to localStorage', () => {
    let ctx: ReturnType<typeof useTheme> | null = null;
    render(
      <ThemeProvider>
        <TestConsumer onContext={(c) => { ctx = c; }} />
      </ThemeProvider>,
    );

    act(() => {
      ctx!.setDarkMode(true);
    });

    expect(localStorage.getItem('theme')).toBe('dark');

    act(() => {
      ctx!.setDarkMode(false);
    });

    expect(localStorage.getItem('theme')).toBe('light');
  });
});
