"use client";

import { AnimatePresence, motion } from "framer-motion";
import {
	Box,
	Cpu,
	Layers,
	Search,
	ShieldAlert,
	SlidersHorizontal,
	Terminal,
	Star,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "../../services/api";
import type { Profile } from "../../types";

export default function ProfilesPage() {
	const [profiles, setProfiles] = useState<Profile[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);

	// Filter and search state
	const [searchQuery, setSearchQuery] = useState("");
	const [selectedOS, setSelectedOS] = useState("ALL");
	const [cudaFilter, setCudaFilter] = useState("ALL");// ALL, REQUIRED, OPTIONAL
	const [favorites, setFavorites] = useState<string[]>([]);
	const [recentProfiles, setRecentProfiles] = useState<
	{ slug: string; name: string; description?: string }[]>([]);

	useEffect(() => {
		async function loadProfiles() {
			try {
				const data = await api.getProfiles();
				setProfiles(data);
			} catch (err) {
				setError(
					err instanceof Error ? err.message : "Failed to load profiles",
				);
			} finally {
				setLoading(false);
			}
		}
		loadProfiles();
	}, []);
	useEffect(() => {
		const saved = localStorage.getItem("favoriteProfiles");
		if (saved) {
			try {
				const parsed = JSON.parse(saved);
				if (Array.isArray(parsed) && parsed.every((i) => typeof i === "string")) {
					// eslint-disable-next-line react-hooks/set-state-in-effect
					setFavorites(parsed);
				} else {
					setFavorites([]);
				}
			} catch {
				setFavorites([]);
			}
		}
	}, []);

	useEffect(() => {
  const saved = localStorage.getItem("recentProfiles");

			if (saved) {
				try {
					// eslint-disable-next-line react-hooks/set-state-in-effect
					setRecentProfiles(JSON.parse(saved));
				} catch {
					setRecentProfiles([]);
			}
		}
	}, []);

const toggleFavorite = (slug: string) => {
	const updated = favorites.includes(slug)
		? favorites.filter((id) => id !== slug)
		: [...favorites, slug];

	setFavorites(updated);

	localStorage.setItem(
		"favoriteProfiles",
		JSON.stringify(updated),
	);
};

	// Filter profiles based on search and selected options
	const filteredProfiles = profiles.filter((p) => {
		const description = p.description ?? "";
		const tags = p.tags ?? [];
		const normalizedQuery = searchQuery.toLowerCase();

		const matchesSearch =
			p.name.toLowerCase().includes(normalizedQuery) ||
			description.toLowerCase().includes(normalizedQuery) ||
			tags.some((tag) => tag.toLowerCase().includes(normalizedQuery));

		const matchesOS =
			selectedOS === "ALL" ||
			p.os_support.some((os) => os.toUpperCase() === selectedOS.toUpperCase());

		const matchesCuda =
			cudaFilter === "ALL" ||
			(cudaFilter === "REQUIRED" && p.cuda_required) ||
			(cudaFilter === "OPTIONAL" && !p.cuda_required);

		return matchesSearch && matchesOS && matchesCuda;
	});

	const recentProfileData = recentProfiles
  		.map((recent) =>
    		profiles.find((p) => p.slug === recent.slug)
  		)
  		.filter(Boolean);

	if (loading) {
		return (
			<div
				className="container"
				style={{
					paddingTop: "6rem",
					textAlign: "center",
					color: "var(--text-muted)",
				}}
			>
				<motion.div
					animate={{ rotate: 360 }}
					transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
					style={{ display: "inline-block", marginBottom: "1rem" }}
				>
					<Cpu size={40} />
				</motion.div>
				<h2>Loading Environment Profiles...</h2>
			</div>
		);
	}

	if (error) {
		return (
			<div
				className="container"
				style={{ paddingTop: "6rem", textAlign: "center" }}
			>
				<ShieldAlert
					size={48}
					color="#ef4444"
					style={{ margin: "0 auto 1rem" }}
				/>
				<h2 style={{ marginBottom: "1rem" }}>Error Loading Profiles</h2>
				<p style={{ color: "var(--text-secondary)", marginBottom: "2rem" }}>
					{error}
				</p>
				<button
					onClick={() => window.location.reload()}
					className="btn btn-primary"
				>
					Try Again
				</button>
			</div>
		);
	}

	return (
		<div
			className="container"
			style={{ paddingTop: "3rem", paddingBottom: "6rem" }}
		>
			<div style={{ marginBottom: "3rem", textAlign: "center" }}>
				<motion.div
					initial={{ opacity: 0, y: -10 }}
					animate={{ opacity: 1, y: 0 }}
					transition={{ duration: 0.4 }}
				>
					<h1 style={{ fontSize: "3rem", marginBottom: "1rem" }}>
						ML Environment <span className="text-gradient">Profiles</span>
					</h1>
					<p
						style={{
							fontSize: "1.1rem",
							color: "var(--text-secondary)",
							maxWidth: "600px",
							margin: "0 auto",
						}}
					>
						Pre-configured, hardware-optimized environment definitions for top
						machine learning frameworks. Select a profile to generate a safe
						setup script.
					</p>
				</motion.div>
			</div>

			{recentProfileData.length > 0 && (
			<motion.div
				initial={{ opacity: 0 }}
				animate={{ opacity: 1 }}
				className="glass-panel"
				style={{
				padding: "1.5rem",
				marginBottom: "2rem",
				}}
			>
				<h2
				style={{
					marginBottom: "1rem",
					fontSize: "1.4rem",
				}}
				>
				🕒 Recently Used Profiles
				</h2>

				<div
				style={{
					display: "grid",
					gap: "1rem",
				}}
				>
				{recentProfileData.map((profile) => (
					<Link
					key={profile!.slug}
					href={`/profiles/${profile!.slug}`}
					style={{
						padding: "1rem",
						border: "1px solid var(--border-subtle)",
						borderRadius: "8px",
						textDecoration: "none",
						color: "var(--text-primary)",
					}}
					>
					<strong>{profile!.name}</strong>

					<p
						style={{
						marginTop: "0.5rem",
						color: "var(--text-secondary)",
						fontSize: "0.9rem",
						}}
					>
						{profile!.description}
					</p>
					</Link>
				))}
				</div>
			</motion.div>
			)}

			{/* Filter and Search Bar */}
			<motion.div
				initial={{ opacity: 0, y: 10 }}
				animate={{ opacity: 1, y: 0 }}
				transition={{ duration: 0.4, delay: 0.1 }}
				className="glass-panel"
				style={{
					padding: "1.5rem",
					marginBottom: "3rem",
					display: "flex",
					flexWrap: "wrap",
					gap: "1.5rem",
					alignItems: "center",
					justifyContent: "space-between",
				}}
			>
				{/* Search */}
				<div
					style={{
						display: "flex",
						alignItems: "center",
						gap: "0.75rem",
						background: "rgba(255,255,255,0.05)",
						padding: "0.5rem 1rem",
						borderRadius: "8px",
						border: "1px solid var(--border-subtle)",
						flex: "1 1 300px",
					}}
				>
					<Search size={18} color="var(--text-muted)" />
					<input
						type="text"
						placeholder="Search profiles (e.g. PyTorch, CUDA, YOLO)..."
						value={searchQuery}
						onChange={(e) => setSearchQuery(e.target.value)}
						style={{
							background: "transparent",
							border: "none",
							color: "var(--text-primary)",
							outline: "none",
							width: "100%",
							fontFamily: "var(--font-sans)",
							fontSize: "0.95rem",
						}}
					/>
				</div>

				{/* Filters */}
				<div
					style={{
						display: "flex",
						flexWrap: "wrap",
						gap: "1rem",
						alignItems: "center",
					}}
				>
					<div
						style={{
							display: "flex",
							alignItems: "center",
							gap: "0.5rem",
							fontSize: "0.9rem",
							color: "var(--text-muted)",
						}}
					>
						<SlidersHorizontal size={16} />
						<span>Filters:</span>
					</div>

					<select
						value={selectedOS}
						onChange={(e) => setSelectedOS(e.target.value)}
						style={{
							background: "transparent",
							border: "1px solid var(--border-subtle)",
							borderRadius: "8px",
							color: "var(--text-primary)",
							padding: "0.5rem 1rem",
							outline: "none",
							cursor: "pointer",
							fontSize: "0.9rem",
						}}
					>
						<option value="ALL">All Operating Systems</option>
						<option value="WIN">Windows</option>
						<option value="LINUX">Linux</option>
						<option value="WSL">WSL</option>
					</select>

					<select
						value={cudaFilter}
						onChange={(e) => setCudaFilter(e.target.value)}
						style={{
							background: "transparent",
							border: "1px solid var(--border-subtle)",
							borderRadius: "8px",
							color: "var(--text-primary)",
							padding: "0.5rem 1rem",
							outline: "none",
							cursor: "pointer",
							fontSize: "0.9rem",
						}}
					>
						<option value="ALL">All CUDA Configs</option>
						<option value="REQUIRED">CUDA Required</option>
						<option value="OPTIONAL">CPU / Non-CUDA</option>
					</select>
				</div>
			</motion.div>

			{/* Grid of Profiles */}
			<AnimatePresence mode="popLayout">
				{filteredProfiles.length === 0 ? (
					<motion.div
						initial={{ opacity: 0 }}
						animate={{ opacity: 1 }}
						exit={{ opacity: 0 }}
						style={{
							textAlign: "center",
							padding: "4rem 0",
							color: "var(--text-secondary)",
						}}
					>
						<Layers
							size={48}
							style={{ margin: "0 auto 1.5rem", opacity: 0.5 }}
						/>
						<h3>No profiles matched your search or filters.</h3>
						<p style={{ color: "var(--text-muted)", marginTop: "0.5rem" }}>
							Try clearing your search query or filters to browse all options.
						</p>
					</motion.div>
				) : (
					<motion.div
						layout
						style={{
							display: "grid",
							gridTemplateColumns: "repeat(auto-fill, minmax(360px, 1fr))",
							gap: "2rem",
						}}
					>
						{filteredProfiles.map((p, index) => (
							<motion.div
								key={p.slug}
								layout
								initial={{ opacity: 0, y: 20 }}
								animate={{ opacity: 1, y: 0 }}
								exit={{ opacity: 0, scale: 0.95 }}
								transition={{ duration: 0.3, delay: index * 0.05 }}
								className="glass-panel"
								style={{
									padding: "2rem",
									display: "flex",
									flexDirection: "column",
									justifyContent: "space-between",
									border: "1px solid var(--border-subtle)",
									position: "relative",
									overflow: "hidden",
								}}
								whileHover={{
									y: -5,
									borderColor: "var(--brand-primary)",
									boxShadow: "var(--shadow-glow)",
								}}
							>
								{/* Glow effect on hover */}
								<div
									style={{
										position: "absolute",
										top: 0,
										right: 0,
										width: "100px",
										height: "100px",
										background:
											"radial-gradient(circle, rgba(99,102,241,0.08) 0%, transparent 70%)",
										pointerEvents: "none",
									}}
								/>

								<div>
									<div
										style={{
											display: "flex",
											justifyContent: "space-between",
											alignItems: "flex-start",
											marginBottom: "1rem",
										}}
									>
										<div
											style={{
												background: "rgba(99, 102, 241, 0.1)",
												color: "var(--brand-primary)",
												padding: "0.5rem",
												borderRadius: "8px",
											}}
										>
											<Box size={24} />
											<button
												onClick={() => toggleFavorite(p.slug)}
												aria-label={favorites.includes(p.slug) ? `Remove ${p.slug} from favorites` : `Add ${p.slug} to favorites`}
												aria-pressed={favorites.includes(p.slug)}
												title={favorites.includes(p.slug) ? `Remove ${p.slug} from favorites` : `Add ${p.slug} to favorites`}
												style={{
													background: "transparent",
													border: "none",
													cursor: "pointer",
													marginLeft: "10px",
												}}
											>
												<Star
													size={20}
													fill={favorites.includes(p.slug) ? "gold" : "none"}
												/>
											</button>
										</div>
										<div style={{ display: "flex", gap: "0.5rem" }}>
											{p.cuda_required ? (
												<span
													style={{
														fontSize: "0.75rem",
														background: "rgba(16, 185, 129, 0.1)",
														color: "var(--brand-accent)",
														padding: "0.2rem 0.5rem",
														borderRadius: "4px",
														fontWeight: 600,
													}}
												>
													CUDA Req
												</span>
											) : (
												<span
													style={{
														fontSize: "0.75rem",
														background: "rgba(255, 255, 255, 0.05)",
														color: "var(--text-muted)",
														padding: "0.2rem 0.5rem",
														borderRadius: "4px",
													}}
												>
													CPU / CPU+GPU
												</span>
											)}
										</div>
									</div>

									<h3 style={{ fontSize: "1.4rem", marginBottom: "0.75rem" }}>
										{p.name}
									</h3>
									<p
										style={{
											color: "var(--text-secondary)",
											fontSize: "0.92rem",
											lineHeight: 1.5,
											marginBottom: "1.5rem",
											minHeight: "4.5rem",
										}}
									>
										{p.description ?? "No description available."}
									</p>

									{/* OS & Python specs */}
									<div
										style={{
											borderTop: "1px solid var(--border-subtle)",
											paddingTop: "1rem",
											marginBottom: "1.5rem",
										}}
									>
										<div
											style={{
												display: "flex",
												justifyContent: "space-between",
												fontSize: "0.85rem",
												marginBottom: "0.5rem",
											}}
										>
											<span style={{ color: "var(--text-muted)" }}>
												Platforms:
											</span>
											<span
												style={{
													color: "var(--text-primary)",
													fontWeight: 500,
												}}
											>
												{p.os_support.join(", ")}
											</span>
										</div>
										<div
											style={{
												display: "flex",
												justifyContent: "space-between",
												fontSize: "0.85rem",
											}}
										>
											<span style={{ color: "var(--text-muted)" }}>
												Python:
											</span>
											<span
												style={{
													color: "var(--text-primary)",
													fontFamily: "var(--font-mono)",
												}}
											>
												{p.python_versions.join(", ")}
											</span>
										</div>
									</div>

									{/* Packages previews */}
									<div
										style={{
											display: "flex",
											flexWrap: "wrap",
											gap: "0.5rem",
											marginBottom: "2rem",
										}}
									>
										{p.packages &&
											p.packages.slice(0, 3).map((pkg) => (
												<span
													key={pkg.package_name}
													style={{
														fontSize: "0.8rem",
														background: "rgba(255, 255, 255, 0.04)",
														border: "1px solid var(--border-subtle)",
														padding: "0.2rem 0.5rem",
														borderRadius: "4px",
														color: "var(--text-secondary)",
													}}
												>
													{pkg.package_name}@{pkg.version_spec}
												</span>
											))}
										{p.packages && p.packages.length > 3 && (
											<span
												style={{
													fontSize: "0.8rem",
													color: "var(--text-muted)",
													alignSelf: "center",
												}}
											>
												+{p.packages.length - 3} more
											</span>
										)}
									</div>
								</div>

								<div style={{ display: "flex", gap: "1rem", width: "100%" }}>
									<motion.div
  whileHover={{ scale: 1.05, y: -2 }}
  whileTap={{ scale: 0.96 }}
  style={{ flex: 1.5 }}
>
  <Link
    href={`/generate?profile=${p.slug}`}
    className="btn btn-primary"
    style={{
      width: "100%",
      fontSize: "0.9rem",
      padding: "0.6rem 0",
      display: "flex",
      gap: "0.4rem",
      justifyContent: "center",
      alignItems: "center",
    }}
  >
    <motion.div whileHover={{ x: 3, rotate: 10 }}>
      <Terminal size={14} />
    </motion.div>
    Generate
  </Link>
</motion.div>
								</div>
							</motion.div>
						))}
					</motion.div>
				)}
			</AnimatePresence>
		</div>
	);
}
