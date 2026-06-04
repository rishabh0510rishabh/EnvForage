"use client";

import { AnimatePresence, motion } from "framer-motion";
import {
	AlertCircle,
	AlertTriangle,
	Brain,
	Check,
	ChevronDown,
	ChevronUp,
	Copy,
	Download,
	Info,
	Loader2,
	Shield,
	Sparkles,
	Terminal,
	Wrench,
} from "lucide-react";
import { useState } from "react";
import { api } from "../../services/api";
import type {
	RepairResponse,
	TroubleshootRequest,
	TroubleshootResponse,
} from "../../types";

// Severity color/icon map
const severityConfig = {
	CRITICAL: {
		color: "#ef4444",
		bg: "rgba(239, 68, 68, 0.08)",
		border: "rgba(239, 68, 68, 0.25)",
		icon: AlertCircle,
		label: "Critical",
	},
	WARNING: {
		color: "#eab308",
		bg: "rgba(234, 179, 8, 0.08)",
		border: "rgba(234, 179, 8, 0.25)",
		icon: AlertTriangle,
		label: "Warning",
	},
	INFO: {
		color: "#6366f1",
		bg: "rgba(99, 102, 241, 0.08)",
		border: "rgba(99, 102, 241, 0.25)",
		icon: Info,
		label: "Info",
	},
};

// Sample diagnostic for the prefill button
const SAMPLE_DIAGNOSTIC = {
	agent_version: "1.0.0",
	os: {
		name: "Ubuntu 22.04.3 LTS",
		version: "22.04",
		architecture: "x86_64",
		wsl_version: null,
	},
	cpu: { brand: "Intel Core i9-13900K", cores: 24, threads: 32 },
	ram: { total_gb: 64, available_gb: 48 },
	gpus: [
		{
			name: "NVIDIA GeForce RTX 4090",
			vram_gb: 24,
			driver_version: "535.129.03",
			index: 0,
		},
	],
	cuda: {
		version: "11.8",
		toolkit_path: "/usr/local/cuda-11.8",
		cudnn_version: "8.7.0",
		nccl_version: null,
	},
	python_installations: [
		{
			version: "3.10.12",
			path: "/usr/bin/python3.10",
			is_venv: false,
			venv_path: null,
			pip_version: "22.0.2",
		},
		{
			version: "3.11.4",
			path: "/usr/bin/python3.11",
			is_venv: false,
			venv_path: null,
			pip_version: "23.2.1",
		},
	],
	active_python: {
		version: "3.10.12",
		path: "/usr/bin/python3.10",
		is_venv: false,
		venv_path: null,
		pip_version: "22.0.2",
	},
};

// ── Confidence bar ─────────────────────────────────────────────────────
const ConfidenceBar = ({ value }: { value: number }) => {
	const pct = Math.round(value * 100);
	const color =
		pct >= 70 ? "var(--brand-accent)" : pct >= 40 ? "#eab308" : "#ef4444";
	return (
		<div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
			<div
				style={{
					flexGrow: 1,
					height: "6px",
					background: "rgba(255,255,255,0.06)",
					borderRadius: "3px",
					overflow: "hidden",
				}}
			>
				<motion.div
					initial={{ width: 0 }}
					animate={{ width: `${pct}%` }}
					transition={{ duration: 0.8, ease: "easeOut" }}
					style={{ height: "100%", background: color, borderRadius: "3px" }}
				/>
			</div>
			<span
				style={{
					fontSize: "0.85rem",
					fontWeight: 600,
					color,
					minWidth: "40px",
				}}
			>
				{pct}%
			</span>
		</div>
	);
};

