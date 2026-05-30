import type {
	DiagnosticReport,
	DiagnosticResponse,
	Profile,
	RepairRequest,
	RepairResponse,
	RepairTemplateListResponse,
	ScriptGenerationRequest,
	ScriptGenerationResponse,
	TroubleshootRequest,
	TroubleshootResponse,
} from "../types";

const getApiBaseUrl = () => {
	const url = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
	return url.endsWith("/api/v1") ? url : `${url}/api/v1`;
};

const API_BASE_URL = getApiBaseUrl();

export const api = {
	getProfiles: async (
		os?: string,
		cuda?: boolean,
		tags?: string[],
	): Promise<Profile[]> => {
		const params = new URLSearchParams();
		if (os) params.append("os", os);
		if (cuda !== undefined) params.append("cuda_required", cuda.toString());
		if (tags && tags.length > 0) {
			tags.forEach((tag) => params.append("tags", tag));
		}

		const url = `${API_BASE_URL}/profiles${params.toString() ? `?${params.toString()}` : ""}`;
		const response = await fetch(url, { cache: "no-store" });
		if (!response.ok) throw new Error("Failed to fetch profiles");
		const data = await response.json();
		return data.profiles || [];
	},

	getProfile: async (slug: string): Promise<Profile> => {
		const response = await fetch(`${API_BASE_URL}/profiles/${slug}`, {
			cache: "no-store",
		});
		if (!response.ok) throw new Error(`Failed to fetch profile: ${slug}`);
		return response.json();
	},

	generateScript: async (
		request: ScriptGenerationRequest,
	): Promise<ScriptGenerationResponse> => {
		const response = await fetch(`${API_BASE_URL}/scripts/generate`, {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
			},
			body: JSON.stringify(request),
		});
		if (!response.ok) throw new Error("Failed to generate script");
		return response.json();
	},

	diagnose: async (
		report: DiagnosticReport,
		profileId?: string,
	): Promise<DiagnosticResponse> => {
		const url = profileId
			? `${API_BASE_URL}/diagnose?profile_id=${profileId}`
			: `${API_BASE_URL}/diagnose`;
		const response = await fetch(url, {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
			},
			body: JSON.stringify(report),
		});
		if (!response.ok) throw new Error("Failed to analyze diagnostic report");
		return response.json();
	},

	troubleshoot: async (
		request: TroubleshootRequest,
		onToken: (token: string) => void,
	): Promise<TroubleshootResponse> => {
		const response = await fetch(`${API_BASE_URL}/troubleshoot`, {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
			},
			body: JSON.stringify(request),
		});

		if (!response.ok) {
			const errorData = await response.json().catch(() => ({}));
			throw new Error(errorData.detail?.message || "AI troubleshooting failed");
		}

		if (!response.body) {
			throw new Error("Response body is null");
		}

		const reader = response.body.getReader();
		const decoder = new TextDecoder("utf-8");
		let fullContent = "";
		let buffer = "";

		while (true) {
			const { done, value } = await reader.read();

			const chunk = decoder.decode(value, { stream: !done });
			buffer += chunk;

			const lines = buffer.split("\n");
			buffer = lines.pop() || "";

			for (const line of lines) {
				if (line.startsWith("data: ")) {
					const token = line.slice(6);
					fullContent += token;
					onToken(token);
				}
			}

			if (done) {
				if (buffer.startsWith("data: ")) {
					const token = buffer.slice(6);
					fullContent += token;
					onToken(token);
				}
				break;
			}
		}

		// After stream completes, parse the full accumulated JSON
		try {
			return JSON.parse(fullContent) as TroubleshootResponse;
		} catch {
			console.error("Failed to parse final AI response:", fullContent);
			throw new Error("AI returned invalid JSON structure");
		}
	},

	generateRepair: async (request: RepairRequest): Promise<RepairResponse> => {
		const response = await fetch(`${API_BASE_URL}/repair`, {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
			},
			body: JSON.stringify(request),
		});
		if (!response.ok) {
			const errorData = await response.json().catch(() => ({}));
			throw new Error(
				errorData.detail?.message || "Repair script generation failed",
			);
		}
		return response.json();
	},

	getRepairTemplates: async (): Promise<RepairTemplateListResponse> => {
		const response = await fetch(`${API_BASE_URL}/repair/templates`, {
			cache: "no-store",
		});
		if (!response.ok) throw new Error("Failed to fetch repair templates");
		return response.json();
	},
};
