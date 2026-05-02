/**
 * Theme utility — toggle dark/light via data-theme attribute on <html>.
 * Persists choice in localStorage.raidio.theme. Default = system preference.
 */

export type Theme = "dark" | "light";

const STORAGE_KEY = "raidio.theme";

/** Detect system color-scheme preference. */
function systemPreference(): Theme {
  if (typeof window === "undefined") return "dark";
  return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

/** Load persisted theme or fall back to system preference. */
export function loadTheme(): Theme {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "dark" || stored === "light") return stored;
  } catch {
    // localStorage may be unavailable
  }
  return systemPreference();
}

/** Apply theme to <html> element. */
export function applyTheme(theme: Theme): void {
  document.documentElement.setAttribute("data-theme", theme);
}

/** Persist and apply a theme choice. */
export function setTheme(theme: Theme): void {
  try {
    localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    // ignore
  }
  applyTheme(theme);
}

/** Cycle between dark and light. */
export function toggleTheme(): Theme {
  const current = loadTheme();
  const next: Theme = current === "dark" ? "light" : "dark";
  setTheme(next);
  return next;
}
