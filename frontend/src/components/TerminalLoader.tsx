"use client";

import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, Server, Terminal, Wifi } from "lucide-react";
import React, { useEffect, useRef, useState } from "react";

interface TerminalLoaderProps {
	targetOs?: string;
	profileName?: string;
	pythonVersion?: string;
	cudaVersion?: string;
	isResolved?: boolean;
	onComplete: () => void;
	title?: string;
}

interface LogItem {
	text: string;
	type:
		| "info"
		| "success"
		| "warn"
		| "error"
		| "input"
		| "network"
		| "compiler";
	minProgress: number;
}

export default function TerminalLoader({
	targetOs = "LINUX",
	profileName = "PyTorch",
	pythonVersion = "3.10",
	cudaVersion,
	isResolved = true,
	onComplete,
	title = "EnvForage Environment Compiler",
}: TerminalLoaderProps) {
	const [progress, setProgress] = useState(0);
	const scrollContainerRef = useRef<HTMLDivElement>(null);

	// Generate logs dynamic configuration
	const logSequence: LogItem[] = [
		{
			text: `envforage compile --profile="${profileName}" --os="${targetOs}" --python="${pythonVersion}"${
				cudaVersion ? ` --cuda="${cudaVersion}"` : ""
			}`,
			type: "input",
			minProgress: 0,
		},
		{
			text: "[system] Initializing EnvForage loading sequence...",
			type: "info",
			minProgress: 4,
		},
		{
			text: "[system] Loading security policies and environment constraints...",
			type: "info",
			minProgress: 10,
		},
		{
			text: "[network] Resolving repository endpoint and telemetry pathways...",
			type: "network",
			minProgress: 16,
		},
		{
			text: "[network] SECURE CONNECTION ESTABLISHED (TLS 1.3, AES-256-GCM)",
			type: "success",
			minProgress: 22,
		},
		{
			text: "[host] Analyzing target environment parameters:",
			type: "info",
			minProgress: 28,
		},
		{
			text: `  → Target OS Platform : ${targetOs}`,
			type: "compiler",
			minProgress: 32,
		},
		{
			text: `  → Python Version    : ${pythonVersion}`,
			type: "compiler",
			minProgress: 36,
		},
		{
			text: `  → CUDA Acceleration : ${cudaVersion ? `v${cudaVersion}` : "DISABLED"}`,
			type: "compiler",
			minProgress: 40,
		},
		{
			text: `[host] Fetching remote device profile details for "${profileName}"...`,
			type: "network",
			minProgress: 46,
		},
		{
			text: "[compiler] Building custom installation dependency matrices...",
			type: "info",
			minProgress: 52,
		},
		{
			text: "[compiler] Resolving Python dependencies and system binaries...",
			type: "info",
			minProgress: 58,
		},
		{
			text: "[compiler] Compiling build scripts (setup.sh / setup.ps1)...",
			type: "compiler",
			minProgress: 65,
		},
		{
			text: "[compiler] Generating workspace requirements and Lockfiles...",
			type: "compiler",
			minProgress: 72,
		},
		{
			text: "[security] Triggering AI-powered Safety Filter validation...",
			type: "info",
			minProgress: 78,
		},
		{
			text: "[security] Checking for privilege escalations & system configuration hazards...",
			type: "warn",
			minProgress: 84,
		},
		{
			text: "[security] Validation SUCCESS: 0 hazards detected, signature verified",
			type: "success",
			minProgress: 90,
		},
		{
			text: "[system] Optimizing scripts for target hardware architecture...",
			type: "info",
			minProgress: 94,
		},
		{
			text: "[system] Exporting final workspace manifests...",
			type: "info",
			minProgress: 97,
		},
		{
			text: "[system] Compilation COMPLETED successfully. Assets ready.",
			type: "success",
			minProgress: 100,
		},
	];

	// Derived logs visible based on progress
	const logs = logSequence.filter((item) => progress >= item.minProgress);

	// Auto-scroll terminal logs inside its own container
	useEffect(() => {
		if (scrollContainerRef.current) {
			scrollContainerRef.current.scrollTop =
				scrollContainerRef.current.scrollHeight;
		}
	}, [logs.length]);

	// Progress count-up simulation logic
	useEffect(() => {
		const updateProgress = () => {
			setProgress((prev) => {
				if (prev >= 100) {
					return 100;
				}

				// Pause / slow down at 95% if not yet resolved from the API
				if (prev >= 95 && !isResolved) {
					// Micro increments to feel active
					return Math.min(95.5, prev + 0.05);
				}

				// Random simulated compilation increments
				const step = Math.random() * 5 + 2; // 2% to 7% per interval
				const next = prev + step;

				if (next >= 100) {
					return 100;
				}
				return next;
			});
		};

		// Fast pace early, slows down around compilation steps, then wraps up
		const getIntervalTime = () => {
			if (progress < 30) return 80;
			if (progress < 75) return 150; // compilation takes more time
			if (progress < 95) return 100;
			return 50; // wrap up speed
		};

		const timer = setInterval(updateProgress, getIntervalTime());

		return () => clearInterval(timer);
	}, [progress, isResolved]);

	// Trigger onComplete when hitting 100
	useEffect(() => {
		if (progress >= 100) {
			const delay = setTimeout(() => {
				onComplete();
			}, 600); // Small delay to let user see "100%" and final success log
			return () => clearTimeout(delay);
		}
	}, [progress, onComplete]);

	// Progress Matrix block styling helper
	const renderProgressMatrix = () => {
		const totalBlocks = 20;
		const filledBlocks = Math.floor((progress / 100) * totalBlocks);

		return (
			<div style={{ display: "flex", gap: "3px", alignItems: "center" }}>
				{Array.from({ length: totalBlocks }).map((_, idx) => {
					const isFilled = idx < filledBlocks;
					return (
						<motion.div
							key={idx}
							animate={
								isFilled
									? { scale: [1, 1.1, 1], opacity: 1 }
									: { scale: 1, opacity: 0.2 }
							}
							transition={{ duration: 0.3 }}
							style={{
								width: "8px",
								height: "14px",
								borderRadius: "2px",
								background: isFilled
									? "linear-gradient(to bottom, var(--brand-secondary), var(--brand-primary))"
									: "rgba(255, 255, 255, 0.15)",
								boxShadow: isFilled ? "0 0 6px var(--brand-primary)" : "none",
							}}
						/>
					);
				})}
			</div>
		);
	};

	const getLogColor = (type: LogItem["type"]) => {
		switch (type) {
			case "input":
				return "var(--text-primary)";
			case "success":
				return "var(--brand-accent)";
			case "warn":
				return "#f59e0b";
			case "error":
				return "#ef4444";
			case "network":
				return "#3b82f6";
			case "compiler":
				return "#a855f7";
			default:
				return "var(--text-secondary)";
		}
	};

	return (
		<div
			style={{
				width: "100%",
				maxWidth: "750px",
				margin: "0 auto",
				perspective: "1000px",
			}}
		>
			<motion.div
				initial={{ opacity: 0, y: 30, rotateX: 5 }}
				animate={{ opacity: 1, y: 0, rotateX: 0 }}
				exit={{ opacity: 0, scale: 0.95 }}
				transition={{ duration: 0.5, ease: "easeOut" }}
				className="glass-panel"
				style={{
					border: "1px solid rgba(99, 102, 241, 0.2)",
					boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.5), var(--glow-indigo)",
					overflow: "hidden",
					background: "rgba(10, 10, 15, 0.88)",
					position: "relative",
				}}
			>
				{/* Terminal Header Toolbar */}
				<div
					style={{
						padding: "0.85rem 1.25rem",
						background: "rgba(18, 18, 25, 0.95)",
						borderBottom: "1px solid rgba(255, 255, 255, 0.05)",
						display: "flex",
						justifyContent: "space-between",
						alignItems: "center",
					}}
				>
					{/* Windows buttons with subtle neon glow on hover */}
					<div style={{ display: "flex", gap: "8px" }}>
						<span
							style={{
								width: "12px",
								height: "12px",
								borderRadius: "50%",
								background: "#ef4444",
								boxShadow: "0 0 8px rgba(239, 68, 68, 0.4)",
								cursor: "pointer",
							}}
						/>
						<span
							style={{
								width: "12px",
								height: "12px",
								borderRadius: "50%",
								background: "#f59e0b",
								boxShadow: "0 0 8px rgba(245, 158, 11, 0.4)",
								cursor: "pointer",
							}}
						/>
						<span
							style={{
								width: "12px",
								height: "12px",
								borderRadius: "50%",
								background: "#10b981",
								boxShadow: "0 0 8px rgba(16, 185, 129, 0.4)",
								cursor: "pointer",
							}}
						/>
					</div>

					{/* Window Title */}
					<div
						style={{
							fontFamily: "var(--font-mono)",
							fontSize: "0.8rem",
							color: "var(--text-secondary)",
							fontWeight: 500,
							display: "flex",
							alignItems: "center",
							gap: "8px",
						}}
					>
						<Terminal size={14} color="var(--brand-primary)" />
						<span>{title}</span>
					</div>

					{/* Telemetry connection status badge */}
					<div
						style={{
							display: "flex",
							alignItems: "center",
							gap: "6px",
							fontSize: "0.7rem",
							fontFamily: "var(--font-mono)",
							color: "var(--brand-accent)",
							background: "rgba(16, 185, 129, 0.1)",
							padding: "2px 8px",
							borderRadius: "4px",
							border: "1px solid rgba(16, 185, 129, 0.2)",
						}}
					>
						<Wifi size={10} />
						<span style={{ letterSpacing: "0.05em" }}>TELEMETRY_CONNECTED</span>
					</div>
				</div>

				{/* Scanline CRT overlay effect */}
				<div
					style={{
						position: "absolute",
						top: 0,
						left: 0,
						right: 0,
						bottom: 0,
						backgroundImage:
							"linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%)",
						backgroundSize: "100% 4px",
						pointerEvents: "none",
						zIndex: 10,
						opacity: 0.4,
					}}
				/>

				{/* Terminal Body Console */}
				<div
					ref={scrollContainerRef}
					style={{
						padding: "1.5rem",
						height: "320px",
						overflowY: "auto",
						display: "flex",
						flexDirection: "column",
						gap: "0.5rem",
						position: "relative",
					}}
					className="custom-scrollbar"
				>
					<AnimatePresence initial={false}>
						{logs.map((log, index) => (
							<motion.div
								key={index}
								initial={{ opacity: 0, y: 10, x: -5 }}
								animate={{ opacity: 1, y: 0, x: 0 }}
								transition={{ duration: 0.25 }}
								style={{
									fontFamily: "var(--font-mono)",
									fontSize: "0.875rem",
									lineHeight: "1.5",
									color: getLogColor(log.type),
									whiteSpace: "pre-wrap",
									display: "flex",
									gap: "0.5rem",
								}}
							>
								{log.type === "input" && (
									<span
										style={{ color: "var(--brand-accent)", fontWeight: "bold" }}
									>
										guest@envforage:~$
									</span>
								)}
								<span>{log.text}</span>
							</motion.div>
						))}
					</AnimatePresence>

					{/* Active compiling prompt blinking cursor */}
					{progress < 100 && (
						<div
							style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}
						>
							<span
								style={{
									fontFamily: "var(--font-mono)",
									fontSize: "0.875rem",
									color: "var(--brand-secondary)",
								}}
							>
								compiling:
							</span>
							<motion.span
								animate={{ opacity: [1, 0, 1] }}
								transition={{ repeat: Infinity, duration: 1 }}
								style={{
									width: "8px",
									height: "15px",
									background: "var(--brand-secondary)",
									display: "inline-block",
								}}
							/>
						</div>
					)}
					{/* removed consoleEndRef */}
				</div>

				{/* Progress Section */}
				<div
					style={{
						padding: "1.25rem 1.5rem",
						background: "rgba(12, 12, 18, 0.95)",
						borderTop: "1px solid rgba(255, 255, 255, 0.05)",
						display: "flex",
						flexDirection: "column",
						gap: "0.75rem",
					}}
				>
					<div
						style={{
							display: "flex",
							justifyContent: "space-between",
							alignItems: "center",
						}}
					>
						{/* Progress Matrix */}
						{renderProgressMatrix()}

						{/* Percentage counter */}
						<div
							style={{
								fontFamily: "var(--font-mono)",
								fontSize: "1.1rem",
								fontWeight: 700,
								color: "var(--brand-secondary)",
								display: "flex",
								alignItems: "center",
								gap: "8px",
							}}
						>
							<span>{Math.floor(progress)}%</span>
							{progress === 100 ? (
								<CheckCircle2
									size={16}
									color="var(--brand-accent)"
									className="text-glow"
								/>
							) : (
								<motion.div
									animate={{ rotate: 360 }}
									transition={{
										repeat: Infinity,
										duration: 1.5,
										ease: "linear",
									}}
									style={{ display: "inline-block", height: "14px" }}
								>
									<Server size={14} color="var(--brand-primary)" />
								</motion.div>
							)}
						</div>
					</div>

					{/* Telemetry info row */}
					<div
						style={{
							display: "flex",
							justifyContent: "space-between",
							fontSize: "0.75rem",
							fontFamily: "var(--font-mono)",
							color: "var(--text-muted)",
						}}
					>
						<span>
							STATUS:{" "}
							<span
								style={{
									color:
										progress === 100
											? "var(--brand-accent)"
											: "var(--brand-primary)",
									fontWeight: 600,
								}}
							>
								{progress === 100 ? "READY" : "BUILDING"}
							</span>
						</span>
						<span>
							THREAD_EXECUTION:{" "}
							{progress === 100
								? "DONE"
								: `${(((Math.floor(progress) * 7) % 3) + 1.5).toFixed(1)} MB/s`}
						</span>
					</div>
				</div>
			</motion.div>
		</div>
	);
}
