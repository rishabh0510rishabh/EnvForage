"use client";

import Link from "next/link";
import { BookOpen, Terminal, Layers, Code, ArrowRight } from "lucide-react";

export default function DocsIndexPage() {
	return (
		<div style={{ paddingBottom: "2rem" }}>
			<div
				style={{
					display: "flex",
					alignItems: "center",
					gap: "0.75rem",
					color: "var(--brand-primary)",
					marginBottom: "1rem",
					fontWeight: 600,
					fontSize: "0.95rem",
				}}
			>
				<BookOpen size={20} />
				<span>Overview</span>
			</div>

			<h1
				style={{
					fontSize: "3rem",
					fontWeight: 800,
					letterSpacing: "-0.03em",
					lineHeight: 1.15,
					marginBottom: "1.5rem",
					color: "var(--text-primary)",
				}}
			>
				EnvForage Documentation
			</h1>

			<p
				style={{
					fontSize: "1.15rem",
					lineHeight: 1.7,
					color: "var(--text-secondary)",
					marginBottom: "2.5rem",
					maxWidth: "800px",
				}}
			>
				Welcome to the EnvForage documentation. EnvForage is a production-grade
				ML environment provisioning platform that automates one of the most
				frustrating parts of machine learning development: creating reliable,
				compatible development environments.
			</p>

			<h2
				style={{
					fontSize: "1.85rem",
					fontWeight: 700,
					marginTop: "3rem",
					marginBottom: "1.5rem",
					borderBottom: "1px solid var(--border-subtle)",
					paddingBottom: "0.5rem",
					color: "var(--text-primary)",
				}}
			>
				Explore the Guides
			</h2>

			<div
				style={{
					display: "grid",
					gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
					gap: "1.5rem",
					marginBottom: "4rem",
				}}
			>
				{/* Getting Started Card */}
				<Link
					href="/docs/getting-started"
					style={{
						display: "flex",
						flexDirection: "column",
						padding: "2rem",
						borderRadius: "12px",
						backgroundColor: "var(--bg-secondary)",
						border: "1px solid var(--border-subtle)",
						transition: "all var(--transition-fast)",
						height: "100%",
						textDecoration: "none",
					}}
					onMouseEnter={(e) => {
						e.currentTarget.style.borderColor = "var(--brand-primary)";
						e.currentTarget.style.transform = "translateY(-2px)";
					}}
					onMouseLeave={(e) => {
						e.currentTarget.style.borderColor = "var(--border-subtle)";
						e.currentTarget.style.transform = "translateY(0)";
					}}
				>
					<div
						style={{
							display: "flex",
							alignItems: "center",
							justifyContent: "center",
							width: "48px",
							height: "48px",
							borderRadius: "8px",
							backgroundColor: "rgba(99, 102, 241, 0.1)",
							color: "var(--brand-primary)",
							marginBottom: "1.5rem",
						}}
					>
						<Terminal size={24} />
					</div>
					<h3
						style={{
							fontSize: "1.25rem",
							fontWeight: 700,
							color: "var(--text-primary)",
							marginBottom: "0.75rem",
							display: "flex",
							alignItems: "center",
							justifyContent: "space-between",
						}}
					>
						Getting Started
						<ArrowRight size={16} />
					</h3>
					<p style={{ fontSize: "0.95rem", color: "var(--text-secondary)", lineHeight: 1.5, margin: 0 }}>
						Install the command line diagnostic agent and audit your hardware specs.
					</p>
				</Link>

				{/* Architecture Card */}
				<Link
					href="/docs/architecture"
					style={{
						display: "flex",
						flexDirection: "column",
						padding: "2rem",
						borderRadius: "12px",
						backgroundColor: "var(--bg-secondary)",
						border: "1px solid var(--border-subtle)",
						transition: "all var(--transition-fast)",
						height: "100%",
						textDecoration: "none",
					}}
					onMouseEnter={(e) => {
						e.currentTarget.style.borderColor = "var(--brand-primary)";
						e.currentTarget.style.transform = "translateY(-2px)";
					}}
					onMouseLeave={(e) => {
						e.currentTarget.style.borderColor = "var(--border-subtle)";
						e.currentTarget.style.transform = "translateY(0)";
					}}
				>
					<div
						style={{
							display: "flex",
							alignItems: "center",
							justifyContent: "center",
							width: "48px",
							height: "48px",
							borderRadius: "8px",
							backgroundColor: "rgba(99, 102, 241, 0.1)",
							color: "var(--brand-primary)",
							marginBottom: "1.5rem",
						}}
					>
						<Layers size={24} />
					</div>
					<h3
						style={{
							fontSize: "1.25rem",
							fontWeight: 700,
							color: "var(--text-primary)",
							marginBottom: "0.75rem",
							display: "flex",
							alignItems: "center",
							justifyContent: "space-between",
						}}
					>
						Architecture
						<ArrowRight size={16} />
					</h3>
					<p style={{ fontSize: "0.95rem", color: "var(--text-secondary)", lineHeight: 1.5, margin: 0 }}>
						Dive deep into the compatibility engine, script templates, and LLM diagnostics.
					</p>
				</Link>

				{/* API Card */}
				<Link
					href="/docs/api"
					style={{
						display: "flex",
						flexDirection: "column",
						padding: "2rem",
						borderRadius: "12px",
						backgroundColor: "var(--bg-secondary)",
						border: "1px solid var(--border-subtle)",
						transition: "all var(--transition-fast)",
						height: "100%",
						textDecoration: "none",
					}}
					onMouseEnter={(e) => {
						e.currentTarget.style.borderColor = "var(--brand-primary)";
						e.currentTarget.style.transform = "translateY(-2px)";
					}}
					onMouseLeave={(e) => {
						e.currentTarget.style.borderColor = "var(--border-subtle)";
						e.currentTarget.style.transform = "translateY(0)";
					}}
				>
					<div
						style={{
							display: "flex",
							alignItems: "center",
							justifyContent: "center",
							width: "48px",
							height: "48px",
							borderRadius: "8px",
							backgroundColor: "rgba(99, 102, 241, 0.1)",
							color: "var(--brand-primary)",
							marginBottom: "1.5rem",
						}}
					>
						<Code size={24} />
					</div>
					<h3
						style={{
							fontSize: "1.25rem",
							fontWeight: 700,
							color: "var(--text-primary)",
							marginBottom: "0.75rem",
							display: "flex",
							alignItems: "center",
							justifyContent: "space-between",
						}}
					>
						API Reference
						<ArrowRight size={16} />
					</h3>
					<p style={{ fontSize: "0.95rem", color: "var(--text-secondary)", lineHeight: 1.5, margin: 0 }}>
						Integrate version resolution programmatically using the FastAPI REST endpoints.
					</p>
				</Link>
			</div>

			<h2
				style={{
					fontSize: "1.85rem",
					fontWeight: 700,
					marginBottom: "1.5rem",
					borderBottom: "1px solid var(--border-subtle)",
					paddingBottom: "0.5rem",
					color: "var(--text-primary)",
				}}
			>
				Key Features
			</h2>

			<ul style={{ listStyleType: "none", padding: 0, color: "var(--text-secondary)", fontSize: "1.05rem", display: "flex", flexDirection: "column", gap: "1rem", marginBottom: "3rem" }}>
				<li style={{ display: "flex", alignItems: "flex-start", gap: "0.75rem" }}>
					<span style={{ color: "var(--brand-primary)", fontWeight: "bold", fontSize: "1.25rem", lineHeight: 1 }}>✓</span>
					<div>
						<strong>Deterministic Engine:</strong> Relies on a strict version compatibility mapping database instead of random guessing.
					</div>
				</li>
				<li style={{ display: "flex", alignItems: "flex-start", gap: "0.75rem" }}>
					<span style={{ color: "var(--brand-primary)", fontWeight: "bold", fontSize: "1.25rem", lineHeight: 1 }}>✓</span>
					<div>
						<strong>Local Diagnostics:</strong> Run environmental introspection commands locally and get instant CUDA, Python, and GPU status reports.
					</div>
				</li>
				<li style={{ display: "flex", alignItems: "flex-start", gap: "0.75rem" }}>
					<span style={{ color: "var(--brand-primary)", fontWeight: "bold", fontSize: "1.25rem", lineHeight: 1 }}>✓</span>
					<div>
						<strong>Safety Filter:</strong> Generated shell and powershell scripts undergo command-injection verification blocks.
					</div>
				</li>
			</ul>
		</div>
	);
}
