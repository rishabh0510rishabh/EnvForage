"use client";

import { motion } from "framer-motion";
import { Construction } from "lucide-react";
import Link from "next/link";

export default function ComingSoonPage() {
	return (
		<div
			style={{
				minHeight: "60vh",
				display: "flex",
				flexDirection: "column",
				alignItems: "center",
				justifyContent: "center",
				padding: "4rem 2rem",
				textAlign: "center",
			}}
		>
			<motion.div
				initial={{ opacity: 0, scale: 0.9 }}
				animate={{ opacity: 1, scale: 1 }}
				transition={{ duration: 0.5 }}
			>
				<Construction
					size={64}
					color="#22c55e"
					style={{
						margin: "0 auto 2rem",
						filter: "drop-shadow(0 0 15px rgba(34,197,94,0.5))",
					}}
				/>
				<h1
					style={{
						fontSize: "3.5rem",
						fontWeight: 800,
						marginBottom: "1rem",
						background: "linear-gradient(to right, #22c55e, #06b6d4)",
						WebkitBackgroundClip: "text",
						WebkitTextFillColor: "transparent",
					}}
				>
					Landing Soon
				</h1>
				<p
					style={{
						fontSize: "1.2rem",
						color: "var(--text-secondary)",
						maxWidth: "500px",
						margin: "0 auto 3rem",
						lineHeight: "1.6",
					}}
				>
					We are currently forging this page. Check back soon for updates as we
					continue building out EnvForage!
				</p>

				<Link
					href="/"
					style={{
						padding: "0.8rem 2rem",
						borderRadius: "999px",
						background: "rgba(255,255,255,0.05)",
						border: "1px solid rgba(255,255,255,0.1)",
						color: "var(--text-primary)",
						fontWeight: 600,
						textDecoration: "none",
						transition: "all 0.3s ease",
					}}
				>
					Return Home
				</Link>
			</motion.div>
		</div>
	);
}
