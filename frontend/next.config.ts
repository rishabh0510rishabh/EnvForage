import type { NextConfig } from "next";
import { withSentryConfig } from "@sentry/nextjs";

const nextConfig: NextConfig = {
																output: "standalone",
																allowedDevOrigins: ["192.168.1.14", "192.168.1.37", "192.168.1.48"],
																async redirects() {
																								return [
																																{
																																								source: "/install",
																																								destination: "/download",
																																								permanent: true,
																																},
																								];
																},
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

export default withSentryConfig(nextConfig, {
 // For all available options, see:
	// https://www.npmjs.com/package/@sentry/webpack-plugin#options

	org: "open-source-0h",

 project: "javascript-nextjs",

 // Only print logs for uploading source maps in CI
	silent: !process.env.CI,

 // For all available options, see:
	// https://docs.sentry.io/platforms/javascript/guides/nextjs/manual-setup/

	// Upload a larger set of source maps for prettier stack traces (increases build time)
	widenClientFileUpload: true,

 // Route browser requests to Sentry through a Next.js rewrite to circumvent ad-blockers.
	// This can increase your server load as well as your hosting bill.
	// Note: Check that the configured route will not match with your Next.js middleware, otherwise reporting of client-
	// side errors will fail.
	tunnelRoute: "/monitoring",

 webpack: {
			// Enables automatic instrumentation of Vercel Cron Monitors. (Does not yet work with App Router route handlers.)
			// See the following for more information:
			// https://docs.sentry.io/product/crons/
			// https://vercel.com/docs/cron-jobs
			automaticVercelMonitors: true,

			// Tree-shaking options for reducing bundle size
			treeshake: {
					// Automatically tree-shake Sentry logger statements to reduce bundle size
					removeDebugLogging: true,
			},
	},
});
