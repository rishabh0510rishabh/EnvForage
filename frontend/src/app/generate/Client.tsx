"use client";

import React, { Component, ErrorInfo } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Check, ChevronRight, Download, Loader2, Server } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import TerminalLoader from "../../components/TerminalLoader";
import { api } from "../../services/api";
import type {
	Profile,
	ScriptGenerationRequest,
	ScriptGenerationResponse,
} from "../../types";

function WizardContent() {
	const searchParams = useSearchParams();
	const initialProfileSlug = searchParams.get("profile");

	const [profiles, setProfiles] = useState<Profile[]>([]);
	const [selectedProfile, setSelectedProfile] = useState<string>(
		initialProfileSlug || "",
	);
	const [targetOs, setTargetOs] = useState<string>("LINUX");
	const [outputFormats, setOutputFormats] = useState<string[]>(["setup.sh"]);
	const [pythonVersion, setPythonVersion] = useState<string>("");
	const [cudaVersion, setCudaVersion] = useState<string>("");

	const [step, setStep] = useState(1);
	const [loadingProfiles, setLoadingProfiles] = useState(true);

	const [generating, setGenerating] = useState(false);
	const [apiDone, setApiDone] = useState(false);
	const [result, setResult] = useState<ScriptGenerationResponse | null>(null);
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		window.scrollTo({ top: 0, behavior: "smooth" });
	}, [step]);

	useEffect(() => {
		async function fetchProfiles() {
			try {
				const data = await api.getProfiles();
				setProfiles(data);

				let active = data[0];
				if (initialProfileSlug) {
					const found = data.find((p) => p.slug === initialProfileSlug);
					if (found) {
						active = found;
					} else if (data.length > 0) {
						setSelectedProfile(data[0].slug);
					}
				} else if (data.length > 0) {
					setSelectedProfile(data[0].slug);
				}

				if (active) {
					if (active.python_versions && active.python_versions.length > 0) {
						setPythonVersion(active.python_versions[0]);
					}
					if (
						active.cuda_required &&
						active.cuda_versions &&
						active.cuda_versions.length > 0
					) {
						setCudaVersion(active.cuda_versions[0]);
					} else {
						setCudaVersion("");
					}
				}
			} catch (err) {
				console.error(err);
			} finally {
				setLoadingProfiles(false);
			}
		}
		fetchProfiles();
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, []);

	const handleGenerate = async () => {
		if (!activeProfile) return;

		// 1. Normalize OS
		let normalizedOs = targetOs;
		if (!activeProfile.os_support.includes(targetOs)) {
			normalizedOs = activeProfile.os_support[0] || "LINUX";
			setTargetOs(normalizedOs);
		}

		// 2. Normalize Python
		let normalizedPy = pythonVersion;
		if (!activeProfile.python_versions.includes(pythonVersion)) {
			normalizedPy = activeProfile.python_versions[0] || "";
			setPythonVersion(normalizedPy);
		}

		// 3. Normalize CUDA
		let normalizedCuda = cudaVersion;
		if (activeProfile.cuda_required && activeProfile.cuda_versions) {
			if (!activeProfile.cuda_versions.includes(cudaVersion)) {
				normalizedCuda = activeProfile.cuda_versions[0] || "";
				setCudaVersion(normalizedCuda);
			}
		} else {
			normalizedCuda = "";
			setCudaVersion("");
		}

		// 4. Normalize Output Formats
		let normalizedFormats = [...outputFormats];
		if (normalizedOs === "WIN") {
			normalizedFormats = normalizedFormats.filter((f) => f !== "setup.sh");
		} else {
			normalizedFormats = normalizedFormats.filter((f) => f !== "setup.ps1");
		}
		if (normalizedFormats.length === 0) {
			normalizedFormats = [normalizedOs === "WIN" ? "setup.ps1" : "setup.sh"];
		}
		setOutputFormats(normalizedFormats);

		setGenerating(true);
		setApiDone(false);
		setError(null);
		try {
			const req: ScriptGenerationRequest = {
				profile_id: selectedProfile,
				target_os: normalizedOs,
				output_formats: normalizedFormats,
				python_version: normalizedPy,
				...(activeProfile.cuda_required && normalizedCuda
					? { cuda_version: normalizedCuda }
					: {}),
			};
			const res = await api.generateScript(req);
			setResult(res);
			setApiDone(true);
		} catch (err) {
			setError(
				err instanceof Error ? err.message : "Failed to generate script",
			);
			setGenerating(false);
		}
	};

	const handleDownload = () => {
		if (result) {
			// download_url from backend is a full path like "/api/v1/scripts/{job_id}/download"
			// so we only need the origin (host), not the API_BASE_URL which already includes /api/v1
			const baseUrl = (
				process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"
			).replace(/\/api\/v1$/, "");
			window.open(`${baseUrl}${result.download_url}`, "_blank");
		}
	};

	const toggleFormat = (fmt: string) => {
		if (outputFormats.includes(fmt)) {
			if (outputFormats.length > 1) {
				setOutputFormats(outputFormats.filter((f) => f !== fmt));
			}
		} else {
			setOutputFormats([...outputFormats, fmt]);
		}
	};

	const activeProfile = profiles.find((p) => p.slug === selectedProfile);

	if (loadingProfiles) {
		return (
			<div
				style={{
					textAlign: "center",
					padding: "4rem",
					color: "var(--text-muted)",
				}}
			>
				<motion.div
					animate={{ rotate: 360 }}
					transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
					style={{ display: "inline-block", marginBottom: "1rem" }}
				>
					<Server size={32} />
				</motion.div>
				<p>Loading profiles...</p>
			</div>
		);
	}

	return (
		<div style={{ maxWidth: "800px", margin: "0 auto" }}>
			{/* Progress Indicator */}
			<div
				style={{
					display: "flex",
					alignItems: "center",
					justifyContent: "center",
					marginBottom: "3rem",
					gap: "1rem",
				}}
			>
				<StepIndicator num={1} active={step >= 1} label="Select" />
				<div
					style={{
						height: "2px",
						width: "50px",
						background:
							step >= 2 ? "var(--brand-primary)" : "var(--border-strong)",
					}}
				/>
				<StepIndicator num={2} active={step >= 2} label="Configure" />
				<div
					style={{
						height: "2px",
						width: "50px",
						background:
							step >= 3 ? "var(--brand-primary)" : "var(--border-strong)",
					}}
				/>
				<StepIndicator num={3} active={step >= 3} label="Result" />
			</div>

			<AnimatePresence mode="wait">
				{/* Step 1: Select Profile */}
				{step === 1 && (
					<motion.div
						key="step1"
						initial={{ opacity: 0, x: 20 }}
						animate={{ opacity: 1, x: 0 }}
						exit={{ opacity: 0, x: -20 }}
						className="glass-panel"
						style={{ padding: "2rem" }}
					>
						<h2 style={{ marginBottom: "1.5rem" }}>
							Select Environment Profile
						</h2>
						<div
							style={{ display: "flex", flexDirection: "column", gap: "1rem" }}
						>
							{profiles.map((p) => (
								<div
									key={p.slug}
									onClick={() => {
										setSelectedProfile(p.slug);

										if (p.python_versions?.length > 0) {
											setPythonVersion(p.python_versions[0]);
										}

										const cudaVersions = p.cuda_versions ?? [];
										if (p.cuda_required && cudaVersions.length > 0) {
											setCudaVersion(cudaVersions[0]);
										} else {
											setCudaVersion("");
										}

										const isWin =
											p.os_support.includes("WIN") &&
											!p.os_support.includes("LINUX");

										if (isWin) {
											setTargetOs("WIN");

											setOutputFormats((prev) =>
												prev.map((f) => (f === "setup.sh" ? "setup.ps1" : f)),
											);
										}
									}}
									style={{
										padding: "1rem",
										border: `1px solid ${selectedProfile === p.slug ? "var(--brand-primary)" : "var(--border-subtle)"}`,
										borderRadius: "8px",
										cursor: "pointer",
										background:
											selectedProfile === p.slug
												? "rgba(99, 102, 241, 0.1)"
												: "transparent",
										display: "flex",
										justifyContent: "space-between",
										alignItems: "center",
									}}
								>
									<div>
										<div style={{ fontWeight: 600, fontSize: "1.1rem" }}>
											{p.name}
										</div>
										<div
											style={{
												fontSize: "0.85rem",
												color: "var(--text-secondary)",
											}}
										>
											{p.description}
										</div>
									</div>
									{selectedProfile === p.slug && (
										<Check color="var(--brand-primary)" />
									)}
								</div>
							))}
						</div>
						<div
							style={{
								display: "flex",
								justifyContent: "flex-end",
								marginTop: "2rem",
							}}
						>
							<button className="btn btn-primary" onClick={() => setStep(2)}>
								Next <ChevronRight size={18} />
							</button>
						</div>
					</motion.div>
				)}

				{/* Step 2: Configure */}
				{step === 2 &&
					activeProfile &&
					(generating ? (
						<TerminalLoader
							targetOs={targetOs}
							profileName={activeProfile.name}
							pythonVersion={pythonVersion}
							cudaVersion={cudaVersion || undefined}
							isResolved={apiDone}
							onComplete={() => {
								setStep(3);
								setGenerating(false);
							}}
							title="EnvForage Script Compiler"
						/>
					) : (
						<motion.div
							key="step2"
							initial={{ opacity: 0, x: 20 }}
							animate={{ opacity: 1, x: 0 }}
							exit={{ opacity: 0, x: -20 }}
							className="glass-panel"
							style={{ padding: "2rem" }}
						>
							<h2 style={{ marginBottom: "0.5rem" }}>Configure Setup</h2>
							<p
								style={{ color: "var(--text-secondary)", marginBottom: "2rem" }}
							>
								Targeting: <strong>{activeProfile.name}</strong>
							</p>

							<div style={{ marginBottom: "2rem" }}>
								<label
									style={{
										display: "block",
										marginBottom: "0.75rem",
										fontWeight: 500,
									}}
								>
									Target Operating System
								</label>
								<div style={{ display: "flex", gap: "1rem" }}>
									{["LINUX", "WSL", "WIN"].map((os) => {
										const isSupported = activeProfile.os_support.includes(os);
										return (
											<button
												key={os}
												disabled={!isSupported}
												onClick={() => setTargetOs(os)}
												style={{
													flex: 1,
													padding: "1rem",
													background:
														targetOs === os
															? "rgba(99, 102, 241, 0.1)"
															: "transparent",
													border: `1px solid ${targetOs === os ? "var(--brand-primary)" : "var(--border-strong)"}`,
													borderRadius: "8px",
													color: isSupported
														? "var(--text-primary)"
														: "var(--text-muted)",
													cursor: isSupported ? "pointer" : "not-allowed",
													fontFamily: "var(--font-sans)",
													fontWeight: 500,
												}}
											>
												{os}
												{!isSupported && (
													<div
														style={{ fontSize: "0.7rem", marginTop: "0.25rem" }}
													>
														(Unsupported)
													</div>
												)}
											</button>
										);
									})}
								</div>
							</div>

							<div
								style={{ display: "flex", gap: "2rem", marginBottom: "2rem" }}
							>
								<div style={{ flex: 1 }}>
									<label
										style={{
											display: "block",
											marginBottom: "0.75rem",
											fontWeight: 500,
										}}
									>
										Python Version
									</label>
									<select
										value={pythonVersion}
										onChange={(e) => setPythonVersion(e.target.value)}
										style={{
											width: "100%",
											padding: "0.75rem",
											borderRadius: "8px",
											background: "rgba(255,255,255,0.05)",
											border: "1px solid var(--border-strong)",
											color: "var(--text-primary)",
											fontFamily: "var(--font-mono)",
										}}
									>
										{activeProfile.python_versions.map((v) => (
											<option
												key={v}
												value={v}
												style={{ background: "#1e1e1e" }}
											>
												{v}
											</option>
										))}
									</select>
								</div>

								{activeProfile.cuda_required && activeProfile.cuda_versions && (
									<div style={{ flex: 1 }}>
										<label
											style={{
												display: "block",
												marginBottom: "0.75rem",
												fontWeight: 500,
											}}
										>
											CUDA Version
										</label>
										<select
											value={cudaVersion}
											onChange={(e) => setCudaVersion(e.target.value)}
											style={{
												width: "100%",
												padding: "0.75rem",
												borderRadius: "8px",
												background: "rgba(255,255,255,0.05)",
												border: "1px solid var(--brand-accent)",
												color: "var(--text-primary)",
												fontFamily: "var(--font-mono)",
											}}
										>
											{activeProfile.cuda_versions.map((v) => (
												<option
													key={v}
													value={v}
													style={{ background: "#1e1e1e" }}
												>
													{v}
												</option>
											))}
										</select>
									</div>
								)}
							</div>

							<div style={{ marginBottom: "3rem" }}>
								<label
									style={{
										display: "block",
										marginBottom: "0.75rem",
										fontWeight: 500,
									}}
								>
									Output Formats
								</label>
								<div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
									{[
										"setup.sh",
										"setup.ps1",
										"requirements.txt",
										"Dockerfile",
									].map((fmt) => {
										// Disable setup.sh if OS is Linux, and vice versa
										if (fmt === "setup.sh" && targetOs === "WIN") return null;
										if (fmt === "setup.ps1" && targetOs !== "WIN") return null;

										return (
											<button
												key={fmt}
												onClick={() => toggleFormat(fmt)}
												style={{
													padding: "0.75rem 1.5rem",
													background: outputFormats.includes(fmt)
														? "rgba(99, 102, 241, 0.1)"
														: "transparent",
													border: `1px solid ${outputFormats.includes(fmt) ? "var(--brand-primary)" : "var(--border-strong)"}`,
													borderRadius: "8px",
													color: "var(--text-primary)",
													cursor: "pointer",
													fontFamily: "var(--font-mono)",
													fontSize: "0.9rem",
												}}
											>
												{fmt}
											</button>
										);
									})}
								</div>
							</div>

							{error && (
								<div
									style={{
										background: "rgba(239, 68, 68, 0.1)",
										color: "#ef4444",
										padding: "1rem",
										borderRadius: "8px",
										marginBottom: "2rem",
										border: "1px solid rgba(239, 68, 68, 0.2)",
									}}
								>
									{error}
								</div>
							)}

							<div
								style={{
									display: "flex",
									justifyContent: "space-between",
									marginTop: "2rem",
								}}
							>
								<button
									className="btn btn-secondary"
									onClick={() => setStep(1)}
								>
									Back
								</button>
								<button
									className="btn btn-primary"
									onClick={handleGenerate}
									disabled={generating}
								>
									{generating ? (
										<>
											<Loader2
												className="animate-spin"
												size={18}
												style={{ marginRight: "0.5rem" }}
											/>{" "}
											Generating...
										</>
									) : (
										"Generate Scripts"
									)}
								</button>
							</div>
						</motion.div>
					))}

				{/* Step 3: Result */}
				{step === 3 && result && (
					<motion.div
						key="step3"
						initial={{ opacity: 0, x: 20 }}
						animate={{ opacity: 1, x: 0 }}
						className="glass-panel"
						style={{ padding: "2rem" }}
					>
						<div
							style={{
								display: "flex",
								alignItems: "center",
								gap: "1rem",
								marginBottom: "2rem",
								color: "var(--brand-accent)",
							}}
						>
							<CheckCircleIcon size={32} />
							<div>
								<h2 style={{ color: "var(--text-primary)" }}>Success!</h2>
								<p style={{ color: "var(--brand-accent)" }}>
									{result.scripts.length} files generated securely.
								</p>
							</div>
						</div>

						<div
							style={{
								background: "#1e1e1e",
								borderRadius: "8px",
								overflow: "hidden",
								marginBottom: "2rem",
							}}
						>
							<div
								style={{
									display: "flex",
									justifyContent: "space-between",
									alignItems: "center",
									padding: "0.75rem 1rem",
									background: "#252526",
									borderBottom: "1px solid #3e3e42",
								}}
							>
								<div
									style={{
										fontFamily: "var(--font-mono)",
										fontSize: "0.85rem",
										color: "#cccccc",
									}}
								>
									Job ID: {result.job_id}
								</div>
							</div>
							<div
								style={{
									padding: "1.5rem",
									maxHeight: "400px",
									overflowY: "auto",
								}}
							>
								<SyntaxHighlighter
									language="bash"
									style={vscDarkPlus}
									customStyle={{ margin: 0, background: "transparent" }}
								>
									{`# Your scripts have been generated and are ready to download.\n# Files included:\n${result.scripts.map((s) => `# - ${s.filename} (${s.size_bytes} bytes)`).join("\n")}\n\n# Note: Scripts have passed the EnvForage Safety Filter.`}
								</SyntaxHighlighter>
							</div>
						</div>

						<div
							style={{
								display: "flex",
								justifyContent: "flex-end",
								gap: "1rem",
							}}
						>
							<button
								className="btn btn-secondary"
								onClick={() => {
									setStep(1);
									setResult(null);
								}}
							>
								Start Over
							</button>
							<button
								className="btn btn-primary"
								onClick={handleDownload}
								style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}
							>
								<Download size={18} /> Download ZIP Archive
							</button>
						</div>
					</motion.div>
				)}
			</AnimatePresence>
		</div>
	);
}

