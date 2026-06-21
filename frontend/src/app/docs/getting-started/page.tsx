"use client";

import { useState } from "react";
import { Terminal, Copy, Check, Info } from "lucide-react";

export default function QuickStartPage() {
	const [activeOS, setActiveOS] = useState<"linux" | "windows" | "macos">("linux");
	const [activeStep, setActiveStep] = useState<1 | 2 | 3>(1);
	const [copiedId, setCopiedId] = useState<string>("");

	const copyText = (text: string, id: string) => {
		navigator.clipboard.writeText(text);
		setCopiedId(id);
		setTimeout(() => setCopiedId(""), 2000);
	};

	const installCommands = {
		linux: "pip install envforage",
		windows: "pip install envforage",
		macos: "brew install envforage || pip install envforage",
	};

	const auditCommands = {
		linux: "envforage audit --verbose",
		windows: "envforage.exe audit --verbose",
		macos: "envforage audit --verbose",
	};

	const generateCommands = {
		linux: "envforage generate --framework pytorch --export shell",
		windows: "envforage generate --framework pytorch --export powershell",
		macos: "envforage generate --framework pytorch --export shell",
	};

	// Mock outputs for the terminal simulator
	const terminalOutputs = {
		1: {
			cmd: installCommands[activeOS],
			output: `Collecting envforage
  Downloading envforage-2.0.0-py3-none-any.whl (42 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 42.1/42.1 kB 1.2 MB/s eta 0:00:00
Collecting psutil>=5.9.0 (from envforage)
  Downloading psutil-5.9.8-cp310-cp310-manylinux_2_12_x86_64.manylinux2010_x86_64.whl (278 kB)
Installing collected packages: psutil, envforage
Successfully installed envforage-2.0.0 psutil-5.9.8`,
		},
		2: {
			cmd: auditCommands[activeOS],
			output: `[envforage] Running system diagnostics...
[SYSTEM] OS Detected: ${activeOS === "windows" ? "Windows 11 Professional" : activeOS === "macos" ? "macOS Sonoma (v14.4)" : "Ubuntu 22.04 LTS (Linux)"}
[HARDWARE] CPU Cores: 16 threads | RAM: 32.4 GB detected
[HARDWARE] GPU Vendor: Nvidia Corp. (RTX 4090 - 24GB VRAM)
[DRIVERS] Active GPU Driver: 535.104
[CUDA] Core Library version: 12.1 detected
[INFO] Hardware query completed. Matrix resolution signature calculated.`,
		},
		3: {
			cmd: generateCommands[activeOS],
			output: `[envforage] Querying matrix core api...
[RESOLVER] Query signature matching PyTorch...
[RESOLVER] Compatibility match found!
  >> Chosen Python Target: 3.10
  >> Chosen CUDA SDK Target: 12.1
  >> Core Packages Selected: torch==2.1.0+cu121, torchvision==0.16.0+cu121
[COMPILER] Synthesizing output scripts...
[OK] Security validation filter checks passed. No unsafe shell targets.
[SUCCESS] Generated local installation script: setup_env.${activeOS === "windows" ? "ps1" : "sh"}`,
		},
	};

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
				<Terminal size={20} />
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
				Quick Start Guide
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
				Get EnvForage installed and run your first machine learning compatibility audit in under 5 minutes.
			</p>

			{/* System Requirements Callout */}
			<div
				style={{
					display: "flex",
					gap: "1rem",
					padding: "1.25rem 1.5rem",
					borderRadius: "12px",
					backgroundColor: "rgba(99, 102, 241, 0.05)",
					border: "1px solid rgba(99, 102, 241, 0.15)",
					marginBottom: "3rem",
					alignItems: "flex-start",
				}}
			>
				<div style={{ color: "var(--brand-primary)", marginTop: "2px" }}>
					<Info size={20} />
				</div>
				<div>
					<h4 style={{ margin: "0 0 0.5rem 0", fontWeight: 700, color: "var(--text-primary)", fontSize: "1rem" }}>
						Prerequisites & Requirements
					</h4>
					<ul style={{ margin: 0, paddingLeft: "1.2rem", fontSize: "0.95rem", color: "var(--text-secondary)", lineHeight: 1.6 }}>
						<li>Python 3.8, 3.9, 3.10, or 3.11 installed.</li>
						<li>Nvidia GPU & CUDA Drivers installed (required for local CUDA audits, otherwise mocks are used).</li>
						<li>Administrator or Root access (recommended for hardware query steps).</li>
					</ul>
				</div>
			</div>

			{/* OS Selection Tabs */}
			<div style={{ marginBottom: "2.5rem" }}>
				<h3 style={{ fontSize: "1.25rem", fontWeight: 700, marginBottom: "1rem", color: "var(--text-primary)" }}>
					Select Your Operating System
				</h3>
				<div
					style={{
						display: "flex",
						gap: "0.5rem",
						borderBottom: "1px solid var(--border-subtle)",
						paddingBottom: "2px",
					}}
				>
					{(["linux", "windows", "macos"] as const).map((os) => (
						<button
							key={os}
							onClick={() => setActiveOS(os)}
							style={{
								padding: "0.75rem 1.5rem",
								background: "none",
								border: "none",
								color: activeOS === os ? "var(--brand-primary)" : "var(--text-secondary)",
								borderBottom: activeOS === os ? "2px solid var(--brand-primary)" : "2px solid transparent",
								fontWeight: 600,
								fontSize: "0.925rem",
								cursor: "pointer",
								transition: "all var(--transition-fast)",
								textTransform: "capitalize",
							}}
						>
							{os === "macos" ? "macOS" : os}
						</button>
					))}
				</div>
			</div>

			{/* INTERACTIVE TERMINAL SIMULATOR */}
			<div style={{ marginBottom: "4rem" }}>
				<h3 style={{ fontSize: "1.35rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "1.25rem" }}>
					Interactive Setup Run
				</h3>
				
				<div style={{ display: "grid", gridTemplateColumns: "1fr", gap: "1.5rem" }}>
					{/* Steps Checklist Controls */}
					<div style={{ display: "flex", flexWrap: "wrap", gap: "1rem" }}>
						{([1, 2, 3] as const).map((step) => (
							<button
								key={step}
								onClick={() => setActiveStep(step)}
								style={{
									flex: "1 1 200px",
									display: "flex",
									alignItems: "center",
									gap: "0.75rem",
									padding: "1rem",
									borderRadius: "8px",
									backgroundColor: activeStep === step ? "rgba(99, 102, 241, 0.08)" : "var(--bg-secondary)",
									border: activeStep === step ? "1.5px solid var(--brand-primary)" : "1.5px solid var(--border-subtle)",
									textAlign: "left",
									cursor: "pointer",
									color: activeStep === step ? "var(--text-primary)" : "var(--text-secondary)",
									transition: "all var(--transition-fast)",
								}}
							>
								<div
									style={{
										width: "24px",
										height: "24px",
										borderRadius: "50%",
										backgroundColor: activeStep === step ? "var(--brand-primary)" : "var(--border-strong)",
										color: "#fff",
										display: "flex",
										alignItems: "center",
										justifyContent: "center",
										fontWeight: 700,
										fontSize: "0.8rem",
									}}
								>
									{step}
								</div>
								<div>
									<div style={{ fontWeight: 600, fontSize: "0.9rem" }}>
										{step === 1 ? "Install CLI" : step === 2 ? "Audit Workstation" : "Compile Environment"}
									</div>
								</div>
							</button>
						))}
					</div>

					{/* Terminal Shell Window */}
					<div
						style={{
							backgroundColor: "#09090b",
							border: "1px solid var(--border-strong)",
							borderRadius: "12px",
							overflow: "hidden",
							boxShadow: "var(--shadow-lg)",
							fontFamily: "var(--font-mono)",
							fontSize: "0.9rem",
						}}
					>
						{/* Window Topbar */}
						<div
							style={{
								backgroundColor: "#18181b",
								padding: "0.75rem 1rem",
								display: "flex",
								alignItems: "center",
								justifyContent: "space-between",
								borderBottom: "1px solid rgba(255, 255, 255, 0.05)",
							}}
						>
							<div style={{ display: "flex", gap: "0.35rem" }}>
								<span style={{ width: "12px", height: "12px", borderRadius: "50%", backgroundColor: "#ef4444", display: "inline-block" }}></span>
								<span style={{ width: "12px", height: "12px", borderRadius: "50%", backgroundColor: "#eab308", display: "inline-block" }}></span>
								<span style={{ width: "12px", height: "12px", borderRadius: "50%", backgroundColor: "#22c55e", display: "inline-block" }}></span>
							</div>
							<div style={{ color: "var(--text-muted)", fontSize: "0.75rem", fontWeight: 600 }}>
								bash - envforage
							</div>
							<div style={{ width: "42px" }}></div>
						</div>

						{/* Terminal Body */}
						<div style={{ padding: "1.25rem", color: "#f4f4f5", minHeight: "220px", display: "flex", flexDirection: "column", gap: "1rem", position: "relative" }}>
							{/* Prompt Line */}
							<div style={{ display: "flex", alignItems: "baseline", gap: "0.5rem" }}>
								<span style={{ color: "#22c55e", fontWeight: "bold" }}>user@workstation:~$</span>
								<span style={{ color: "#3b82f6" }}>{terminalOutputs[activeStep].cmd}</span>
							</div>
							{/* Console Output */}
							<div style={{ margin: 0, whiteSpace: "pre-wrap", color: "#e4e4e7", lineHeight: 1.6, fontFamily: "var(--font-mono)", fontSize: "0.9rem" }}>
								{terminalOutputs[activeStep].output}
							</div>

							{/* Terminal Actions */}
							<button
								onClick={() => copyText(terminalOutputs[activeStep].cmd, "terminal")}
								style={{
									position: "absolute",
									right: "1.25rem",
									top: "1.25rem",
									background: "rgba(255, 255, 255, 0.05)",
									border: "1px solid rgba(255, 255, 255, 0.1)",
									borderRadius: "6px",
									padding: "0.5rem",
									cursor: "pointer",
									color: copiedId === "terminal" ? "var(--brand-primary)" : "#a1a1aa",
									transition: "all var(--transition-fast)",
									display: "flex",
									alignItems: "center",
									gap: "0.25rem",
									fontSize: "0.8rem",
									fontWeight: 600,
								}}
							>
								{copiedId === "terminal" ? (
									<>
										<Check size={14} />
										<span>Copied</span>
									</>
								) : (
									<>
										<Copy size={14} />
										<span>Copy Command</span>
									</>
								)}
							</button>
						</div>
					</div>
				</div>
			</div>

			{/* Parameters Reference Table */}
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
				CLI Command Flags & Reference
			</h2>

			<div style={{ overflowX: "auto", marginBottom: "2rem" }}>
				<table style={{ width: "100%", borderCollapse: "collapse", color: "var(--text-secondary)", fontSize: "0.95rem" }}>
					<thead>
						<tr style={{ borderBottom: "2px solid var(--border-subtle)", textAlign: "left" }}>
							<th style={{ padding: "0.75rem 1rem", fontWeight: 700, color: "var(--text-primary)" }}>Flag</th>
							<th style={{ padding: "0.75rem 1rem", fontWeight: 700, color: "var(--text-primary)" }}>Type</th>
							<th style={{ padding: "0.75rem 1rem", fontWeight: 700, color: "var(--text-primary)" }}>Default</th>
							<th style={{ padding: "0.75rem 1rem", fontWeight: 700, color: "var(--text-primary)" }}>Description</th>
						</tr>
					</thead>
					<tbody>
						<tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
							<td style={{ padding: "1rem", fontFamily: "var(--font-mono)", color: "var(--brand-secondary)" }}>--framework</td>
							<td style={{ padding: "1rem" }}>string</td>
							<td style={{ padding: "1rem", fontFamily: "var(--font-mono)" }}>pytorch</td>
							<td style={{ padding: "1rem" }}>Target framework to build. Options: pytorch, tensorflow, jax</td>
						</tr>
						<tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
							<td style={{ padding: "1rem", fontFamily: "var(--font-mono)", color: "var(--brand-secondary)" }}>--export</td>
							<td style={{ padding: "1rem" }}>string</td>
							<td style={{ padding: "1rem", fontFamily: "var(--font-mono)" }}>shell</td>
							<td style={{ padding: "1rem" }}>Output file format. Options: shell, powershell, conda, dockerfile</td>
						</tr>
						<tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
							<td style={{ padding: "1rem", fontFamily: "var(--font-mono)", color: "var(--brand-secondary)" }}>--cuda</td>
							<td style={{ padding: "1rem" }}>string</td>
							<td style={{ padding: "1rem", fontFamily: "var(--font-mono)" }}>auto</td>
							<td style={{ padding: "1rem" }}>Override target CUDA version instead of running auto-detection.</td>
						</tr>
						<tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
							<td style={{ padding: "1rem", fontFamily: "var(--font-mono)", color: "var(--brand-secondary)" }}>--verbose</td>
							<td style={{ padding: "1rem" }}>flag</td>
							<td style={{ padding: "1rem", fontFamily: "var(--font-mono)" }}>false</td>
							<td style={{ padding: "1rem" }}>Enable detailed console output logging during environment check.</td>
						</tr>
					</tbody>
				</table>
			</div>
		</div>
	);
}
