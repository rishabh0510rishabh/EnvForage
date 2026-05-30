"use client";

import { AnimatePresence, motion } from "framer-motion";
import {
	FileText,
	HelpCircle,
	Maximize2,
	Network,
	Search,
	ZoomIn,
	ZoomOut,
} from "lucide-react";
import type React from "react";
import { useRef, useState } from "react";

// --- Types ---
interface Node {
	id: string;
	label: string;
	type: "root" | "profile" | "package" | "system" | "env" | "service";
	description: string;
	details?: Record<string, string | number | string[]>;
	x: number;
	y: number;
}

interface Edge {
	source: string;
	target: string;
	type: "dependency" | "contains" | "config" | "dataflow";
}

// --- Data ---
const ML_NODES: Node[] = [
	{
		id: "python",
		label: "Python Runtime",
		type: "root",
		description:
			"Core programming language runtime underpinning all environments.",
		details: {
			Supported: "3.9, 3.10, 3.11, 3.12",
			Purpose: "Execution Environment",
		},
		x: 450,
		y: 300,
	},
	{
		id: "cuda",
		label: "NVIDIA CUDA",
		type: "root",
		description: "Parallel computing platform for acceleration on NVIDIA GPUs.",
		details: { Supported: "11.8, 12.1", Purpose: "Hardware Acceleration" },
		x: 650,
		y: 300,
	},

	// Profiles
	{
		id: "prof-pytorch",
		label: "PyTorch CUDA Profile",
		type: "profile",
		description: "GPU-accelerated deep learning environment.",
		details: { Tags: "deep-learning, gpu, cuda", OS: "Linux, WSL" },
		x: 250,
		y: 150,
	},
	{
		id: "prof-tensorflow",
		label: "TensorFlow GPU Profile",
		type: "profile",
		description: "TensorFlow GPU acceleration via CUDA.",
		details: { Tags: "deep-learning, gpu, tensorflow", OS: "Linux, WSL" },
		x: 250,
		y: 450,
	},
	{
		id: "prof-yolov8",
		label: "YOLOv8 Profile",
		type: "profile",
		description: "Ultralytics YOLOv8 computer vision stack.",
		details: {
			Tags: "computer-vision, detection, yolo",
			OS: "Linux, WSL, Windows",
		},
		x: 850,
		y: 150,
	},
	{
		id: "prof-sd",
		label: "Stable Diffusion Profile",
		type: "profile",
		description: "Hugging Face Diffusers generative image stack.",
		details: { Tags: "generative-ai, diffusion, gpu", OS: "Linux, WSL" },
		x: 850,
		y: 450,
	},
	{
		id: "prof-jax",
		label: "JAX CUDA Profile",
		type: "profile",
		description: "Google JAX high-performance numerical computing.",
		details: { Tags: "deep-learning, gpu, jax", OS: "Linux, WSL" },
		x: 550,
		y: 100,
	},
	{
		id: "prof-rag",
		label: "LangChain RAG Profile",
		type: "profile",
		description: "CPU-friendly LangChain retrieval augmented generation stack.",
		details: {
			Tags: "langchain, rag, vector-db, cpu",
			OS: "Linux, WSL, Windows",
		},
		x: 550,
		y: 500,
	},

	// Packages
	{
		id: "torch",
		label: "torch (v2.1.2)",
		type: "package",
		description:
			"Tensors and Dynamic neural networks in Python with strong GPU acceleration.",
		details: { License: "BSD-3", CUDA_Variant: "cu118 / cu121" },
		x: 380,
		y: 220,
	},
	{
		id: "torchvision",
		label: "torchvision (v0.16.2)",
		type: "package",
		description:
			"Image and video datasets, transforms, and models for PyTorch.",
		details: { Dependency: "torch" },
		x: 220,
		y: 280,
	},
	{
		id: "torchaudio",
		label: "torchaudio (v2.1.2)",
		type: "package",
		description: "Audio signal processing library for PyTorch.",
		details: { Dependency: "torch" },
		x: 380,
		y: 120,
	},
	{
		id: "tensorflow-pkg",
		label: "tensorflow (v2.14.0)",
		type: "package",
		description: "End-to-end open source platform for machine learning.",
		details: { CUDA_Required: "11.8" },
		x: 180,
		y: 380,
	},
	{
		id: "numpy",
		label: "numpy (v1.26.4)",
		type: "package",
		description: "Fundamental package for array computing in Python.",
		details: { Category: "Math / Arrays" },
		x: 550,
		y: 300,
	},
	{
		id: "ultralytics",
		label: "ultralytics (v8.2.0)",
		type: "package",
		description:
			"YOLOv8 framework for object detection, segmentation, and classification.",
		details: { Dependencies: "torch, opencv-python" },
		x: 780,
		y: 220,
	},
	{
		id: "opencv-python",
		label: "opencv-python (v4.9.0)",
		type: "package",
		description: "Wrapper package for OpenCV computer vision library.",
		details: { Category: "Computer Vision" },
		x: 720,
		y: 200,
	},
	{
		id: "diffusers",
		label: "diffusers (v0.27.2)",
		type: "package",
		description: "State-of-the-art pretrained diffusion models.",
		details: { Core: "Hugging Face" },
		x: 750,
		y: 380,
	},
	{
		id: "transformers",
		label: "transformers (v4.40.0)",
		type: "package",
		description:
			"State-of-the-art Machine Learning for PyTorch, TensorFlow, and JAX.",
		details: { Core: "Hugging Face" },
		x: 880,
		y: 320,
	},
	{
		id: "jax-pkg",
		label: "jax (v0.4.26)",
		type: "package",
		description:
			"Autograd and XLA, brought together for high-performance ML research.",
		details: { Compiler: "XLA" },
		x: 480,
		y: 180,
	},
	{
		id: "jaxlib",
		label: "jaxlib (v0.4.26)",
		type: "package",
		description: "C++ library supporting JAX runtime.",
		details: { GPU_Support: "CUDA / XLA" },
		x: 620,
		y: 180,
	},
	{
		id: "langchain-pkg",
		label: "langchain (v0.3.0)",
		type: "package",
		description: "Building applications with LLMs through composability.",
		details: { Category: "Orchestration" },
		x: 420,
		y: 440,
	},
	{
		id: "chromadb",
		label: "chromadb (v0.5.0)",
		type: "package",
		description: "Open-source AI application database for embeddings.",
		details: { Type: "Vector Store" },
		x: 680,
		y: 440,
	},
];

