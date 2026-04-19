"use client";

import { useState, useEffect, useCallback } from "react";
import { API_BASE } from "@/lib/api";

interface TicketSummary {
  ticket_id: string;
  subject: string;
  customer_email: string;
  body: string;
  source: string;
  created_at: string;
  state: string;
  final_decision: string | null;
  confidence_score: number | null;
  tool_call_count: number;
  llm_feedback?: string;
}

interface StatusData {
  job_status: string;
  total: number;
  completed: number;
  counts: Record<string, number>;
  tickets: { ticket_id: string; state: string }[];
}

interface CustomerProfile {
  customer_id: string;
  name: string;
  email: string;
  phone: string;
  tier: string;
  member_since: string;
  total_orders: number;
  total_spent: number;
  address?: {
    street: string;
    city: string;
    state: string;
    zip: string;
  };
  notes?: string;
}

interface CustomerDetailResponse {
  customer: CustomerProfile | null;
  customer_email: string;
  queries: TicketSummary[];
}

export default function Dashboard() {
  const [tickets, setTickets] = useState<TicketSummary[]>([]);
  const [status, setStatus] = useState<StatusData | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isCustomerOpen, setIsCustomerOpen] = useState(false);
  const [isCustomerLoading, setIsCustomerLoading] = useState(false);
  const [customerError, setCustomerError] = useState<string | null>(null);
  const [selectedCustomer, setSelectedCustomer] = useState<CustomerDetailResponse | null>(null);

  const fetchTickets = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/tickets`);
      if (res.ok) {
        const data = await res.json();
        setTickets(data.tickets || []);
      }
    } catch {
      /* backend not running yet */
    }
  }, []);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/status`);
      if (res.ok) {
        const data: StatusData = await res.json();
        setStatus(data);
        return data;
      }
    } catch {
      /* backend not running yet */
    }
    return null;
  }, []);

  const runAgent = async () => {
    setIsRunning(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/run`, { method: "POST" });
      if (!res.ok) throw new Error("Failed to start agent");

      const poll = setInterval(async () => {
        const statusData = await fetchStatus();
        await fetchTickets();

        if (statusData && statusData.completed === statusData.total && statusData.total > 0) {
          clearInterval(poll);
          setIsRunning(false);
        }
      }, 2000);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
      setIsRunning(false);
    }
  };

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void fetchTickets();
      void fetchStatus();
    }, 0);

    return () => window.clearTimeout(timer);
  }, [fetchTickets, fetchStatus]);

  const resolved = status?.counts?.RESOLVED || 0;
  const escalated = status?.counts?.ESCALATED || 0;
  const failed = (status?.counts?.FAILED || 0) + (status?.counts?.DEAD_LETTER || 0);
  const total = status?.total || 0;

  const getBadgeClass = (state: string) => {
    const s = state.toLowerCase();
    if (s === "resolved") return "badge badge-resolved";
    if (s === "escalated") return "badge badge-escalated";
    if (s === "failed" || s === "dead_letter") return "badge badge-failed";
    if (s === "executing") return "badge badge-processing";
    return "badge badge-ingested";
  };

  const getConfidenceColor = (score: number | null) => {
    if (score === null) return "var(--beige)";
    if (score >= 0.8) return "var(--resolved)";
    if (score >= 0.6) return "var(--escalated)";
    return "var(--failed)";
  };

  const formatNameFromEmail = (email: string) => {
    const [localPart] = email.split("@");
    return localPart
      .split(/[._-]+/)
      .filter(Boolean)
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(" ");
  };

  const openCustomerDetail = async (customerEmail: string) => {
    setIsCustomerOpen(true);
    setIsCustomerLoading(true);
    setCustomerError(null);
    setSelectedCustomer(null);

    try {
      const encoded = encodeURIComponent(customerEmail);
      const res = await fetch(`${API_BASE}/customers/${encoded}`);
      if (!res.ok) throw new Error("Unable to load customer details");
      const data: CustomerDetailResponse = await res.json();
      setSelectedCustomer(data);
    } catch (e: unknown) {
      setCustomerError(e instanceof Error ? e.message : "Unknown error while loading customer details");
    } finally {
      setIsCustomerLoading(false);
    }
  };

  const closeCustomerDetail = () => {
    setIsCustomerOpen(false);
    setSelectedCustomer(null);
    setCustomerError(null);
    setIsCustomerLoading(false);
  };

  useEffect(() => {
    if (!isCustomerOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") closeCustomerDetail();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [isCustomerOpen]);

  return (
    <section className="page-stack" aria-label="Dashboard">
      <div className="hero">
        <div className="hero-card">
          <p className="eyebrow">Autonomous Support</p>
          <h1 className="hero-title">Resolve repetitive tickets without losing human judgment.</h1>
          <p className="hero-subtitle">
            ShopWave triages, acts, escalates, and audits every customer request with an explainable tool-driven loop.
          </p>
          <div className="hero-actions">
            <button
              className="btn-primary"
              onClick={runAgent}
              disabled={isRunning}
              aria-label={isRunning ? "Agent is processing tickets" : "Run agent to process all tickets"}
            >
              {isRunning ? "Processing..." : "Run Agent"}
            </button>
            <span className="pill">{total > 0 ? `${status?.completed}/${total} processed` : "Awaiting first run"}</span>
          </div>
        </div>

        <div className="hero-side">
          <div className="hero-card signal-card">
            <span className="signal-label">Run status</span>
            <div className="signal-value">{status?.job_status === "running" ? "Live" : "Ready"}</div>
            <p className="signal-copy">
              The dashboard refreshes while tickets are being processed concurrently.
            </p>
          </div>
          <div className="hero-card signal-card">
            <span className="signal-label">Coverage</span>
            <div className="signal-value">{total || 20}</div>
            <p className="signal-copy">
              Simulated tickets covering refunds, cancellations, replacements, warranty, fraud, and FAQ flows.
            </p>
          </div>
        </div>
      </div>

      {error && (
        <div className="panel" style={{ borderColor: "rgba(185, 101, 87, 0.35)", color: "var(--failed)" }}>
          {error}
        </div>
      )}

      <div className="summary-grid">
        <div className="card summary-card">
          <div className="summary-top">
            <span className="signal-label">Resolved</span>
            <span className="badge badge-resolved">Autonomous</span>
          </div>
          <span className="count" style={{ color: "var(--resolved)" }}>{resolved}</span>
          <span className="label">Tickets completed without specialist intervention.</span>
          <div className="status-strip" style={{ background: "var(--resolved)" }} />
        </div>

        <div className="card summary-card">
          <div className="summary-top">
            <span className="signal-label">Escalated</span>
            <span className="badge badge-escalated">Guardrails</span>
          </div>
          <span className="count" style={{ color: "var(--escalated)" }}>{escalated}</span>
          <span className="label">Cases routed with context when confidence or policy required it.</span>
          <div className="status-strip" style={{ background: "var(--escalated)" }} />
        </div>

        <div className="card summary-card">
          <div className="summary-top">
            <span className="signal-label">Failures</span>
            <span className="badge badge-failed">Recovery</span>
          </div>
          <span className="count" style={{ color: "var(--failed)" }}>{failed}</span>
          <span className="label">Tickets that hit failure paths or dead-letter scenarios.</span>
          <div className="status-strip" style={{ background: "var(--failed)" }} />
        </div>

        <div className="card summary-card">
          <div className="summary-top">
            <span className="signal-label">Total queue</span>
            <span className="badge badge-processing">Batch</span>
          </div>
          <span className="count" style={{ color: "var(--info)" }}>{total}</span>
          <span className="label">Tickets observed by the current run state.</span>
          <div className="status-strip" style={{ background: "var(--info)" }} />
        </div>
      </div>

      <div className="panel">
        <div className="section-row">
          <div>
            <h2 className="section-title">Ticket Queue</h2>
            <p className="page-subtitle">Live status, confidence, and tool depth for every processed ticket.</p>
          </div>
          <span className="pill">Concurrent execution enabled</span>
        </div>

        <div className="table-shell">
          <table className="data-table">
            <thead>
              <tr>
                <th>Ticket</th>
                <th>Subject</th>
                <th>Customer</th>
                <th>Status</th>
                <th>Confidence</th>
                <th>Tool Calls</th>
              </tr>
            </thead>
            <tbody>
              {tickets.length === 0 && (
                <tr>
                  <td colSpan={6}>
                    <div className="empty-state">
                      <div>
                        <strong>No tickets processed yet.</strong>
                        <div style={{ marginTop: "8px" }}>Run the agent to populate the support queue and audit trail.</div>
                      </div>
                    </div>
                  </td>
                </tr>
              )}
              {tickets.map((t) => (
                <tr key={t.ticket_id}>
                  <td className="meta-text" style={{ fontWeight: 700 }}>{t.ticket_id}</td>
                  <td style={{ maxWidth: "320px" }}>
                    <div style={{ fontWeight: 700 }}>{t.subject}</div>
                  </td>
                  <td>
                    <button
                      className="customer-name-link"
                      onClick={() => openCustomerDetail(t.customer_email)}
                      aria-label={`Open details for customer ${formatNameFromEmail(t.customer_email)}`}
                    >
                      {formatNameFromEmail(t.customer_email)}
                    </button>
                  </td>
                  <td>
                    <span className={getBadgeClass(t.final_decision || t.state)} role="status">
                      {t.final_decision || t.state}
                    </span>
                  </td>
                  <td>
                    {t.confidence_score !== null ? (
                      <div style={{ display: "grid", gap: "8px", minWidth: "120px" }}>
                        <div className="confidence-gauge" role="progressbar" aria-valuenow={Math.round((t.confidence_score || 0) * 100)} aria-valuemin={0} aria-valuemax={100}>
                          <div className="confidence-gauge-fill" style={{ width: `${(t.confidence_score || 0) * 100}%`, background: getConfidenceColor(t.confidence_score) }} />
                        </div>
                        <span style={{ fontSize: "12px", fontWeight: "700" }}>{(t.confidence_score || 0).toFixed(2)}</span>
                      </div>
                    ) : (
                      <span className="meta-text">-</span>
                    )}
                  </td>
                  <td style={{ fontWeight: "700" }}>{t.tool_call_count || "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {isCustomerOpen && (
        <div className="modal-overlay" role="dialog" aria-modal="true" aria-label="Customer details popup">
          <div className="modal-shell">
            <div className="modal-header">
              <div>
                <p className="eyebrow">Customer Details</p>
                <h2 className="section-title" style={{ marginTop: "2px" }}>
                  {selectedCustomer?.customer?.name || formatNameFromEmail(selectedCustomer?.customer_email || "customer@email.com")}
                </h2>
              </div>
              <button className="btn-secondary" onClick={closeCustomerDetail} aria-label="Close customer details popup">
                Close
              </button>
            </div>

            <div className="modal-body">
              {isCustomerLoading && <div className="empty-state">Loading customer details...</div>}

              {!isCustomerLoading && customerError && (
                <div className="panel" style={{ borderColor: "rgba(185, 101, 87, 0.35)", color: "var(--failed)" }}>
                  {customerError}
                </div>
              )}

              {!isCustomerLoading && !customerError && selectedCustomer && (
                <div className="modal-stack">
                  <div className="query-meta-grid">
                    <div className="query-meta-card">
                      <span className="query-meta-label">Email</span>
                      <div className="query-meta-value">{selectedCustomer.customer?.email || selectedCustomer.customer_email}</div>
                    </div>
                    <div className="query-meta-card">
                      <span className="query-meta-label">Tier</span>
                      <div className="query-meta-value">{selectedCustomer.customer?.tier || "-"}</div>
                    </div>
                    <div className="query-meta-card">
                      <span className="query-meta-label">Total Orders</span>
                      <div className="query-meta-value">{selectedCustomer.customer?.total_orders ?? "-"}</div>
                    </div>
                    <div className="query-meta-card">
                      <span className="query-meta-label">Total Spent</span>
                      <div className="query-meta-value">
                        {selectedCustomer.customer?.total_spent !== undefined
                          ? `$${selectedCustomer.customer.total_spent.toFixed(2)}`
                          : "-"}
                      </div>
                    </div>
                  </div>

                  <div className="panel">
                    <div className="section-row">
                      <h3 className="section-title" style={{ fontSize: "1.2rem" }}>Customer Profile</h3>
                    </div>
                    <div className="action-checklist">
                      <div className="action-checklist-item"><strong>Customer ID:</strong> {selectedCustomer.customer?.customer_id || "-"}</div>
                      <div className="action-checklist-item"><strong>Phone:</strong> {selectedCustomer.customer?.phone || "-"}</div>
                      <div className="action-checklist-item"><strong>Member Since:</strong> {selectedCustomer.customer?.member_since || "-"}</div>
                      <div className="action-checklist-item"><strong>Address:</strong> {selectedCustomer.customer?.address ? `${selectedCustomer.customer.address.street}, ${selectedCustomer.customer.address.city}, ${selectedCustomer.customer.address.state} ${selectedCustomer.customer.address.zip}` : "-"}</div>
                      <div className="action-checklist-item"><strong>Notes:</strong> {selectedCustomer.customer?.notes || "-"}</div>
                    </div>
                  </div>

                  <div className="panel">
                    <div className="section-row">
                      <h3 className="section-title" style={{ fontSize: "1.2rem" }}>All Queries Related To This Customer</h3>
                      <span className="pill">{selectedCustomer.queries.length} queries</span>
                    </div>

                    <div className="panel" style={{ padding: "14px", marginBottom: "14px" }}>
                      <div className="section-row" style={{ marginBottom: "10px" }}>
                        <h4 className="section-title" style={{ fontSize: "1rem" }}>LLM Response Feedback</h4>
                      </div>
                      <div className="action-checklist">
                        {selectedCustomer.queries.length === 0 && (
                          <div className="meta-text">No query feedback available.</div>
                        )}
                        {selectedCustomer.queries.map((q) => (
                          <div key={`${q.ticket_id}-llm`} className="action-checklist-item">
                            <strong>{q.ticket_id}:</strong> {q.llm_feedback || "No customer response available yet."}
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="table-shell">
                      <table className="data-table">
                        <thead>
                          <tr>
                            <th>Ticket</th>
                            <th>Subject</th>
                            <th>Status</th>
                            <th>Confidence</th>
                            <th>Tool Calls</th>
                            <th>LLM Response</th>
                          </tr>
                        </thead>
                        <tbody>
                          {selectedCustomer.queries.length === 0 && (
                            <tr>
                              <td colSpan={6}><span className="meta-text">No related queries found.</span></td>
                            </tr>
                          )}
                          {selectedCustomer.queries.map((q) => (
                            <tr key={q.ticket_id}>
                              <td className="meta-text" style={{ fontWeight: 700 }}>{q.ticket_id}</td>
                              <td>
                                <div style={{ fontWeight: 700 }}>{q.subject}</div>
                                <div className="meta-text" style={{ marginTop: "5px" }}>{q.body}</div>
                              </td>
                              <td>
                                <span className={getBadgeClass(q.final_decision || q.state)}>{q.final_decision || q.state}</span>
                              </td>
                              <td className="meta-text">
                                {q.confidence_score !== null ? q.confidence_score.toFixed(2) : "-"}
                              </td>
                              <td className="meta-text" style={{ fontWeight: 700 }}>
                                {q.tool_call_count || "-"}
                              </td>
                              <td className="meta-text">{q.llm_feedback || "No customer response available yet."}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
