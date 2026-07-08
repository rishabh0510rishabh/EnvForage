"use client";

import { Moon, Sun, Monitor } from "lucide-react"; 
import { useTheme } from "../app/providers"; 

export function ThemeToggle() {
	const { theme, toggleTheme, mounted } = useTheme();

	// Prevent hydration mismatch by not rendering until mounted
	if (!mounted) {
		return null;
	}

	const nextTheme =
		theme === "dark" ? "light" : theme === "light" ? "system" : "dark";

	return (
		<button
			onClick={toggleTheme}
			className="theme-toggle-navbar"
			title={`Switch to ${nextTheme} mode`}
			aria-label={`Switch to ${nextTheme} mode`}
		>
			{theme === "dark" ? (
				<Sun size={18} />
			) : theme === "light" ? (
				<Moon size={18} />
			) : (
				<Monitor size={18} />
			)}
		</button>
	);
} 