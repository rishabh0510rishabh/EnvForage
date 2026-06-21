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



// --- Advanced Report Exporter ---
interface DiagnosticReport {
    os?: { name: string; version: string };
    gpus?: { name: string; vram_gb: number }[];
    [key: string]: unknown;
}

export class DiagnosticReportExporter {
    static async exportToJSON(reportData: DiagnosticReport, filename: string = 'diagnostic-report.json') {
        try {
            const dataStr = JSON.stringify(reportData, null, 2);
            const blob = new Blob([dataStr], { type: 'application/json' });
            this.downloadBlob(blob, filename);
            return true;
        } catch (error) {
            console.error("Failed to export JSON report", error);
            return false;
        }
    }

    static async exportToMarkdown(reportData: DiagnosticReport, filename: string = 'diagnostic-report.md') {
        try {
            let md = `# Diagnostic Report\n\n`;
            md += `Generated at: ${new Date().toISOString()}\n\n`;
            
            if (reportData.os) {
                md += `## Operating System\n`;
                md += `- Name: ${reportData.os.name}\n`;
                md += `- Version: ${reportData.os.version}\n\n`;
            }

            if (reportData.gpus && Array.isArray(reportData.gpus)) {
                md += `## Hardware\n`;
                reportData.gpus.forEach((gpu) => {
                    md += `- GPU: ${gpu.name} (${gpu.vram_gb}GB VRAM)\n`;
                });
                md += `\n`;
            }

            const blob = new Blob([md], { type: 'text/markdown' });
            this.downloadBlob(blob, filename);
            return true;
        } catch (error) {
            console.error("Failed to export Markdown report", error);
            return false;
        }
    }

    private static downloadBlob(blob: Blob, filename: string) {
        if (typeof window === 'undefined') return;
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
}

