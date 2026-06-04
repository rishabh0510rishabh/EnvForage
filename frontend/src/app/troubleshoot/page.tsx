import { Metadata } from "next";
import Client from "./Client";

export const metadata: Metadata = {
	alternates: {
		canonical: "/troubleshoot",
	},
};

export default function Page() {
	return <Client />;
}
