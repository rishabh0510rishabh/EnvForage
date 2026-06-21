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
const delay = (ms: number) =>
	new Promise((resolve) => setTimeout(resolve, ms));

async function fetchWithRetry(
	url: string,
	options: RequestInit = {},
	retries = 3,
	backoff = 1000,
): Promise<Response> {
	try {
		const response = await fetch(url, options);

		if (!response.ok && response.status >= 500 && retries > 0) {
			throw new Error(`Server error: ${response.status}`);
		}

		return response;
	} catch (error) {
		if (retries <= 0) {
			throw error;
		}

		await delay(backoff);

		return fetchWithRetry(
			url,
			options,
			retries - 1,
			backoff * 2,
		);
	}
}

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
		const response = await fetchWithRetry(url, { cache: "no-store" });
		if (!response.ok) throw new Error("Failed to fetch profiles");
		const data = await response.json();
		return data.profiles || [];
	},

	getProfile: async (slug: string): Promise<Profile> => {
		const response = await fetchWithRetry(
			`${API_BASE_URL}/profiles/${slug}`,
			{
				cache: "no-store",
			},
		);
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
		const response = await fetchWithRetry(
			`${API_BASE_URL}/repair/templates`,
			{
				cache: "no-store",
			},
		);
		if (!response.ok) throw new Error("Failed to fetch repair templates");
		return response.json();
	},

	submitUninstallFeedback: async (request: {
		rating?: number | null;
		reasons: string[];
		comments?: string;
		email?: string;
	}): Promise<unknown> => {
		const response = await fetch(`${API_BASE_URL}/uninstall/feedback`, {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
			},
			body: JSON.stringify(request),
		});
		if (!response.ok) throw new Error("Failed to submit feedback");
		return response.json();
	},
};

// --- Axios Retry Interceptor ---
import axios, { AxiosError } from 'axios';

const MAX_RETRIES = 3;
const BASE_DELAY_MS = 1000;

export const apiClient = axios.create({
    baseURL: process.env.NEXT_PUBLIC_API_URL || '/api/v1',
    timeout: 10000,
});

apiClient.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
        const config = error.config as typeof error.config & { retryCount?: number };
        
        if (!config || !config.retryCount) {
            config.retryCount = 0;
        }

        const shouldRetry = 
            error.response?.status && 
            error.response.status >= 500 && 
            config.retryCount < MAX_RETRIES;

        if (shouldRetry) {
            config.retryCount += 1;
            const delay = BASE_DELAY_MS * (2 ** (config.retryCount - 1));
            
            console.warn(`[API] Transient error. Retrying request (${config.retryCount}/${MAX_RETRIES}) in ${delay}ms...`);
            
            await new Promise((resolve) => setTimeout(resolve, delay));
            return apiClient(config);
        }

        return Promise.reject(error);
    }
);
