import { Metadata } from "next";
import Client from "./Client";

export const metadata: Metadata = {
	alternates: {
		canonical: "/dependencies",
	},
};

export default function Page() {
	return <Client />;
}
