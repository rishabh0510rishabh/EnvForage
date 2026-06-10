import type { Metadata } from "next";
import { Inter, JetBrains_Mono, Outfit } from "next/font/google";
import Script from "next/script";
import "./globals.css";
import { Analytics } from "@vercel/analytics/next";
import { SpeedInsights } from "@vercel/speed-insights/next";
import Footer from "./components/Footer";
import Navbar from "./components/Navbar";
import ScrollToTop from "./components/ScrollToTop";
import { ThemeProvider } from "./providers";

const inter = Inter({
	subsets: ["latin"],
	variable: "--font-inter",
	display: "swap",
});

const outfit = Outfit({
	subsets: ["latin"],
	variable: "--font-outfit",
	display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
	subsets: ["latin"],
	variable: "--font-jetbrains-mono",
	display: "swap",
});

const BASE_URL = (() => {
	let raw = process.env.NEXT_PUBLIC_BASE_URL?.trim() || "http://localhost:3000";
	if (raw.endsWith("/")) raw = raw.slice(0, -1);
	if (!raw.startsWith("http")) raw = `https://${raw}`;
	return raw;
})();

// NOTE: Per-page canonical URLs are set via individual page metadata exports
// and the <CanonicalURL /> client component mounted below in <head>.
// Do NOT set a root-level canonical here — it would override every page with "/".
export const metadata: Metadata = {
	metadataBase: new URL(BASE_URL),
	title: "EnvForage | ML Environment Provisioning",
	description:
		"Generate intelligent, safe, and deterministic ML/AI environment setup scripts.",
	openGraph: {
		title: "EnvForage | ML Environment Provisioning",
		description:
			"Generate intelligent, safe, and deterministic ML/AI environment setup scripts.",
		url: BASE_URL,
		siteName: "EnvForage",
		locale: "en_US",
		type: "website",
	},
	twitter: {
		card: "summary_large_image",
		title: "EnvForage | ML Environment Provisioning",
		description:
			"Generate intelligent, safe, and deterministic ML/AI environment setup scripts.",
	},
	// NOTE: Per-page canonical URLs are set via individual page metadata exports
	// and the <CanonicalURL /> client component mounted below in <head>.
	// Do NOT set a root-level canonical here — it would override every page with "/".
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>): JSX.Element {
	children,
}: Readonly<{
	children: React.ReactNode;
}>) {
	return (
		<html lang="en" suppressHydrationWarning>
			<head>
				<Script id="theme-init" strategy="beforeInteractive">
					{`
            try {
              const storedTheme = localStorage.getItem("theme");
              const theme =
                storedTheme === "dark" ||
                storedTheme === "light" ||
                storedTheme === "system"
                  ? storedTheme
                  : "light";

              if (theme === "system") {
                const prefersDark =
                  window.matchMedia("(prefers-color-scheme: dark)").matches;

                document.documentElement.setAttribute(
                  "data-theme",
                  prefersDark ? "dark" : "light"
                );
              } else {
                document.documentElement.setAttribute(
                  "data-theme",
                  theme
                );
              }
            } catch {
              document.documentElement.setAttribute("data-theme", "dark");
            }
          `}
				</Script>
			</head>

			<body
				className={`${inter.variable} ${outfit.variable} ${jetbrainsMono.variable}`}
				style={{ backgroundColor: "var(--bg-core)" }}
			>
				<ThemeProvider>
					{/* Navigation Header */}
					<Navbar />

					{/* Main Content */}
					<main
						style={{ minHeight: "calc(100vh - 140px)", paddingTop: "76px" }}
					>
						{children}
					</main>

					{/* Footer */}
					<Footer />
					<ScrollToTop />
				</ThemeProvider>
				<Analytics />
				<SpeedInsights />
			</body>
		</html>
	);
}


// --- Advanced Navigation Context ---
import React, { createContext, useContext, useState, useEffect } from 'react';

interface NavigationContextType {
    isNavigating: boolean;
    startNavigation: () => void;
    endNavigation: () => void;
}

const NavigationContext = createContext<NavigationContextType>({
    isNavigating: false,
    startNavigation: () => {},
    endNavigation: () => {}
});

export const NavigationProvider = ({ children }: { children: React.ReactNode }) => {
    const [isNavigating, setIsNavigating] = useState(false);

    // This simulates listening to Next.js router events
    // In App Router, we usually track this via a custom hook on pathname change
    useEffect(() => {
        let timeout: ReturnType<typeof setTimeout>;
        if (isNavigating) {
            // Failsafe to turn off navigating state
            timeout = setTimeout(() => setIsNavigating(false), 5000);
        }
        return () => clearTimeout(timeout);
    }, [isNavigating]);

    return (
        <NavigationContext.Provider 
            value={{ 
                isNavigating, 
                startNavigation: () => setIsNavigating(true),
                endNavigation: () => setIsNavigating(false)
            }}
        >
            {isNavigating && (
                <div style={{
                    position: 'fixed', top: 0, left: 0, right: 0, height: '3px',
                    background: 'linear-gradient(90deg, transparent, var(--brand-primary), transparent)',
                    zIndex: 9999, animation: 'slide-right 1s infinite linear'
                }} />
            )}
            {children}
        </NavigationContext.Provider>
    );
};

export const useNavigation = () => useContext(NavigationContext);

