"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { API_BASE } from "@/lib/api";

interface ToolCall {
  step: number;
  tag: string;
  tool_name: string;
  inputs: Record<string, unknown>;
  outputs: Record<string, unknown>;
  success: boolean;
  duration_ms: number;
  timestamp: string;
}

interface AuditLog {
  ticket_id: string;
  customer_email: string;
  subject: string;
  started_at: string;
  completed_at: string;
  customer_ref: string;
  order_ref: string;
  product_ref: string;
  tool_calls: ToolCall[];
  retry_events: Array<{ tool_name: string; attempt: number; backoff_seconds: number; reason: string }>;
  confidence_score: number | null;
  final_decision: string;
  escalation_summary: string | null;
  reply_sent: string | null;
  errors: Array<{ tag: string; error: string }>;
  reasoning_trace: Array<{ step: string; reasoning: string }>;
}

interface TicketDetail {
  ticket_id: string;
  original_ticket: {
    ticket_id: string;
    customer_email: string;
    subject: string;
    body: string;
    source: string;
    created_at: string;
  };
  audit: AuditLog;
}

interface QuerySignal {
  label: string;
  note: string;
}

const QUERY_TYPE_RULES: Array<{ keywords: string[]; label: string; note: string }> = [
  {
    keywords: ["refund", "money back", "charge"],
    label: "Refund request",
    note: "Customer seeks reimbursement or payment correction.",
  },
  {
    keywords: ["cancel", "subscription", "renewal"],
    label: "Cancellation",
    note: "Likely account termination or renewal stop request.",
  },
  {
    keywords: ["replace", "broken", "damaged", "defective"],
    label: "Replacement / defect",
    note: "Physical product quality or replacement workflow issue.",
  },
  {
    keywords: ["late", "delivery", "shipping", "tracking"],
    label: "Fulfillment / delivery",
    note: "Ticket concerns order movement, delay, or carrier status.",
  },
  {
    keywords: ["warranty", "coverage", "guarantee"],
    label: "Warranty",
    note: "Customer asks about policy-backed product coverage.",
  },
];

function buildQueryTypeSignal(subject: string, body: string): QuerySignal {
  const source = `${subject} ${body}`.toLowerCase();
  const match = QUERY_TYPE_RULES.find((rule) => rule.keywords.some((k) => source.includes(k)));

  if (match) {
    return { label: match.label, note: match.note };
  }

  return {
    label: "General support",
    note: "No dominant keyword cluster found; treat as broad support inquiry.",
  };
}

function buildUrgencySignal(subject: string, body: string): QuerySignal {
  const source = `${subject} ${body}`.toLowerCase();
  const highUrgency = ["urgent", "asap", "immediately", "fraud", "charged twice", "angry"];
  const mediumUrgency = ["today", "soon", "deadline", "important"];

  if (highUrgency.some((k) => source.includes(k))) {
    return {
      label: "High urgency",
      note: "Contains escalation language indicating immediate human attention.",
    };
  }

  if (mediumUrgency.some((k) => source.includes(k))) {
    return {
      label: "Medium urgency",
      note: "Time-sensitive wording detected; prioritize same-day follow-up.",
    };
  }

  return {
    label: "Normal urgency",
    note: "No explicit urgency language detected in customer text.",
  };
}

function getCustomerName(email: string): string {
  const [local] = email.split("@");
  return local
    .replace(/[._-]+/g, " ")
    .split(" ")
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(" ");
}

function formatDate(value: string): string {
  if (!value) return "-";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString();
}

function buildActionChecklist(audit: AuditLog): string[] {
  const actions: string[] = [];

  if (audit.final_decision === "ESCALATED") {
    actions.push("Assign to specialist queue and preserve full tool timeline for handoff.");
  }

  if (audit.final_decision === "RESOLVED") {
    actions.push("Confirm customer-facing reply quality and tone before closing ticket.");
  }

  if (audit.retry_events?.length > 0) {
    actions.push("Review retry events to identify flaky tools or brittle inputs.");
  }

  if (audit.errors?.length > 0) {
    actions.push("Inspect latest error tags and validate fallback path behavior.");
  }

  if (audit.confidence_score !== null && audit.confidence_score < 0.6) {
    actions.push("Confidence is below threshold; require human approval before outbound action.");
  }

  if (actions.length === 0) {
    actions.push("No critical blockers found. Verify references and close ticket if customer need is satisfied.");
  }

  return actions;
}

