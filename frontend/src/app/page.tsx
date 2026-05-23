"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { ArrowRight, Zap, Shield, Brain, Cpu } from "lucide-react";

export default function HomePage() {
  const features = [
    {
      icon: Zap,
      title: "Lightning Fast Setup",
      description: "Generate ML environment scripts in seconds, not hours",
    },
    {
      icon: Shield,
      title: "Safety First",
      description: "AI-powered validation prevents harmful configurations",
    },
    {
      icon: Brain,
      title: "AI-Powered",
      description: "Get intelligent recommendations for your setup",
    },
    {
      icon: Cpu,
      title: "Hardware Aware",
      description: "Optimized scripts for your specific hardware",
    },
  ];

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Hero Section */}
      <section style={{ paddingTop: '6rem', paddingBottom: '6rem', textAlign: 'center' }}>
        <div className="container">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
            <h1 style={{ fontSize: '4rem', fontWeight: 700, marginBottom: '1.5rem', lineHeight: '1.2' }}>
              Smart ML <span className="text-gradient">Environment</span> Setup
            </h1>
            <p style={{ fontSize: '1.3rem', color: 'var(--text-secondary)', marginBottom: '2rem', maxWidth: '600px', margin: '0 auto 2rem' }}>
              Generate intelligent, safe, and deterministic ML/AI environment setup scripts in seconds.
            </p>
            <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center', flexWrap: 'wrap' }}>
              <Link href="/diagnose" className="btn btn-primary" style={{ padding: '0.75rem 2rem', fontSize: '1rem', display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}>
                Get Started <ArrowRight size={20} />
              </Link>
              <Link href="/profiles" className="btn btn-secondary" style={{ padding: '0.75rem 2rem', fontSize: '1rem' }}>
                Browse Profiles
              </Link>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Features Section */}
      <section style={{ paddingTop: '4rem', paddingBottom: '4rem', background: 'rgba(0,0,0,0.2)' }}>
        <div className="container">
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2, duration: 0.6 }}>
            <h2 style={{ textAlign: 'center', fontSize: '2.5rem', marginBottom: '4rem' }}>Why Choose EnvForge?</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '2rem' }}>
              {features.map((feature, i) => {
                const Icon = feature.icon;
                return (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 + i * 0.1 }}
                    className="glass-panel"
                    style={{ padding: '2rem', textAlign: 'center' }}
                  >
                    <Icon size={40} color="var(--brand-primary)" style={{ margin: '0 auto 1rem' }} />
                    <h3 style={{ marginBottom: '0.75rem' }}>{feature.title}</h3>
                    <p style={{ color: 'var(--text-secondary)' }}>{feature.description}</p>
                  </motion.div>
                );
              })}
            </div>
          </motion.div>
        </div>
      </section>

      {/* How It Works */}
      <section style={{ paddingTop: '4rem', paddingBottom: '4rem' }}>
        <div className="container">
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4, duration: 0.6 }}>
            <h2 style={{ textAlign: 'center', fontSize: '2.5rem', marginBottom: '4rem' }}>How It Works</h2>
            <div style={{ maxWidth: '800px', margin: '0 auto' }}>
              {[
                { num: 1, title: "Run Diagnostics", desc: "Use `envforge diagnose` to analyze your system" },
                { num: 2, title: "Choose Profile", desc: "Select your ML framework (PyTorch, TensorFlow, etc.)" },
                { num: 3, title: "Verify Compatibility", desc: "EnvForge checks your hardware compatibility" },
                { num: 4, title: "Generate Script", desc: "Get a safe, optimized setup script" },
              ].map((step, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.5 + i * 0.1 }}
                  style={{ display: 'flex', gap: '2rem', marginBottom: i < 3 ? '2rem' : 0, alignItems: 'flex-start' }}
                >
                  <div style={{ background: 'var(--brand-primary)', color: 'white', width: '48px', height: '48px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, flexShrink: 0 }}>
                    {step.num}
                  </div>
                  <div style={{ paddingTop: '0.5rem' }}>
                    <h4 style={{ marginBottom: '0.5rem' }}>{step.title}</h4>
                    <p style={{ color: 'var(--text-secondary)' }}>{step.desc}</p>
                  </div>
                  {i < 3 && <div style={{ width: '2px', background: 'var(--border-strong)', margin: '-2rem 0 0 0', flexGrow: 1 }} />}
                </motion.div>
              ))}
            </div>
          </motion.div>
        </div>
      </section>

      {/* CTA Section */}
      <section style={{ paddingTop: '4rem', paddingBottom: '6rem', background: 'rgba(99, 102, 241, 0.05)', marginTop: '2rem' }}>
        <div className="container" style={{ textAlign: 'center' }}>
          <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.6, duration: 0.6 }}>
            <h2 style={{ fontSize: '2.5rem', marginBottom: '1.5rem' }}>Ready to Set Up Your Environment?</h2>
            <p style={{ fontSize: '1.1rem', color: 'var(--text-secondary)', marginBottom: '2rem' }}>
              Start with diagnostics or explore our ML profiles
            </p>
            <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center', flexWrap: 'wrap' }}>
              <Link href="/diagnose" className="btn btn-primary" style={{ padding: '0.75rem 2rem', fontSize: '1rem' }}>
                Run Diagnostics
              </Link>
              <Link href="/profiles" className="btn btn-secondary" style={{ padding: '0.75rem 2rem', fontSize: '1rem' }}>
                View Profiles
              </Link>
              <Link href="/troubleshoot" className="btn btn-secondary" style={{ padding: '0.75rem 2rem', fontSize: '1rem' }}>
                AI Troubleshoot
              </Link>
            </div>
          </motion.div>
        </div>
      </section>
    </div>
  );
}