export default function GeneratePage() {
	useGenerateAnalytics();
	return (
		<div
			className="container"
			style={{ paddingTop: "4rem", paddingBottom: "6rem" }}
		>
			<div style={{ textAlign: "center", marginBottom: "3rem" }}>
				<h1 style={{ fontSize: "3rem", marginBottom: "1rem" }}>
					Script Generator
				</h1>
				<p style={{ color: "var(--text-secondary)", fontSize: "1.1rem" }}>
					Deterministic, safe script generation for your environment.
				</p>
			</div>

			<Suspense
				fallback={
					<div style={{ textAlign: "center", color: "var(--text-muted)" }}>
						Loading...
					</div>
				}
			>
				<WizardContent />
			</Suspense>
		</div>
	);
}

function StepIndicator({
	num,
	active,
	label,
}: {
	num: number;
	active: boolean;
	label: string;
}) {
	return (
		<div
			style={{
				display: "flex",
				flexDirection: "column",
				alignItems: "center",
				gap: "0.5rem",
			}}
		>
			<div
				style={{
					width: "32px",
					height: "32px",
					borderRadius: "50%",
					display: "flex",
					alignItems: "center",
					justifyContent: "center",
					background: active ? "var(--brand-primary)" : "transparent",
					border: `2px solid ${active ? "var(--brand-primary)" : "var(--border-strong)"}`,
					color: active ? "white" : "var(--text-muted)",
					fontWeight: 600,
					transition: "all var(--transition-normal)",
				}}
			>
				{num}
			</div>
			<div
				style={{
					fontSize: "0.8rem",
					color: active ? "var(--text-primary)" : "var(--text-muted)",
					fontWeight: 500,
				}}
			>
				{label}
			</div>
		</div>
	);
}