export default function TicketDetailPage() {
  const params = useParams();
  const ticketId = params.id as string;
  const [data, setData] = useState<TicketDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDetail = async () => {
      try {
        const res = await fetch(`${API_BASE}/tickets/${ticketId}`);
        if (res.ok) {
          const json = await res.json();
          setData(json);
        }
      } catch {
        /* ignore */
      }
      setLoading(false);
    };
    fetchDetail();
  }, [ticketId]);

  if (loading) {
    return (
      <section className="page-stack" aria-label="Loading ticket">
        <div className="panel empty-state">Loading ticket detail...</div>
      </section>
    );
  }

  if (!data || !data.audit || !data.audit.ticket_id) {
    return (
      <section className="page-stack" aria-label="Ticket not found">
        <Link href="/" className="back-link">
          &larr; Back to Dashboard
        </Link>
        <div className="panel empty-state">Ticket not found. Run the agent first.</div>
      </section>
    );
  }

  const { original_ticket: orig, audit } = data;
  const queryType = buildQueryTypeSignal(orig.subject || "", orig.body || "");
  const urgency = buildUrgencySignal(orig.subject || "", orig.body || "");
  const customerName = getCustomerName(orig.customer_email || "customer");
  const checklist = buildActionChecklist(audit);

  const getDecisionBadge = (decision: string) => {
    const cls =
      decision === "RESOLVED"
        ? "badge-resolved"
        : decision === "ESCALATED"
          ? "badge-escalated"
          : "badge-failed";
    return (
      <span className={`badge ${cls}`} role="status">
        {decision}
      </span>
    );
  };

  const confidenceColor = (score: number) => {
    if (score >= 0.8) return "var(--resolved)";
    if (score >= 0.6) return "var(--escalated)";
    return "var(--failed)";
  };

  return (
    <section className="page-stack" aria-label={`Ticket detail for ${ticketId}`}>
      <Link href="/" className="back-link" aria-label="Back to dashboard">
        &larr; Back to Dashboard
      </Link>

      <div className="page-header">
        <div>
          <p className="eyebrow">Ticket Detail</p>
          <h1 className="page-title">{ticketId}</h1>
          <p className="page-subtitle">
            Human review workspace for understanding the customer query, AI execution path, and recommended follow-up.
          </p>
        </div>
        {audit.final_decision && getDecisionBadge(audit.final_decision)}
      </div>

      <article className="panel query-overview">
        <div className="section-row" style={{ marginBottom: "14px" }}>
          <h2 className="section-title">Customer Query Overview</h2>
          <span className="pill">Human-facing summary</span>
        </div>

        <div className="query-meta-grid">
          <div className="query-meta-card">
            <span className="query-meta-label">Customer</span>
            <div className="query-meta-value">{customerName || "Customer"}</div>
            <div className="meta-text">{orig.customer_email || "-"}</div>
          </div>
          <div className="query-meta-card">
            <span className="query-meta-label">Query Type</span>
            <div className="query-meta-value">{queryType.label}</div>
            <div className="meta-text">{queryType.note}</div>
          </div>
          <div className="query-meta-card">
            <span className="query-meta-label">Urgency</span>
            <div className="query-meta-value">{urgency.label}</div>
            <div className="meta-text">{urgency.note}</div>
          </div>
          <div className="query-meta-card">
            <span className="query-meta-label">Created</span>
            <div className="query-meta-value">{formatDate(orig.created_at)}</div>
            <div className="meta-text">Source: {orig.source || "-"}</div>
          </div>
        </div>

        <div className="customer-query-box">
          <div className="query-subject">{orig.subject}</div>
          <p className="query-body">{orig.body}</p>
        </div>
      </article>

      <div className="detail-grid">
        <div className="detail-stack">
          <article className="panel">
            <div className="section-row">
              <h2 className="section-title">Original Ticket</h2>
              <span className="pill">{orig.source}</span>
            </div>
            <h3 style={{ margin: 0, fontSize: "1.25rem" }}>{orig.subject}</h3>
            <p style={{ color: "var(--text-muted)", lineHeight: "1.8", margin: "14px 0 0" }}>{orig.body}</p>
            <div style={{ display: "flex", gap: "18px", flexWrap: "wrap", marginTop: "18px" }} className="meta-text">
              <span>Email: {orig.customer_email}</span>
              <span>Date: {formatDate(orig.created_at)}</span>
              <span>Source: {orig.source}</span>
            </div>
          </article>

          <div className="panel">
            <div className="section-row">
              <h2 className="section-title">Tool Call Timeline</h2>
              <span className="pill">{audit.tool_calls?.length || 0} calls</span>
            </div>
            <div className="timeline">
              {audit.tool_calls?.map((tc, i) => (
                <div
                  key={i}
                  className={`timeline-item ${tc.success ? "success" : "failure"}`}
                  data-step={tc.step}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "12px", marginBottom: "10px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
                      <span style={{ fontWeight: "800" }}>{tc.tool_name}</span>
                      <span className={`badge ${tc.success ? "badge-resolved" : "badge-failed"}`}>{tc.tag}</span>
                    </div>
                    <span className="meta-text">{tc.duration_ms.toFixed(0)}ms</span>
                  </div>
                  <div style={{ fontSize: "0.92rem", color: "var(--text-muted)", lineHeight: "1.6" }}>
                    <div><strong style={{ color: "var(--text)" }}>Input:</strong> {JSON.stringify(tc.inputs).substring(0, 220)}</div>
                    <div style={{ marginTop: "6px" }}>
                      <strong style={{ color: "var(--text)" }}>Output:</strong> {JSON.stringify(tc.outputs).substring(0, 320)}
                      {JSON.stringify(tc.outputs).length > 320 && "..."}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {audit.reasoning_trace?.length > 0 && (
            <div className="panel">
              <div className="section-row">
                <h2 className="section-title">Reasoning Trace</h2>
              </div>
              <div className="timeline">
                {audit.reasoning_trace.map((r, i) => (
                  <div key={i} className="timeline-item">
                    <div style={{ marginBottom: "10px" }}>
                      <span className="badge badge-ingested">{r.step}</span>
                    </div>
                    <div style={{ color: "var(--text-muted)", lineHeight: "1.7" }}>{r.reasoning}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="detail-stack">
          <div className="panel">
            <div className="section-row">
              <h2 className="section-title">Confidence</h2>
            </div>
            {audit.confidence_score !== null ? (
              <div>
                <div style={{ fontSize: "4rem", fontWeight: "800", color: confidenceColor(audit.confidence_score), lineHeight: 1 }}>
                  {audit.confidence_score.toFixed(2)}
                </div>
                <div className="confidence-gauge" role="progressbar" aria-valuenow={Math.round(audit.confidence_score * 100)} aria-valuemin={0} aria-valuemax={100} style={{ marginTop: "16px" }}>
                  <div className="confidence-gauge-fill" style={{ width: `${audit.confidence_score * 100}%`, background: confidenceColor(audit.confidence_score) }} />
                </div>
                <p className="meta-text" style={{ marginTop: "12px" }}>
                  {audit.confidence_score < 0.6 ? "Below threshold - escalation required." : "Above threshold - autonomous decision permitted."}
                </p>
              </div>
            ) : (
              <div className="meta-text">Not scored</div>
            )}
          </div>

          <div className="panel">
            <div className="section-row">
              <h2 className="section-title">Recommended Next Actions</h2>
            </div>
            <div className="action-checklist">
              {checklist.map((item, idx) => (
                <div key={idx} className="action-checklist-item">
                  <span className="action-index">{idx + 1}</span>
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="panel">
            <div className="section-row">
              <h2 className="section-title">References</h2>
            </div>
            <div style={{ display: "grid", gap: "10px" }}>
              <div><strong>Customer:</strong> <span className="meta-text">{audit.customer_ref || "-"}</span></div>
              <div><strong>Order:</strong> <span className="meta-text">{audit.order_ref || "-"}</span></div>
              <div><strong>Product:</strong> <span className="meta-text">{audit.product_ref || "-"}</span></div>
            </div>
          </div>

          {audit.escalation_summary && (
            <div className="panel" style={{ borderLeft: "5px solid var(--escalated)" }}>
              <div className="section-row">
                <h2 className="section-title">Escalation Summary</h2>
              </div>
              <div className="meta-text" style={{ lineHeight: "1.7" }}>{audit.escalation_summary}</div>
            </div>
          )}

          {audit.reply_sent && (
            <div className="panel" style={{ borderLeft: "5px solid var(--sage)" }}>
              <div className="section-row">
                <h2 className="section-title">Reply Sent</h2>
              </div>
              <div style={{ color: "var(--text-muted)", lineHeight: "1.7", fontStyle: "italic" }}>{audit.reply_sent}</div>
            </div>
          )}

          {audit.retry_events?.length > 0 && (
            <div className="panel">
              <div className="section-row">
                <h2 className="section-title">Retry Events</h2>
              </div>
              <div className="timeline">
                {audit.retry_events.map((r, i) => (
                  <div key={i} className="timeline-item">
                    <div style={{ fontWeight: "700" }}>{r.tool_name}</div>
                    <div className="meta-text" style={{ marginTop: "8px" }}>
                      Attempt {r.attempt}, backoff {r.backoff_seconds}s, reason: {r.reason}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {audit.errors?.length > 0 && (
            <div className="panel">
              <div className="section-row">
                <h2 className="section-title">Errors</h2>
              </div>
              <div className="timeline">
                {audit.errors.map((err, i) => (
                  <div key={i} className="timeline-item failure">
                    <div style={{ marginBottom: "8px" }}>
                      <span className="badge badge-failed">{err.tag}</span>
                    </div>
                    <div className="meta-text">{err.error}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
