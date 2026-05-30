"use client";

import { useEffect, useState } from "react";

export default function CurrentYear() {
	const [year, setYear] = useState<number | string>("");

	useEffect(() => {
		const handle = requestAnimationFrame(() => {
			setYear(new Date().getFullYear());
		});
		return () => cancelAnimationFrame(handle);
	}, []);

	return <>{year || "2026"}</>;
}
