import { create } from 'zustand';
import { devtools, persist, createJSONStorage } from 'zustand/middleware';

// --- Type Definitions ---
export interface DiagnosticData {
    os?: { name: string; version: string; architecture: string };
    cpu?: { brand: string; cores: number };
    gpus?: Array<{ name: string; vram_gb: number }>;
    cuda?: { version: string; toolkit_path: string };
}

export interface TroubleshootResult {
    session_id: string;
    root_cause: string;
    confidence: number;
    suggested_fixes: Array<{ step: number; title: string; severity: string; repair_template_id?: string }>;
}

export interface AppState {
    // UI State
    isSidebarOpen: boolean;
    activeTheme: 'light' | 'dark' | 'system';
    
    // Diagnostic State
    diagnosticData: DiagnosticData | null;
    isAnalyzing: boolean;
    analysisResult: TroubleshootResult | null;
    
    // Profile State
    activeProfileSlug: string;
    customParams: Record<string, unknown>;

    // Actions
    toggleSidebar: () => void;
    setTheme: (theme: 'light' | 'dark' | 'system') => void;
    setDiagnosticData: (data: DiagnosticData) => void;
    setAnalysisState: (isAnalyzing: boolean, result?: TroubleshootResult | null) => void;
    setActiveProfile: (slug: string) => void;
    updateCustomParams: (key: string, value: unknown) => void;
    resetState: () => void;
}

// --- Initial State ---
const initialState = {
    isSidebarOpen: false,
    activeTheme: 'system' as const,
    diagnosticData: null,
    isAnalyzing: false,
    analysisResult: null,
    activeProfileSlug: 'pytorch-cuda',
    customParams: {},
};

// --- Store Implementation ---
export const useAppStore = create<AppState>()(
    devtools(
        persist(
            (set) => ({
                ...initialState,

                // --- UI Actions ---
                toggleSidebar: () => set((state) => ({ isSidebarOpen: !state.isSidebarOpen }), false, 'toggleSidebar'),
                
                setTheme: (theme) => {
                    set({ activeTheme: theme }, false, 'setTheme');
                    if (typeof document !== 'undefined') {
                        document.documentElement.setAttribute('data-theme', theme);
                    }
                },

                // --- Diagnostic Actions ---
                setDiagnosticData: (data) => set({ diagnosticData: data }, false, 'setDiagnosticData'),
                
                setAnalysisState: (isAnalyzing, result) => set((state) => ({ 
                    isAnalyzing, 
                    analysisResult: result !== undefined ? result : state.analysisResult 
                }), false, 'setAnalysisState'),

                // --- Profile Actions ---
                setActiveProfile: (slug) => set({ activeProfileSlug: slug }, false, 'setActiveProfile'),
                
                updateCustomParams: (key, value) => set((state) => ({
                    customParams: { ...state.customParams, [key]: value }
                }), false, 'updateCustomParams'),

                // --- Reset ---
                resetState: () => set(initialState, false, 'resetState'),
            }),
            {
                name: 'envforage-storage', // unique name
                storage: createJSONStorage(() => localStorage),
                partialize: (state) => ({ 
                    activeTheme: state.activeTheme, 
                    activeProfileSlug: state.activeProfileSlug,
                    customParams: state.customParams
                }), // Only persist specific fields
            }
        ),
        { name: 'EnvForageStore' }
    )
);

// --- Advanced Selectors ---
export const selectIsDarkTheme = (state: AppState) => {
    if (state.activeTheme === 'system') {
        return typeof window !== 'undefined' ? window.matchMedia('(prefers-color-scheme: dark)').matches : true;
    }
    return state.activeTheme === 'dark';
};

export const selectHardwareSummary = (state: AppState) => {
    const d = state.diagnosticData;
    if (!d) return null;
    return {
        os: d.os?.name || 'Unknown',
        gpu: d.gpus?.[0]?.name || 'No GPU',
        cuda: d.cuda?.version || 'N/A'
    };
};

// --- Hooks ---
export const useHardwareSummary = () => useAppStore(selectHardwareSummary);
export const useThemeStatus = () => useAppStore(selectIsDarkTheme);

// --- Middleware & Event Listeners ---
if (typeof window !== 'undefined') {
    window.addEventListener('storage', (e) => {
        if (e.key === 'envforage-storage') {
            useAppStore.persist.rehydrate();
        }
    });
}
