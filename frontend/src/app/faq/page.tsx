export default function FAQPage() {
  const faqs = [
    {
      question: "What is EnvForage?",
      answer: "EnvForage generates deterministic, hardware-aware setup scripts for PyTorch, CUDA, and GPU drivers so your ML environment works on the first try."
    },
    {
      question: "How do I install the CLI agent?",
      answer: "Run: pip install envforage, then use envforage diagnose to scan your hardware."
    },
    {
      question: "Which GPUs are supported?",
      answer: "EnvForage supports NVIDIA GPUs with CUDA. AMD ROCm support is currently in development."
    },
    {
      question: "Is EnvForage free to use?",
      answer: "Yes, EnvForage is fully open-source under the MIT license."
    },
    {
      question: "Which ML frameworks does EnvForage support?",
      answer: "Currently PyTorch, TensorFlow, JAX, and YOLOv8 profiles are supported out of the box."
    }
  ];

  return (
    <main style={{ maxWidth: "800px", margin: "0 auto", padding: "4rem 2rem" }}>
      <h1 style={{
        fontSize: "3rem",
        fontWeight: 800,
        marginBottom: "1rem",
        color: "var(--text-primary)"
      }}>
        Frequently Asked Questions
      </h1>
      <p style={{
        color: "var(--text-secondary)",
        marginBottom: "3rem",
        fontSize: "1.2rem"
      }}>
        Everything you need to know about EnvForage.
      </p>
      <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
        {faqs.map((faq, index) => (
          <details
            key={index}
            style={{
              border: "1px solid var(--border-subtle)",
              borderRadius: "8px",
              padding: "1.25rem 1.5rem",
              backgroundColor: "var(--bg-secondary)",
              cursor: "pointer"
            }}
          >
            <summary style={{
              fontWeight: 600,
              fontSize: "1.1rem",
              color: "var(--text-primary)",
              cursor: "pointer",
              listStyle: "none",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center"
            }}>
              {faq.question}
              <span style={{ color: "var(--brand-secondary)", fontSize: "1.5rem" }}>+</span>
            </summary>
            <p style={{
              marginTop: "1rem",
              color: "var(--text-secondary)",
              lineHeight: 1.7,
              fontSize: "1rem"
            }}>
              {faq.answer}
            </p>
          </details>
        ))}
      </div>
    </main>
  );
}