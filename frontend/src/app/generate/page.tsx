import { Metadata } from "next";
import Client, { GenerateErrorBoundary } from "./Client";

export const metadata: Metadata = {
	alternates: {
		canonical: "/generate",
	},
};

export default function Page() {
	return (
		<GenerateErrorBoundary>
			<Client />
		</GenerateErrorBoundary>
	);
}