const ML_EDGES: Edge[] = [
	// Profile to packages/roots
	{ source: "prof-pytorch", target: "torch", type: "contains" },
	{ source: "prof-pytorch", target: "torchvision", type: "contains" },
	{ source: "prof-pytorch", target: "torchaudio", type: "contains" },
	{ source: "prof-pytorch", target: "numpy", type: "contains" },
	{ source: "prof-tensorflow", target: "tensorflow-pkg", type: "contains" },
	{ source: "prof-tensorflow", target: "numpy", type: "contains" },
	{ source: "prof-yolov8", target: "ultralytics", type: "contains" },
	{ source: "prof-yolov8", target: "opencv-python", type: "contains" },
	{ source: "prof-yolov8", target: "numpy", type: "contains" },
	{ source: "prof-sd", target: "diffusers", type: "contains" },
	{ source: "prof-sd", target: "transformers", type: "contains" },
	{ source: "prof-sd", target: "torch", type: "contains" },
	{ source: "prof-jax", target: "jax-pkg", type: "contains" },
	{ source: "prof-jax", target: "jaxlib", type: "contains" },
	{ source: "prof-rag", target: "langchain-pkg", type: "contains" },
	{ source: "prof-rag", target: "chromadb", type: "contains" },

	// Package dependencies
	{ source: "torch", target: "python", type: "dependency" },
	{ source: "torch", target: "cuda", type: "dependency" },
	{ source: "torchvision", target: "torch", type: "dependency" },
	{ source: "torchaudio", target: "torch", type: "dependency" },
	{ source: "tensorflow-pkg", target: "python", type: "dependency" },
	{ source: "tensorflow-pkg", target: "cuda", type: "dependency" },
	{ source: "ultralytics", target: "torch", type: "dependency" },
	{ source: "ultralytics", target: "opencv-python", type: "dependency" },
	{ source: "diffusers", target: "torch", type: "dependency" },
	{ source: "transformers", target: "torch", type: "dependency" },
	{ source: "jax-pkg", target: "python", type: "dependency" },
	{ source: "jaxlib", target: "cuda", type: "dependency" },
	{ source: "jax-pkg", target: "jaxlib", type: "dependency" },
	{ source: "langchain-pkg", target: "python", type: "dependency" },
	{ source: "chromadb", target: "numpy", type: "dependency" },
];

