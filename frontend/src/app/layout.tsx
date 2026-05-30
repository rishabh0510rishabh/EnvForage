import type { Metadata } from "next";
import { Inter, JetBrains_Mono, Outfit } from "next/font/google";
import Script from "next/script";
import "./globals.css";
import { Analytics } from "@vercel/analytics/next";
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

export const metadata: Metadata = {
	title: "EnvForage | ML Environment Provisioning",
	description:
		"Generate intelligent, safe, and deterministic ML/AI environment setup scripts.",
};

export default function RootLayout({
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
			</body>
		</html>
	);
}
