import Link from "next/link";
import CurrentYear from "./CurrentYear";

export default function Footer() {
	return (
		<footer
			className="glass-footer"
			style={{
				marginTop: "4rem",
				padding: "5rem 0 2rem",
			}}
		>
			<div
				className="container"
				style={{
					display: "flex",
					flexWrap: "wrap",
					gap: "3rem",
					justifyContent: "space-between",
				}}
			>
				{/* Brand */}
				<div style={{ flex: "1 1 350px", maxWidth: "450px" }}>
					<h2
						style={{
							fontSize: "1.8rem",
							marginBottom: "1rem",
							background: "linear-gradient(to right,#22c55e,#06b6d4,#3b82f6)",
							WebkitBackgroundClip: "text",
							WebkitTextFillColor: "transparent",
							fontWeight: 800,
						}}
					>
						EnvForage ⚡
					</h2>

					<p
						style={{
							color: "var(--text-secondary)",
							lineHeight: "1.8",
						}}
					>
						Build, diagnose and optimize AI/ML environments with confidence.
						Designed for developers who want faster setup, fewer errors and
						smarter workflows.
					</p>

					<div
						style={{
							marginTop: "1.5rem",
							display: "flex",
							gap: "0.8rem",
						}}
					>
						<span
							style={{
								padding: "6px 12px",
								borderRadius: "999px",
								background: "rgba(34,197,94,0.15)",
								border: "1px solid rgba(34,197,94,0.25)",
								fontSize: "0.85rem",
								color: "#22c55e",
							}}
						>
							Open Source
						</span>
						<span
							style={{
								padding: "6px 12px",
								borderRadius: "999px",
								background: "rgba(59,130,246,0.15)",
								border: "1px solid rgba(59,130,246,0.25)",
								fontSize: "0.85rem",
								color: "#3b82f6",
							}}
						>
							AI Powered
						</span>
					</div>
				</div>

				{/* Links Container */}
				<div
					style={{
						display: "flex",
						flexWrap: "wrap",
						gap: "4rem",
						flex: "1 1 400px",
						justifyContent: "flex-end",
					}}
				>
					{/* Product */}
					<div style={{ minWidth: "120px" }}>
						<h4
							style={{
								marginBottom: "1.5rem",
								fontWeight: 600,
								color: "var(--text-primary)",
							}}
						>
							Product
						</h4>
						<div
							style={{
								display: "flex",
								flexDirection: "column",
								gap: "0.8rem",
							}}
						>
							<Link
								href="/profiles"
								style={{
									color: "var(--text-secondary)",
									textDecoration: "none",
								}}
							>
								Profiles
							</Link>
							<Link
								href="/diagnose"
								style={{
									color: "var(--text-secondary)",
									textDecoration: "none",
								}}
							>
								Diagnose
							</Link>
							<Link
								href="/troubleshoot"
								style={{
									color: "var(--text-secondary)",
									textDecoration: "none",
								}}
							>
								Troubleshoot
							</Link>
							<Link
								href="/dependencies"
								style={{
									color: "var(--text-secondary)",
									textDecoration: "none",
								}}
							>
								Dependencies
							</Link>
						</div>
					</div>

					{/* Resources */}
					<div style={{ minWidth: "120px" }}>
						<h4
							style={{
								marginBottom: "1.5rem",
								fontWeight: 600,
								color: "var(--text-primary)",
							}}
						>
							Resources
						</h4>
						<div
							style={{
								display: "flex",
								flexDirection: "column",
								gap: "0.8rem",
							}}
						>
							<Link
								href="/coming-soon"
								style={{
									color: "var(--text-secondary)",
									textDecoration: "none",
								}}
							>
								Documentation
							</Link>
							<Link
								href="/coming-soon"
								style={{
									color: "var(--text-secondary)",
									textDecoration: "none",
								}}
							>
								Guides
							</Link>
							<Link
								href="/coming-soon"
								style={{
									color: "var(--text-secondary)",
									textDecoration: "none",
								}}
							>
								API Reference
							</Link>
							<Link
								href="/coming-soon"
								style={{
									color: "var(--text-secondary)",
									textDecoration: "none",
								}}
							>
								FAQ
							</Link>
						</div>
					</div>

					{/* Community */}
					<div style={{ minWidth: "120px" }}>
						<h4
							style={{
								marginBottom: "1.5rem",
								fontWeight: 600,
								color: "var(--text-primary)",
							}}
						>
							Community
						</h4>
						<div
							style={{
								display: "flex",
								flexDirection: "column",
								gap: "0.8rem",
							}}
						>
							<Link
								href="/coming-soon"
								style={{
									color: "var(--text-secondary)",
									textDecoration: "none",
								}}
							>
								Contribute
							</Link>
							<Link
								href="https://github.com"
								target="_blank"
								style={{
									color: "var(--text-secondary)",
									textDecoration: "none",
								}}
							>
								GitHub
							</Link>
							<Link
								href="/coming-soon"
								style={{
									color: "var(--text-secondary)",
									textDecoration: "none",
								}}
							>
								Report Issues
							</Link>
							<Link
								href="/coming-soon"
								style={{
									color: "var(--text-secondary)",
									textDecoration: "none",
								}}
							>
								Discussions
							</Link>
						</div>
					</div>
				</div>
			</div>

			{/* Bottom Bar */}
			<div
				style={{
					marginTop: "4rem",
					paddingTop: "2rem",
					borderTop: "1px solid var(--border-subtle)",
					textAlign: "center",
					color: "var(--text-muted)",
					fontSize: "0.9rem",
				}}
			>
				<p>
					© <CurrentYear /> EnvForage. Built for Developers ❤️ • Powered by AI ⚡
				</p>
			</div>
		</footer>
	);
}