function CheckCircleIcon(
	props: React.SVGProps<SVGSVGElement> & { size?: number },
) {
	return (
		<svg
			xmlns="http://www.w3.org/2000/svg"
			width={props.size || 24}
			height={props.size || 24}
			viewBox="0 0 24 24"
			fill="none"
			stroke="currentColor"
			strokeWidth="2"
			strokeLinecap="round"
			strokeLinejoin="round"
			{...props}
		>
			<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
			<polyline points="22 4 12 14.01 9 11.01" />
		</svg>
	);
}

export class GenerateErrorBoundary extends Component<{ children: React.ReactNode }, { hasError: boolean, error: Error | null }> {
    constructor(props: { children: React.ReactNode }) {
        super(props);
        this.state = { hasError: false, error: null };
    }

    static getDerivedStateFromError(error: Error) {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        console.error("Generate Module Error:", error, errorInfo);
        try {
            fetch('/api/telemetry/errors', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ error: error.message, stack: errorInfo.componentStack })
            }).catch(() => {});
        } catch {}
    }

    render() {
        if (this.state.hasError) {
            return (
                <div style={{ padding: '2rem', background: '#fee2e2', color: '#991b1b', borderRadius: '8px', margin: '2rem' }}>
                    <h2>Generation Module Crashed</h2>
                    <p>We caught an unexpected error in the generator pipeline.</p>
                    <pre style={{ fontSize: '0.8rem', marginTop: '1rem', overflowX: 'auto' }}>
                        {this.state.error?.message}
                    </pre>
                    <button 
                        onClick={() => this.setState({ hasError: false, error: null })}
                        style={{ marginTop: '1rem', padding: '0.5rem 1rem', background: '#991b1b', color: 'white', border: 'none', borderRadius: '4px' }}
                    >
                        Retry Pipeline
                    </button>
                </div>
            );
        }
        return this.props.children;
    }
}

export function useGenerateAnalytics() {
    useEffect(() => {
        const startTime = performance.now();
        return () => {
            const duration = performance.now() - startTime;
            console.debug(`Generate page session duration: ${duration}ms`);
        };
    }, []);
}
