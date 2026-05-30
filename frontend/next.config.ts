import type { NextConfig } from "next";

const nextConfig: NextConfig = {
	output: "standalone",
	allowedDevOrigins: ["192.168.1.14"],
	async rewrites() {
		const backendApiUrl =
			process.env.BACKEND_API_URL || process.env.NEXT_PUBLIC_API_URL;
		if (!backendApiUrl && process.env.NODE_ENV === "production") {
			throw new Error(
				"BACKEND_API_URL or NEXT_PUBLIC_API_URL must be set at build time.",
			);
		}
		const finalUrl = backendApiUrl || "http://localhost:8000";
		return [
			{
				source: "/api/v1/:path*",
				destination: `${finalUrl}/api/v1/:path*`,
			},
		];
	},
};

export default nextConfig;
