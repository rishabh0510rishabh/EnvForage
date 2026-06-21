"use client";

import { Layers, ShieldCheck, Database, Cpu, Terminal, GitMerge, FileText } from "lucide-react";

export default function ArchitecturePage() {
	const flowSteps = [
		{
			icon: Cpu,
			title: "1. Introspection (CLI)",
			desc: "The CLI agent executes local OS commands to extract hardware levels (GPU model, architecture, active driver version, and CUDA capabilities).",
		},
		{
			icon: GitMerge,
			title: "2. Compatibility Request",
			desc: "Introspected attributes are packaged into a structured JSON query payload and transmitted securely to the Matrix API Engine.",
		},
		{
			icon: Database,
			title: "3. Matrix Database Check",
			desc: "FastAPI resolves the optimum combinations by cross-referencing Nvidia support tables and version matching schemas.",
		},
		{
			icon: FileText,
			title: "4. Template compilation",
			desc: "The resolver merges framework configuration rules into secure output shell scripts, validating execution patterns against security policies.",
		},
	];

	return (
		<div style={{ paddingBottom: "4rem" }}>
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
				<Layers size={20} />
				<span>Documentation</span>
			</div>

			<h1
				style={{
					fontSize: "2.75rem",
					fontWeight: 800,
					fontFamily: "var(--font-display)",
					letterSpacing: "-0.03em",
					lineHeight: 1.15,
					marginBottom: "1.25rem",
					color: "var(--text-primary)",
				}}
			>
				Architecture Overview
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
				EnvForage utilizes a client-server architecture built for fast, deterministic, and safe dependency resolution in GPU-accelerated workloads.
			</p>

			{/* Architecture Diagram Image */}
			<div
				style={{
					width: "100%",
					borderRadius: "16px",
					overflow: "hidden",
					border: "1px solid var(--border-subtle)",
					boxShadow: "var(--shadow-lg)",
					marginBottom: "3rem",
					backgroundColor: "rgba(255, 255, 255, 0.01)",
				}}
			>
				{/* eslint-disable-next-line @next/next/no-img-element */}
				<img
					src="/architecture_diagram.png"
					alt="EnvForage System Architecture Diagram"
					style={{
						width: "100%",
						height: "auto",
						display: "block",
					}}
				/>
			</div>

			{/* Flow Diagram / Steps Timeline */}
			<h2
				style={{
					fontSize: "1.65rem",
					fontWeight: 700,
					marginTop: "2.5rem",
					marginBottom: "1.5rem",
					color: "var(--text-primary)",
				}}
			>
				The Matrix Resolution Lifecycle
			</h2>

			<div
				style={{
					display: "grid",
					gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
					gap: "1rem",
					marginBottom: "3rem",
				}}
			>
				{flowSteps.map((step, idx) => {
					const StepIcon = step.icon;
					return (
						<div
							key={idx}
							style={{
								padding: "1.5rem",
								borderRadius: "12px",
								backgroundColor: "var(--bg-secondary)",
								border: "1px solid var(--border-subtle)",
								display: "flex",
								flexDirection: "column",
								gap: "0.75rem",
								position: "relative",
							}}
						>
							<div
								style={{
									display: "flex",
									alignItems: "center",
									justifyContent: "center",
									width: "40px",
									height: "40px",
									borderRadius: "8px",
									backgroundColor: "rgba(99, 102, 241, 0.1)",
									color: "var(--brand-primary)",
								}}
							>
								<StepIcon size={20} />
							</div>
							<h4 style={{ margin: 0, fontWeight: 700, color: "var(--text-primary)", fontSize: "1.05rem" }}>
								{step.title}
							</h4>
							<p style={{ margin: 0, fontSize: "0.875rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
								{step.desc}
							</p>
						</div>
					);
				})}
			</div>

			{/* Architecture Layers */}
			<h2
				style={{
					fontSize: "1.65rem",
					fontWeight: 700,
					marginTop: "2.5rem",
					marginBottom: "1.5rem",
					color: "var(--text-primary)",
				}}
			>
				Core Components
			</h2>

			<div style={{ display: "flex", flexDirection: "column", gap: "1.5rem", marginBottom: "3rem" }}>
				{/* Layer 1 */}
				<div
					style={{
						display: "flex",
						gap: "1.5rem",
						padding: "1.5rem",
						borderRadius: "12px",
						backgroundColor: "var(--bg-secondary)",
						border: "1px solid var(--border-subtle)",
						alignItems: "flex-start",
					}}
				>
					<div
						style={{
							padding: "12px",
							borderRadius: "8px",
							backgroundColor: "rgba(59, 130, 246, 0.1)",
							color: "#3b82f6",
							display: "flex",
							flexShrink: 0,
						}}
					>
						<Terminal size={24} />
					</div>
					<div>
						<h3 style={{ margin: "0 0 0.5rem 0", fontSize: "1.2rem", fontWeight: 700, color: "var(--text-primary)" }}>
							The CLI Agent (Local Introspection Engine)
						</h3>
						<p style={{ margin: 0, fontSize: "0.95rem", color: "var(--text-secondary)", lineHeight: 1.6 }}>
							A lightweight, dependency-free Python client that uses platform libraries to query hardware specifics like system processor counts, driver version registries, and target libraries. It verifies active shell contexts and prepares environment profiles.
						</p>
					</div>
				</div>

				{/* Layer 2 */}
				<div
					style={{
						display: "flex",
						gap: "1.5rem",
						padding: "1.5rem",
						borderRadius: "12px",
						backgroundColor: "var(--bg-secondary)",
						border: "1px solid var(--border-subtle)",
						alignItems: "flex-start",
					}}
				>
					<div
						style={{
							padding: "12px",
							borderRadius: "8px",
							backgroundColor: "rgba(34, 197, 94, 0.1)",
							color: "#22c55e",
							display: "flex",
							flexShrink: 0,
						}}
					>
						<Layers size={24} />
					</div>
					<div>
						<h3 style={{ margin: "0 0 0.5rem 0", fontSize: "1.2rem", fontWeight: 700, color: "var(--text-primary)" }}>
							The FastAPI Resolver Engine (Backend Service)
						</h3>
						<p style={{ margin: 0, fontSize: "0.95rem", color: "var(--text-secondary)", lineHeight: 1.6 }}>
							The centralized API handles version matching. Using a structured compatibility registry model, the resolver checks constraints (e.g. PyTorch v2.1 requires CUDA v11.8 or v12.1, which requires Nvidia driver &gt;= 525) and chooses matching parameters without dependency bloat.
						</p>
					</div>
				</div>

				{/* Layer 3 */}
				<div
					style={{
						display: "flex",
						gap: "1.5rem",
						padding: "1.5rem",
						borderRadius: "12px",
						backgroundColor: "var(--bg-secondary)",
						border: "1px solid var(--border-subtle)",
						alignItems: "flex-start",
					}}
				>
					<div
						style={{
							padding: "12px",
							borderRadius: "8px",
							backgroundColor: "rgba(168, 85, 247, 0.1)",
							color: "#a855f7",
							display: "flex",
							flexShrink: 0,
						}}
					>
						<ShieldCheck size={24} />
					</div>
					<div>
						<h3 style={{ margin: "0 0 0.5rem 0", fontSize: "1.2rem", fontWeight: 700, color: "var(--text-primary)" }}>
							The Security Filter & Template Compiler
						</h3>
						<p style={{ margin: 0, fontSize: "0.95rem", color: "var(--text-secondary)", lineHeight: 1.6 }}>
							Outputs generated scripts (Bash, PowerShell, or Dockerfile). This compiler includes structural validations to filter out malicious CLI arguments, escaping variables, and locking down executable targets.
						</p>
					</div>
				</div>
			</div>

			{/* Security Callout */}
			<div
				style={{
					display: "flex",
					gap: "1rem",
					padding: "1.25rem 1.5rem",
					borderRadius: "12px",
					backgroundColor: "rgba(34, 197, 94, 0.05)",
					border: "1px solid rgba(34, 197, 94, 0.15)",
					marginBottom: "3rem",
					alignItems: "flex-start",
				}}
			>
				<div style={{ color: "#22c55e", marginTop: "2px" }}>
					<ShieldCheck size={20} />
				</div>
				<div>
					<h4 style={{ margin: "0 0 0.5rem 0", fontWeight: 700, color: "var(--text-primary)", fontSize: "1rem" }}>
						Security Sandboxing
					</h4>
					<p style={{ margin: 0, fontSize: "0.95rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
						EnvForage implements a strict sanitation filter. Any command execution paths are evaluated against an active whitelist. Shell scripts do not pull external binaries dynamically without structural signature checking.
					</p>
				</div>
			</div>
		</div>
	);
}
