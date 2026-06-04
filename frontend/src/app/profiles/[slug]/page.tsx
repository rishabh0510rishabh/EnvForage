import { Metadata } from "next";
import Client from "./Client";

export async function generateMetadata(props: { params: Promise<{ slug: string }> }): Promise<Metadata> {
	const params = await props.params;
	return {
		alternates: {
			canonical: `/profiles/${encodeURIComponent(params.slug)}`,
		},
	};
}

export default function Page() {
	return <Client />;
}
