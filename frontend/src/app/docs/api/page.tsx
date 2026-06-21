"use client";

import { useState } from "react";
import { Code, Copy, Check, Play } from "lucide-react";

export default function ApiReferencePage() {
	const [activeTab, setActiveTab] = useState<"curl" | "python" | "javascript">("curl");
	const [copiedId, setCopiedId] = useState<string>("");

	// Simulator State
	const [simOS, setSimOS] = useState<"linux" | "windows" | "macos">("linux");
	const [simFramework, setSimFramework] = useState<"pytorch" | "tensorflow" | "jax">("pytorch");
	const [simDriver, setSimDriver] = useState<string>("535.104");

	const copyCode = (text: string, id: string) => {
		navigator.clipboard.writeText(text);
		setCopiedId(id);
		setTimeout(() => setCopiedId(""), 2000);
	};

	const codeSnippets = {
		curl: `curl -X POST "http://localhost:8000/api/v1/compatibility/resolve" \\
  -H "Content-Type: application/json" \\
  -d '{
    "os": "${simOS}",
    "gpu_vendor": "${simOS === "macos" ? "apple" : "nvidia"}",
    "driver_version": "${simOS === "macos" ? "N/A" : simDriver}",
    "framework": "${simFramework}"
  }'`,
		python: `import requests

url = "http://localhost:8000/api/v1/compatibility/resolve"
payload = {
    "os": "${simOS}",
    "gpu_vendor": "${simOS === "macos" ? "apple" : "nvidia"}",
    "driver_version": "${simOS === "macos" ? "N/A" : simDriver}",
    "framework": "${simFramework}"
}

response = requests.post(url, json=payload)
data = response.json()

print(f"CUDA: {data['cuda_version']}")
print(f"Packages: {data['packages']}")`,
		javascript: `const resolveDependencies = async () => {
  const url = "http://localhost:8000/api/v1/compatibility/resolve";
  const payload = {
    os: "${simOS}",
    gpu_vendor: "${simOS === "macos" ? "apple" : "nvidia"}",
    driver_version: "${simOS === "macos" ? "N/A" : simDriver}",
    framework: "${simFramework}"
  };

  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  
  const data = await response.json();
  console.log("Resolved Packages:", data.packages);
};`,
	};

	// Generate dynamic simulated response based on inputs
	const getSimulatedResponse = () => {
		const pythonVersion = "3.10";
		let cudaVersion = "12.1";
		let packages: string[] = [];

		if (simOS === "macos") {
			cudaVersion = "N/A (Metal)";
			if (simFramework === "pytorch") {
				packages = ["torch==2.2.0", "torchvision==0.17.0"];
			} else if (simFramework === "tensorflow") {
				packages = ["tensorflow-macos==2.15.0", "tensorflow-metal==1.1.0"];
			} else {
				packages = ["jax[cpu]==0.4.23"];
			}
		} else {
			// Linux or Windows Nvidia matches
			if (simDriver === "535.104") {
				cudaVersion = "12.1";
				if (simFramework === "pytorch") {
					packages = ["torch==2.1.0+cu121", "torchvision==0.16.0+cu121", "torchaudio==2.1.0+cu121"];
				} else if (simFramework === "tensorflow") {
					packages = ["tensorflow==2.13.0"];
				} else {
					packages = ["jax[cuda12_pip]==0.4.14", "jaxlib==0.4.14+cuda12.cudnn89"];
				}
			} else if (simDriver === "525.60") {
				cudaVersion = "11.8";
				if (simFramework === "pytorch") {
					packages = ["torch==2.0.0+cu118", "torchvision==0.15.1+cu118"];
				} else if (simFramework === "tensorflow") {
					packages = ["tensorflow==2.12.0"];
				} else {
					packages = ["jax[cuda11_pip]==0.4.10", "jaxlib==0.4.10+cuda11.cudnn86"];
				}
			} else {
				// Older drivers v515
				cudaVersion = "11.7";
				if (simFramework === "pytorch") {
					packages = ["torch==1.13.1+cu117", "torchvision==0.14.1+cu117"];
				} else if (simFramework === "tensorflow") {
					packages = ["tensorflow==2.10.0"];
				} else {
					packages = ["jax[cuda11_pip]==0.3.25", "jaxlib==0.3.25+cuda11.cudnn82"];
				}
			}
		}

		return JSON.stringify({
			status: "success",
			python_version: pythonVersion,
			cuda_version: cudaVersion,
			packages: packages,
			verification_status: "verified"
		}, null, 2);
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
				<Code size={20} />
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
				REST API Reference
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
				Integrate the EnvForage dependency matrix resolution logic directly into your custom CI/CD pipelines, DevOps tooling, or setup workflows.
			</p>

			{/* API Endpoint header */}
			<div
				style={{
					backgroundColor: "var(--bg-secondary)",
					border: "1px solid var(--border-subtle)",
					borderRadius: "12px",
					padding: "1.25rem 1.5rem",
					marginBottom: "2.5rem",
					display: "flex",
					alignItems: "center",
					gap: "1rem",
					flexWrap: "wrap",
				}}
			>
				<span
					style={{
						backgroundColor: "var(--brand-primary)",
						color: "#fff",
						padding: "4px 8px",
						borderRadius: "4px",
						fontSize: "0.8rem",
						fontWeight: 800,
					}}
				>
					POST
				</span>
				<code style={{ fontSize: "1rem", color: "var(--text-primary)", fontWeight: 600, fontFamily: "var(--font-mono)" }}>
					/api/v1/compatibility/resolve
				</code>
				<span style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
					(Resolves CUDA, Python, and package targets)
				</span>
			</div>

			{/* API SIMULATOR WIDGET */}
			<div
				style={{
					backgroundColor: "var(--bg-secondary)",
					border: "1px solid var(--border-subtle)",
					borderRadius: "16px",
					padding: "2rem",
					marginBottom: "3.5rem",
					boxShadow: "var(--shadow-lg)",
				}}
			>
				<div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "1.5rem" }}>
					<Play size={18} color="var(--brand-primary)" />
					<h3 style={{ fontSize: "1.25rem", fontWeight: 700, margin: 0, color: "var(--text-primary)" }}>
						Live Interactive Endpoint Simulator
					</h3>
				</div>
				
				{/* Selectors Grid */}
				<div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "1.25rem", marginBottom: "2rem" }}>
					<div>
						<label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "0.5rem" }}>
							Operating System
						</label>
						<select
							value={simOS}
							onChange={(e) => setSimOS(e.target.value as "linux" | "windows" | "macos")}
							style={{
								width: "100%",
								padding: "0.6rem 0.75rem",
								borderRadius: "8px",
								backgroundColor: "var(--bg-secondary)",
								border: "1px solid var(--border-subtle)",
								color: "var(--text-primary)",
								outline: "none",
								fontWeight: 600,
							}}
						>
							<option value="linux">Linux</option>
							<option value="windows">Windows</option>
							<option value="macos">macOS</option>
						</select>
					</div>

					<div>
						<label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "0.5rem" }}>
							ML Framework
						</label>
						<select
							value={simFramework}
							onChange={(e) => setSimFramework(e.target.value as "pytorch" | "tensorflow" | "jax")}
							style={{
								width: "100%",
								padding: "0.6rem 0.75rem",
								borderRadius: "8px",
								backgroundColor: "var(--bg-secondary)",
								border: "1px solid var(--border-subtle)",
								color: "var(--text-primary)",
								outline: "none",
								fontWeight: 600,
							}}
						>
							<option value="pytorch">PyTorch</option>
							<option value="tensorflow">TensorFlow</option>
							<option value="jax">JAX</option>
						</select>
					</div>

					{simOS !== "macos" && (
						<div>
							<label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "0.5rem" }}>
								Nvidia Driver Version
							</label>
							<select
								value={simDriver}
								onChange={(e) => setSimDriver(e.target.value)}
								style={{
									width: "100%",
									padding: "0.6rem 0.75rem",
									borderRadius: "8px",
									backgroundColor: "var(--bg-secondary)",
									border: "1px solid var(--border-subtle)",
									color: "var(--text-primary)",
									outline: "none",
									fontWeight: 600,
								}}
							>
								<option value="535.104">v535.104 (CUDA 12.1+)</option>
								<option value="525.60">v525.60 (CUDA 11.8+)</option>
								<option value="515.48">v515.48 (CUDA 11.7+)</option>
							</select>
						</div>
					)}
				</div>

				{/* Code Panels Split View */}
				<div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "1.5rem" }}>
					{/* Live Request */}
					<div>
						<div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
							<span style={{ fontSize: "0.85rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase" }}>
								Simulated Request
							</span>
							<div style={{ display: "flex", gap: "0.2rem" }}>
								{(["curl", "python", "javascript"] as const).map((lang) => (
									<button
										key={lang}
										onClick={() => setActiveTab(lang)}
										style={{
											fontSize: "0.75rem",
											fontWeight: 600,
											padding: "2px 6px",
											background: activeTab === lang ? "rgba(99, 102, 241, 0.15)" : "none",
											border: "none",
											borderRadius: "4px",
											color: activeTab === lang ? "var(--brand-primary)" : "var(--text-muted)",
											cursor: "pointer",
										}}
									>
										{lang === "curl" ? "cURL" : lang}
									</button>
								))}
							</div>
						</div>
						<div style={{ position: "relative" }}>
							<pre
								style={{
									backgroundColor: "#09090b",
									border: "1px solid var(--border-strong)",
									borderRadius: "10px",
									padding: "1rem",
									overflowX: "auto",
									fontFamily: "var(--font-mono)",
									fontSize: "0.825rem",
									color: "#e4e4e7",
									margin: 0,
									height: "180px",
								}}
							>
								<code style={{ color: "inherit" }}>{codeSnippets[activeTab]}</code>
							</pre>
							<button
								onClick={() => copyCode(codeSnippets[activeTab], "request")}
								style={{
									position: "absolute",
									right: "0.75rem",
									top: "0.75rem",
									background: "rgba(255, 255, 255, 0.05)",
									border: "1px solid rgba(255, 255, 255, 0.1)",
									borderRadius: "6px",
									padding: "4px",
									cursor: "pointer",
									color: copiedId === "request" ? "var(--brand-primary)" : "#a1a1aa",
								}}
							>
								{copiedId === "request" ? <Check size={14} /> : <Copy size={14} />}
							</button>
						</div>
					</div>

					{/* Live Response */}
					<div>
						<div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
							<span style={{ fontSize: "0.85rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase" }}>
								JSON Response (200 OK)
							</span>
						</div>
						<div style={{ position: "relative" }}>
							<pre
								style={{
									backgroundColor: "#09090b",
									border: "1px solid var(--border-strong)",
									borderRadius: "10px",
									padding: "1rem",
									overflowX: "auto",
									fontFamily: "var(--font-mono)",
									fontSize: "0.825rem",
									color: "#22c55e",
									margin: 0,
									height: "180px",
								}}
							>
								<code style={{ color: "inherit" }}>{getSimulatedResponse()}</code>
							</pre>
							<button
								onClick={() => copyCode(getSimulatedResponse(), "response")}
								style={{
									position: "absolute",
									right: "0.75rem",
									top: "0.75rem",
									background: "rgba(255, 255, 255, 0.05)",
									border: "1px solid rgba(255, 255, 255, 0.1)",
									borderRadius: "6px",
									padding: "4px",
									cursor: "pointer",
									color: copiedId === "response" ? "var(--brand-primary)" : "#a1a1aa",
								}}
							>
								{copiedId === "response" ? <Check size={14} /> : <Copy size={14} />}
							</button>
						</div>
					</div>
				</div>
			</div>

			{/* Request Payload Definition */}
			<h2
				style={{
					fontSize: "1.65rem",
					fontWeight: 700,
					marginBottom: "1.25rem",
					color: "var(--text-primary)",
				}}
			>
				Request Body Parameters
			</h2>

			<div style={{ overflowX: "auto", marginBottom: "3rem" }}>
				<table style={{ width: "100%", borderCollapse: "collapse", color: "var(--text-secondary)", fontSize: "0.95rem" }}>
					<thead>
						<tr style={{ borderBottom: "2px solid var(--border-subtle)", textAlign: "left" }}>
							<th style={{ padding: "0.75rem 1rem", fontWeight: 700, color: "var(--text-primary)" }}>Parameter</th>
							<th style={{ padding: "0.75rem 1rem", fontWeight: 700, color: "var(--text-primary)" }}>Type</th>
							<th style={{ padding: "0.75rem 1rem", fontWeight: 700, color: "var(--text-primary)" }}>Required</th>
							<th style={{ padding: "0.75rem 1rem", fontWeight: 700, color: "var(--text-primary)" }}>Description</th>
						</tr>
					</thead>
					<tbody>
						<tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
							<td style={{ padding: "1rem", fontFamily: "var(--font-mono)", color: "var(--brand-secondary)" }}>os</td>
							<td style={{ padding: "1rem" }}>string</td>
							<td style={{ padding: "1rem", color: "#ef4444", fontWeight: 600 }}>Yes</td>
							<td style={{ padding: "1rem" }}>Target operating system. Allowed: linux, windows, macos</td>
						</tr>
						<tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
							<td style={{ padding: "1rem", fontFamily: "var(--font-mono)", color: "var(--brand-secondary)" }}>gpu_vendor</td>
							<td style={{ padding: "1rem" }}>string</td>
							<td style={{ padding: "1rem", color: "#ef4444", fontWeight: 600 }}>Yes</td>
							<td style={{ padding: "1rem" }}>Graphics processor driver set. E.g. nvidia, amd, cpu</td>
						</tr>
						<tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
							<td style={{ padding: "1rem", fontFamily: "var(--font-mono)", color: "var(--brand-secondary)" }}>driver_version</td>
							<td style={{ padding: "1rem" }}>string</td>
							<td style={{ padding: "1rem", color: "#ef4444", fontWeight: 600 }}>Yes</td>
							<td style={{ padding: "1rem" }}>Local graphic driver version identifier. E.g. &quot;535.104&quot;, &quot;525.60&quot;</td>
						</tr>
						<tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
							<td style={{ padding: "1rem", fontFamily: "var(--font-mono)", color: "var(--brand-secondary)" }}>framework</td>
							<td style={{ padding: "1rem" }}>string</td>
							<td style={{ padding: "1rem", color: "#ef4444", fontWeight: 600 }}>Yes</td>
							<td style={{ padding: "1rem" }}>Desired ML framework stack. Allowed: pytorch, tensorflow, jax</td>
						</tr>
					</tbody>
				</table>
			</div>

			{/* Status Codes */}
			<h2
				style={{
					fontSize: "1.65rem",
					fontWeight: 700,
					marginTop: "3rem",
					marginBottom: "1.25rem",
					color: "var(--text-primary)",
				}}
			>
				HTTP Response Codes
			</h2>

			<div style={{ overflowX: "auto" }}>
				<table style={{ width: "100%", borderCollapse: "collapse", color: "var(--text-secondary)", fontSize: "0.95rem" }}>
					<thead>
						<tr style={{ borderBottom: "2px solid var(--border-subtle)", textAlign: "left" }}>
							<th style={{ padding: "0.75rem 1rem", fontWeight: 700, color: "var(--text-primary)", width: "15%" }}>Code</th>
							<th style={{ padding: "0.75rem 1rem", fontWeight: 700, color: "var(--text-primary)", width: "25%" }}>Status</th>
							<th style={{ padding: "0.75rem 1rem", fontWeight: 700, color: "var(--text-primary)" }}>Description</th>
						</tr>
					</thead>
					<tbody>
						<tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
							<td style={{ padding: "1rem", fontFamily: "var(--font-mono)", color: "#22c55e", fontWeight: 700 }}>200</td>
							<td style={{ padding: "1rem", fontWeight: 600 }}>OK</td>
							<td style={{ padding: "1rem" }}>Dependencies resolved successfully. Returns compatible packages configuration.</td>
						</tr>
						<tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
							<td style={{ padding: "1rem", fontFamily: "var(--font-mono)", color: "#eab308", fontWeight: 700 }}>400</td>
							<td style={{ padding: "1rem", fontWeight: 600 }}>Bad Request</td>
							<td style={{ padding: "1rem" }}>Query attributes could not be resolved or driver specifications are missing.</td>
						</tr>
						<tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
							<td style={{ padding: "1rem", fontFamily: "var(--font-mono)", color: "#eab308", fontWeight: 700 }}>422</td>
							<td style={{ padding: "1rem", fontWeight: 600 }}>Validation Error</td>
							<td style={{ padding: "1rem" }}>Request payload contains invalid properties or fails data scheme validations.</td>
						</tr>
						<tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
							<td style={{ padding: "1rem", fontFamily: "var(--font-mono)", color: "#ef4444", fontWeight: 700 }}>500</td>
							<td style={{ padding: "1rem", fontWeight: 600 }}>Internal Error</td>
							<td style={{ padding: "1rem" }}>Resolution server experienced an issue or cannot query dependency db.</td>
						</tr>
					</tbody>
				</table>
			</div>
		</div>
	);
}
