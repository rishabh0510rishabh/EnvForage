"use client";

import { motion } from "framer-motion";
import {
	ArrowRight,
	Check,
	Copy,
	Cpu,
	Sparkles,
	Terminal,
	Wrench,
} from "lucide-react";
import Link from "next/link";
import React, { useState } from "react";

export default function InstallPage() {
	const [copied, setCopied] = useState(false);
	const installCommand = "pip install envforage";

	const handleCopy = async () => {
		try {
			await navigator.clipboard.writeText(installCommand);
			setCopied(true);
			setTimeout(() => setCopied(false), 2000);
		} catch (err) {
			console.error("Failed to copy text: ", err);
		}
	};

	const steps = [
		{
			icon: Cpu,
			title: "1. Diagnose Your Machine",
			description:
				"Run hardware introspection to detect OS, RAM, GPU, VRAM, and CUDA details without an internet connection.",
			command: "envforage diagnose",
		},
		{
			icon: Sparkles,
			title: "2. Verify Compatibility",
			description:
				"Check if a specific ML environment profile is fully compatible with your current hardware setup.",
			command: "envforage verify --profile pytorch-cuda",
		},
		{
			icon: Wrench,
			title: "3. Auto-Fix or Generate Setup Scripts",
			description:
				"Generate deterministic setup and repair scripts (setup.sh, setup.ps1, Dockerfile) validated against our engine.",
			command: "envforage fix --profile pytorch-cuda",
		},
	];

	return (
		<div
			className="container"
			style={{ paddingTop: "4rem", paddingBottom: "6rem", maxWidth: "800px" } as React.CSSProperties}
		>
			{/* Hero Section */}
			<div style={{ textAlign: "center", marginBottom: "3.5rem" } as React.CSSProperties}>
				<motion.div
					initial={{ scale: 0.9, opacity: 0 }}
					animate={{ scale: 1, opacity: 1 }}
					transition={{ duration: 0.5 }}
				>
					<h1 style={{ fontSize: "3rem", marginBottom: "1rem" }}>
						Get Started with <span className="text-gradient">EnvForage</span>
					</h1>
					<p
						style={{
							color: "var(--text-secondary)",
							fontSize: "1.15rem",
							maxWidth: "600px",
							margin: "0 auto",
							lineHeight: "1.6",
						} as React.CSSProperties}
					>
						Install the lightweight diagnostic agent to scan your system and eliminate AI/ML dependency conflicts.
					</p>
				</motion.div>
			</div>

			{/* Installation Command Card */}
			<motion.div
				initial={{ opacity: 0, y: 15 }}
				animate={{ opacity: 1, y: 0 }}
				transition={{ delay: 0.1, duration: 0.5 }}
				className="glass-panel"
				style={{ padding: "2rem", marginBottom: "3rem" } as React.CSSProperties}
			>
				<div
					style={{
						display: "flex",
						alignItems: "center",
						gap: "0.5rem",
						marginBottom: "1rem",
						color: "var(--brand-primary)",
						fontSize: "0.85rem",
						fontWeight: 700,
						textTransform: "uppercase",
						letterSpacing: "0.05em",
					} as React.CSSProperties}
				>
					<Terminal size={16} /> Installation
				</div>
				<h2 style={{ fontSize: "1.35rem", marginBottom: "1.25rem" }}>
					Install via pip
				</h2>

				<div
					style={{
						display: "flex",
						alignItems: "center",
						justifyContent: "space-between",
						background: "rgba(0, 0, 0, 0.25)",
						border: "1px solid var(--border-strong)",
						borderRadius: "8px",
						padding: "1rem 1.25rem",
						fontFamily: "var(--font-mono)",
						fontSize: "1rem",
						marginBottom: "1rem",
					}}
				>
					<code style={{ color: "var(--text-primary)" }}>
						<span style={{ color: "var(--text-muted)", marginRight: "0.5rem" }}>
							$
						</span>
						{installCommand}
					</code>
					<button
						onClick={handleCopy}
						style={{
							background: "none",
							border: "none",
							cursor: "pointer",
							color: copied ? "var(--brand-accent)" : "var(--text-secondary)",
							display: "flex",
							alignItems: "center",
							gap: "0.4rem",
							fontSize: "0.85rem",
							fontWeight: 600,
							transition: "color var(--transition-fast)",
						}}
						title="Copy to clipboard"
					>
						{copied ? (
							<>
								<Check size={16} /> Copied
							</>
						) : (
							<>
								<Copy size={16} /> Copy
							</>
						)}
					</button>
				</div>
				<p style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
					Requires Python 3.8+ and pip. EnvForage CLI is fully supported on Linux, WSL2, and Windows.
				</p>
			</motion.div>

			{/* Usage Guide */}
			<div style={{ marginBottom: "4rem" }}>
				<h2 style={{ fontSize: "1.75rem", marginBottom: "2rem" }}>
					Quick Start Guide
				</h2>
				<div style={{ display: "flex", flexDirection: "column", gap: "1.75rem" }}>
					{steps.map((step, idx) => {
						const Icon = step.icon;
						return (
							<motion.div
								key={idx}
								initial={{ opacity: 0, x: -15 }}
								animate={{ opacity: 1, x: 0 }}
								transition={{ delay: 0.2 + idx * 0.1, duration: 0.5 }}
								style={{ display: "flex", gap: "1.25rem" }}
							>
								<div
									style={{
										width: "40px",
										height: "40px",
										borderRadius: "8px",
										background: "rgba(99, 102, 241, 0.08)",
										border: "1px solid rgba(99, 102, 241, 0.15)",
										display: "flex",
										alignItems: "center",
										justifyContent: "center",
										flexShrink: 0,
										color: "var(--brand-primary)",
									}}
								>
									<Icon size={20} />
								</div>
								<div style={{ flexGrow: 1 }}>
									<h3 style={{ fontSize: "1.1rem", marginBottom: "0.4rem" }}>
										{step.title}
									</h3>
									<p
										style={{
											color: "var(--text-secondary)",
											fontSize: "0.925rem",
											lineHeight: "1.6",
											marginBottom: "0.75rem",
										}}
									>
										{step.description}
									</p>
									<div
										style={{
											background: "rgba(0, 0, 0, 0.15)",
											border: "1px solid var(--border-subtle)",
											borderRadius: "6px",
											padding: "0.5rem 0.85rem",
											fontFamily: "var(--font-mono)",
											fontSize: "0.85rem",
											color: "var(--brand-primary)",
											display: "inline-block",
										}}
									>
										<code>$ {step.command}</code>
									</div>
								</div>
							</motion.div>
						);
					})}
				</div>
			</div>

			{/* Online Tools Callout */}
			<motion.div
				initial={{ opacity: 0, y: 15 }}
				animate={{ opacity: 1, y: 0 }}
				transition={{ delay: 0.5, duration: 0.5 }}
				className="glass-panel"
				style={{
					padding: "2rem",
					display: "flex",
					flexDirection: "column",
					gap: "1.5rem",
					alignItems: "center",
					textAlign: "center",
					background: "linear-gradient(135deg, rgba(99, 102, 241, 0.03), rgba(236, 72, 153, 0.03))",
					border: "1px solid rgba(99, 102, 241, 0.1)",
					marginBottom: "3rem",
				}}
			>
				<div>
					<h3 style={{ fontSize: "1.25rem", marginBottom: "0.5rem" }}>
						Prefer using Web tools?
					</h3>
					<p
						style={{
							color: "var(--text-secondary)",
							fontSize: "0.925rem",
							maxWidth: "500px",
						}}
					>
						You can also use our cloud-based wizard to generate scripts or analyze pasted diagnostic reports.
					</p>
				</div>
				<div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", justifyContent: "center" }}>
					<Link href="/generate" className="btn btn-primary" style={{ fontSize: "0.9rem" }}>
						Script Generator <ArrowRight size={16} style={{ marginLeft: "0.5rem" }} />
					</Link>
					<Link href="/diagnose" className="btn btn-secondary" style={{ fontSize: "0.9rem" }}>
						Online Diagnostics
					</Link>
				</div>
			</motion.div>

			{/* Return Link */}
			<div style={{ textAlign: "center" }}>
				<Link
					href="/"
					style={{
						fontSize: "0.9rem",
						color: "var(--text-muted)",
						textDecoration: "underline",
					}}
				>
					Back to Home Page
				</Link>
			</div>
		</div>
	);
}
