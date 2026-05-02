import { useCallback } from "react";
import { getTheme, setTheme, type Theme } from "../lib/theme";

export function ThemeToggle() {
  const current = getTheme();

  const handleChange = useCallback((e: React.ChangeEvent<HTMLSelectElement>) => {
    setTheme(e.target.value as Theme);
  }, []);

  return (
    <select
      value={current}
      onChange={handleChange}
      aria-label="Theme"
      className="theme-toggle"
    >
      <option value="light">Light</option>
      <option value="dark">Dark</option>
      <option value="system">System</option>
    </select>
  );
}
