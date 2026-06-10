"use client";

import { Moon, Sun } from "lucide-react";
import { createContext, useContext, useEffect, useState } from "react";

// Create a context to share theme state across components
const ThemeContext = createContext<{
	theme: "dark" | "light" | "system";
	toggleTheme: () => void;
	mounted: boolean;
} | null>(null);

export function useTheme() {
	const context = useContext(ThemeContext);
	if (!context) {
		throw new Error("useTheme must be used within ThemeProvider");
	}
	return context;
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
	const [theme, setTheme] = useState<"dark" | "light" | "system">("light");
	const [mounted, setMounted] = useState(false);

	const applyTheme = (newTheme: "dark" | "light" | "system") => {
		const htmlElement = document.documentElement;

		if (newTheme === "dark") {
			htmlElement.setAttribute("data-theme", "dark");
		} else if (newTheme === "light") {
			htmlElement.setAttribute("data-theme", "light");
		} else {
			// System mode
			const prefersDark = window.matchMedia(
				"(prefers-color-scheme: dark)",
			).matches;
			htmlElement.setAttribute("data-theme", prefersDark ? "dark" : "light");
		}
	};

	// Initialize theme from localStorage on mount
	useEffect(() => {
		// eslint-disable-next-line react-hooks/set-state-in-effect
		setMounted(true);
		const storedTheme = localStorage.getItem("theme") as
			| "dark"
			| "light"
			| "system"
			| null;
		if (storedTheme) {
			setTheme(storedTheme);
			applyTheme(storedTheme);
		} else {
			// Default to dark mode
			applyTheme("dark");
		}
	}, []);

	const toggleTheme = () => {
		const newTheme = theme === "dark" ? "light" : "dark";
		setTheme(newTheme);
		localStorage.setItem("theme", newTheme);
		applyTheme(newTheme);
	};

	return (
		<ThemeContext.Provider value={{ theme, toggleTheme, mounted }}>
			{children}
		</ThemeContext.Provider>
	);
}

export function ThemeToggle() {
	const { theme, toggleTheme, mounted } = useTheme();

	// Prevent hydration mismatch by not rendering until mounted
	if (!mounted) {
		return null;
	}

	return (
		<button
			onClick={toggleTheme}
			className="theme-toggle-navbar"
			title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
			aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
		>
			{theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
		</button>
	);
}


// --- Advanced System Preference Media Listener ---
export function useSystemThemePreference() {
    const [systemTheme, setSystemTheme] = React.useState<'dark' | 'light'>('dark');

    React.useEffect(() => {
        if (typeof window === 'undefined') return;
        
        const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        const handleChange = (e: MediaQueryListEvent) => {
            const newTheme = e.matches ? 'dark' : 'light';
            setSystemTheme(newTheme);
            document.documentElement.setAttribute('data-system-theme', newTheme);
            
            // Sync with other tabs if needed
            try {
                localStorage.setItem('system-theme-snapshot', newTheme);
                window.dispatchEvent(new Event('system-theme-change'));
            } catch (err) {}
        };

        // Initial setup
        setSystemTheme(mediaQuery.matches ? 'dark' : 'light');
        document.documentElement.setAttribute('data-system-theme', mediaQuery.matches ? 'dark' : 'light');

        // Add listener safely
        if (mediaQuery.addEventListener) {
            mediaQuery.addEventListener('change', handleChange);
        } else {
            mediaQuery.addListener(handleChange);
        }

        return () => {
            if (mediaQuery.removeEventListener) {
                mediaQuery.removeEventListener('change', handleChange);
            } else {
                mediaQuery.removeListener(handleChange);
            }
        };
    }, []);

    return systemTheme;
}

export const ThemeSyncManager = {
    forceSync: () => {
        if (typeof window !== 'undefined') {
            const current = localStorage.getItem('theme');
            if (current) {
                document.documentElement.className = current;
            }
        }
    }
};

