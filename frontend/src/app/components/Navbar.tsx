"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import packageJson from "../../../package.json";
import { ThemeToggle } from "../providers";

export default function Navbar() {
	const pathname = usePathname();

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
				padding: "0.85rem 0",
				boxShadow: "0 4px 30px rgba(0, 0, 0, 0.03)",
			}}
		>
			<div
				className="container"
				style={{
					display: "flex",
					justifyContent: "space-between",
					alignItems: "center",
				}}
			>
				<div style={{ display: "flex", alignItems: "center", gap: "2.5rem" }}>
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
							style={{
								color: "var(--text-muted)",
								fontSize: "0.85rem",
								fontWeight: 500,
							}}
						>
							MLOps • v{packageJson.version}
						</span>
					</div>
					<nav
						style={{
							display: "flex",
							gap: "1.75rem",
							fontSize: "0.925rem",
							fontWeight: 500,
						}}
					>
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
				<div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
					<ThemeToggle />
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
							textDecoration: "none",
						}}
					>
						<span style={{ color: "var(--brand-secondary)" }}>★</span> GitHub
					</a>
				</div>
			</div>
		</header>
	);
}
