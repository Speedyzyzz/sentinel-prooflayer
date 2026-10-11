"use client";

import React, { useState, useEffect, useMemo } from "react";
import {
  UserCheck,
  CheckCircle,
  XCircle,
  AlertTriangle,
  FileSpreadsheet,
  Lock,
  ShieldAlert,
  ArrowRight,
  Receipt,
  Building,
  Layers,
  X,
  Clock,
} from "lucide-react";
import type { ColDef } from "ag-grid-community";
import {
  api,
  type PaymentIntent,
  SEEDED_INTENTS,
} from "@/lib/api";
import {
  AgGridGovernanceTable,
  StatusBadgeRenderer,
  RiskGaugeRenderer,
  CurrencyRenderer,
  MonospaceHashRenderer,
} from "@/components/AgGridGovernanceTable";

export default function ApprovalsPage() {
  const [intents, setIntents] = useState<PaymentIntent[]>(SEEDED_INTENTS);
  const [selectedIntent, setSelectedIntent] = useState<PaymentIntent | null>(SEEDED_INTENTS[1]);
  const [activeTab, setActiveTab] = useState<"ALL" | "PENDING" | "APPROVED" | "BLOCKED">("ALL");
  const [actionFeedback, setActionFeedback] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        const data = await api.getIntents();
        setIntents(data);
      } catch (err) {
        console.error("Failed to load intents:", err);
      }
    }
    loadData();
  }, []);

  const handleApprove = async (intent: PaymentIntent) => {
    try {
      const updated = await api.approveIntent(intent.id, "usr_maya");
      setIntents((prev) => prev.map((i) => (i.id === intent.id ? updated : i)));
      setSelectedIntent(updated);
      setActionFeedback(`APPROVED: Intent ${intent.id} authorized and captured by CFO Maya via PayPal.`);
      setTimeout(() => setActionFeedback(null), 4000);
    } catch (err) {
      setActionFeedback(`Error approving: ${(err as Error).message}`);
    }
  };

  const handleReject = async (intent: PaymentIntent) => {
    try {
      const updated = await api.rejectIntent(intent.id, "CFO policy cap exceeded");
      setIntents((prev) => prev.map((i) => (i.id === intent.id ? updated : i)));
      setSelectedIntent(updated);
      setActionFeedback(`REJECTED: Intent ${intent.id} rejected by CFO Maya.`);
      setTimeout(() => setActionFeedback(null), 4000);
    } catch (err) {
      setActionFeedback(`Error rejecting: ${(err as Error).message}`);
    }
  };

  const handleHaltLevel1 = async (intent: PaymentIntent) => {
    try {
      await api.triggerKillSwitch(1, intent.id);
      const updated: PaymentIntent = { ...intent, status: "BLOCKED" };
      setIntents((prev) => prev.map((i) => (i.id === intent.id ? updated : i)));
      setSelectedIntent(updated);
      setActionFeedback(`HALTED: Level 1 Kill Switch triggered on ${intent.id}. Operations stopped.`);
      setTimeout(() => setActionFeedback(null), 4000);
    } catch (err) {
      setActionFeedback(`Error halting: ${(err as Error).message}`);
    }
  };

  const filteredIntents = useMemo(() => {
    if (activeTab === "PENDING") {
      return intents.filter((i) => i.status === "HUMAN_REVIEW" || i.status === "PROPOSED");
    }
    if (activeTab === "APPROVED") {
      return intents.filter((i) =>
        ["AUTO_APPROVED", "APPROVED", "CAPTURED", "RECONCILED"].includes(i.status)
      );
    }
    if (activeTab === "BLOCKED") {
      return intents.filter((i) => ["BLOCKED", "EXPIRED"].includes(i.status));
    }
    return intents;
  }, [intents, activeTab]);

  const columnDefs = useMemo<ColDef<PaymentIntent>[]>(
    () => [
      {
        field: "id",
        headerName: "Intent ID",
        width: 150,
        cellRenderer: MonospaceHashRenderer,
      },
      {
        field: "agent_id",
        headerName: "Agent",
        width: 140,
        cellClass: "font-mono text-slate-300 text-xs",
      },
      {
        field: "vendor_name",
        headerName: "Vendor Entity",
        width: 170,
        cellRenderer: (p: any) => (
          <div className="flex flex-col justify-center">
            <span className="font-semibold text-slate-100">{p.value}</span>
            <span className="text-[10px] text-slate-400 font-mono">{p.data?.vendor_category}</span>
          </div>
        ),
      },
      {
        field: "amount",
        headerName: "Amount",
        width: 120,
        cellRenderer: CurrencyRenderer,
      },
      {
        headerName: "PO Match (M)",
        width: 140,
        cellRenderer: (p: any) => {
          const match = p.data?.matching;
          if (!match) return null;
          return (
            <div className="flex items-center gap-1.5 font-mono text-xs">
              <span className="font-bold text-emerald-400">{match.score.toFixed(2)}</span>
              <span className="text-[10px] text-slate-400">({match.variance_pct}% var)</span>
            </div>
          );
        },
      },
      {
        field: "risk",
        headerName: "Risk Score (R)",
        width: 140,
        cellRenderer: (p: any) => <RiskGaugeRenderer value={p.data?.risk?.score} />,
      },
      {
        field: "status",
        headerName: "Status",
        width: 160,
        cellRenderer: StatusBadgeRenderer,
      },
      {
        headerName: "Inline Actions",
        width: 160,
        cellRenderer: (p: any) => {
          const item = p.data as PaymentIntent;
          if (!item) return null;
          const isPending = item.status === "HUMAN_REVIEW" || item.status === "PROPOSED";
          if (!isPending) {
            return <span className="text-[11px] text-slate-500 font-mono">Processed</span>;
          }
          return (
            <div className="flex items-center gap-1.5">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleApprove(item);
                }}
                className="px-2 py-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-[10px] font-bold"
              >
                Approve
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleReject(item);
                }}
                className="px-2 py-1 bg-rose-600 hover:bg-rose-500 text-white rounded text-[10px] font-bold"
              >
                Reject
              </button>
            </div>
          );
        },
      },
    ],
    []
  );

  return (
    <div className="flex flex-col gap-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-sentinel-border pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded text-[11px] font-mono font-bold bg-amber-950/80 text-amber-300 border border-amber-800">
              SCREEN 2 — APPROVAL QUEUE
            </span>
            <span className="text-slate-500 text-xs">•</span>
            <span className="text-xs font-mono text-slate-400">CFO Maya Operational Console</span>
          </div>
          <h1 className="text-2xl font-black text-white tracking-tight">
            Agent Payment Approval Console
          </h1>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl">
            Real-time multi-dimensional risk inspection, deterministic PO-to-Invoice matching verification, and idempotent CFO sign-off.
          </p>
        </div>

        {/* Tab Filters */}
        <div className="flex items-center gap-1.5 p-1 bg-sentinel-card border border-sentinel-border rounded-xl">
          <button
            onClick={() => setActiveTab("ALL")}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
              activeTab === "ALL"
                ? "bg-paypal-cyan/20 text-paypal-cyan border border-paypal-cyan/40"
                : "text-slate-400 hover:text-white"
            }`}
          >
            All ({intents.length})
          </button>
          <button
            onClick={() => setActiveTab("PENDING")}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
              activeTab === "PENDING"
                ? "bg-amber-950/80 text-amber-400 border border-amber-800"
                : "text-slate-400 hover:text-white"
            }`}
          >
            Pending Review ({intents.filter((i) => i.status === "HUMAN_REVIEW").length})
          </button>
          <button
            onClick={() => setActiveTab("APPROVED")}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
              activeTab === "APPROVED"
                ? "bg-emerald-950/80 text-emerald-400 border border-emerald-800"
                : "text-slate-400 hover:text-white"
            }`}
          >
            Approved ({intents.filter((i) => ["AUTO_APPROVED", "CAPTURED", "RECONCILED"].includes(i.status)).length})
          </button>
          <button
            onClick={() => setActiveTab("BLOCKED")}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
              activeTab === "BLOCKED"
                ? "bg-rose-950/80 text-rose-400 border border-rose-800"
                : "text-slate-400 hover:text-white"
            }`}
          >
            Blocked ({intents.filter((i) => i.status === "BLOCKED").length})
          </button>
        </div>
      </div>

      {actionFeedback && (
        <div className="p-3.5 bg-emerald-950/70 border border-emerald-800 text-emerald-300 rounded-xl text-xs font-mono shadow-md animate-in fade-in">
          {actionFeedback}
        </div>
      )}

      {/* Main Grid & Inspection Drawer Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: AG Grid Table */}
        <div className="lg:col-span-2">
          <AgGridGovernanceTable
            rowData={filteredIntents}
            columnDefs={columnDefs}
            onRowClicked={(row) => setSelectedIntent(row)}
            title="Procurement Intent Governance Ledger"
            height="520px"
          />
        </div>

        {/* Right 1 Col: Selected Intent Inspector */}
        <div className="bg-sentinel-card border border-sentinel-border rounded-xl p-5 shadow-lg flex flex-col gap-4">
          <div className="flex items-center justify-between border-b border-sentinel-border pb-3">
            <div className="flex items-center gap-2">
              <UserCheck className="w-4 h-4 text-paypal-cyan" />
              <h3 className="text-sm font-bold text-slate-100">Intent Inspector</h3>
            </div>
            {selectedIntent && <StatusBadgeRenderer value={selectedIntent.status} />}
          </div>

          {selectedIntent ? (
            <div className="flex flex-col gap-4">
              {/* Core Details */}
              <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                <div className="bg-sentinel-bg p-2 rounded border border-slate-800">
                  <span className="text-[10px] text-slate-500 block">INTENT ID</span>
                  <span className="text-slate-200 font-bold">{selectedIntent.id}</span>
                </div>
                <div className="bg-sentinel-bg p-2 rounded border border-slate-800">
                  <span className="text-[10px] text-slate-500 block">AMOUNT</span>
                  <span className="text-emerald-400 font-bold">${selectedIntent.amount.toFixed(2)} USD</span>
                </div>
                <div className="bg-sentinel-bg p-2 rounded border border-slate-800">
                  <span className="text-[10px] text-slate-500 block">VENDOR</span>
                  <span className="text-slate-200">{selectedIntent.vendor_name}</span>
                </div>
                <div className="bg-sentinel-bg p-2 rounded border border-slate-800">
                  <span className="text-[10px] text-slate-500 block">{"INVOICE // PO"}</span>
                  <span className="text-slate-300">{selectedIntent.invoice_id}</span>
                </div>
              </div>

              {/* PO Matching Dimensions Breakdown (M) */}
              <div className="flex flex-col gap-1.5 p-3 bg-sentinel-bg border border-sentinel-border rounded-lg text-xs">
                <div className="flex justify-between items-center font-mono">
                  <span className="text-slate-300 font-semibold">PO Match Score (M):</span>
                  <span className="text-emerald-400 font-bold text-sm">
                    {selectedIntent.matching.score.toFixed(2)} / 1.00
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-1 text-[11px] font-mono text-slate-400 pt-1 border-t border-slate-800">
                  <span>Vendor: {selectedIntent.matching.s_vendor.toFixed(2)}</span>
                  <span>Total: {selectedIntent.matching.s_total.toFixed(2)}</span>
                  <span>Items: {selectedIntent.matching.s_line_items.toFixed(2)}</span>
                  <span>Terms: {selectedIntent.matching.s_terms.toFixed(2)}</span>
                </div>
                <div className="text-[10px] text-slate-400 mt-1">
                  Variance: <strong className="text-amber-400">{selectedIntent.matching.variance_pct}%</strong> (Policy limit &lt;= 2.0%)
                </div>
              </div>

              {/* Risk Engine 5-Dimension Breakdown (R) */}
              <div className="flex flex-col gap-2 p-3 bg-sentinel-bg border border-sentinel-border rounded-lg text-xs">
                <div className="flex justify-between items-center font-mono">
                  <span className="text-slate-300 font-semibold">Risk Breakdown (R):</span>
                  <span className="font-bold font-mono text-slate-100">{selectedIntent.risk.score.toFixed(2)}</span>
                </div>
                <RiskGaugeRenderer value={selectedIntent.risk.score} />
                <div className="grid grid-cols-3 gap-1 text-[10px] font-mono text-slate-400 pt-1">
                  <span>V (Vendor): {selectedIntent.risk.v_entity}</span>
                  <span>D (Dupl): {selectedIntent.risk.d_duplicate}</span>
                  <span>A (Amount): {selectedIntent.risk.a_amount}</span>
                  <span>C (Cat): {selectedIntent.risk.c_category}</span>
                  <span>H (Hist): {selectedIntent.risk.h_history}</span>
                </div>
                {/* Human-readable reasons */}
                <div className="flex flex-col gap-1 pt-2 border-t border-slate-800">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Evaluation Reasons:</span>
                  {selectedIntent.risk.reasons.map((r, i) => (
                    <div key={i} className="text-[11px] text-slate-300 bg-sentinel-card p-1.5 rounded border border-slate-800">
                      • {r}
                    </div>
                  ))}
                </div>
              </div>

              {/* Idempotency & Cryptographic Audit */}
              <div className="p-3 bg-sentinel-bg border border-slate-800 rounded-lg text-[10px] font-mono text-slate-400 flex flex-col gap-1">
                <div>
                  Idempotency Key: <span className="text-slate-200">{selectedIntent.idempotency_key}</span>
                </div>
                {selectedIntent.paypal_capture_id && (
                  <div>
                    PayPal Capture: <span className="text-emerald-400 font-bold">{selectedIntent.paypal_capture_id}</span>
                  </div>
                )}
              </div>

              {/* Action Buttons */}
              {selectedIntent.status === "HUMAN_REVIEW" || selectedIntent.status === "PROPOSED" ? (
                <div className="flex flex-col gap-2 pt-2">
                  <button
                    onClick={() => handleApprove(selectedIntent)}
                    className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-bold transition-colors flex items-center justify-center gap-1.5 shadow-lg shadow-emerald-950"
                  >
                    <Lock className="w-3.5 h-3.5" /> Approve & Capture via PayPal (CFO Maya)
                  </button>
                  <button
                    onClick={() => handleReject(selectedIntent)}
                    className="w-full py-2 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-xs font-semibold transition-colors flex items-center justify-center gap-1.5"
                  >
                    <XCircle className="w-3.5 h-3.5" /> Reject Intent
                  </button>
                </div>
              ) : null}

              {/* Level 1 Kill Switch Trigger */}
              <button
                onClick={() => handleHaltLevel1(selectedIntent)}
                className="w-full py-1.5 border border-rose-900/60 hover:bg-rose-950/40 text-rose-300 rounded text-xs font-mono font-medium transition-colors flex items-center justify-center gap-1.5"
              >
                <ShieldAlert className="w-3.5 h-3.5 text-rose-400" /> Level 1 Kill Switch: Halt This Intent
              </button>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-slate-500 text-xs">
              Select an intent row from the table to inspect details.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
