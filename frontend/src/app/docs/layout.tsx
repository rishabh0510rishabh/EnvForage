"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import { useState, useEffect } from "react";
import {
	BookOpen,
	ChevronDown,
	Code,
	ExternalLink,
	Layers,
	Menu,
	Search,
	Terminal,
	X,
} from "lucide-react";

interface NavItem {
	title: string;
	href: string;
	icon: React.ComponentType<{ size?: number; color?: string }>;
	isExternal?: boolean;
}

interface NavSection {
	category: string;
	items: NavItem[];
}

const docsNavigation: NavSection[] = [
	{
		category: "Getting Started",
		items: [
			{
				title: "Quick Start Guide",
				href: "/docs/getting-started",
				icon: Terminal,
			},
		],
	},
	{
		category: "Core Concepts",
		items: [
			{
				title: "Architecture Overview",
				href: "/docs/architecture",
				icon: Layers,
			},
		],
	},
	{
		category: "API Reference",
		items: [
			{
				title: "REST API Schema",
				href: "/docs/api",
				icon: Code,
			},
		],
	},
	{
		category: "Resources",
		items: [
			{
				title: "Back to Home",
				href: "/",
				icon: BookOpen,
			},
			{
				title: "CLI Reference",
				href: "https://github.com/rishabh0510rishabh/EnvForage/blob/main/docs/CLI_REFERENCE.md",
				icon: Terminal,
				isExternal: true,
			},
			{
				title: "GitHub Repository",
				href: "https://github.com/rishabh0510rishabh/EnvForage",
				icon: ExternalLink,
				isExternal: true,
			},
		],
	},
];

const versions = [
	{ id: "v2.0.0", label: "v2.0.0 (Latest)" },
	{ id: "v1.9.0", label: "v1.9.0" },
	{ id: "v1.8.0", label: "v1.8.0" },
];

