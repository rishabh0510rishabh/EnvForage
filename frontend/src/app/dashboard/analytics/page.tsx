import { Metadata } from "next";
import Client from "./Client";

export const metadata: Metadata = {
	title: "Analytics Dashboard",
	description: "Aggregated CLI agent diagnostics and usage analytics.",
	alternates: {
		canonical: "/dashboard/analytics",
	},
};

export default function Page() {
	return <Client />;
}
