"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { Menu, X } from "lucide-react";
import packageJson from "../../../package.json";
import { ThemeToggle } from "../providers";

export default function Navbar() {
	const pathname = usePathname();
	const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

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
			<div
				className="container nav-container"
				style={{ padding: "0.85rem 2rem" }}
			>
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
						href="#"
						target="_blank"
						rel="noreferrer"
						className="nav-hide"
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
						className="nav-hide"
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
						onClick={() => setMobileMenuOpen((prev) => !prev)}
						aria-label="Toggle navigation menu"
						aria-expanded={mobileMenuOpen}
					>
						{mobileMenuOpen ? <X size={22} /> : <Menu size={22} />}
					</button>
				</div>
			</div>

			{mobileMenuOpen && (
				<div className="mobile-menu-overlay">
					{navLinks.map((link) => {
						const active = isActive(link.path);
						return (
							<Link
								key={link.path}
								href={link.path}
								onClick={() => setMobileMenuOpen(false)}
								style={{
									color: active
										? "var(--brand-primary)"
										: "var(--text-secondary)",
									fontSize: "1rem",
									fontWeight: active ? 600 : 500,
									padding: "0.25rem 0",
								}}
								className="nav-link"
							>
								{link.name}
							</Link>
						);
					})}
					<div
						style={{
							display: "flex",
							gap: "1.5rem",
							paddingTop: "0.75rem",
							borderTop: "1px solid var(--border-subtle)",
						}}
					>
						<a
							href="#"
							target="_blank"
							rel="noreferrer"
							style={{
								display: "flex",
								alignItems: "center",
								gap: "0.5rem",
								fontSize: "0.925rem",
								fontWeight: 600,
								color: "var(--text-secondary)",
							}}
						>
							<span style={{ color: "#5865F2" }}>💬</span> Discord
						</a>
						<a
							href="https://github.com/rishabh0510rishabh/EnvForage"
							target="_blank"
							rel="noreferrer"
							style={{
								display: "flex",
								alignItems: "center",
								gap: "0.5rem",
								fontSize: "0.925rem",
								fontWeight: 600,
								color: "var(--text-secondary)",
							}}
						>
							<span style={{ color: "var(--brand-secondary)" }}>★</span> GitHub
						</a>
					</div>
				</div>
			)}
		</header>
	);
}
