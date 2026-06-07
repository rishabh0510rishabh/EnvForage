"use client";

import { motion } from "framer-motion";
import {
	ArrowLeft,
	Box,
	CheckCircle,
	Cpu,
	ShieldAlert,
	Terminal,
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "../../../services/api";
import type { Profile } from "../../../types";

export default function ProfileDetailPage() {
	const params = useParams();
	const slug = params.slug as string;

	const [profile, setProfile] = useState<Profile | null>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		async function loadProfile() {
			try {
				const data = await api.getProfile(slug);
				setProfile(data);
			} catch (err) {
				setError(err instanceof Error ? err.message : "Failed to load profile");
			} finally {
				setLoading(false);
			}
		}
		loadProfile();
	}, [slug]);

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
				<h2>Loading Profile Data...</h2>
			</div>
		);
	}

	if (error || !profile) {
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
				<h2 style={{ marginBottom: "1rem" }}>Error Loading Profile</h2>
				<p style={{ color: "var(--text-secondary)", marginBottom: "2rem" }}>
					{error}
				</p>
				<Link href="/profiles" className="btn btn-secondary">
					← Back to Profiles
				</Link>
			</div>
		);
	}

	return (
		<div
			className="container"
			style={{ paddingTop: "3rem", paddingBottom: "6rem" }}
		>
			<Link
				href="/profiles"
				style={{
					display: "inline-flex",
					alignItems: "center",
					gap: "0.5rem",
					color: "var(--text-muted)",
					marginBottom: "2rem",
					fontSize: "0.9rem",
				}}
			>
				<ArrowLeft size={16} /> Back to Profiles
			</Link>

			<div
				style={{
					display: "grid",
					gridTemplateColumns: "1fr 350px",
					gap: "3rem",
					alignItems: "start",
				}}
			>
				{/* Main Content */}
				<motion.div
					initial={{ opacity: 0, x: -20 }}
					animate={{ opacity: 1, x: 0 }}
					transition={{ duration: 0.4 }}
				>
					<div style={{ marginBottom: "3rem" }}>
						<h1 style={{ fontSize: "3.5rem", marginBottom: "1rem" }}>
							{profile.name}
						</h1>
						<p
							style={{
								fontSize: "1.2rem",
								color: "var(--text-secondary)",
								lineHeight: 1.6,
								maxWidth: "800px",
							}}
						>
							{profile.description}
						</p>
					</div>

					<div
						style={{
							display: "flex",
							gap: "1rem",
							marginBottom: "3rem",
							flexWrap: "wrap",
						}}
					>
						<div
							className="glass-panel"
							style={{ padding: "1.5rem", flex: "1 1 200px" }}
						>
							<div
								style={{
									color: "var(--text-muted)",
									fontSize: "0.85rem",
									marginBottom: "0.5rem",
									textTransform: "uppercase",
									letterSpacing: "0.05em",
									fontWeight: 600,
								}}
							>
								OS Support
							</div>
							<div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
								{profile.os_support.map((os) => (
									<span
										key={os}
										style={{
											background: "rgba(255,255,255,0.05)",
											padding: "0.25rem 0.5rem",
											borderRadius: "4px",
											fontSize: "0.9rem",
										}}
									>
										{os}
									</span>
								))}
							</div>
						</div>

						<div
							className="glass-panel"
							style={{ padding: "1.5rem", flex: "1 1 200px" }}
						>
							<div
								style={{
									color: "var(--text-muted)",
									fontSize: "0.85rem",
									marginBottom: "0.5rem",
									textTransform: "uppercase",
									letterSpacing: "0.05em",
									fontWeight: 600,
								}}
							>
								CUDA Requirement
							</div>
							<div
								style={{
									fontSize: "1.1rem",
									fontWeight: 500,
									color: profile.cuda_required
										? "var(--brand-accent)"
										: "var(--text-primary)",
								}}
							>
								{profile.cuda_required ? "Required" : "Optional / None"}
							</div>
							{profile.cuda_versions && (
								<div
									style={{
										fontSize: "0.85rem",
										color: "var(--text-secondary)",
										marginTop: "0.5rem",
									}}
								>
									Supported: {profile.cuda_versions.join(", ")}
								</div>
							)}
						</div>
					</div>

					<h2 style={{ fontSize: "2rem", marginBottom: "1.5rem" }}>
						Included Packages
					</h2>
					<div className="glass-panel" style={{ overflow: "hidden" }}>
						<table
							style={{
								width: "100%",
								borderCollapse: "collapse",
								textAlign: "left",
							}}
						>
							<thead>
								<tr
									style={{
										background: "rgba(255,255,255,0.02)",
										borderBottom: "1px solid var(--border-subtle)",
									}}
								>
									<th
										style={{
											padding: "1rem 1.5rem",
											color: "var(--text-muted)",
											fontWeight: 500,
										}}
									>
										Package
									</th>
									<th
										style={{
											padding: "1rem 1.5rem",
											color: "var(--text-muted)",
											fontWeight: 500,
										}}
									>
										Version
									</th>
									<th
										style={{
											padding: "1rem 1.5rem",
											color: "var(--text-muted)",
											fontWeight: 500,
										}}
									>
										Core
									</th>
								</tr>
							</thead>
							<tbody>
								{profile.packages.map((pkg, idx) => (
									<tr
										key={pkg.package_name}
										style={{
											borderBottom:
												idx === profile.packages.length - 1
													? "none"
													: "1px solid var(--border-subtle)",
										}}
									>
										<td
											style={{
												padding: "1rem 1.5rem",
												display: "flex",
												alignItems: "center",
												gap: "0.75rem",
											}}
										>
											<Box size={16} color="var(--brand-primary)" />
											{pkg.package_name}
											{pkg.cuda_variant && (
												<span
													style={{
														fontSize: "0.7rem",
														background: "rgba(16, 185, 129, 0.1)",
														color: "var(--brand-accent)",
														padding: "0.1rem 0.4rem",
														borderRadius: "4px",
													}}
												>
													CUDA suffix
												</span>
											)}
										</td>
										<td
											style={{
												padding: "1rem 1.5rem",
												fontFamily: "var(--font-mono)",
											}}
										>
											{pkg.version_spec}
										</td>
										<td style={{ padding: "1rem 1.5rem" }}>
											{!pkg.is_optional ? (
												<CheckCircle size={18} color="var(--brand-accent)" />
											) : (
												<span style={{ color: "var(--text-muted)" }}>-</span>
											)}
										</td>
									</tr>
								))}
							</tbody>
						</table>
					</div>
				</motion.div>

				{/* Sidebar Actions */}
				<motion.div
					initial={{ opacity: 0, x: 20 }}
					animate={{ opacity: 1, x: 0 }}
					transition={{ duration: 0.4, delay: 0.1 }}
					style={{ position: "sticky", top: "6rem" }}
				>
					<div className="glass-panel" style={{ padding: "2rem" }}>
						<h3 style={{ fontSize: "1.2rem", marginBottom: "1rem" }}>
							Generate Script
						</h3>
						<p
							style={{
								color: "var(--text-secondary)",
								fontSize: "0.9rem",
								marginBottom: "2rem",
								lineHeight: 1.5,
							}}
						>
							Use the generation wizard to configure your OS, Python version,
							and output formats to get your deterministic setup script.
						</p>
						<Link
							href={`/generate?profile=${profile.slug}`}
							className="btn btn-primary"
							style={{
								width: "100%",
								marginBottom: "1rem",
								display: "flex",
								gap: "0.5rem",
								alignItems: "center",
								justifyContent: "center",
							}}
						>
							<Terminal size={18} />
							Open Wizard
						</Link>

						<div
							style={{
								borderTop: "1px solid var(--border-subtle)",
								margin: "1.5rem 0",
							}}
						/>

						<h4
							style={{
								fontSize: "0.9rem",
								color: "var(--text-muted)",
								marginBottom: "1rem",
								textTransform: "uppercase",
								letterSpacing: "0.05em",
							}}
						>
							Supported Python Versions
						</h4>
						<div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
							{profile.python_versions.map((py) => (
								<span
									key={py}
									style={{
										background: "rgba(255,255,255,0.05)",
										padding: "0.2rem 0.5rem",
										borderRadius: "4px",
										fontSize: "0.85rem",
										fontFamily: "var(--font-mono)",
									}}
								>
									{py}
								</span>
							))}
						</div>
					</div>
				</motion.div>
			</div>
		</div>
	);
}
