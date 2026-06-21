import { Metadata } from "next";
import UninstallClient from "./UninstallClient";

export const metadata: Metadata = {
	title: "We're Sad to See You Go | EnvForage",
	description: "Please let us know how we can improve EnvForage CLI.",
	alternates: {
		canonical: "/uninstall",
	},
};

export default function Page() {
	return <UninstallClient />;
}
