import { Metadata } from "next";
import Client from "./Client";

export const metadata: Metadata = {
	alternates: {
		canonical: "/coming-soon",
	},
};

export default function Page() {
	return <Client />;
}