export default function TroubleshootPage() {
	// ── State ──────────────────────────────────────────────────────────────
	const [diagnosticJson, setDiagnosticJson] = useState("");
	const [profileSlug, setProfileSlug] = useState("pytorch-cuda");
	const [userDescription, setUserDescription] = useState("");
	const [loading, setLoading] = useState(false);
	const [streamingText, setStreamingText] = useState("");
	const [error, setError] = useState<string | null>(null);
	const [result, setResult] = useState<TroubleshootResponse | null>(null);
	const [expandedFix, setExpandedFix] = useState<number | null>(null);
	const [repairScripts, setRepairScripts] = useState<
		Record<string, RepairResponse>
	>({});
	const [repairLoading, setRepairLoading] = useState<string | null>(null);
	const [copiedId, setCopiedId] = useState<string | null>(null);

	// ── Handlers ───────────────────────────────────────────────────────────

	const handleSubmit = async () => {
		setError(null);
		setResult(null);
		setStreamingText("");
		setRepairScripts({});

		// Validate JSON
		let diagnostic: Record<string, unknown>;
		try {
			diagnostic = JSON.parse(diagnosticJson);
			if (!diagnostic.os || !diagnostic.cpu) {
				throw new Error("Missing required fields: os, cpu");
			}
		} catch (err) {
			setError(err instanceof Error ? err.message : "Invalid JSON format.");
			return;
		}

		setLoading(true);
		try {
			const request: TroubleshootRequest = {
				diagnostic,
				profile_slug: profileSlug || undefined,
				user_description: userDescription || undefined,
			};

			const response = await api.troubleshoot(request, (token) => {
				setStreamingText((prev) => prev + token);
			});

			setResult(response);
			// Auto-expand the first fix
			if (response.suggested_fixes.length > 0) {
				setExpandedFix(0);
			}
		} catch (err) {
			setError(
				err instanceof Error
					? err.message
					: "AI troubleshooting failed. Check that the backend is running.",
			);
		} finally {
			setLoading(false);
			setStreamingText("");
		}
	};

	const handleRepair = async (templateId: string) => {
		setRepairLoading(templateId);
		try {
			const response = await api.generateRepair({
				template_id: templateId,
				params: {
					target_cuda_version: "12.1",
					target_python_version: "3.11",
				},
			});
			setRepairScripts((prev) => ({ ...prev, [templateId]: response }));
		} catch (err) {
			setError(
				err instanceof Error ? err.message : "Repair script generation failed.",
			);
		} finally {
			setRepairLoading(null);
		}
	};

	const handleCopy = async (text: string, id: string) => {
		await navigator.clipboard.writeText(text);
		setCopiedId(id);
		setTimeout(() => setCopiedId(null), 2000);
	};

	const handlePrefill = () => {
		setDiagnosticJson(JSON.stringify(SAMPLE_DIAGNOSTIC, null, 2));
		setUserDescription(
			"PyTorch says torch.cuda.is_available() returns False even though I have an NVIDIA GPU.",
		);
		setProfileSlug("pytorch-cuda");
	};

	// ── Render ─────────────────────────────────────────────────────────────

	return (
		<div
			className="container"
			style={{ paddingTop: "4rem", paddingBottom: "6rem", maxWidth: "900px" }}
		>
			{/* Header */}
			<div style={{ textAlign: "center", marginBottom: "3rem" }}>
				<motion.div
					initial={{ scale: 0 }}
					animate={{ scale: 1 }}
					transition={{ type: "spring", stiffness: 200 }}
				>
					<div
						style={{
							display: "inline-flex",
							padding: "1rem",
							borderRadius: "16px",
							background:
								"linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(236, 72, 153, 0.15))",
							marginBottom: "1.5rem",
						}}
					>
						<Brain size={40} color="var(--brand-primary)" />
					</div>
				</motion.div>
				<h1 style={{ fontSize: "3rem", marginBottom: "1rem" }}>
					AI <span className="text-gradient">Troubleshoot</span>
				</h1>
				<p
					style={{
						color: "var(--text-secondary)",
						fontSize: "1.1rem",
						maxWidth: "600px",
						margin: "0 auto",
					}}
				>
					Paste your diagnostic report and let AI analyze your environment for
					compatibility issues, mismatches, and fixes.
				</p>
			</div>

			{/* Input Form */}
			{!result && (
				<motion.div
					initial={{ opacity: 0, y: 20 }}
					animate={{ opacity: 1, y: 0 }}
				>
					<div
						className="glass-panel"
						style={{ padding: "2rem", marginBottom: "1.5rem" }}
					>
						{/* Profile + Description Row */}
						<div
							style={{
								display: "grid",
								gridTemplateColumns: "1fr 1fr",
								gap: "1.5rem",
								marginBottom: "1.5rem",
							}}
						>
							<div>
								<label
									style={{
										display: "block",
										fontSize: "0.85rem",
										color: "var(--text-muted)",
										textTransform: "uppercase",
										letterSpacing: "0.05em",
										marginBottom: "0.5rem",
									}}
								>
									Target Profile
								</label>
								<select
									value={profileSlug}
									onChange={(e) => setProfileSlug(e.target.value)}
									style={{
										width: "100%",
										padding: "0.75rem 1rem",
										background: "rgba(0,0,0,0.2)",
										border: "1px solid var(--border-strong)",
										color: "white",
										borderRadius: "8px",
										fontSize: "0.95rem",
										outline: "none",
									}}
								>
									<option value="pytorch-cuda">PyTorch + CUDA</option>
									<option value="tf-gpu">TensorFlow GPU</option>
									<option value="yolov8">YOLOv8</option>
									<option value="stable-diffusion">Stable Diffusion</option>
									<option value="opencv-beginner">OpenCV (CPU)</option>
									<option value="llm-finetune">LLM Fine-tuning</option>
								</select>
							</div>
							<div>
								<label
									style={{
										display: "block",
										fontSize: "0.85rem",
										color: "var(--text-muted)",
										textTransform: "uppercase",
										letterSpacing: "0.05em",
										marginBottom: "0.5rem",
									}}
								>
									Describe Your Issue
								</label>
								<input
									type="text"
									value={userDescription}
									onChange={(e) => setUserDescription(e.target.value)}
									placeholder="e.g. torch.cuda.is_available() returns False"
									maxLength={500}
									style={{
										width: "100%",
										padding: "0.75rem 1rem",
										background: "rgba(0,0,0,0.2)",
										border: "1px solid var(--border-strong)",
										color: "white",
										borderRadius: "8px",
										fontSize: "0.95rem",
										outline: "none",
									}}
								/>
							</div>
						</div>

						{/* Diagnostic JSON */}
						<div style={{ marginBottom: "1.5rem" }}>
							<div
								style={{
									display: "flex",
									justifyContent: "space-between",
									alignItems: "center",
									marginBottom: "0.5rem",
								}}
							>
								<label
									style={{
										fontSize: "0.85rem",
										color: "var(--text-muted)",
										textTransform: "uppercase",
										letterSpacing: "0.05em",
									}}
								>
									Diagnostic Report (JSON)
								</label>
								<button
									onClick={handlePrefill}
									style={{
										fontSize: "0.8rem",
										color: "var(--brand-primary)",
										background: "none",
										border: "none",
										cursor: "pointer",
										textDecoration: "underline",
									}}
								>
									Load Sample Data
								</button>
							</div>
							<textarea
								value={diagnosticJson}
								onChange={(e) => setDiagnosticJson(e.target.value)}
								placeholder={
									'{\n  "agent_version": "1.0.0",\n  "os": { "name": "Ubuntu 22.04" ... },\n  "gpus": [{ "name": "RTX 4090" ... }],\n  "cuda": { "version": "12.1" ... }\n}'
								}
								style={{
									width: "100%",
									height: "240px",
									background: "rgba(0,0,0,0.3)",
									border: "1px solid var(--border-strong)",
									borderRadius: "8px",
									padding: "1rem",
									color: "var(--text-primary)",
									fontFamily: "var(--font-mono)",
									fontSize: "0.85rem",
									resize: "vertical",
									outline: "none",
									lineHeight: "1.6",
								}}
							/>
						</div>

						{/* Error */}
						<AnimatePresence>
							{error && (
								<motion.div
									initial={{ opacity: 0, height: 0 }}
									animate={{ opacity: 1, height: "auto" }}
									exit={{ opacity: 0, height: 0 }}
									style={{
										padding: "0.75rem 1rem",
										background: "rgba(239, 68, 68, 0.08)",
										border: "1px solid rgba(239, 68, 68, 0.25)",
										borderRadius: "8px",
										color: "#fca5a5",
										fontSize: "0.9rem",
										marginBottom: "1.5rem",
										display: "flex",
										gap: "0.5rem",
										alignItems: "center",
									}}
								>
									<AlertCircle size={16} />
									{error}
								</motion.div>
							)}
						</AnimatePresence>

						{/* Streaming Preview */}
						<AnimatePresence>
							{loading && streamingText && (
								<motion.div
									initial={{ opacity: 0, y: 10 }}
									animate={{ opacity: 1, y: 0 }}
									exit={{ opacity: 0 }}
									style={{ marginBottom: "1.5rem" }}
								>
									<div
										className="glass-panel"
										style={{
											padding: "1rem",
											background: "rgba(0,0,0,0.4)",
											border: "1px solid var(--brand-primary-alpha)",
										}}
									>
										<div
											style={{
												display: "flex",
												alignItems: "center",
												gap: "0.5rem",
												marginBottom: "0.5rem",
												color: "var(--brand-primary)",
												fontSize: "0.75rem",
												fontWeight: 700,
												textTransform: "uppercase",
												letterSpacing: "0.05em",
											}}
										>
											<Terminal size={14} /> Live Analysis Stream
										</div>
										<pre
											style={{
												fontFamily: "var(--font-mono)",
												fontSize: "0.8rem",
												color: "var(--text-secondary)",
												whiteSpace: "pre-wrap",
												wordBreak: "break-all",
												margin: 0,
												maxHeight: "150px",
												overflowY: "auto",
											}}
										>
											{streamingText}
											<motion.span
												animate={{ opacity: [1, 0] }}
												transition={{ repeat: Infinity, duration: 0.8 }}
												style={{
													display: "inline-block",
													width: "8px",
													height: "14px",
													background: "var(--brand-primary)",
													marginLeft: "4px",
													verticalAlign: "middle",
												}}
											/>
										</pre>
									</div>
								</motion.div>
							)}
						</AnimatePresence>

						{/* Submit */}
						<div style={{ display: "flex", justifyContent: "center" }}>
							<button
								className="btn btn-primary"
								onClick={handleSubmit}
								disabled={loading || !diagnosticJson.trim()}
								style={{
									padding: "0.85rem 2.5rem",
									fontSize: "1rem",
									gap: "0.5rem",
									display: "flex",
									alignItems: "center",
								}}
							>
								{loading ? (
									<>
										<Loader2
											size={18}
											className="spin-animation"
											style={{ animation: "spin 1s linear infinite" }}
										/>
										Analyzing...
									</>
								) : (
									<>
										<Sparkles size={18} />
										Run AI Analysis
									</>
								)}
							</button>
						</div>
					</div>
				</motion.div>
			)}

			{/* Results */}
			<AnimatePresence>
				{result && (
					<motion.div
						initial={{ opacity: 0, y: 30 }}
						animate={{ opacity: 1, y: 0 }}
						exit={{ opacity: 0 }}
						transition={{ duration: 0.4 }}
					>
						{/* Action bar */}
						<div
							style={{
								display: "flex",
								justifyContent: "space-between",
								alignItems: "center",
								marginBottom: "2rem",
							}}
						>
							<h2
								style={{
									fontSize: "1.5rem",
									display: "flex",
									alignItems: "center",
									gap: "0.5rem",
								}}
							>
								<Sparkles size={22} color="var(--brand-primary)" /> Analysis
								Results
							</h2>
							<button
								className="btn btn-secondary"
								onClick={() => {
									setResult(null);
									setError(null);
									setRepairScripts({});
								}}
								style={{ padding: "0.5rem 1rem", fontSize: "0.85rem" }}
							>
								New Analysis
							</button>
						</div>

						{/* Root Cause Card */}
						<div
							className="glass-panel"
							style={{ padding: "1.5rem", marginBottom: "1.5rem" }}
						>
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
										fontSize: "0.85rem",
										color: "var(--text-muted)",
										textTransform: "uppercase",
										letterSpacing: "0.05em",
									}}
								>
									Root Cause
								</div>
								<div
									style={{
										padding: "0.25rem 0.75rem",
										borderRadius: "12px",
										fontSize: "0.75rem",
										background: "rgba(99, 102, 241, 0.1)",
										border: "1px solid rgba(99, 102, 241, 0.3)",
										color: "var(--brand-primary)",
										fontWeight: 600,
									}}
								>
									Session: {result.session_id.slice(0, 8)}...
								</div>
							</div>
							<p
								style={{
									fontSize: "1.05rem",
									lineHeight: "1.7",
									color: "var(--text-primary)",
								}}
							>
								{result.root_cause}
							</p>
							<div style={{ marginTop: "1rem" }}>
								<div
									style={{
										fontSize: "0.85rem",
										color: "var(--text-muted)",
										marginBottom: "0.5rem",
									}}
								>
									Confidence
								</div>
								<ConfidenceBar value={result.confidence} />
							</div>
						</div>

						{/* Suggested Fixes */}
						<div style={{ marginBottom: "1.5rem" }}>
							<h3
								style={{
									fontSize: "1.1rem",
									color: "var(--text-secondary)",
									marginBottom: "1rem",
									display: "flex",
									alignItems: "center",
									gap: "0.5rem",
								}}
							>
								<Wrench size={18} />
								Suggested Fixes ({result.suggested_fixes.length})
							</h3>

							<div
								style={{
									display: "flex",
									flexDirection: "column",
									gap: "0.75rem",
								}}
							>
								{result.suggested_fixes.map((fix, idx) => {
									const config = severityConfig[fix.severity];
									const SeverityIcon = config.icon;
									const isExpanded = expandedFix === idx;
									const repair = fix.repair_template_id
										? repairScripts[fix.repair_template_id]
										: null;

									return (
										<motion.div
											key={idx}
											initial={{ opacity: 0, x: -20 }}
											animate={{ opacity: 1, x: 0 }}
											transition={{ delay: idx * 0.1 }}
											className="glass-panel"
											style={{
												border: `1px solid ${config.border}`,
												overflow: "hidden",
											}}
										>
											{/* Fix Header */}
											<button
												onClick={() => setExpandedFix(isExpanded ? null : idx)}
												style={{
													width: "100%",
													padding: "1.25rem 1.5rem",
													background: "none",
													border: "none",
													cursor: "pointer",
													color: "inherit",
													display: "flex",
													alignItems: "center",
													gap: "1rem",
													textAlign: "left",
												}}
											>
												<div
													style={{
														width: "32px",
														height: "32px",
														borderRadius: "8px",
														display: "flex",
														alignItems: "center",
														justifyContent: "center",
														background: config.bg,
														flexShrink: 0,
													}}
												>
													<SeverityIcon size={18} color={config.color} />
												</div>
												<div style={{ flexGrow: 1 }}>
													<div
														style={{
															display: "flex",
															alignItems: "center",
															gap: "0.75rem",
														}}
													>
														<span
															style={{
																fontSize: "0.7rem",
																fontWeight: 700,
																padding: "0.15rem 0.5rem",
																borderRadius: "4px",
																background: config.bg,
																color: config.color,
																textTransform: "uppercase",
																letterSpacing: "0.05em",
															}}
														>
															Step {fix.step}
														</span>
														<span
															style={{
																fontSize: "0.7rem",
																padding: "0.15rem 0.5rem",
																borderRadius: "4px",
																background: config.bg,
																color: config.color,
															}}
														>
															{config.label}
														</span>
													</div>
													<div
														style={{
															fontSize: "1rem",
															fontWeight: 600,
															marginTop: "0.35rem",
														}}
													>
														{fix.title}
													</div>
												</div>
												{isExpanded ? (
													<ChevronUp size={18} color="var(--text-muted)" />
												) : (
													<ChevronDown size={18} color="var(--text-muted)" />
												)}
											</button>

											{/* Fix Details (expanded) */}
											<AnimatePresence>
												{isExpanded && (
													<motion.div
														initial={{ height: 0, opacity: 0 }}
														animate={{ height: "auto", opacity: 1 }}
														exit={{ height: 0, opacity: 0 }}
														transition={{ duration: 0.2 }}
														style={{ overflow: "hidden" }}
													>
														<div
															style={{
																padding: "0 1.5rem 1.5rem",
																borderTop: `1px solid ${config.border}`,
																paddingTop: "1.25rem",
															}}
														>
															<p
																style={{
																	color: "var(--text-secondary)",
																	lineHeight: "1.7",
																	fontSize: "0.95rem",
																	marginBottom: "1rem",
																}}
															>
																{fix.description}
															</p>

															{/* Safe Commands */}
															{fix.safe_commands.length > 0 && (
																<div style={{ marginBottom: "1rem" }}>
																	<div
																		style={{
																			display: "flex",
																			alignItems: "center",
																			gap: "0.5rem",
																			marginBottom: "0.5rem",
																		}}
																	>
																		<Terminal
																			size={14}
																			color="var(--text-muted)"
																		/>
																		<span
																			style={{
																				fontSize: "0.8rem",
																				color: "var(--text-muted)",
																				textTransform: "uppercase",
																				letterSpacing: "0.05em",
																			}}
																		>
																			Diagnostic Commands
																		</span>
																	</div>
																	{fix.safe_commands.map((cmd, ci) => (
																		<div
																			key={ci}
																			style={{
																				display: "flex",
																				alignItems: "center",
																				justifyContent: "space-between",
																				padding: "0.5rem 0.75rem",
																				background: "rgba(0,0,0,0.3)",
																				borderRadius: "6px",
																				fontFamily: "var(--font-mono)",
																				fontSize: "0.85rem",
																				marginBottom: "0.35rem",
																				border:
																					"1px solid var(--border-subtle)",
																			}}
																		>
																			<code
																				style={{ color: "var(--brand-accent)" }}
																			>
																				$ {cmd}
																			</code>
																			<button
																				onClick={() =>
																					handleCopy(cmd, `cmd-${idx}-${ci}`)
																				}
																				style={{
																					background: "none",
																					border: "none",
																					cursor: "pointer",
																					padding: "0.25rem",
																					color: "var(--text-muted)",
																				}}
																			>
																				{copiedId === `cmd-${idx}-${ci}` ? (
																					<Check
																						size={14}
																						color="var(--brand-accent)"
																					/>
																				) : (
																					<Copy size={14} />
																				)}
																			</button>
																		</div>
																	))}
																</div>
															)}

															{/* Repair Script Button */}
															{fix.repair_template_id && !repair && (
																<button
																	className="btn btn-primary"
																	onClick={() =>
																		handleRepair(fix.repair_template_id!)
																	}
																	disabled={
																		repairLoading === fix.repair_template_id
																	}
																	style={{
																		fontSize: "0.85rem",
																		padding: "0.6rem 1.25rem",
																		gap: "0.5rem",
																	}}
																>
																	{repairLoading === fix.repair_template_id ? (
																		<>
																			<Loader2
																				size={14}
																				style={{
																					animation: "spin 1s linear infinite",
																				}}
																			/>{" "}
																			Generating...
																		</>
																	) : (
																		<>
																			<Download size={14} /> Generate Repair
																			Script
																		</>
																	)}
																</button>
															)}

															{/* Repair Script Output */}
															{repair && (
																<motion.div
																	initial={{ opacity: 0 }}
																	animate={{ opacity: 1 }}
																	style={{ marginTop: "0.75rem" }}
																>
																	<div
																		style={{
																			display: "flex",
																			justifyContent: "space-between",
																			alignItems: "center",
																			padding: "0.5rem 0.75rem",
																			background: "rgba(16, 185, 129, 0.08)",
																			border:
																				"1px solid rgba(16, 185, 129, 0.25)",
																			borderRadius: "8px 8px 0 0",
																			fontSize: "0.8rem",
																		}}
																	>
																		<span
																			style={{
																				color: "var(--brand-accent)",
																				fontWeight: 600,
																			}}
																		>
																			{repair.filename}
																		</span>
																		<span
																			style={{ color: "var(--text-muted)" }}
																		>
																			{repair.size_bytes} bytes
																		</span>
																	</div>
																	<pre
																		style={{
																			background: "rgba(0,0,0,0.4)",
																			padding: "1rem",
																			borderRadius: "0 0 8px 8px",
																			fontFamily: "var(--font-mono)",
																			fontSize: "0.8rem",
																			color: "var(--text-secondary)",
																			overflowX: "auto",
																			maxHeight: "300px",
																			lineHeight: "1.6",
																			margin: 0,
																			border: "1px solid var(--border-subtle)",
																			borderTop: "none",
																		}}
																	>
																		{repair.content}
																	</pre>
																	<div
																		style={{
																			display: "flex",
																			gap: "0.5rem",
																			marginTop: "0.75rem",
																		}}
																	>
																		<button
																			className="btn btn-secondary"
																			onClick={() =>
																				handleCopy(
																					repair.content,
																					`repair-${fix.repair_template_id}`,
																				)
																			}
																			style={{
																				fontSize: "0.8rem",
																				padding: "0.4rem 0.8rem",
																				gap: "0.4rem",
																			}}
																		>
																			{copiedId ===
																			`repair-${fix.repair_template_id}` ? (
																				<>
																					<Check size={14} /> Copied!
																				</>
																			) : (
																				<>
																					<Copy size={14} /> Copy Script
																				</>
																			)}
																		</button>
																		<button
																			className="btn btn-secondary"
																			onClick={() => {
																				const blob = new Blob(
																					[repair.content],
																					{ type: "text/x-shellscript" },
																				);
																				const url = URL.createObjectURL(blob);
																				const a = document.createElement("a");
																				a.href = url;
																				a.download = repair.filename;
																				a.click();
																				URL.revokeObjectURL(url);
																			}}
																			style={{
																				fontSize: "0.8rem",
																				padding: "0.4rem 0.8rem",
																				gap: "0.4rem",
																			}}
																		>
																			<Download size={14} /> Download .sh
																		</button>
																	</div>
																</motion.div>
															)}
														</div>
													</motion.div>
												)}
											</AnimatePresence>
										</motion.div>
									);
								})}
							</div>
						</div>

						{/* Disclaimer */}
						<div
							style={{
								display: "flex",
								gap: "0.75rem",
								padding: "1rem 1.25rem",
								background: "rgba(99, 102, 241, 0.05)",
								border: "1px solid rgba(99, 102, 241, 0.15)",
								borderRadius: "8px",
								fontSize: "0.85rem",
								color: "var(--text-muted)",
								alignItems: "flex-start",
							}}
						>
							<Shield
								size={16}
								color="var(--brand-primary)"
								style={{ flexShrink: 0, marginTop: "2px" }}
							/>
							<span>{result.disclaimer}</span>
						</div>
					</motion.div>
				)}
			</AnimatePresence>

			{/* Spinner keyframe */}
			<style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
		</div>
	);
}