const INFRA_NODES: Node[] = [
	// Services
	{
		id: "sys-fe",
		label: "Frontend (Next.js)",
		type: "system",
		description: "Modern React-based UI running under Next.js 16.",
		details: {
			Framework: "Next.js 16 (App Router)",
			Styling: "Vanilla CSS + Cyberpunk tokens",
			State: "React State & Framer Motion",
		},
		x: 250,
		y: 300,
	},
	{
		id: "sys-be",
		label: "Backend (FastAPI)",
		type: "system",
		description: "Python ASGI Web Framework for high-performance API routing.",
		details: {
			Framework: "FastAPI / Python",
			Server: "Uvicorn ASGI",
			Async: "Enabled",
		},
		x: 500,
		y: 300,
	},
	{
		id: "sys-cli",
		label: "CLI Tool",
		type: "system",
		description: "Command line utility for developer system diagnostics.",
		details: { Package: "poetry/pip", Language: "Python 3.10+" },
		x: 500,
		y: 120,
	},
	{
		id: "sys-db",
		label: "PostgreSQL Database",
		type: "service",
		description:
			"Primary relational storage for profiles, logs, and configurations.",
		details: {
			Driver: "asyncpg",
			ORM: "SQLAlchemy / Alembic",
			Tables: "Profiles, Jobs, Recommendations",
		},
		x: 750,
		y: 200,
	},
	{
		id: "sys-redis",
		label: "Redis Cache & Limiter",
		type: "service",
		description: "High-speed key-value cache and rate limit broker.",
		details: {
			Client: "redis-py",
			Purpose: "Rate Limiting & Matrix Cache",
			Production: "Required",
		},
		x: 750,
		y: 400,
	},
	{
		id: "sys-llm",
		label: "AI Troubleshooter Engine",
		type: "service",
		description: "Intelligent diagnostic agent recommending fixes and repairs.",
		details: {
			Providers: "OpenAI, OpenRouter, Ollama, Mock",
			Speed: "Streaming Responses",
		},
		x: 750,
		y: 100,
	},

	// Environment Variables
	{
		id: "env-db-url",
		label: "DATABASE_URL",
		type: "env",
		description: "PostgreSQL connection string.",
		details: {
			Format: "postgresql+asyncpg://...",
			ConfigPath: "Settings.database_url",
		},
		x: 200,
		y: 480,
	},
	{
		id: "env-redis-url",
		label: "REDIS_URL",
		type: "env",
		description: "Redis Broker URL connection endpoint.",
		details: { Format: "redis://...", ConfigPath: "Settings.redis_url" },
		x: 380,
		y: 480,
	},
	{
		id: "env-provider",
		label: "ENVFORGE_LLM_PROVIDER",
		type: "env",
		description: "Specifies which AI system model to resolve queries.",
		details: { Allowed: "openai, openrouter, ollama, mock", Default: "mock" },
		x: 560,
		y: 480,
	},
	{
		id: "env-admin-key",
		label: "ADMIN_API_KEY",
		type: "env",
		description: "Security key that protects administrative REST actions.",
		details: {
			Usage: "Admin auth headers",
			Production: "Mandatory if defined",
		},
		x: 740,
		y: 480,
	},
];

const INFRA_EDGES: Edge[] = [
	// Inter-service flows
	{ source: "sys-fe", target: "sys-be", type: "dataflow" },
	{ source: "sys-cli", target: "sys-be", type: "dataflow" },
	{ source: "sys-be", target: "sys-db", type: "dependency" },
	{ source: "sys-be", target: "sys-redis", type: "dependency" },
	{ source: "sys-be", target: "sys-llm", type: "dependency" },

	// Config variables targeting systems
	{ source: "env-db-url", target: "sys-be", type: "config" },
	{ source: "env-redis-url", target: "sys-be", type: "config" },
	{ source: "env-provider", target: "sys-be", type: "config" },
	{ source: "env-admin-key", target: "sys-be", type: "config" },
	{ source: "env-db-url", target: "sys-db", type: "config" },
	{ source: "env-redis-url", target: "sys-redis", type: "config" },
	{ source: "env-provider", target: "sys-llm", type: "config" },
];

