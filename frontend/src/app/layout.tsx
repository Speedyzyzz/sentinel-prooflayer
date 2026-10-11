import type { Metadata } from "next";
import "./globals.css";
import { InstitutionalAppShell } from "@/components/InstitutionalAppShell";

export const metadata: Metadata = {
  title: "Sentinel & ProofLayer — Institutional Agent Governance & Evidence Graph",
  description:
    "Agent Mandate Control Plane & Causal Pre-Dispute Evidence Defense Engine for PayPal AI Hackathon 2026",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-sentinel-bg text-sentinel-text antialiased min-h-screen flex flex-col font-sans">
        <InstitutionalAppShell>{children}</InstitutionalAppShell>
      </body>
    </html>
  );
}
