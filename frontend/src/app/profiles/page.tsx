import { Metadata } from "next";
import Client from "./Client";

export const metadata: Metadata = {
	alternates: {
		canonical: "/profiles",
	},
};

export default function Page() {
	return <Client />;
}
