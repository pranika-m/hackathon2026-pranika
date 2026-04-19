import type { Metadata } from "next";
import { Fraunces, Manrope } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const fraunces = Fraunces({
  variable: "--font-display",
  subsets: ["latin"],
});

const manrope = Manrope({
  variable: "--font-body",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "ShopWave Autonomous Support Agent",
  description:
    "Audit-friendly dashboard for autonomous ticket resolution, escalations, retries, and analytics.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${fraunces.variable} ${manrope.variable}`}>
      <body>
        <div className="app-shell">
          <aside className="sidebar" aria-label="Primary">
            <div className="brand-block">
              <p className="eyebrow">ShopWave</p>
              <h1>Support Resolution</h1>
              <p className="brand-copy">
                Autonomous triage, action, escalation, and audit visibility.
              </p>
            </div>

            <nav className="nav-list">
              <Link href="/">
                <strong>Dashboard</strong>
                <div className="meta-text">Ticket queue, resolutions, and operational status.</div>
              </Link>
              <Link href="/analytics">
                <strong>Analytics</strong>
                <div className="meta-text">Confidence, retries, failures, and tool usage.</div>
              </Link>
            </nav>

            <div className="sidebar-footer">
              <strong>Operator note</strong>
              <div style={{ marginTop: "8px" }}>
                Interface tuned for long support sessions with clear status visibility and readable ticket context.
              </div>
            </div>
          </aside>

          <main className="main-shell">{children}</main>
        </div>
      </body>
    </html>
  );
}
