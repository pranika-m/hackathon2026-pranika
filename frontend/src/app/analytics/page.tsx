"use client";

import { useState, useEffect } from "react";
import { API_BASE } from "@/lib/api";

interface Analytics {
  total: number;
  resolved: number;
  escalated: number;
  dead_letter: number;
  avg_confidence: number;
  confidence_distribution: Record<string, number>;
  failure_types: Record<string, number>;
  tool_call_frequency: Record<string, number>;
}

export default function AnalyticsPage() {
  const [data, setData] = useState<Analytics | null>(null);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const res = await fetch(`${API_BASE}/analytics`);
        if (res.ok) setData(await res.json());
      } catch {
        /* ignore */
      }
    };
    fetchAnalytics();
  }, []);

  if (!data) {
    return (
      <section className="page-stack" aria-label="Analytics">
        <div className="panel empty-state">
          <div>
            <h1 className="page-title">Analytics</h1>
            <div style={{ marginTop: "10px" }}>No data yet. Run the agent first.</div>
          </div>
        </div>
      </section>
    );
  }

  const maxDecision = Math.max(data.resolved, data.escalated, data.dead_letter, 1);
  const confEntries = Object.entries(data.confidence_distribution);
  const maxConf = Math.max(...confEntries.map(([, v]) => v), 1);
  const toolEntries = Object.entries(data.tool_call_frequency).sort(([, a], [, b]) => b - a);
  const maxTool = Math.max(...toolEntries.map(([, v]) => v), 1);

  return (
    <section className="page-stack" aria-label="Analytics page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Observability</p>
          <h1 className="page-title">Performance and trust signals</h1>
          <p className="page-subtitle">
            Resolution mix, confidence distribution, failure patterns, and tool usage across the full ticket batch.
          </p>
        </div>
        <span className="pill">{data.total} total tickets</span>
      </div>

      <div className="summary-grid">
        <div className="card summary-card">
          <div className="summary-top">
            <span className="signal-label">Resolved</span>
            <span className="badge badge-resolved">Direct</span>
          </div>
          <span className="count" style={{ color: "var(--resolved)" }}>{data.resolved}</span>
          <span className="label">Autonomous completions with tool-backed decisions.</span>
          <div className="status-strip" style={{ background: "var(--resolved)" }} />
        </div>

        <div className="card summary-card">
          <div className="summary-top">
            <span className="signal-label">Escalated</span>
            <span className="badge badge-escalated">Specialist</span>
          </div>
          <span className="count" style={{ color: "var(--escalated)" }}>{data.escalated}</span>
          <span className="label">Cases handed off with structured context and rationale.</span>
          <div className="status-strip" style={{ background: "var(--escalated)" }} />
        </div>

        <div className="card summary-card">
          <div className="summary-top">
            <span className="signal-label">Dead letters</span>
            <span className="badge badge-failed">Recovery</span>
          </div>
          <span className="count" style={{ color: "var(--failed)" }}>{data.dead_letter}</span>
          <span className="label">Failures that could not be recovered within the agent loop.</span>
          <div className="status-strip" style={{ background: "var(--failed)" }} />
        </div>

        <div className="card summary-card">
          <div className="summary-top">
            <span className="signal-label">Avg confidence</span>
            <span className="badge badge-processing">Score</span>
          </div>
          <span className="count" style={{ color: "var(--info)" }}>{data.avg_confidence.toFixed(2)}</span>
          <span className="label">Mean confidence after automated deductions.</span>
          <div className="status-strip" style={{ background: "var(--info)" }} />
        </div>
      </div>

      <div className="metric-grid">
        <div className="card stat-card">
          <div className="section-row">
            <h2 className="section-title">Resolution Distribution</h2>
          </div>
          <div className="chart-shell">
            <div className="bar-columns">
              {[
                { label: "Resolved", value: data.resolved, color: "var(--resolved)" },
                { label: "Escalated", value: data.escalated, color: "var(--escalated)" },
                { label: "Dead letter", value: data.dead_letter, color: "var(--failed)" },
              ].map((item) => (
                <div key={item.label} className="bar-column">
                  <div className="bar-column-value">{item.value}</div>
                  <div
                    className="bar-column-fill"
                    style={{ height: `${(item.value / maxDecision) * 150}px`, background: item.color }}
                  />
                  <div className="bar-column-label">{item.label}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="card stat-card">
          <div className="section-row">
            <h2 className="section-title">Confidence Distribution</h2>
          </div>
          <div className="chart-shell">
            <div className="bar-columns">
              {confEntries.map(([bucket, count]) => (
                <div key={bucket} className="bar-column">
                  <div className="bar-column-value">{count}</div>
                  <div
                    className="bar-column-fill"
                    style={{
                      height: `${(count / maxConf) * 150}px`,
                      background:
                        bucket.startsWith("0.8")
                          ? "var(--resolved)"
                          : bucket.startsWith("0.6")
                            ? "var(--escalated)"
                            : bucket.startsWith("0.4")
                              ? "var(--terracotta)"
                              : "var(--failed)",
                    }}
                  />
                  <div className="bar-column-label">{bucket}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="metric-grid">
        <div className="card stat-card">
          <div className="section-row">
            <h2 className="section-title">Failure Breakdown</h2>
          </div>
          <div className="table-shell">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Count</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(data.failure_types).map(([type, count]) => (
                  <tr key={type}>
                    <td><span className="badge badge-failed">{type}</span></td>
                    <td style={{ fontWeight: "700" }}>{count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="card stat-card">
          <div className="section-row">
            <h2 className="section-title">Tool Call Frequency</h2>
          </div>
          <div className="bar-list">
            {toolEntries.map(([name, count]) => (
              <div key={name} className="bar-row">
                <span className="meta-text">{name}</span>
                <div className="bar-track">
                  <div className="bar-fill" style={{ width: `${(count / maxTool) * 100}%` }} />
                </div>
                <span style={{ fontWeight: "700" }}>{count}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