export default function DocsLayout({
	children,
}: {
	children: React.ReactNode;
}) {
	const pathname = usePathname();
	const [selectedVersion, setSelectedVersion] = useState("v2.0.0");
	const [isVersionDropdownOpen, setIsVersionDropdownOpen] = useState(false);
	const [searchQuery, setSearchQuery] = useState("");
	const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

	// Close mobile menu when route changes
	useEffect(() => {
		// eslint-disable-next-line react-hooks/set-state-in-effect
		setIsMobileMenuOpen(false);
	}, [pathname]);

	// Filter navigation items based on search query
	const filteredNavigation = docsNavigation
		.map((section) => ({
			...section,
			items: section.items.filter((item) =>
				item.title.toLowerCase().includes(searchQuery.toLowerCase())
			),
		}))
		.filter((section) => section.items.length > 0);

	// Get current page category and title for breadcrumbs
	let currentCategory = "Documentation";
	let currentPageTitle = "";
	for (const section of docsNavigation) {
		const foundItem = section.items.find((item) => item.href === pathname);
		if (foundItem) {
			currentCategory = section.category;
			currentPageTitle = foundItem.title;
			break;
		}
	}

	return (
		<div
			style={{
				display: "flex",
				minHeight: "calc(100vh - 140px)",
				backgroundColor: "var(--bg-core)",
				position: "relative",
			}}
		>
			{/* DESKTOP SIDEBAR */}
			<aside
				className="hide-on-mobile glass-panel"
				style={{
					width: "300px",
					borderRight: "1px solid var(--border-subtle)",
					borderTop: "none",
					borderBottom: "none",
					borderLeft: "none",
					borderRadius: 0,
					padding: "2rem",
					height: "calc(100vh - 140px)",
					position: "sticky",
					top: "76px",
					overflowY: "auto",
					zIndex: 8,
				}}
			>
				{/* Version Selector */}
				<div style={{ position: "relative", marginBottom: "2rem" }}>
					<button
						onClick={() => setIsVersionDropdownOpen(!isVersionDropdownOpen)}
						style={{
							width: "100%",
							display: "flex",
							alignItems: "center",
							justifyContent: "space-between",
							padding: "0.75rem 1rem",
							borderRadius: "8px",
							backgroundColor: "var(--bg-secondary)",
							border: "1px solid var(--border-subtle)",
							color: "var(--text-primary)",
							fontWeight: 600,
							fontSize: "0.875rem",
							cursor: "pointer",
							transition: "all var(--transition-fast)",
						}}
					>
						<span style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
							<BookOpen size={16} color="var(--brand-primary)" />
							{versions.find((v) => v.id === selectedVersion)?.label}
						</span>
						<ChevronDown
							size={16}
							style={{
								transform: isVersionDropdownOpen ? "rotate(180deg)" : "none",
								transition: "transform var(--transition-fast)",
							}}
						/>
					</button>

					{isVersionDropdownOpen && (
						<div
							style={{
								position: "absolute",
								top: "105%",
								left: 0,
								right: 0,
								backgroundColor: "var(--bg-secondary)",
								border: "1px solid var(--border-strong)",
								borderRadius: "8px",
								boxShadow: "var(--shadow-lg)",
								zIndex: 20,
								overflow: "hidden",
							}}
						>
							{versions.map((ver) => (
								<button
									key={ver.id}
									onClick={() => {
										setSelectedVersion(ver.id);
										setIsVersionDropdownOpen(false);
									}}
									style={{
										width: "100%",
										textAlign: "left",
										padding: "0.75rem 1rem",
										background: "none",
										border: "none",
										color: selectedVersion === ver.id ? "var(--brand-primary)" : "var(--text-primary)",
										fontWeight: selectedVersion === ver.id ? 700 : 500,
										fontSize: "0.875rem",
										cursor: "pointer",
										transition: "background var(--transition-fast)",
										backgroundColor: selectedVersion === ver.id ? "rgba(99, 102, 241, 0.08)" : "transparent",
									}}
									onMouseEnter={(e) => {
										if (selectedVersion !== ver.id) {
											e.currentTarget.style.backgroundColor = "rgba(255, 255, 255, 0.02)";
										}
									}}
									onMouseLeave={(e) => {
										if (selectedVersion !== ver.id) {
											e.currentTarget.style.backgroundColor = "transparent";
										}
									}}
								>
									{ver.label}
								</button>
							))}
						</div>
					)}
				</div>

				{/* Search Input */}
				<div style={{ position: "relative", marginBottom: "2rem" }}>
					<span style={{ position: "absolute", left: "0.75rem", top: "50%", transform: "translateY(-50%)", color: "var(--text-muted)", display: "flex" }}>
						<Search size={16} />
					</span>
					<input
						type="text"
						placeholder="Search documentation..."
						value={searchQuery}
						onChange={(e) => setSearchQuery(e.target.value)}
						style={{
							width: "100%",
							padding: "0.75rem 1rem 0.75rem 2.25rem",
							borderRadius: "8px",
							backgroundColor: "var(--bg-secondary)",
							border: "1px solid var(--border-subtle)",
							color: "var(--text-primary)",
							fontSize: "0.875rem",
							outline: "none",
							transition: "border-color var(--transition-fast)",
						}}
						onFocus={(e) => (e.target.style.borderColor = "var(--brand-primary)")}
						onBlur={(e) => (e.target.style.borderColor = "var(--border-subtle)")}
					/>
				</div>

				{/* Navigation Links */}
				<nav style={{ display: "flex", flexDirection: "column", gap: "1.75rem" }}>
					{filteredNavigation.map((section, idx) => (
						<div key={idx}>
							<h4
								style={{
									fontSize: "0.75rem",
									fontWeight: 700,
									textTransform: "uppercase",
									letterSpacing: "0.1em",
									color: "var(--text-muted)",
									marginBottom: "0.75rem",
								}}
							>
								{section.category}
							</h4>
							<ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: "0.35rem" }}>
								{section.items.map((item, itemIdx) => {
									const Icon = item.icon;
									const isActive = pathname === item.href;
									return (
										<li key={itemIdx}>
											<Link
												href={item.href}
												target={item.isExternal ? "_blank" : undefined}
												rel={item.isExternal ? "noopener noreferrer" : undefined}
												style={{
													display: "flex",
													alignItems: "center",
													gap: "0.75rem",
													padding: "0.6rem 0.75rem",
													borderRadius: "6px",
													fontSize: "0.9rem",
													fontWeight: isActive ? 600 : 500,
													color: isActive ? "var(--text-primary)" : "var(--text-secondary)",
													backgroundColor: isActive ? "rgba(99, 102, 241, 0.12)" : "transparent",
													transition: "all var(--transition-fast)",
													borderLeft: isActive ? "3px solid var(--brand-primary)" : "3px solid transparent",
													paddingLeft: isActive ? "calc(0.75rem - 3px)" : "0.75rem",
												}}
											>
												<Icon size={16} color={isActive ? "var(--brand-primary)" : "var(--text-muted)"} />
												{item.title}
											</Link>
										</li>
									);
								})}
							</ul>
						</div>
					))}
				</nav>
			</aside>

			{/* MOBILE MENUBAR & TOGGLE */}
			<div
				className="p-mobile-sm"
				style={{
					display: "none",
					width: "100%",
					backgroundColor: "var(--bg-secondary)",
					borderBottom: "1px solid var(--border-subtle)",
					padding: "1rem 1.25rem",
					position: "fixed",
					top: "76px",
					left: 0,
					zIndex: 9,
					alignItems: "center",
					justifyContent: "space-between",
				}}
				// We override the 'display: none' using CSS responsive helper
				ref={(el) => {
					if (el) {
						if (window.innerWidth <= 1024) {
							el.style.display = "flex";
						} else {
							el.style.display = "none";
						}
					}
				}}
			>
				<button
					onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
					style={{
						display: "flex",
						alignItems: "center",
						gap: "0.5rem",
						background: "none",
						border: "none",
						color: "var(--text-primary)",
						fontSize: "0.9rem",
						fontWeight: 600,
						cursor: "pointer",
					}}
				>
					<Menu size={20} />
					<span>Menu</span>
				</button>
				<div style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--brand-primary)" }}>
					{versions.find((v) => v.id === selectedVersion)?.id}
				</div>
			</div>

			{/* MOBILE SIDEBAR DRAWER OVERLAY */}
			{isMobileMenuOpen && (
				<div
					style={{
						position: "fixed",
						top: "133px",
						left: 0,
						right: 0,
						bottom: 0,
						backgroundColor: "rgba(5, 5, 10, 0.8)",
						zIndex: 99,
						display: "flex",
					}}
				>
					<div
						style={{
							width: "80%",
							maxWidth: "320px",
							backgroundColor: "var(--bg-primary)",
							height: "100%",
							padding: "2rem 1.25rem",
							boxShadow: "var(--shadow-lg)",
							display: "flex",
							flexDirection: "column",
							borderRight: "1px solid var(--border-subtle)",
						}}
					>
						<div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "2rem" }}>
							<span style={{ fontSize: "1.1rem", fontWeight: 800, fontFamily: "var(--font-display)" }}>
								Navigation
							</span>
							<button
								onClick={() => setIsMobileMenuOpen(false)}
								style={{ background: "none", border: "none", color: "var(--text-primary)", cursor: "pointer", padding: "0.25rem" }}
							>
								<X size={20} />
							</button>
						</div>

						{/* Version Selector for Mobile */}
						<div style={{ marginBottom: "1.5rem" }}>
							<select
								value={selectedVersion}
								onChange={(e) => setSelectedVersion(e.target.value)}
								style={{
									width: "100%",
									padding: "0.75rem",
									borderRadius: "8px",
									backgroundColor: "var(--bg-secondary)",
									border: "1px solid var(--border-subtle)",
									color: "var(--text-primary)",
									fontSize: "0.875rem",
									fontWeight: 600,
									outline: "none",
								}}
							>
								{versions.map((ver) => (
									<option key={ver.id} value={ver.id}>
										{ver.label}
									</option>
								))}
							</select>
						</div>

						{/* Search Input for Mobile */}
						<div style={{ position: "relative", marginBottom: "1.5rem" }}>
							<span style={{ position: "absolute", left: "0.75rem", top: "50%", transform: "translateY(-50%)", color: "var(--text-muted)", display: "flex" }}>
								<Search size={16} />
							</span>
							<input
								type="text"
								placeholder="Search..."
								value={searchQuery}
								onChange={(e) => setSearchQuery(e.target.value)}
								style={{
									width: "100%",
									padding: "0.6rem 1rem 0.6rem 2.25rem",
									borderRadius: "8px",
									backgroundColor: "var(--bg-secondary)",
									border: "1px solid var(--border-subtle)",
									color: "var(--text-primary)",
									fontSize: "0.875rem",
								}}
							/>
						</div>

						{/* Navigation Links for Mobile */}
						<nav style={{ display: "flex", flexDirection: "column", gap: "1.5rem", overflowY: "auto" }}>
							{filteredNavigation.map((section, idx) => (
								<div key={idx}>
									<h4 style={{ fontSize: "0.75rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--text-muted)", marginBottom: "0.5rem" }}>
										{section.category}
									</h4>
									<ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: "0.25rem" }}>
										{section.items.map((item, itemIdx) => {
											const Icon = item.icon;
											const isActive = pathname === item.href;
											return (
												<li key={itemIdx}>
													<Link
														href={item.href}
														target={item.isExternal ? "_blank" : undefined}
														rel={item.isExternal ? "noopener noreferrer" : undefined}
														style={{
															display: "flex",
															alignItems: "center",
															gap: "0.75rem",
															padding: "0.5rem 0.75rem",
															borderRadius: "6px",
															fontSize: "0.9rem",
															fontWeight: isActive ? 600 : 500,
															color: isActive ? "var(--text-primary)" : "var(--text-secondary)",
															backgroundColor: isActive ? "rgba(99, 102, 241, 0.1)" : "transparent",
														}}
													>
														<Icon size={16} color={isActive ? "var(--brand-primary)" : "var(--text-muted)"} />
														{item.title}
													</Link>
												</li>
											);
										})}
									</ul>
								</div>
							))}
						</nav>
					</div>
					{/* Click outside to close */}
					<div style={{ flex: 1 }} onClick={() => setIsMobileMenuOpen(false)} />
				</div>
			)}

			{/* MAIN READER CONTENT */}
			<main
				style={{
					flex: 1,
					minWidth: 0,
					padding: "3rem 4rem 6rem",
					overflowY: "auto",
				}}
				// Custom inline responsive styles handled safely via class or layout resize
				ref={(el) => {
					if (el) {
						const adjustPadding = () => {
							if (window.innerWidth <= 768) {
								el.style.padding = "6.5rem 1.25rem 4rem";
							} else if (window.innerWidth <= 1024) {
								el.style.padding = "6.5rem 2.5rem 4rem";
							} else {
								el.style.padding = "3rem 4rem 6rem";
							}
						};
						adjustPadding();
						window.addEventListener("resize", adjustPadding);
					}
				}}
			>
				{/* Breadcrumb Header */}
				<div
					style={{
						display: "flex",
						alignItems: "center",
						gap: "0.5rem",
						fontSize: "0.85rem",
						color: "var(--text-muted)",
						marginBottom: "2rem",
						fontFamily: "var(--font-sans)",
					}}
				>
					<span style={{ cursor: "pointer" }}>Docs</span>
					<span style={{ fontSize: "0.75rem" }}>/</span>
					<span>{currentCategory}</span>
					{currentPageTitle && (
						<>
							<span style={{ fontSize: "0.75rem" }}>/</span>
							<span style={{ color: "var(--text-secondary)", fontWeight: 500 }}>
								{currentPageTitle}
							</span>
						</>
					)}
				</div>

				{/* Reading Pane container */}
				<article
					className="markdown-body"
					style={{
						maxWidth: "840px",
						lineHeight: 1.7,
						color: "var(--text-primary)",
					}}
				>
					{/* Style Injector for MDX markup */}
					<style dangerouslySetInnerHTML={{ __html: `
						.markdown-body h1 {
							font-size: 3rem;
							font-weight: 800;
							color: var(--text-primary);
							margin-top: 1rem;
							margin-bottom: 1.5rem;
							letter-spacing: -0.03em;
							line-height: 1.15;
						}
						.markdown-body h2 {
							font-size: 1.85rem;
							font-weight: 700;
							color: var(--text-primary);
							margin-top: 2.5rem;
							margin-bottom: 1.25rem;
							border-bottom: 1px solid var(--border-subtle);
							padding-bottom: 0.5rem;
							letter-spacing: -0.02em;
						}
						.markdown-body h3 {
							font-size: 1.35rem;
							font-weight: 600;
							color: var(--text-primary);
							margin-top: 2rem;
							margin-bottom: 1rem;
						}
						.markdown-body p {
							margin-bottom: 1.5rem;
							color: var(--text-secondary);
							font-size: 1.05rem;
						}
						.markdown-body ul, .markdown-body ol {
							margin-bottom: 1.5rem;
							padding-left: 1.5rem;
							color: var(--text-secondary);
							font-size: 1.05rem;
						}
						.markdown-body li {
							margin-bottom: 0.5rem;
						}
						.markdown-body code {
							font-family: var(--font-mono);
							font-size: 0.9em;
							background-color: var(--border-subtle);
							padding: 0.2rem 0.4rem;
							border-radius: 4px;
							color: var(--brand-secondary);
						}
						.markdown-body pre {
							background-color: var(--bg-secondary);
							border: 1px solid var(--border-strong);
							border-radius: 8px;
							padding: 1.25rem;
							overflow-x: auto;
							margin-bottom: 2rem;
						}
						.markdown-body pre code {
							background-color: transparent;
							padding: 0;
							border-radius: 0;
							color: var(--text-primary);
							font-size: 0.9rem;
							line-height: 1.5;
						}
						.markdown-body blockquote {
							border-left: 4px solid var(--brand-primary);
							padding-left: 1.25rem;
							margin-left: 0;
							margin-right: 0;
							font-style: italic;
							color: var(--text-muted);
							margin-bottom: 1.75rem;
						}
					` }} />
					{children}
				</article>

				{/* Help / Footer CTA */}
				<div
					style={{
						marginTop: "6rem",
						paddingTop: "2rem",
						borderTop: "1px solid var(--border-subtle)",
						display: "flex",
						justifyContent: "space-between",
						alignItems: "center",
						flexWrap: "wrap",
						gap: "1.5rem",
					}}
				>
					<div style={{ fontSize: "0.875rem", color: "var(--text-muted)" }}>
						Did this guide help you? Reach out on{" "}
						<a
							href="https://github.com/rishabh0510rishabh/EnvForage"
							target="_blank"
							rel="noreferrer"
							style={{ color: "var(--brand-primary)", textDecoration: "underline" }}
						>
							GitHub
						</a>.
					</div>
					<div>
						<Link
							href="/download"
							style={{
								display: "inline-flex",
								alignItems: "center",
								gap: "0.5rem",
								fontSize: "0.875rem",
								fontWeight: 600,
								color: "var(--brand-primary)",
							}}
						>
							Get EnvForage CLI <ChevronRightIcon size={14} />
						</Link>
					</div>
				</div>
			</main>
		</div>
	);
}

// Small helper inline icon
function ChevronRightIcon({ size }: { size: number }) {
	return (
		<svg
			xmlns="http://www.w3.org/2000/svg"
			width={size}
			height={size}
			viewBox="0 0 24 24"
			fill="none"
			stroke="currentColor"
			strokeWidth="2"
			strokeLinecap="round"
			strokeLinejoin="round"
		>
			<path d="m9 18 6-6-6-6" />
		</svg>
	);
}
