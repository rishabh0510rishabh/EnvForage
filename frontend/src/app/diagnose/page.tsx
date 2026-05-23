"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { UploadCloud, CheckCircle, AlertTriangle, ShieldAlert, Cpu, HardDrive, Monitor, Terminal } from "lucide-react";
import { DiagnosticReport, DiagnosticResponse, Profile } from "../../types";
import { api } from "../../services/api";
import Link from "next/link";

export default function DiagnosePage() {
  const [jsonInput, setJsonInput] = useState("");
  const [report, setReport] = useState<DiagnosticReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [selectedProfile, setSelectedProfile] = useState<string>("");
  const [verifying, setVerifying] = useState(false);
  const [verifyResult, setVerifyResult] = useState<DiagnosticResponse | null>(null);

  useEffect(() => {
    async function loadProfiles() {
      try {
        const data = await api.getProfiles();
        setProfiles(data);
        if (data.length > 0) setSelectedProfile(data[0].slug);
      } catch {}
    }
    loadProfiles();
  }, []);

  const handleParse = () => {
    setError(null);
    try {
      const parsed = JSON.parse(jsonInput);
      if (!parsed.os || !parsed.cpu || !parsed.agent_version) {
        throw new Error("Invalid Diagnostic Report format. Ensure you pasted the output of `envforge diagnose`.");
      }
      setReport(parsed as DiagnosticReport);
      setVerifyResult(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invalid JSON.");
    }
  };

  const handleVerify = async () => {
    if (!report || !selectedProfile) return;
    setVerifying(true);
    setVerifyResult(null);
    try {
      const result = await api.diagnose(report, selectedProfile);
      setVerifyResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification failed.");
    } finally {
      setVerifying(false);
    }
  };

  return (
    <div className="container" style={{ paddingTop: '4rem', paddingBottom: '6rem' }}>
      <div style={{ textAlign: 'center', marginBottom: '3rem' }}>
        <h1 style={{ fontSize: '3rem', marginBottom: '1rem' }}>Diagnostic Dashboard</h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '1.1rem' }}>Paste your offline agent report to verify compatibility.</p>
      </div>

      {!report ? (
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="glass-panel" style={{ padding: '2rem', maxWidth: '800px', margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
            <UploadCloud size={48} color="var(--brand-primary)" style={{ margin: '0 auto 1rem' }} />
            <h3>Upload Diagnostic JSON</h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginTop: '0.5rem' }}>
              Run <code style={{ color: 'var(--brand-accent)' }}>envforge diagnose --quiet</code> and paste the output below.
            </p>
          </div>
          <textarea 
            value={jsonInput}
            onChange={(e) => setJsonInput(e.target.value)}
            placeholder='{\n  "agent_version": "1.0.0",\n  "os": {\n    "name": "Ubuntu 22.04"...\n}'
            style={{ 
              width: '100%', height: '300px', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--border-strong)', 
              borderRadius: '8px', padding: '1rem', color: 'var(--text-primary)', fontFamily: 'var(--font-mono)', fontSize: '0.9rem',
              resize: 'vertical', outline: 'none'
            }}
          />
          {error && <div style={{ color: '#ef4444', marginTop: '1rem', fontSize: '0.9rem' }}>{error}</div>}
          <div style={{ display: 'flex', justifyContent: 'center', marginTop: '2rem' }}>
            <button className="btn btn-primary" onClick={handleParse} disabled={!jsonInput.trim()}>
              Analyze Report
            </button>
          </div>
        </motion.div>
      ) : (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
            <h2>Hardware Overview</h2>
            <button className="btn btn-secondary" onClick={() => { setReport(null); setJsonInput(""); }}>Upload New Report</button>
          </div>

          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem', marginBottom: '4rem' }}>
            
            {/* OS Card */}
            <div className="glass-panel" style={{ padding: '1.5rem', display: 'flex', gap: '1rem', alignItems: 'flex-start' }}>
              <div style={{ background: 'rgba(99, 102, 241, 0.1)', padding: '0.75rem', borderRadius: '8px' }}>
                <Monitor color="var(--brand-primary)" size={24} />
              </div>
              <div>
                <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.25rem' }}>Operating System</div>
                <div style={{ fontWeight: 600, fontSize: '1.1rem' }}>{report.os.name}</div>
                <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>{report.os.architecture} {report.os.wsl_version ? `(${report.os.wsl_version})` : ''}</div>
              </div>
            </div>

            {/* CPU Card */}
            <div className="glass-panel" style={{ padding: '1.5rem', display: 'flex', gap: '1rem', alignItems: 'flex-start' }}>
              <div style={{ background: 'rgba(16, 185, 129, 0.1)', padding: '0.75rem', borderRadius: '8px' }}>
                <Cpu color="var(--brand-accent)" size={24} />
              </div>
              <div>
                <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.25rem' }}>Processor</div>
                <div style={{ fontWeight: 600, fontSize: '1.1rem' }}>{report.cpu.brand}</div>
                <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>{report.cpu.cores} Cores / {report.cpu.threads} Threads</div>
              </div>
            </div>

            {/* GPU Card */}
            <div className="glass-panel" style={{ padding: '1.5rem', display: 'flex', gap: '1rem', alignItems: 'flex-start' }}>
              <div style={{ background: 'rgba(236, 72, 153, 0.1)', padding: '0.75rem', borderRadius: '8px' }}>
                <HardDrive color="var(--brand-secondary)" size={24} />
              </div>
              <div>
                <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.25rem' }}>Graphics (GPU)</div>
                {report.gpus.length > 0 ? (
                  <>
                    <div style={{ fontWeight: 600, fontSize: '1.1rem' }}>{report.gpus[0].name}</div>
                    <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>{report.gpus[0].vram_gb} GB VRAM • Driver {report.gpus[0].driver_version}</div>
                  </>
                ) : (
                  <div style={{ fontWeight: 600, fontSize: '1.1rem', color: 'var(--text-secondary)' }}>No NVIDIA GPU Detected</div>
                )}
              </div>
            </div>

            {/* CUDA Card */}
            <div className="glass-panel" style={{ padding: '1.5rem', display: 'flex', gap: '1rem', alignItems: 'flex-start' }}>
              <div style={{ background: 'rgba(234, 179, 8, 0.1)', padding: '0.75rem', borderRadius: '8px' }}>
                <Terminal color="#eab308" size={24} />
              </div>
              <div>
                <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.25rem' }}>CUDA Toolkit</div>
                {report.cuda.version ? (
                  <>
                    <div style={{ fontWeight: 600, fontSize: '1.1rem' }}>v{report.cuda.version}</div>
                    <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>cuDNN: {report.cuda.cudnn_version || 'Not installed'}</div>
                  </>
                ) : (
                  <div style={{ fontWeight: 600, fontSize: '1.1rem', color: 'var(--text-secondary)' }}>Not Installed</div>
                )}
              </div>
            </div>

          </motion.div>

          {/* Verification Engine */}
          <div className="glass-panel" style={{ padding: '2rem' }}>
            <h2 style={{ marginBottom: '1.5rem' }}>Verify Compatibility</h2>
            <div style={{ display: 'flex', gap: '1rem', alignItems: 'flex-end', marginBottom: '2rem' }}>
              <div style={{ flexGrow: 1, maxWidth: '400px' }}>
                <label style={{ display: 'block', fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Target ML Profile</label>
                <select 
                  value={selectedProfile} 
                  onChange={(e) => setSelectedProfile(e.target.value)}
                  style={{ width: '100%', padding: '0.75rem 1rem', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--border-strong)', color: 'white', borderRadius: '8px', fontSize: '1rem', outline: 'none' }}
                >
                  {profiles.map(p => <option key={p.slug} value={p.slug}>{p.name}</option>)}
                </select>
              </div>
              <button className="btn btn-primary" onClick={handleVerify} disabled={verifying || !selectedProfile}>
                {verifying ? "Verifying..." : "Run Check"}
              </button>
            </div>

            {verifyResult && (
              <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} style={{ padding: '1.5rem', background: verifyResult.issues.length === 0 ? 'rgba(16, 185, 129, 0.05)' : 'rgba(239, 68, 68, 0.05)', border: `1px solid ${verifyResult.issues.length === 0 ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)'}`, borderRadius: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
                  {verifyResult.issues.length === 0 ? <CheckCircle color="var(--brand-accent)" size={28} /> : <AlertTriangle color="#ef4444" size={28} />}
                  <h3 style={{ margin: 0, color: verifyResult.issues.length === 0 ? 'var(--brand-accent)' : '#ef4444' }}>
                    {verifyResult.issues.length === 0 ? "Compatible!" : `${verifyResult.issues.length} Issue(s) Found`}
                  </h3>
                </div>

                {verifyResult.compatible_profiles.length > 0 && (
                  <div style={{ marginBottom: '1.5rem' }}>
                    <p style={{ color: 'var(--text-secondary)', marginBottom: '0.75rem', fontSize: '0.9rem' }}>Compatible Profiles:</p>
                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                      {verifyResult.compatible_profiles.map(slug => (
                        <Link key={slug} href={`/generate?profile=${slug}`} style={{ padding: '0.4rem 0.8rem', background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.3)', borderRadius: '6px', fontSize: '0.85rem', color: 'var(--brand-accent)', textDecoration: 'none' }}>
                          {slug}
                        </Link>
                      ))}
                    </div>
                  </div>
                )}

                {verifyResult.issues.length > 0 && (
                  <div style={{ marginBottom: '1.5rem' }}>
                    <p style={{ color: 'var(--text-secondary)', marginBottom: '0.75rem', fontSize: '0.9rem' }}>Issues Detected:</p>
                    <ul style={{ listStyleType: 'none', padding: 0 }}>
                      {verifyResult.issues.map((issue, i) => (
                        <li key={i} style={{ padding: '0.75rem', background: 'rgba(0,0,0,0.2)', borderRadius: '4px', marginBottom: '0.5rem', fontSize: '0.9rem', display: 'flex', gap: '0.75rem' }}>
                          <ShieldAlert size={16} color={issue.severity === 'ERROR' ? '#ef4444' : '#eab308'} style={{ flexShrink: 0, marginTop: '2px' }} />
                          <div>
                            <div style={{ color: issue.severity === 'ERROR' ? '#fca5a5' : '#fde68a' }}>{issue.message}</div>
                            {issue.suggested_fix && <div style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginTop: '0.25rem' }}>💡 {issue.suggested_fix}</div>}
                          </div>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {verifyResult.recommendations.length > 0 && (
                  <div>
                    <p style={{ color: 'var(--text-secondary)', marginBottom: '0.5rem', fontSize: '0.9rem' }}>Recommendations:</p>
                    {verifyResult.recommendations.map((rec, i) => (
                      <div key={i} style={{ color: 'var(--text-primary)', fontSize: '0.9rem' }}>→ {rec}</div>
                    ))}
                  </div>
                )}
              </motion.div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
