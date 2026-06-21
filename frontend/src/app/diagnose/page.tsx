import { Metadata } from "next";
import Client from "./Client";

export const metadata: Metadata = {
	alternates: {
		canonical: "/diagnose",
	},
};

export default function Page() {
	return <Client />;
}