export default function DependenciesPage() {
	// Mode selection
	const [graphMode, setGraphMode] = useState<"ml" | "infra">("ml");

	// Search & Filters
	const [searchQuery, setSearchQuery] = useState("");
	const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
	const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);

	// Zoom & Pan
	const [zoom, setZoom] = useState(1);
	const [pan, setPan] = useState({ x: 0, y: 0 });
	const [isDragging, setIsDragging] = useState(false);
	const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

	const containerRef = useRef<HTMLDivElement>(null);
	const svgRef = useRef<SVGSVGElement>(null);

	// Get active nodes and edges based on mode
	const nodes = graphMode === "ml" ? ML_NODES : INFRA_NODES;
	const edges = graphMode === "ml" ? ML_EDGES : INFRA_EDGES;

	// Zoom and Pan Handlers
	const handleZoomIn = () => setZoom((prev) => Math.min(prev + 0.15, 2.5));
	const handleZoomOut = () => setZoom((prev) => Math.max(prev - 0.15, 0.4));
	const handleZoomReset = () => {
		setZoom(1);
		setPan({ x: 0, y: 0 });
	};

	const handleMouseDown = (e: React.MouseEvent<SVGSVGElement>) => {
		if (e.button !== 0) return; // Only left click drag
		setIsDragging(true);
		setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
	};

	const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
		if (!isDragging) return;
		setPan({
			x: e.clientX - dragStart.x,
			y: e.clientY - dragStart.y,
		});
	};

	const handleMouseUp = () => {
		setIsDragging(false);
	};

	// Find node details
	const activeNode = nodes.find((n) => n.id === selectedNodeId) || null;

	// Filter nodes matching search
	const filteredNodes = nodes.filter(
		(node) =>
			node.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
			node.description.toLowerCase().includes(searchQuery.toLowerCase()),
	);

	// Map of matches for highlighting
	const matchingNodeIds = new Set(filteredNodes.map((n) => n.id));

	// Determine connected nodes for hover highlighting
	const connectedNodeIds = new Set<string>();
	if (hoveredNodeId) {
		connectedNodeIds.add(hoveredNodeId);
		edges.forEach((edge) => {
			if (edge.source === hoveredNodeId) connectedNodeIds.add(edge.target);
			if (edge.target === hoveredNodeId) connectedNodeIds.add(edge.source);
		});
	}

	// Get color for node type
	const getNodeColor = (type: Node["type"], isActiveState: boolean) => {
		switch (type) {
			case "root":
				return {
					bg: "rgba(34, 197, 94, 0.15)",
					border: isActiveState ? "#22c55e" : "#16a34a",
					glow: "rgba(34, 197, 94, 0.4)",
					text: "#4ade80",
				};
			case "profile":
				return {
					bg: "rgba(99, 102, 241, 0.15)",
					border: isActiveState ? "#818cf8" : "#6366f1",
					glow: "rgba(99, 102, 241, 0.4)",
					text: "#a5b4fc",
				};
			case "package":
				return {
					bg: "rgba(168, 85, 247, 0.15)",
					border: isActiveState ? "#c084fc" : "#a855f7",
					glow: "rgba(168, 85, 247, 0.4)",
					text: "#d8b4fe",
				};
			case "system":
				return {
					bg: "rgba(59, 130, 246, 0.15)",
					border: isActiveState ? "#60a5fa" : "#3b82f6",
					glow: "rgba(59, 130, 246, 0.4)",
					text: "#93c5fd",
				};
			case "service":
				return {
					bg: "rgba(236, 72, 153, 0.15)",
					border: isActiveState ? "#f472b6" : "#ec4899",
					glow: "rgba(236, 72, 153, 0.4)",
					text: "#f9a8d4",
				};
			case "env":
				return {
					bg: "rgba(234, 179, 8, 0.15)",
					border: isActiveState ? "#facc15" : "#eab308",
					glow: "rgba(234, 179, 8, 0.4)",
					text: "#fef08a",
				};
			default:
				return {
					bg: "rgba(156, 163, 175, 0.15)",
					border: "#9ca3af",
					glow: "rgba(156, 163, 175, 0.4)",
					text: "#e5e7eb",
				};
		}
	};

	return (
		<div
			style={{
				minHeight: "100vh",
				background:
					"radial-gradient(circle at top right, rgba(99,102,241,0.08), transparent 40%), var(--bg-primary)",
				paddingTop: "2.5rem",
				color: "var(--text-primary)",
			}}
		>
			<div className="container">
				{/* Header */}
				<div
					style={{
						display: "flex",
						justifyContent: "space-between",
						alignItems: "flex-end",
						flexWrap: "wrap",
						gap: "1.5rem",
						marginBottom: "2.5rem",
					}}
				>
					<div>
						<div
							style={{
								display: "flex",
								alignItems: "center",
								gap: "0.75rem",
								marginBottom: "0.5rem",
							}}
						>
							<Network
								size={28}
								color="var(--brand-primary)"
								className="text-glow"
							/>
							<h1 style={{ fontSize: "2.5rem", fontWeight: 800, margin: 0 }}>
								Dependency Explorer
							</h1>
						</div>
						<p
							style={{
								color: "var(--text-secondary)",
								fontSize: "1.05rem",
								maxWidth: "600px",
							}}
						>
							Explore structural relationships, configuration linkages,
							environment variables, and package hierarchies interactively.
						</p>
					</div>

					{/* Toggle Button */}
					<div
						style={{
							display: "flex",
							background: "rgba(255,255,255,0.03)",
							border: "1px solid var(--border-subtle)",
							borderRadius: "12px",
							padding: "0.25rem",
							backdropFilter: "blur(8px)",
						}}
					>
						<button
							onClick={() => {
								setGraphMode("ml");
								setSelectedNodeId(null);
							}}
							style={{
								background:
									graphMode === "ml" ? "var(--brand-primary)" : "transparent",
								color: graphMode === "ml" ? "white" : "var(--text-secondary)",
								padding: "0.6rem 1.25rem",
								borderRadius: "8px",
								border: "none",
								fontWeight: 600,
								fontSize: "0.9rem",
								cursor: "pointer",
								transition: "all var(--transition-fast)",
							}}
						>
							ML Frameworks
						</button>
						<button
							onClick={() => {
								setGraphMode("infra");
								setSelectedNodeId(null);
							}}
							style={{
								background:
									graphMode === "infra"
										? "var(--brand-primary)"
										: "transparent",
								color:
									graphMode === "infra" ? "white" : "var(--text-secondary)",
								padding: "0.6rem 1.25rem",
								borderRadius: "8px",
								border: "none",
								fontWeight: 600,
								fontSize: "0.9rem",
								cursor: "pointer",
								transition: "all var(--transition-fast)",
							}}
						>
							System Infrastructure
						</button>
					</div>
				</div>

				{/* Main Work Area */}
				<div
					style={{
						display: "grid",
						gridTemplateColumns: "1fr 340px",
						gap: "2rem",
						alignItems: "stretch",
					}}
				>
					{/* Left panel containing graph */}
					<div
						style={{ display: "flex", flexDirection: "column", gap: "1rem" }}
					>
						{/* Control Bar */}
						<div
							className="glass-panel"
							style={{
								padding: "1rem",
								display: "flex",
								justifyContent: "space-between",
								alignItems: "center",
								flexWrap: "wrap",
								gap: "1rem",
								background: "rgba(18, 18, 22, 0.45)",
							}}
						>
							{/* Search */}
							<div style={{ position: "relative", width: "260px" }}>
								<Search
									size={16}
									color="var(--text-muted)"
									style={{
										position: "absolute",
										left: "0.75rem",
										top: "50%",
										transform: "translateY(-50%)",
									}}
								/>
								<input
									type="text"
									placeholder="Search dependencies..."
									value={searchQuery}
									onChange={(e) => setSearchQuery(e.target.value)}
									style={{
										width: "100%",
										padding: "0.55rem 0.75rem 0.55rem 2.25rem",
										borderRadius: "8px",
										background: "rgba(255,255,255,0.05)",
										border: "1px solid var(--border-subtle)",
										color: "white",
										fontSize: "0.875rem",
										outline: "none",
										transition: "border-color var(--transition-fast)",
									}}
								/>
							</div>

							{/* Navigation help or Legend */}
							<div
								style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}
							>
								<span
									style={{
										fontSize: "0.8rem",
										color: "var(--text-muted)",
										marginRight: "0.5rem",
									}}
								>
									💡 Drag canvas to Pan • Scroll or click buttons to Zoom
								</span>

								{/* Zoom buttons */}
								<div
									style={{
										display: "flex",
										background: "rgba(255,255,255,0.03)",
										borderRadius: "8px",
										border: "1px solid var(--border-subtle)",
										overflow: "hidden",
									}}
								>
									<button
										onClick={handleZoomIn}
										title="Zoom In"
										style={{
											border: "none",
											background: "transparent",
											color: "var(--text-primary)",
											padding: "0.5rem",
											cursor: "pointer",
											display: "flex",
										}}
									>
										<ZoomIn size={16} />
									</button>
									<button
										onClick={handleZoomOut}
										title="Zoom Out"
										style={{
											border: "none",
											background: "transparent",
											color: "var(--text-primary)",
											padding: "0.5rem",
											cursor: "pointer",
											display: "flex",
											borderLeft: "1px solid var(--border-subtle)",
										}}
									>
										<ZoomOut size={16} />
									</button>
									<button
										onClick={handleZoomReset}
										title="Reset view"
										style={{
											border: "none",
											background: "transparent",
											color: "var(--text-primary)",
											padding: "0.5rem",
											cursor: "pointer",
											display: "flex",
											borderLeft: "1px solid var(--border-subtle)",
										}}
									>
										<Maximize2 size={16} />
									</button>
								</div>
							</div>
						</div>

						{/* Canvas Container */}
						<div
							ref={containerRef}
							className="glass-panel"
							style={{
								position: "relative",
								height: "600px",
								overflow: "hidden",
								cursor: isDragging ? "grabbing" : "grab",
								background: "rgba(5, 5, 10, 0.8)",
								border: "1px solid rgba(255,255,255,0.08)",
								boxShadow: "inset 0 0 40px rgba(0,0,0,0.8)",
							}}
						>
							{/* SVG Grid / Background */}
							<svg
								ref={svgRef}
								width="100%"
								height="100%"
								onMouseDown={handleMouseDown}
								onMouseMove={handleMouseMove}
								onMouseUp={handleMouseUp}
								onMouseLeave={handleMouseUp}
								style={{ position: "absolute", top: 0, left: 0 }}
							>
								{/* Grid Pattern */}
								<defs>
									<pattern
										id="grid"
										width="40"
										height="40"
										patternUnits="userSpaceOnUse"
									>
										<path
											d="M 40 0 L 0 0 0 40"
											fill="none"
											stroke="rgba(255, 255, 255, 0.02)"
											strokeWidth="1"
										/>
									</pattern>
									<linearGradient
										id="edge-gradient"
										x1="0%"
										y1="0%"
										x2="100%"
										y2="100%"
									>
										<stop
											offset="0%"
											stopColor="var(--brand-primary)"
											stopOpacity="0.4"
										/>
										<stop
											offset="100%"
											stopColor="var(--brand-secondary)"
											stopOpacity="0.4"
										/>
									</linearGradient>

									{/* Neon Glow Filters */}
									<filter
										id="glow-indigo"
										x="-20%"
										y="-20%"
										width="140%"
										height="140%"
									>
										<feGaussianBlur stdDeviation="8" result="blur" />
										<feComposite
											in="SourceGraphic"
											in2="blur"
											operator="over"
										/>
									</filter>
								</defs>

								{/* Grid background */}
								<rect width="100%" height="100%" fill="url(#grid)" />

								{/* Transform group representing translation/scale */}
								<g
									transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}
									style={{
										transition: isDragging
											? "none"
											: "transform 0.15s ease-out",
									}}
								>
									{/* Link Edges */}
									<g>
										{edges.map((edge, index) => {
											const sourceNode = nodes.find(
												(n) => n.id === edge.source,
											);
											const targetNode = nodes.find(
												(n) => n.id === edge.target,
											);
											if (!sourceNode || !targetNode) return null;

											// Calculate states for transparency
											const isHighlighted =
												hoveredNodeId === edge.source ||
												hoveredNodeId === edge.target;
											const hasHoverState = hoveredNodeId !== null;
											const opacity = hasHoverState
												? isHighlighted
													? 0.95
													: 0.15
												: 0.5;
											const strokeWidth = isHighlighted ? 2.5 : 1.5;
											const strokeColor = isHighlighted
												? "var(--brand-secondary)"
												: "url(#edge-gradient)";

											return (
												<g key={`edge-${index}`}>
													{/* Main line */}
													<line
														x1={sourceNode.x}
														y1={sourceNode.y}
														x2={targetNode.x}
														y2={targetNode.y}
														stroke={strokeColor}
														strokeWidth={strokeWidth}
														opacity={opacity}
														strokeDasharray={
															edge.type === "config" ? "5,5" : undefined
														}
														style={{
															transition:
																"opacity 0.25s ease, stroke-width 0.25s ease",
														}}
													/>
												</g>
											);
										})}
									</g>

									{/* Interactive Nodes */}
									<g>
										{nodes.map((node) => {
											const isSelected = selectedNodeId === node.id;
											const isHovered = hoveredNodeId === node.id;

											// Highlight connectivity logic
											const hasHoverState = hoveredNodeId !== null;
											const isConnected = connectedNodeIds.has(node.id);
											const isSearchMatched =
												searchQuery === "" || matchingNodeIds.has(node.id);

											// Calculate node state opacity
											let opacity = 1;
											if (hasHoverState) {
												opacity = isConnected ? 1 : 0.25;
											} else if (!isSearchMatched) {
												opacity = 0.25;
											}

											const colors = getNodeColor(
												node.type,
												isSelected || isHovered,
											);

											return (
												<g
													key={node.id}
													transform={`translate(${node.x}, ${node.y})`}
													onClick={(e) => {
														e.stopPropagation();
														setSelectedNodeId(node.id);
													}}
													onMouseEnter={() => setHoveredNodeId(node.id)}
													onMouseLeave={() => setHoveredNodeId(null)}
													style={{
														cursor: "pointer",
														opacity,
														transition: "opacity 0.25s ease",
													}}
												>
													{/* Inner glow on hover */}
													{(isSelected || isHovered) && (
														<circle
															r={node.type === "root" ? 38 : 28}
															fill={colors.border}
															opacity={0.3}
															filter="url(#glow-indigo)"
														/>
													)}

													{/* Main circle */}
													<circle
														r={node.type === "root" ? 28 : 20}
														fill={colors.bg}
														stroke={colors.border}
														strokeWidth={isSelected ? 3.5 : 2}
														style={{
															transition:
																"fill 0.25s ease, stroke 0.25s ease, stroke-width 0.25s ease",
														}}
													/>

													{/* Small center dot for high-end look */}
													<circle r={4} fill={colors.border} />

													{/* Node label */}
													<text
														y={node.type === "root" ? 45 : 36}
														textAnchor="middle"
														fill={colors.text}
														fontWeight={
															node.type === "root" || isSelected ? 700 : 500
														}
														fontSize={
															node.type === "root" ? "0.925rem" : "0.8rem"
														}
														style={{
															textShadow:
																isSelected || isHovered
																	? `0 0 8px ${colors.border}`
																	: "none",
															pointerEvents: "none",
															fontFamily: "var(--font-sans)",
															userSelect: "none",
														}}
													>
														{node.label}
													</text>

													{/* Node Type Badge Text (subtle) */}
													<text
														y={node.type === "root" ? 58 : 48}
														textAnchor="middle"
														fill="var(--text-muted)"
														fontSize="0.65rem"
														fontWeight={600}
														letterSpacing="0.05em"
														style={{
															pointerEvents: "none",
															userSelect: "none",
														}}
													>
														{node.type.toUpperCase()}
													</text>
												</g>
											);
										})}
									</g>
								</g>
							</svg>

							{/* Mode indicator banner */}
							<div
								style={{
									position: "absolute",
									bottom: "1rem",
									left: "1rem",
									display: "flex",
									gap: "0.5rem",
									alignItems: "center",
									background: "rgba(0,0,0,0.5)",
									backdropFilter: "blur(6px)",
									padding: "0.4rem 0.8rem",
									borderRadius: "8px",
									border: "1px solid var(--border-subtle)",
									fontSize: "0.75rem",
									color: "var(--text-secondary)",
								}}
							>
								<div
									style={{
										width: "8px",
										height: "8px",
										borderRadius: "50%",
										background: "var(--brand-accent)",
									}}
								/>
								<span>
									Active Network:{" "}
									{graphMode === "ml"
										? "ML Config Profiles"
										: "Infrastructure Components"}
								</span>
							</div>
						</div>
					</div>

					{/* Right Panel - Information Panel */}
					<div
						style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}
					>
						{/* Details Card */}
						<div
							className="glass-panel"
							style={{
								padding: "1.5rem",
								flexGrow: 1,
								display: "flex",
								flexDirection: "column",
								background: "rgba(18, 18, 22, 0.45)",
								border: "1px solid var(--border-subtle)",
							}}
						>
							<h3
								style={{
									fontSize: "1.25rem",
									display: "flex",
									alignItems: "center",
									gap: "0.5rem",
									marginBottom: "1rem",
								}}
							>
								<FileText size={18} color="var(--brand-primary)" />
								<span>Dependency Details</span>
							</h3>

							<AnimatePresence mode="wait">
								{activeNode ? (
									<motion.div
										key={activeNode.id}
										initial={{ opacity: 0, y: 10 }}
										animate={{ opacity: 1, y: 0 }}
										exit={{ opacity: 0, y: -10 }}
										transition={{ duration: 0.2 }}
										style={{
											display: "flex",
											flexDirection: "column",
											flexGrow: 1,
										}}
									>
										{/* Badge */}
										<div
											style={{
												display: "flex",
												gap: "0.5rem",
												alignItems: "center",
												marginBottom: "0.75rem",
											}}
										>
											<span
												style={{
													fontSize: "0.65rem",
													fontWeight: 700,
													padding: "0.25rem 0.6rem",
													borderRadius: "4px",
													textTransform: "uppercase",
													color: "white",
													background: getNodeColor(activeNode.type, true)
														.border,
												}}
											>
												{activeNode.type}
											</span>
											<span
												style={{
													fontSize: "0.75rem",
													color: "var(--text-muted)",
												}}
											>
												ID: {activeNode.id}
											</span>
										</div>

										<h4
											style={{
												fontSize: "1.4rem",
												fontWeight: 700,
												color: "var(--text-primary)",
												marginBottom: "0.75rem",
											}}
										>
											{activeNode.label}
										</h4>

										<p
											style={{
												fontSize: "0.9rem",
												color: "var(--text-secondary)",
												lineHeight: "1.5",
												marginBottom: "1.5rem",
											}}
										>
											{activeNode.description}
										</p>

										{activeNode.details && (
											<div
												style={{
													marginTop: "auto",
													display: "flex",
													flexDirection: "column",
													gap: "0.75rem",
												}}
											>
												<div
													style={{
														height: "1px",
														background: "var(--border-subtle)",
														margin: "0.5rem 0",
													}}
												/>
												<h5
													style={{
														fontSize: "0.8rem",
														color: "var(--text-muted)",
														textTransform: "uppercase",
														letterSpacing: "0.05em",
														fontWeight: 700,
													}}
												>
													Metadata Parameters
												</h5>

												{Object.entries(activeNode.details).map(
													([key, value]) => (
														<div
															key={key}
															style={{
																display: "flex",
																justifyContent: "space-between",
																fontSize: "0.825rem",
															}}
														>
															<span
																style={{
																	color: "var(--text-secondary)",
																	fontWeight: 500,
																}}
															>
																{key}:
															</span>
															<span
																style={{
																	color: "var(--text-primary)",
																	fontFamily: "var(--font-mono)",
																	fontWeight: 600,
																}}
															>
																{Array.isArray(value)
																	? value.join(", ")
																	: value}
															</span>
														</div>
													),
												)}
											</div>
										)}
									</motion.div>
								) : (
									<motion.div
										initial={{ opacity: 0 }}
										animate={{ opacity: 1 }}
										style={{
											display: "flex",
											flexDirection: "column",
											alignItems: "center",
											justifyContent: "center",
											textAlign: "center",
											color: "var(--text-muted)",
											flexGrow: 1,
											padding: "2rem 0",
										}}
									>
										<HelpCircle
											size={40}
											strokeWidth={1.5}
											style={{ marginBottom: "1rem", opacity: 0.5 }}
										/>
										<p style={{ fontSize: "0.9rem" }}>
											Click any node on the graph network map to view its deep
											dependencies, metadata configuration properties, and usage
											descriptions.
										</p>
									</motion.div>
								)}
							</AnimatePresence>
						</div>

						{/* Legend / Info panel */}
						<div
							className="glass-panel"
							style={{
								padding: "1.25rem",
								background: "rgba(18, 18, 22, 0.45)",
								border: "1px solid var(--border-subtle)",
							}}
						>
							<h4
								style={{
									fontSize: "0.9rem",
									fontWeight: 700,
									textTransform: "uppercase",
									letterSpacing: "0.05em",
									color: "var(--text-muted)",
									marginBottom: "0.75rem",
								}}
							>
								Legend Reference
							</h4>
							<div
								style={{
									display: "grid",
									gridTemplateColumns: "1fr 1fr",
									gap: "0.5rem",
								}}
							>
								{[
									{ name: "Root Nodes", color: "rgba(34, 197, 94, 0.4)" },
									{ name: "Profiles", color: "rgba(99, 102, 241, 0.4)" },
									{ name: "ML Packages", color: "rgba(168, 85, 247, 0.4)" },
									{ name: "System Core", color: "rgba(59, 130, 246, 0.4)" },
									{ name: "Services", color: "rgba(236, 72, 153, 0.4)" },
									{ name: "Env Vars", color: "rgba(234, 179, 8, 0.4)" },
								].map((item, idx) => (
									<div
										key={idx}
										style={{
											display: "flex",
											alignItems: "center",
											gap: "0.4rem",
											fontSize: "0.75rem",
										}}
									>
										<div
											style={{
												width: "10px",
												height: "10px",
												borderRadius: "50%",
												background: item.color,
											}}
										/>
										<span style={{ color: "var(--text-secondary)" }}>
											{item.name}
										</span>
									</div>
								))}
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	);
}
