"use client";

import React, { useState, useEffect, useMemo } from "react";
import {
  Scale,
  Clock,
  ShieldCheck,
  Send,
  CheckCircle2,
  FileText,
  AlertTriangle,
  Award,
  Layers,
  ArrowRight,
  ExternalLink,
  Laptop,
  Check,
} from "lucide-react";
import {
  api,
  type DefenseBrief,
  SEEDED_DEFENSE_BRIEF,
  SEEDED_EVIDENCE_GRAPH,
} from "@/lib/api";
import { TimelineScheduler } from "@/components/TimelineScheduler";

export default function DisputesPage() {
  const [brief, setBrief] = useState<DefenseBrief>(SEEDED_DEFENSE_BRIEF);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submissionResult, setSubmissionResult] = useState<{
    submitted: boolean;
    referenceId?: string;
  }>({ submitted: brief.submitted_to_paypal });
  const [highlightedCitation, setHighlightedCitation] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        const data = await api.getDisputeDefenseBrief("PP-D-99412");
        setBrief(data);
        setSubmissionResult({ submitted: data.submitted_to_paypal });
      } catch (err) {
        console.error("Failed to load defense brief:", err);
      }
    }
    loadData();
  }, []);

  const handleSubmitEvidence = async () => {
    setIsSubmitting(true);
    try {
      const res = await api.submitDisputeEvidence(brief.dispute_id);
      setSubmissionResult({ submitted: true, referenceId: res.paypal_reference_id });
      setBrief((prev) => ({ ...prev, submitted_to_paypal: true }));
    } catch (err) {
      console.error("Submission failed:", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Find info for highlighted citation
  const activeCitedNode = useMemo(() => {
    if (!highlightedCitation) return null;
    return SEEDED_EVIDENCE_GRAPH.nodes.find((n) => n.id === highlightedCitation);
  }, [highlightedCitation]);

  // Parse narrative into interactive parts for bracketed [ev_*] citations
  const renderNarrativeWithCitations = (text: string) => {
    const parts = text.split(/(\[ev_[a-zA-Z0-9_]+\])/g);
    return parts.map((part, index) => {
      const match = part.match(/^\[(ev_[a-zA-Z0-9_]+)\]$/);
      if (match) {
        const citationId = match[1];
        const isHovered = highlightedCitation === citationId;
        const isTelemetry = citationId === "ev_session_118";
        return (
          <span
            key={index}
            onClick={() => setHighlightedCitation(citationId)}
            onMouseEnter={() => setHighlightedCitation(citationId)}
            className={`cursor-pointer inline-flex items-center px-1.5 py-0.5 mx-0.5 rounded text-xs font-mono font-bold transition-all ${
              isTelemetry
                ? "bg-violet-950/90 text-violet-300 border border-violet-700 hover:bg-violet-900"
                : isHovered
                ? "bg-paypal-cyan/30 text-paypal-cyan border border-paypal-cyan ring-1 ring-paypal-cyan"
                : "bg-cyan-950/70 text-cyan-300 border border-cyan-800 hover:bg-cyan-900/80"
            }`}
            title={`Click to inspect cited evidence node: ${citationId}`}
          >
            {isTelemetry && <Laptop className="w-3 h-3 mr-1" />}
            {part}
          </span>
        );
      }
      return <span key={index}>{part}</span>;
    });
  };

  return (
    <div className="flex flex-col gap-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-sentinel-border pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded text-[11px] font-mono font-bold bg-rose-950/80 text-rose-300 border border-rose-800">
              SCREEN 5 — DISPUTE COMMAND CENTER
            </span>
            <span className="text-slate-500 text-xs">•</span>
            <span className="text-xs font-mono text-slate-400">PayPal Disputes API v1 Grounded Defense</span>
          </div>
          <h1 className="text-2xl font-black text-white tracking-tight">
            Autonomous Dispute Defense Package
          </h1>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl">
            Real-time webhook ingestion for dispute PP-D-99412, multi-dimensional evidence readiness scoring (0.94), and grounded defense briefs with inline bracketed citations.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex flex-col items-end font-mono text-xs">
            <span className="text-slate-400 text-[10px]">Dispute Amount:</span>
            <span className="text-lg font-bold text-white">$4,180.50 USD</span>
          </div>
        </div>
      </div>

      {/* Top Section: SLA Timeline Countdown */}
      <TimelineScheduler
        deadlineDate="2026-10-18T23:59:59Z"
        currentStage={submissionResult.submitted ? "SUBMITTED" : "BRIEF_READY"}
        title={`PayPal Dispute SLA Countdown (${brief.dispute_id})`}
      />

      {/* Two Column Workspace: Readiness Score & Cited Defense Brief */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 1 Col: Evidence Readiness Score Card */}
        <div className="bg-sentinel-card border border-sentinel-border rounded-xl p-5 shadow-lg flex flex-col gap-5">
          <div className="flex items-center justify-between border-b border-sentinel-border pb-3">
            <div className="flex items-center gap-2">
              <Award className="w-4 h-4 text-paypal-cyan" />
              <h3 className="text-sm font-bold text-slate-100">Evidence Readiness</h3>
            </div>
            <span className="text-lg font-bold font-mono text-emerald-400">
              {(brief.readiness.overall * 100).toFixed(0)}%
            </span>
          </div>

          {/* 6 Dimension Progress Bars */}
          <div className="flex flex-col gap-3 text-xs">
            <div className="flex flex-col gap-1">
              <div className="flex justify-between text-slate-300 font-mono text-[11px]">
                <span>1. Completeness</span>
                <span className="text-emerald-400 font-bold">{(brief.readiness.completeness * 100).toFixed(0)}%</span>
              </div>
              <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${brief.readiness.completeness * 100}%` }} />
              </div>
            </div>

            <div className="flex flex-col gap-1">
              <div className="flex justify-between text-slate-300 font-mono text-[11px]">
                <span>2. Freshness</span>
                <span className="text-emerald-400 font-bold">{(brief.readiness.freshness * 100).toFixed(0)}%</span>
              </div>
              <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${brief.readiness.freshness * 100}%` }} />
              </div>
            </div>

            <div className="flex flex-col gap-1">
              <div className="flex justify-between text-slate-300 font-mono text-[11px]">
                <span>3. Provenance</span>
                <span className="text-cyan-400 font-bold">{(brief.readiness.provenance * 100).toFixed(0)}%</span>
              </div>
              <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                <div className="h-full bg-cyan-400 rounded-full" style={{ width: `${brief.readiness.provenance * 100}%` }} />
              </div>
            </div>

            <div className="flex flex-col gap-1">
              <div className="flex justify-between text-slate-300 font-mono text-[11px]">
                <span>4. Consistency</span>
                <span className="text-emerald-400 font-bold">{(brief.readiness.consistency * 100).toFixed(0)}%</span>
              </div>
              <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${brief.readiness.consistency * 100}%` }} />
              </div>
            </div>

            <div className="flex flex-col gap-1">
              <div className="flex justify-between text-slate-300 font-mono text-[11px]">
                <span>5. Relevance</span>
                <span className="text-amber-400 font-bold">{(brief.readiness.relevance * 100).toFixed(0)}%</span>
              </div>
              <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                <div className="h-full bg-amber-500 rounded-full" style={{ width: `${brief.readiness.relevance * 100}%` }} />
              </div>
            </div>

            <div className="flex flex-col gap-1">
              <div className="flex justify-between text-slate-300 font-mono text-[11px]">
                <span>6. Verifiability</span>
                <span className="text-emerald-400 font-bold">{(brief.readiness.verifiability * 100).toFixed(0)}%</span>
              </div>
              <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${brief.readiness.verifiability * 100}%` }} />
              </div>
            </div>
          </div>

          {/* Telemetry Substitution Highlight */}
          <div className="p-3 bg-violet-950/40 border border-violet-800/80 rounded-xl flex flex-col gap-1.5 text-xs">
            <div className="flex items-center gap-1.5 text-violet-300 font-semibold">
              <Laptop className="w-4 h-4 text-violet-400" />
              <span>Intangible Telemetry In Place</span>
            </div>
            <p className="text-[11px] text-slate-300 leading-relaxed">
              Substituted physical carrier shipment receipt with 84-hour digital service session logs [ev_session_118] from enterprise IP 198.51.100.44.
            </p>
          </div>

          {/* Active Citation Fact Popup */}
          {activeCitedNode && (
            <div className="p-3 bg-sentinel-bg border border-paypal-cyan/50 rounded-xl flex flex-col gap-1 text-xs font-mono animate-in fade-in">
              <div className="flex items-center justify-between text-paypal-cyan font-bold text-[11px]">
                <span>{activeCitedNode.type}</span>
                <span className="text-slate-400 text-[10px]">{activeCitedNode.id}</span>
              </div>
              <div className="text-slate-200 text-xs mt-1">{activeCitedNode.label}</div>
              <div className="text-[10px] text-slate-500 truncate mt-1">
                Hash: {activeCitedNode.sha256_hash}
              </div>
            </div>
          )}
        </div>

        {/* Right 2 Cols: Grounded Defense Brief & Submitter */}
        <div className="lg:col-span-2 bg-sentinel-card border border-sentinel-border rounded-xl p-6 shadow-lg flex flex-col justify-between gap-6">
          <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between border-b border-sentinel-border pb-3">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-paypal-cyan" />
                <h3 className="text-sm font-bold text-slate-100">
                  Grounded Defense Brief (Citations Enforced)
                </h3>
              </div>
              <span className="text-xs font-mono px-2.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                Reason: {brief.reason}
              </span>
            </div>

            {/* Narrative with Interactive Citations */}
            <div className="bg-sentinel-bg border border-sentinel-border rounded-xl p-5 text-slate-200 text-xs sm:text-sm leading-relaxed tracking-wide">
              {renderNarrativeWithCitations(brief.narrative)}
            </div>

            {/* Cited Nodes Index */}
            <div className="flex flex-col gap-1.5">
              <span className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-wider">
                Indexed Evidence Nodes ({brief.cited_nodes.length}):
              </span>
              <div className="flex flex-wrap gap-1.5">
                {brief.cited_nodes.map((c) => (
                  <button
                    key={c}
                    onClick={() => setHighlightedCitation(c)}
                    className={`px-2 py-0.5 rounded text-[10px] font-mono border transition-colors ${
                      highlightedCitation === c
                        ? "bg-paypal-cyan/20 text-paypal-cyan border-paypal-cyan"
                        : "bg-slate-900 text-slate-300 border-slate-800 hover:border-slate-700"
                    }`}
                  >
                    {c}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Submission Gate & PayPal Actions */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 pt-4 border-t border-sentinel-border">
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>Grounded claims verified against SQLite WAL graph</span>
            </div>

            {submissionResult.submitted ? (
              <div className="flex items-center gap-2 px-4 py-2 bg-emerald-950/80 border border-emerald-800 text-emerald-300 rounded-lg text-xs font-mono font-bold">
                <Check className="w-4 h-4 text-emerald-400" />
                <span>SUBMITTED TO PAYPAL ({submissionResult.referenceId || "EV-SUB-2026-99412"})</span>
              </div>
            ) : (
              <button
                onClick={handleSubmitEvidence}
                disabled={isSubmitting}
                className="flex items-center justify-center gap-2 px-5 py-2.5 bg-gradient-to-r from-paypal-blue to-paypal-cyan text-white text-xs font-bold rounded-lg shadow-lg shadow-paypal-blue/30 hover:opacity-95 transition-opacity disabled:opacity-50"
              >
                <Send className="w-3.5 h-3.5" />
                {isSubmitting ? "Submitting to PayPal API..." : "Submit Defense Evidence to PayPal Sandbox"}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
