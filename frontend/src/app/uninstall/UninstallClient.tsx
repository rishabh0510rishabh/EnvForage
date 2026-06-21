"use client";

import { motion } from "framer-motion";
import { Frown, Send, CheckCircle2, MessageSquare, ArrowRight } from "lucide-react";
import Link from "next/link";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "../../services/api";

const UNINSTALL_REASONS = [
	{ id: "hard_config", label: "Difficult to install or configure" },
	{ id: "bugs", label: "Ran into bugs or crashes" },
	{ id: "slow", label: "Performance was too slow" },
	{ id: "missing_hardware", label: "No support for my hardware/framework" },
	{ id: "unclear_docs", label: "Documentation was unclear" },
	{ id: "one_off", label: "Only needed it for a single task" },
	{ id: "other", label: "Other / Decided on a different tool" },
];

export default function UninstallClient() {
	const router = useRouter();
	const [rating, setRating] = useState<number | null>(null);
	const [selectedReasons, setSelectedReasons] = useState<string[]>([]);
	const [comments, setComments] = useState("");
	const [email, setEmail] = useState("");
	const [isSubmitting, setIsSubmitting] = useState(false);
	const [isSubmitted, setIsSubmitted] = useState(false);
	const [countdown, setCountdown] = useState(6);

	useEffect(() => {
		if (isSubmitted) {
			const timer = setInterval(() => {
				setCountdown((prev) => {
					if (prev <= 1) {
						clearInterval(timer);
						return 0;
					}
					return prev - 1;
				});
			}, 1000);
			return () => clearInterval(timer);
		}
	}, [isSubmitted]);

	useEffect(() => {
		if (isSubmitted && countdown === 0) {
			router.push("/");
		}
	}, [isSubmitted, countdown, router]);

	const toggleReason = (id: string) => {
		setSelectedReasons((prev) =>
			prev.includes(id) ? prev.filter((r) => r !== id) : [...prev, id],
		);
	};

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		setIsSubmitting(true);

		try {
			await api.submitUninstallFeedback({
				rating,
				reasons: selectedReasons,
				comments: comments.trim() || undefined,
				email: email.trim() || undefined,
			});
		} catch (err) {
			console.error("Failed to submit feedback:", err);
		} finally {
			setIsSubmitting(false);
			setIsSubmitted(true);
		}
	};

	if (isSubmitted) {
		return (
			<div className="container" style={{ padding: "6rem 2rem", maxWidth: "600px" }}>
				<motion.div
					initial={{ opacity: 0, scale: 0.95 }}
					animate={{ opacity: 1, scale: 1 }}
					transition={{ type: "spring", stiffness: 300, damping: 25 }}
					className="glass-panel"
					style={{
						padding: "3rem",
						textAlign: "center",
						boxShadow: "var(--shadow-glow)",
						border: "1px solid var(--brand-primary)",
					}}
				>
					<CheckCircle2
						size={64}
						color="var(--brand-accent)"
						style={{ margin: "0 auto 1.5rem", filter: "drop-shadow(0 0 8px var(--brand-accent))" }}
					/>
					<h2
						className="text-gradient"
						style={{ fontSize: "2.25rem", fontWeight: 800, marginBottom: "1rem" }}
					>
						Thank You!
					</h2>
					<p style={{ color: "var(--text-secondary)", fontSize: "1.1rem", lineHeight: 1.6, marginBottom: "2.5rem" }}>
						Your feedback has been submitted successfully. We appreciate your honesty and will use this insight to improve the EnvForage CLI agent experience for everyone.
					</p>
					<div
						style={{
							padding: "1rem",
							background: "rgba(255, 255, 255, 0.02)",
							borderRadius: "8px",
							border: "1px solid var(--border-subtle)",
							marginBottom: "2rem",
							fontSize: "0.9rem",
							color: "var(--text-muted)",
						}}
					>
						Redirecting to homepage in <span style={{ color: "var(--brand-secondary)", fontWeight: 600 }}>{countdown}</span> seconds...
					</div>
					<Link
						href="/"
						className="btn btn-primary"
						style={{ width: "100%", textDecoration: "none", gap: "0.5rem" }}
					>
						Return Home Now <ArrowRight size={18} />
					</Link>
				</motion.div>
			</div>
		);
	}

	return (
		<div className="container" style={{ padding: "4rem 2rem", maxWidth: "800px" }}>
			<div style={{ textAlign: "center", marginBottom: "3rem" }}>
				<motion.div
					initial={{ opacity: 0, scale: 0.8 }}
					animate={{ opacity: 1, scale: 1 }}
					transition={{ duration: 0.5 }}
					style={{
						display: "inline-flex",
						background: "rgba(239, 68, 68, 0.1)",
						padding: "1rem",
						borderRadius: "50%",
						marginBottom: "1.5rem",
						border: "1px solid rgba(239, 68, 68, 0.2)",
					}}
				>
					<Frown size={40} color="#ef4444" style={{ filter: "drop-shadow(0 0 6px #ef4444)" }} />
				</motion.div>
				<h1
					className="text-gradient"
					style={{ fontSize: "3rem", fontWeight: 800, marginBottom: "1rem" }}
				>
					We&apos;re sad to see you go
				</h1>
				<p style={{ color: "var(--text-secondary)", fontSize: "1.15rem", maxWidth: "600px", margin: "0 auto", lineHeight: 1.6 }}>
					Thank you for giving EnvForage CLI a try. To help us build a better environment diagnostic and provisioning agent, please let us know about your experience.
				</p>
			</div>

			<motion.div
				initial={{ opacity: 0, y: 20 }}
				animate={{ opacity: 1, y: 0 }}
				transition={{ duration: 0.5, delay: 0.1 }}
				className="glass-panel"
				style={{ padding: "2.5rem", boxShadow: "var(--shadow-md)" }}
			>
				<form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "2.5rem" }}>
					
					{/* Rating Selector */}
					<div>
						<label
							style={{
								display: "block",
								fontSize: "1.1rem",
								fontWeight: 600,
								color: "var(--text-primary)",
								marginBottom: "1rem",
							}}
						>
							1. How would you rate your experience with the EnvForage CLI?
						</label>
						<div style={{ display: "flex", gap: "0.75rem", justifyContent: "space-between" }}>
							{[1, 2, 3, 4, 5].map((num) => {
								const isActive = rating === num;
								return (
									<motion.button
										key={num}
										type="button"
										onClick={() => setRating(num)}
										whileHover={{ scale: 1.05 }}
										whileTap={{ scale: 0.95 }}
										style={{
											flex: 1,
											padding: "1rem 0",
											borderRadius: "10px",
											background: isActive ? "var(--brand-primary)" : "rgba(255, 255, 255, 0.02)",
											border: isActive ? "1px solid var(--brand-primary)" : "1px solid var(--border-strong)",
											color: isActive ? "var(--text-inverse)" : "var(--text-primary)",
											fontSize: "1.25rem",
											fontWeight: 700,
											cursor: "pointer",
											transition: "background var(--transition-fast), border var(--transition-fast), box-shadow var(--transition-fast)",
											boxShadow: isActive ? "var(--shadow-glow)" : "none",
										}}
									>
										{num}
									</motion.button>
								);
							})}
						</div>
						<div style={{ display: "flex", justifyContent: "space-between", marginTop: "0.5rem", fontSize: "0.85rem", color: "var(--text-muted)" }}>
							<span>Terrible</span>
							<span>Outstanding</span>
						</div>
					</div>

					{/* Reasons Grid */}
					<div>
						<label
							style={{
								display: "block",
								fontSize: "1.1rem",
								fontWeight: 600,
								color: "var(--text-primary)",
								marginBottom: "0.5rem",
							}}
						>
							2. Why did you decide to uninstall EnvForage CLI?
						</label>
						<span style={{ display: "block", fontSize: "0.9rem", color: "var(--text-muted)", marginBottom: "1.25rem" }}>
							Select all that apply
						</span>
						<div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "1rem" }}>
							{UNINSTALL_REASONS.map((reason) => {
								const isSelected = selectedReasons.includes(reason.id);
								return (
									<motion.div
										key={reason.id}
										onClick={() => toggleReason(reason.id)}
										whileHover={{ y: -2 }}
										style={{
											padding: "1rem 1.25rem",
											borderRadius: "10px",
											background: isSelected ? "rgba(99, 102, 241, 0.06)" : "rgba(255, 255, 255, 0.02)",
											border: isSelected ? "1px solid var(--brand-primary)" : "1px solid var(--border-subtle)",
											cursor: "pointer",
											display: "flex",
											alignItems: "center",
											gap: "0.75rem",
											transition: "border-color var(--transition-fast), background var(--transition-fast)",
										}}
									>
										<div
											style={{
												width: "20px",
												height: "20px",
												borderRadius: "4px",
												border: isSelected ? "1px solid var(--brand-primary)" : "1px solid var(--border-strong)",
												background: isSelected ? "var(--brand-primary)" : "transparent",
												display: "flex",
												alignItems: "center",
												justifyContent: "center",
												transition: "all var(--transition-fast)",
											}}
										>
											{isSelected && (
												<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
													<polyline points="20 6 9 17 4 12" />
												</svg>
											)}
										</div>
										<span style={{ fontSize: "0.95rem", color: isSelected ? "var(--text-primary)" : "var(--text-secondary)", fontWeight: isSelected ? 600 : 400 }}>
											{reason.label}
										</span>
									</motion.div>
								);
							})}
						</div>
					</div>

					{/* Comments Textarea */}
					<div>
						<label
							style={{
								display: "block",
								fontSize: "1.1rem",
								fontWeight: 600,
								color: "var(--text-primary)",
								marginBottom: "1rem",
							}}
						>
							3. What could we improve or change in the CLI?
						</label>
						<div style={{ position: "relative" }}>
							<MessageSquare
								size={18}
								color="var(--text-muted)"
								style={{ position: "absolute", left: "1rem", top: "1rem" }}
							/>
							<textarea
								value={comments}
								onChange={(e) => setComments(e.target.value)}
								placeholder="Let us know what went wrong, what was missing, or general ideas..."
								style={{
									width: "100%",
									height: "120px",
									padding: "0.85rem 1rem 0.85rem 2.75rem",
									borderRadius: "8px",
									background: "rgba(0, 0, 0, 0.25)",
									border: "1px solid var(--border-strong)",
									color: "var(--text-primary)",
									fontSize: "0.95rem",
									lineHeight: 1.5,
									fontFamily: "var(--font-sans)",
									outline: "none",
									resize: "none",
									transition: "border-color var(--transition-fast)",
								}}
								onFocus={(e) => (e.target.style.borderColor = "var(--brand-primary)")}
								onBlur={(e) => (e.target.style.borderColor = "var(--border-strong)")}
							/>
						</div>
					</div>

					{/* Contact Email (Optional) */}
					<div>
						<label
							style={{
								display: "block",
								fontSize: "1.1rem",
								fontWeight: 600,
								color: "var(--text-primary)",
								marginBottom: "0.5rem",
							}}
						>
							4. Email address (optional)
						</label>
						<span style={{ display: "block", fontSize: "0.9rem", color: "var(--text-muted)", marginBottom: "1rem" }}>
							If you are open to a quick follow-up conversation about your issues.
						</span>
						<input
							type="email"
							value={email}
							onChange={(e) => setEmail(e.target.value)}
							placeholder="you@example.com"
							style={{
								width: "100%",
								padding: "0.75rem 1rem",
								borderRadius: "8px",
								background: "rgba(0, 0, 0, 0.25)",
								border: "1px solid var(--border-strong)",
								color: "var(--text-primary)",
								fontSize: "0.95rem",
								outline: "none",
								transition: "border-color var(--transition-fast)",
							}}
							onFocus={(e) => (e.target.style.borderColor = "var(--brand-primary)")}
							onBlur={(e) => (e.target.style.borderColor = "var(--border-strong)")}
						/>
					</div>

					{/* Submit Button */}
					<button
						type="submit"
						className="btn btn-primary"
						disabled={isSubmitting}
						style={{
							marginTop: "1rem",
							padding: "1rem",
							fontSize: "1.1rem",
							fontWeight: 600,
							display: "flex",
							justifyContent: "center",
							alignItems: "center",
							gap: "0.75rem",
							cursor: "pointer",
							background: "var(--brand-primary)",
							color: "var(--text-inverse)",
							boxShadow: "var(--shadow-glow)",
						}}
					>
						{isSubmitting ? (
							<>
								<motion.div
									animate={{ rotate: 360 }}
									transition={{ repeat: Infinity, ease: "linear", duration: 0.8 }}
									style={{
										width: "20px",
										height: "20px",
										borderRadius: "50%",
										border: "2px solid rgba(255,255,255,0.2)",
										borderTopColor: "white",
									}}
								/>
								Submitting Feedback...
							</>
						) : (
							<>
								<Send size={18} />
								Submit Feedback
							</>
						)}
					</button>
				</form>
			</motion.div>
		</div>
	);
}
