"use client";

import { AnimatePresence, motion } from "framer-motion";
import { ArrowUp } from "lucide-react";
import { useEffect, useState } from "react";

export default function ScrollToTop() {
	const [isVisible, setIsVisible] = useState(false);

	// Check scroll position
	useEffect(() => {
		const toggleVisibility = () => {
			if (window.scrollY > 400) {
				setIsVisible(true);
			} else {
				setIsVisible(false);
			}
		};

		window.addEventListener("scroll", toggleVisibility);
		return () => window.removeEventListener("scroll", toggleVisibility);
	}, []);

	const scrollToTop = () => {
		window.scrollTo({
			top: 0,
			behavior: "smooth",
		});
	};

	return (
		<AnimatePresence>
			{isVisible && (
				<motion.button
					initial={{ opacity: 0, scale: 0.5, y: 20 }}
					animate={{ opacity: 1, scale: 1, y: 0 }}
					exit={{ opacity: 0, scale: 0.5, y: 20 }}
					whileHover={{ scale: 1.1, y: -2 }}
					whileTap={{ scale: 0.9 }}
					onClick={scrollToTop}
					style={{
						position: "fixed",
						bottom: "2rem",
						right: "2rem",
						width: "50px",
						height: "50px",
						borderRadius: "50%",
						display: "flex",
						alignItems: "center",
						justifyContent: "center",
						background:
							"linear-gradient(135deg, var(--brand-primary), var(--brand-secondary))",
						color: "white",
						border: "none",
						cursor: "pointer",
						boxShadow: "var(--shadow-lg), 0 0 20px rgba(99, 102, 241, 0.4)",
						zIndex: 50,
					}}
					aria-label="Scroll to top"
				>
					<ArrowUp size={24} strokeWidth={2.5} />
				</motion.button>
			)}
		</AnimatePresence>
	);
}
