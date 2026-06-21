"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { Menu, X } from "lucide-react";
import packageJson from "../../../package.json";
import { ThemeToggle } from "../providers";

export default function Navbar() {
	const pathname = usePathname();
	const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

	const isActive = (path: string) => {
		if (path === "/") {
			return pathname === "/";
		}
		return pathname === path || pathname.startsWith(path + "/");
	};

	const navLinks = [
		{ name: "Profiles", path: "/profiles" },
		{ name: "Diagnose", path: "/diagnose" },
		{ name: "AI Troubleshoot", path: "/troubleshoot" },
		{ name: "Dependencies", path: "/dependencies" },
		{ name: "Docs", path: "/docs" },
	];

	return (
		<header
			className="glass-nav"
			style={{
				position: "fixed",
				top: 0,
				left: 0,
				right: 0,
				width: "100%",
				zIndex: 100,
				boxShadow: "0 4px 30px rgba(0, 0, 0, 0.03)",
			}}
		>
			<div className="container nav-container">
				<div className="nav-brand">
					<div style={{ display: "flex", alignItems: "baseline", gap: "1rem" }}>
						<Link
							href="/"
							style={{
								fontSize: "1.5rem",
								fontWeight: 800,
								fontFamily: "var(--font-display)",
								letterSpacing: "-0.03em",
							}}
						>
							Env<span className="text-gradient">Forage</span>
						</Link>
						<span
							className="nav-hide"
							style={{
								color: "var(--text-muted)",
								fontSize: "0.85rem",
								fontWeight: 500,
							}}
						>
							MLOps • v{packageJson.version}
						</span>
					</div>
					<nav className="nav-links-desktop">
						{navLinks.map((link) => {
							const active = isActive(link.path);
							return (
								<Link
									key={link.path}
									href={link.path}
									style={{
										color: active
											? "var(--brand-primary)"
											: "var(--text-secondary)",
										position: "relative",
										padding: "0.25rem 0",
									}}
									className="nav-link"
								>
									{link.name}
									{active && (
										<span
											style={{
												position: "absolute",
												bottom: 0,
												left: 0,
												right: 0,
												height: "2px",
												background:
													"linear-gradient(90deg, var(--brand-primary), var(--brand-secondary))",
												borderRadius: "2px",
											}}
										/>
									)}
								</Link>
							);
						})}
					</nav>
				</div>
				<div className="nav-actions">
					<ThemeToggle />
					<a
						href="https://discord.gg/N2GKNRzDV"
						target="_blank"
						rel="noreferrer"
						className="hide-on-mobile"
						style={{
							display: "flex",
							alignItems: "center",
							gap: "0.5rem",
							fontSize: "0.925rem",
							fontWeight: 600,
							color: "var(--text-secondary)",
							textDecoration: "none",
						}}
					>
						<span style={{ color: "#5865F2" }}>💬</span> Discord
					</a>
					<a
						href="https://github.com/rishabh0510rishabh/EnvForage"
						target="_blank"
						rel="noreferrer"
						className="hide-on-mobile"
						style={{
							display: "flex",
							alignItems: "center",
							gap: "0.5rem",
							fontSize: "0.925rem",
							fontWeight: 600,
							color: "var(--text-secondary)",
							textDecoration: "none",
						}}
					>
						<span style={{ color: "var(--brand-secondary)" }}>★</span> GitHub
					</a>
					<button
						className="mobile-menu-btn"
						onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
						aria-label="Toggle mobile menu"
					>
						{isMobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
					</button>
				</div>
			</div>

			{isMobileMenuOpen && (
				<div className="mobile-menu-overlay">
					{navLinks.map((link) => {
						const active = isActive(link.path);
						return (
							<Link
								key={link.path}
								href={link.path}
								onClick={() => setIsMobileMenuOpen(false)}
								style={{
									color: active
										? "var(--brand-primary)"
										: "var(--text-secondary)",
									fontSize: "1.125rem",
									fontWeight: active ? 600 : 500,
									textDecoration: "none",
								}}
							>
								{link.name}
							</Link>
						);
					})}
					<hr style={{ borderColor: "var(--border-subtle)", margin: "0.5rem 0" }} />
					<div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", width: "100%" }}>
						<span style={{ color: "var(--text-secondary)", fontSize: "1.125rem", fontWeight: 500 }}>Theme</span>
						<ThemeToggle />
					</div>
					<hr style={{ borderColor: "var(--border-subtle)", margin: "0.5rem 0" }} />
					<a
						href="https://discord.gg/N2GKNRzDV"
						target="_blank"
						rel="noreferrer"
						style={{ color: "var(--text-secondary)", fontSize: "1.125rem", fontWeight: 500, textDecoration: "none" }}
					>
						<span style={{ color: "#5865F2", marginRight: "0.5rem" }}>💬</span> Discord
					</a>
					<a
						href="https://github.com/rishabh0510rishabh/EnvForage"
						target="_blank"
						rel="noreferrer"
						style={{ color: "var(--text-secondary)", fontSize: "1.125rem", fontWeight: 500, textDecoration: "none" }}
					>
						<span style={{ color: "var(--brand-secondary)", marginRight: "0.5rem" }}>★</span> GitHub
					</a>
				</div>
			)}
		</header>
	);
}
