"use client";

import { motion } from "framer-motion";
import {
	Cpu,
	HardDrive,
	Monitor,
	ShieldAlert,
	Terminal,
	UploadCloud,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import TerminalLoader from "../../components/TerminalLoader";
import { api } from "../../services/api";
import type {
	DiagnosticReport,
	DiagnosticResponse,
	Profile,
} from "../../types";

export default function DiagnosePage() {
	const [jsonInput, setJsonInput] = useState("");
	const [report, setReport] = useState<DiagnosticReport | null>(null);
	const [error, setError] = useState<string | null>(null);

	const [profiles, setProfiles] = useState<Profile[]>([]);
	const [selectedProfile, setSelectedProfile] = useState<string>("");
	const [verifying, setVerifying] = useState(false);
	const [apiDone, setApiDone] = useState(false);
	const [verifyResult, setVerifyResult] = useState<DiagnosticResponse | null>(
		null,
	);

	const getCompatibilityMetrics = (result: DiagnosticResponse | null) => {
		if (!result)
			return {
				score: 100,
				riskLevel: "LOW",
				riskColor: "#10b981",
				riskBg: "rgba(16, 185, 129, 0.15)",
				breakdown: { os: 100, cuda: 100, gpu: 100, python: 100, ram: 100 },
			};

		let score = 100;
		const breakdown = {
			os: 100,
			cuda: 100,
			gpu: 100,
			python: 100,
			ram: 100,
		};

		result.issues.forEach((issue) => {
			const severity = issue.severity.toUpperCase();
			const component = (issue.component || "").toLowerCase();

			let deduction = 0;
			if (severity === "ERROR" || severity === "CRITICAL") {
				deduction = 30;
			} else if (severity === "WARNING") {
				deduction = 15;
			} else {
				deduction = 5;
			}

			score -= deduction;

			if (component.includes("os"))
				breakdown.os = Math.max(breakdown.os - deduction * 2, 10);
			else if (component.includes("cuda"))
				breakdown.cuda = Math.max(breakdown.cuda - deduction * 2, 10);
			else if (component.includes("gpu"))
				breakdown.gpu = Math.max(breakdown.gpu - deduction * 2, 10);
			else if (component.includes("python"))
				breakdown.python = Math.max(breakdown.python - deduction * 2, 10);
			else if (component.includes("ram"))
				breakdown.ram = Math.max(breakdown.ram - deduction * 2, 10);
		});

		score = Math.max(score, 10);
		if (result.issues.length === 0) score = 100;

		let riskLevel = "LOW";
		let riskColor = "#10b981"; // neon green
		let riskBg = "rgba(16, 185, 129, 0.15)";

		if (score < 35) {
			riskLevel = "CRITICAL";
			riskColor = "#ef4444"; // neon red
			riskBg = "rgba(239, 68, 68, 0.15)";
		} else if (score < 60) {
			riskLevel = "HIGH";
			riskColor = "#f97316"; // neon orange
			riskBg = "rgba(249, 115, 22, 0.15)";
		} else if (score < 85) {
			riskLevel = "MEDIUM";
			riskColor = "#eab308"; // neon yellow
			riskBg = "rgba(234, 179, 8, 0.15)";
		}

		return { score, riskLevel, riskColor, riskBg, breakdown };
	};

	useEffect(() => {
		async function loadProfiles() {
			try {
				const data = await api.getProfiles();
				setProfiles(data);
				if (data.length > 0) setSelectedProfile(data[0].slug);
			} catch {}
		}
		loadProfiles();
	}, []);

	const handleParse = () => {
		setError(null);
		try {
			const parsed = JSON.parse(jsonInput);
			if (!parsed.os || !parsed.cpu || !parsed.agent_version) {
				throw new Error(
					"Invalid Diagnostic Report format. Ensure you pasted the output of `envforge diagnose`.",
				);
			}
			setReport(parsed as DiagnosticReport);
			setVerifyResult(null);
		} catch (err) {
			setError(err instanceof Error ? err.message : "Invalid JSON.");
		}
	};

	const handleVerify = async () => {
		if (!report || !selectedProfile) return;
		setVerifying(true);
		setApiDone(false);
		setError(null);
		setVerifyResult(null);
		try {
			const result = await api.diagnose(report, selectedProfile);
			setVerifyResult(result);
			setApiDone(true);
		} catch (err) {
			setError(err instanceof Error ? err.message : "Verification failed.");
			setApiDone(true);
		}
	};

	return (
		<div
			className="container"
			style={{ paddingTop: "4rem", paddingBottom: "6rem" }}
		>
			<div style={{ textAlign: "center", marginBottom: "3rem" }}>
				<h1 style={{ fontSize: "3rem", marginBottom: "1rem" }}>
					Diagnostic Dashboard
				</h1>
				<p style={{ color: "var(--text-secondary)", fontSize: "1.1rem" }}>
					Paste your offline agent report to verify compatibility.
				</p>
			</div>

			{!report ? (
				<motion.div
					initial={{ opacity: 0, y: 20 }}
					animate={{ opacity: 1, y: 0 }}
					className="glass-panel"
					style={{ padding: "2rem", maxWidth: "800px", margin: "0 auto" }}
				>
					<div style={{ textAlign: "center", marginBottom: "2rem" }}>
						<UploadCloud
							size={48}
							color="var(--brand-primary)"
							style={{ margin: "0 auto 1rem" }}
						/>
						<h3>Upload Diagnostic JSON</h3>
						<p
							style={{
								color: "var(--text-secondary)",
								fontSize: "0.9rem",
								marginTop: "0.5rem",
							}}
						>
							Run{" "}
							<code style={{ color: "var(--brand-accent)" }}>
								envforge diagnose --quiet
							</code>{" "}
							and paste the output below.
						</p>
					</div>
					<textarea
						value={jsonInput}
						onChange={(e) => setJsonInput(e.target.value)}
						placeholder='{\n  "agent_version": "1.0.0",\n  "os": {\n    "name": "Ubuntu 22.04"...\n}'
						style={{
							width: "100%",
							height: "300px",
							background: "rgba(0,0,0,0.2)",
							border: "1px solid var(--border-strong)",
							borderRadius: "8px",
							padding: "1rem",
							color: "var(--text-primary)",
							fontFamily: "var(--font-mono)",
							fontSize: "0.9rem",
							resize: "vertical",
							outline: "none",
						}}
					/>
					{error && (
						<div
							style={{
								color: "#ef4444",
								marginTop: "1rem",
								fontSize: "0.9rem",
							}}
						>
							{error}
						</div>
					)}
					<div
						style={{
							display: "flex",
							justifyContent: "center",
							marginTop: "2rem",
						}}
					>
						<button
							className="btn btn-primary"
							onClick={handleParse}
							disabled={!jsonInput.trim()}
						>
							Analyze Report
						</button>
					</div>
				</motion.div>
			) : (
				<div>
					<div
						style={{
							display: "flex",
							justifyContent: "space-between",
							alignItems: "center",
							marginBottom: "2rem",
						}}
					>
						<h2>Hardware Overview</h2>
						<button
							className="btn btn-secondary"
							onClick={() => {
								setReport(null);
								setJsonInput("");
							}}
						>
							Upload New Report
						</button>
					</div>

					<motion.div
						initial={{ opacity: 0, y: 20 }}
						animate={{ opacity: 1, y: 0 }}
						style={{
							display: "grid",
							gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
							gap: "1.5rem",
							marginBottom: "4rem",
						}}
					>
						{/* OS Card */}
						<div
							className="glass-panel"
							style={{
								padding: "1.5rem",
								display: "flex",
								gap: "1rem",
								alignItems: "flex-start",
							}}
						>
							<div
								style={{
									background: "rgba(99, 102, 241, 0.1)",
									padding: "0.75rem",
									borderRadius: "8px",
								}}
							>
								<Monitor color="var(--brand-primary)" size={24} />
							</div>
							<div>
								<div
									style={{
										color: "var(--text-muted)",
										fontSize: "0.85rem",
										textTransform: "uppercase",
										letterSpacing: "0.05em",
										marginBottom: "0.25rem",
									}}
								>
									Operating System
								</div>
								<div style={{ fontWeight: 600, fontSize: "1.1rem" }}>
									{report.os.name}
								</div>
								<div
									style={{ fontSize: "0.9rem", color: "var(--text-secondary)" }}
								>
									{report.os.architecture}{" "}
									{report.os.wsl_version ? `(${report.os.wsl_version})` : ""}
								</div>
							</div>
						</div>

						{/* CPU Card */}
						<div
							className="glass-panel"
							style={{
								padding: "1.5rem",
								display: "flex",
								gap: "1rem",
								alignItems: "flex-start",
							}}
						>
							<div
								style={{
									background: "rgba(16, 185, 129, 0.1)",
									padding: "0.75rem",
									borderRadius: "8px",
								}}
							>
								<Cpu color="var(--brand-accent)" size={24} />
							</div>
							<div>
								<div
									style={{
										color: "var(--text-muted)",
										fontSize: "0.85rem",
										textTransform: "uppercase",
										letterSpacing: "0.05em",
										marginBottom: "0.25rem",
									}}
								>
									Processor
								</div>
								<div style={{ fontWeight: 600, fontSize: "1.1rem" }}>
									{report.cpu.brand}
								</div>
								<div
									style={{ fontSize: "0.9rem", color: "var(--text-secondary)" }}
								>
									{report.cpu.cores} Cores / {report.cpu.threads} Threads
								</div>
							</div>
						</div>

						{/* GPU Card */}
						<div
							className="glass-panel"
							style={{
								padding: "1.5rem",
								display: "flex",
								gap: "1rem",
								alignItems: "flex-start",
							}}
						>
							<div
								style={{
									background: "rgba(236, 72, 153, 0.1)",
									padding: "0.75rem",
									borderRadius: "8px",
								}}
							>
								<HardDrive color="var(--brand-secondary)" size={24} />
							</div>
							<div>
								<div
									style={{
										color: "var(--text-muted)",
										fontSize: "0.85rem",
										textTransform: "uppercase",
										letterSpacing: "0.05em",
										marginBottom: "0.25rem",
									}}
								>
									Graphics (GPU)
								</div>
								{report.gpus.length > 0 ? (
									<>
										<div style={{ fontWeight: 600, fontSize: "1.1rem" }}>
											{report.gpus[0].name}
										</div>
										<div
											style={{
												fontSize: "0.9rem",
												color: "var(--text-secondary)",
											}}
										>
											{report.gpus[0].vram_gb} GB VRAM • Driver{" "}
											{report.gpus[0].driver_version}
										</div>
									</>
								) : (
									<div
										style={{
											fontWeight: 600,
											fontSize: "1.1rem",
											color: "var(--text-secondary)",
										}}
									>
										No NVIDIA GPU Detected
									</div>
								)}
							</div>
						</div>

						{/* CUDA Card */}
						<div
							className="glass-panel"
							style={{
								padding: "1.5rem",
								display: "flex",
								gap: "1rem",
								alignItems: "flex-start",
							}}
						>
							<div
								style={{
									background: "rgba(234, 179, 8, 0.1)",
									padding: "0.75rem",
									borderRadius: "8px",
								}}
							>
								<Terminal color="#eab308" size={24} />
							</div>
							<div>
								<div
									style={{
										color: "var(--text-muted)",
										fontSize: "0.85rem",
										textTransform: "uppercase",
										letterSpacing: "0.05em",
										marginBottom: "0.25rem",
									}}
								>
									CUDA Toolkit
								</div>
								{report.cuda.version ? (
									<>
										<div style={{ fontWeight: 600, fontSize: "1.1rem" }}>
											v{report.cuda.version}
										</div>
										<div
											style={{
												fontSize: "0.9rem",
												color: "var(--text-secondary)",
											}}
										>
											cuDNN: {report.cuda.cudnn_version || "Not installed"}
										</div>
									</>
								) : (
									<div
										style={{
											fontWeight: 600,
											fontSize: "1.1rem",
											color: "var(--text-secondary)",
										}}
									>
										Not Installed
									</div>
								)}
							</div>
						</div>
					</motion.div>

					{/* Verification Engine */}
					{verifying ? (
						<TerminalLoader
							targetOs={report.os.name}
							profileName={
								profiles.find((p) => p.slug === selectedProfile)?.name ||
								selectedProfile
							}
							cudaVersion={report.cuda.version || undefined}
							isResolved={apiDone}
							onComplete={() => {
								setVerifying(false);
							}}
							title="EnvForage Diagnostic Compiler"
						/>
					) : (
						<div className="glass-panel" style={{ padding: "2rem" }}>
							<h2 style={{ marginBottom: "1.5rem" }}>Verify Compatibility</h2>
							<div
								style={{
									display: "flex",
									gap: "1rem",
									alignItems: "flex-end",
									marginBottom: "2rem",
								}}
							>
								<div style={{ flexGrow: 1, maxWidth: "400px" }}>
									<label
										style={{
											display: "block",
											fontSize: "0.9rem",
											color: "var(--text-secondary)",
											marginBottom: "0.5rem",
										}}
									>
										Target ML Profile
									</label>
									<select
										value={selectedProfile}
										onChange={(e) => setSelectedProfile(e.target.value)}
										style={{
											width: "100%",
											padding: "0.75rem 1rem",
											background: "rgba(0,0,0,0.2)",
											border: "1px solid var(--border-strong)",
											color: "white",
											borderRadius: "8px",
											fontSize: "1rem",
											outline: "none",
										}}
									>
										{profiles.map((p) => (
											<option key={p.slug} value={p.slug}>
												{p.name}
											</option>
										))}
									</select>
								</div>
								<button
									className="btn btn-primary"
									onClick={handleVerify}
									disabled={verifying || !selectedProfile}
								>
									Run Check
								</button>
							</div>

							{error && (
								<div
									style={{
										color: "#ef4444",
										marginBottom: "1.5rem",
										fontSize: "0.9rem",
									}}
								>
									{error}
								</div>
							)}

							{verifyResult &&
								(() => {
									const metrics = getCompatibilityMetrics(verifyResult);
									return (
										<motion.div
											initial={{ opacity: 0, scale: 0.97 }}
											animate={{ opacity: 1, scale: 1 }}
											style={{
												padding: "2rem",
												background: "rgba(18, 18, 22, 0.65)",
												border: `1px solid ${metrics.score >= 85 ? "rgba(16, 185, 129, 0.2)" : metrics.score >= 60 ? "rgba(234, 179, 8, 0.2)" : "rgba(239, 68, 68, 0.2)"}`,
												borderRadius: "16px",
												boxShadow: "0 8px 30px rgba(0, 0, 0, 0.3)",
												backdropFilter: "blur(12px)",
											}}
										>
											{/* Score & Risk Dashboard Widgets */}
											<div
												style={{
													display: "grid",
													gridTemplateColumns:
														"repeat(auto-fit, minmax(240px, 1fr))",
													gap: "2rem",
													marginBottom: "2.5rem",
													alignItems: "center",
												}}
											>
												{/* Gauge */}
												<div
													style={{
														display: "flex",
														flexDirection: "column",
														alignItems: "center",
														textAlign: "center",
													}}
												>
													<div
														style={{
															position: "relative",
															width: "130px",
															height: "130px",
															display: "flex",
															alignItems: "center",
															justifyContent: "center",
														}}
													>
														<svg
															width="130"
															height="130"
															style={{ transform: "rotate(-90deg)" }}
														>
															<circle
																cx="65"
																cy="65"
																r="55"
																fill="transparent"
																stroke="rgba(255,255,255,0.03)"
																strokeWidth="10"
															/>
															<motion.circle
																cx="65"
																cy="65"
																r="55"
																fill="transparent"
																stroke={metrics.riskColor}
																strokeWidth="10"
																strokeDasharray={2 * Math.PI * 55}
																initial={{ strokeDashoffset: 2 * Math.PI * 55 }}
																animate={{
																	strokeDashoffset:
																		2 *
																		Math.PI *
																		55 *
																		(1 - metrics.score / 100),
																}}
																transition={{ duration: 1, ease: "easeOut" }}
																strokeLinecap="round"
																style={{
																	filter: `drop-shadow(0 0 6px ${metrics.riskColor})`,
																}}
															/>
														</svg>
														<div
															style={{
																position: "absolute",
																display: "flex",
																flexDirection: "column",
																alignItems: "center",
															}}
														>
															<span
																style={{
																	fontSize: "2rem",
																	fontWeight: 800,
																	color: "white",
																	fontFamily: "var(--font-display)",
																}}
															>
																{metrics.score}%
															</span>
															<span
																style={{
																	fontSize: "0.65rem",
																	color: "var(--text-muted)",
																	textTransform: "uppercase",
																	fontWeight: 700,
																	letterSpacing: "0.05em",
																}}
															>
																COMPATIBILITY
															</span>
														</div>
													</div>
												</div>

												{/* Risk Classification Meter */}
												<div
													style={{
														display: "flex",
														flexDirection: "column",
														justifyContent: "center",
													}}
												>
													<div
														style={{
															display: "flex",
															gap: "0.5rem",
															alignItems: "center",
															marginBottom: "0.5rem",
														}}
													>
														<span
															style={{
																fontSize: "0.7rem",
																fontWeight: 800,
																padding: "0.25rem 0.75rem",
																borderRadius: "6px",
																background: metrics.riskBg,
																color: metrics.riskColor,
																border: `1px solid ${metrics.riskColor}30`,
																letterSpacing: "0.05em",
																boxShadow: `0 0 10px ${metrics.riskColor}20`,
															}}
														>
															RISK LEVEL: {metrics.riskLevel}
														</span>
													</div>
													<h3
														style={{
															margin: "0.25rem 0 0.5rem 0",
															fontSize: "1.4rem",
															fontWeight: 700,
														}}
													>
														{metrics.score === 100
															? "System Fully Harmonious!"
															: "Deductions Registered"}
													</h3>
													<p
														style={{
															color: "var(--text-secondary)",
															fontSize: "0.85rem",
															lineHeight: "1.4",
														}}
													>
														{metrics.score === 100
															? "Your hardware meets or exceeds all requirements for this profile. Zero compatibility friction detected."
															: `Compatibility score dropped to ${metrics.score}% due to ${verifyResult.issues.length} detected package/driver issue(s).`}
													</p>
												</div>

												{/* Sub-score bars breakdown */}
												<div
													style={{
														display: "flex",
														flexDirection: "column",
														gap: "0.6rem",
													}}
												>
													<h4
														style={{
															fontSize: "0.75rem",
															color: "var(--text-muted)",
															textTransform: "uppercase",
															letterSpacing: "0.05em",
															fontWeight: 700,
															marginBottom: "0.25rem",
														}}
													>
														Resource Stability Ratings
													</h4>
													{[
														{
															name: "OS Platform",
															score: metrics.breakdown.os,
														},
														{
															name: "Python Version",
															score: metrics.breakdown.python,
														},
														{
															name: "CUDA Matching",
															score: metrics.breakdown.cuda,
														},
														{
															name: "GPU Architecture",
															score: metrics.breakdown.gpu,
														},
														{
															name: "RAM Adequacy",
															score: metrics.breakdown.ram,
														},
													].map((comp, idx) => (
														<div
															key={idx}
															style={{
																display: "flex",
																flexDirection: "column",
																gap: "0.2rem",
															}}
														>
															<div
																style={{
																	display: "flex",
																	justifyContent: "space-between",
																	fontSize: "0.75rem",
																	fontWeight: 500,
																}}
															>
																<span
																	style={{ color: "var(--text-secondary)" }}
																>
																	{comp.name}
																</span>
																<span
																	style={{
																		color:
																			comp.score >= 85
																				? "var(--brand-accent)"
																				: comp.score >= 60
																					? "#eab308"
																					: "#ef4444",
																		fontWeight: 700,
																	}}
																>
																	{comp.score}%
																</span>
															</div>
															<div
																style={{
																	width: "100%",
																	height: "4px",
																	background: "rgba(255,255,255,0.03)",
																	borderRadius: "2px",
																	overflow: "hidden",
																}}
															>
																<motion.div
																	initial={{ width: 0 }}
																	animate={{ width: `${comp.score}%` }}
																	transition={{
																		duration: 0.8,
																		delay: 0.2 + idx * 0.05,
																	}}
																	style={{
																		height: "100%",
																		borderRadius: "2px",
																		background:
																			comp.score >= 85
																				? "var(--brand-accent)"
																				: comp.score >= 60
																					? "#eab308"
																					: "#ef4444",
																	}}
																/>
															</div>
														</div>
													))}
												</div>
											</div>

											{verifyResult.compatible_profiles.length > 0 && (
												<div style={{ marginBottom: "2rem" }}>
													<p
														style={{
															color: "var(--text-secondary)",
															marginBottom: "0.75rem",
															fontSize: "0.9rem",
															fontWeight: 600,
														}}
													>
														Compatible Alternative Profiles:
													</p>
													<div
														style={{
															display: "flex",
															gap: "0.5rem",
															flexWrap: "wrap",
														}}
													>
														{verifyResult.compatible_profiles.map((slug) => (
															<Link
																key={slug}
																href={`/generate?profile=${slug}`}
																style={{
																	padding: "0.4rem 0.8rem",
																	background: "rgba(16, 185, 129, 0.08)",
																	border: "1px solid rgba(16, 185, 129, 0.2)",
																	borderRadius: "6px",
																	fontSize: "0.85rem",
																	color: "var(--brand-accent)",
																	textDecoration: "none",
																	transition: "all 0.25s ease",
																}}
															>
																{slug}
															</Link>
														))}
													</div>
												</div>
											)}

											{verifyResult.issues.length > 0 && (
												<div style={{ marginBottom: "2rem" }}>
													<p
														style={{
															color: "var(--text-secondary)",
															marginBottom: "0.75rem",
															fontSize: "0.9rem",
															fontWeight: 600,
														}}
													>
														Issues Detected:
													</p>
													<ul style={{ listStyleType: "none", padding: 0 }}>
														{verifyResult.issues.map((issue, i) => (
															<li
																key={i}
																style={{
																	padding: "0.85rem 1rem",
																	background: "rgba(0,0,0,0.25)",
																	borderLeft: `3px solid ${issue.severity === "ERROR" ? "#ef4444" : "#eab308"}`,
																	borderRadius: "4px",
																	marginBottom: "0.5rem",
																	fontSize: "0.9rem",
																	display: "flex",
																	gap: "0.75rem",
																}}
															>
																<ShieldAlert
																	size={16}
																	color={
																		issue.severity === "ERROR"
																			? "#ef4444"
																			: "#eab308"
																	}
																	style={{ flexShrink: 0, marginTop: "3px" }}
																/>
																<div>
																	<div
																		style={{
																			fontWeight: 600,
																			color:
																				issue.severity === "ERROR"
																					? "#fca5a5"
																					: "#fde68a",
																			marginBottom: "0.15rem",
																		}}
																	>
																		{issue.message}
																	</div>
																	{issue.suggested_fix && (
																		<div
																			style={{
																				color: "var(--text-secondary)",
																				fontSize: "0.85rem",
																				marginTop: "0.25rem",
																			}}
																		>
																			💡 {issue.suggested_fix}
																		</div>
																	)}
																</div>
															</li>
														))}
													</ul>
												</div>
											)}

											{verifyResult.recommendations.length > 0 && (
												<div
													style={{
														background: "rgba(255,255,255,0.02)",
														padding: "1rem",
														borderRadius: "8px",
														border: "1px solid rgba(255,255,255,0.05)",
													}}
												>
													<p
														style={{
															color: "var(--text-secondary)",
															marginBottom: "0.5rem",
															fontSize: "0.9rem",
															fontWeight: 600,
														}}
													>
														Optimization Recommendations:
													</p>
													{verifyResult.recommendations.map((rec, i) => (
														<div
															key={i}
															style={{
																color: "var(--text-primary)",
																fontSize: "0.85rem",
																display: "flex",
																gap: "0.5rem",
																alignItems: "center",
																marginTop: "0.25rem",
															}}
														>
															<span style={{ color: "var(--brand-primary)" }}>
																•
															</span>
															<span>{rec}</span>
														</div>
													))}
												</div>
											)}
										</motion.div>
									);
								})()}
						</div>
					)}
				</div>
			)}
		</div>
	);
}
