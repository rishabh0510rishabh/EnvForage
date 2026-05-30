export interface PackageDef {
	package_name: string;
	version_spec: string;
	is_optional: boolean;
	cuda_variant: string | null;
}

export interface Profile {
	slug: string;
	name: string;
	description: string;
	tags: string[];
	os_support: string[];
	cuda_required: boolean;
	python_versions: string[];
	cuda_versions: string[] | null;
	status: string;
	packages: PackageDef[];
	created_at?: string;
	updated_at?: string;
}

export interface ScriptGenerationRequest {
	profile_id: string;
	target_os: string;
	output_formats: string[];
	cuda_version?: string;
	python_version?: string;
}

export interface ResolvedPackage {
	name: string;
	version: string;
	cuda_variant: string | null;
}

export interface ScriptPreview {
	filename: string;
	content: string;
	size_bytes: number;
}

export interface ScriptGenerationResponse {
	job_id: string;
	status: string;
	profile_slug: string;
	target_os: string;
	python_version: string;
	cuda_version: string | null;
	resolved_packages: ResolvedPackage[];
	scripts: ScriptPreview[];
	warnings: string[];
	download_url: string;
}

export interface OSInfo {
	name: string;
	version: string;
	architecture: string;
	wsl_version: string | null;
}

export interface CPUInfo {
	brand: string;
	cores: number;
	threads: number;
}

export interface RAMInfo {
	total_gb: number;
	available_gb: number;
}

export interface GPUInfo {
	name: string;
	vram_gb: number;
	driver_version: string;
	index: number;
}

export interface CUDAInfo {
	version: string | null;
	toolkit_path: string | null;
	cudnn_version: string | null;
	nccl_version: string | null;
}

export interface PythonInfo {
	version: string;
	path: string;
	is_venv: boolean;
	venv_path: string | null;
	pip_version: string | null;
}

export interface DiagnosticReport {
	agent_version: string;
	os: OSInfo;
	cpu: CPUInfo;
	ram: RAMInfo;
	gpus: GPUInfo[];
	cuda: CUDAInfo;
	python_installations: PythonInfo[];
	active_python: PythonInfo | null;
}

export interface CompatibilityIssue {
	severity: string;
	component: string;
	message: string;
	suggested_fix: string;
	docs_url?: string;
}

export interface DiagnosticResponse {
	report_id: string;
	compatible_profiles: string[];
	issues: CompatibilityIssue[];
	recommendations: string[];
}

// ── AI Troubleshoot Types ────────────────────────────────────────────────────

export interface TroubleshootRequest {
	diagnostic: Record<string, unknown>;
	profile_slug?: string;
	profile_name?: string;
	target_os?: string;
	python_version?: string;
	cuda_version?: string;
	user_description?: string;
}

export interface SuggestedFix {
	step: number;
	title: string;
	description: string;
	severity: "CRITICAL" | "WARNING" | "INFO";
	safe_commands: string[];
	repair_template_id: string | null;
}

export interface TroubleshootResponse {
	session_id: string;
	root_cause: string;
	suggested_fixes: SuggestedFix[];
	repair_script_available: boolean;
	confidence: number;
	disclaimer: string;
}

// ── AI Repair Types ──────────────────────────────────────────────────────────

export interface RepairRequest {
	template_id: string;
	params?: Record<string, unknown>;
}

export interface RepairResponse {
	template_id: string;
	filename: string;
	content: string;
	size_bytes: number;
	disclaimer: string;
}

export interface RepairTemplateInfo {
	id: string;
	description: string;
}

export interface RepairTemplateListResponse {
	templates: RepairTemplateInfo[];
}
