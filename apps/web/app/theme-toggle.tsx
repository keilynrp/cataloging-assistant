"use client";

import { useEffect, useState } from "react";

function applyTheme(dark: boolean): void {
  document.documentElement.classList.toggle("dark", dark);
  try {
    localStorage.setItem("theme", dark ? "dark" : "light");
  } catch {
    // Private browsing or a disabled localStorage; the toggle still works
    // for this page load, it just won't persist across visits.
  }
}

function IconSun() {
  return (
    <svg
      viewBox="0 0 24 24"
      width="20"
      height="20"
      aria-hidden="true"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
    </svg>
  );
}

function IconMoon() {
  return (
    <svg
      viewBox="0 0 24 24"
      width="20"
      height="20"
      aria-hidden="true"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79Z" />
    </svg>
  );
}

/** Class-based dark mode toggle. The `.dark` class is applied to <html> by
 * an inline script (in layout.tsx, before hydration) reading the same
 * localStorage key, so there's no flash of the wrong theme on load. */
export function ThemeToggle() {
  const [dark, setDark] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setDark(document.documentElement.classList.contains("dark"));
    setMounted(true);
  }, []);

  if (!mounted) {
    return <span className="inline-block h-10 w-10" aria-hidden="true" />;
  }

  return (
    <button
      type="button"
      className="bell-trigger"
      aria-label={dark ? "Cambiar a modo claro" : "Cambiar a modo oscuro"}
      onClick={() => {
        const next = !dark;
        setDark(next);
        applyTheme(next);
      }}
    >
      {dark ? <IconSun /> : <IconMoon />}
    </button>
  );
}
