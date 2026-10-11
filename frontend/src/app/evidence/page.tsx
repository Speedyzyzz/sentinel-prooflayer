"use client";

import React, { useState, useEffect, useMemo } from "react";
import {
  Network,
  Filter,
  CheckCircle2,
  FileCode,
  ShieldCheck,
  Hash,
  Clock,
  Layers,
  ArrowRight,
  ExternalLink,
  Info,
} from "lucide-react";
import {
  api,
  type EvidenceGraphData,
  type EvidenceNode,
  type NodeType,
  SEEDED_EVIDENCE_GRAPH,
} from "@/lib/api";
import { CausalGraphCanvas } from "@/components/CausalGraphCanvas";

const SUBGRAPH_FILTERS: Array<{ id: NodeType | "ALL"; label: string }> = [
  { id: "ALL", label: "Full Causal Graph (18 Nodes)" },
  { id: "AGENT_MANDATE", label: "Governance Mandate" },
  { id: "PAYMENT_INTENT", label: "Payment Intent" },
  { id: "POLICY_DECISION", label: "Policy Decisions" },
  { id: "APPROVAL_RECORD", label: "CFO Approvals" },
  { id: "PURCHASE_ORDER", label: "Purchase Orders" },
  { id: "INVOICE", label: "Invoices" },
  { id: "PAYPAL_CAPTURE", label: "PayPal Captures" },
  { id: "CUSTOMER_SESSION", label: "Digital Telemetry" },
  { id: "DISPUTE", label: "PayPal Disputes" },
  { id: "EVIDENCE_CLAIM", label: "Evidence Claims" },
];

export default function EvidenceGraphPage() {
  const [graphData, setGraphData] = useState<EvidenceGraphData>(SEEDED_EVIDENCE_GRAPH);
  const [selectedNode, setSelectedNode] = useState<EvidenceNode | null>(SEEDED_EVIDENCE_GRAPH.nodes[0]);
  const [activeFilter, setActiveFilter] = useState<NodeType | "ALL">("ALL");

  useEffect(() => {
    async function loadData() {
      try {
        const data = await api.getEvidenceGraph("int_2026_0918");
        setGraphData(data);
      } catch (err) {
        console.error("Failed to load evidence graph:", err);
      }
    }
    loadData();
  }, []);

  // Compute inbound & outbound edges for the selected node
  const relatedEdges = useMemo(() => {
    if (!selectedNode) return { inbound: [], outbound: [] };
    const inbound = graphData.edges.filter((e) => e.target === selectedNode.id);
    const outbound = graphData.edges.filter((e) => e.source === selectedNode.id);
    return { inbound, outbound };
  }, [graphData.edges, selectedNode]);

  return (
    <div className="flex flex-col gap-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-sentinel-border pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded text-[11px] font-mono font-bold bg-violet-950/80 text-violet-300 border border-violet-800">
              SCREEN 4 — EVIDENCE GRAPH EXPLORER
            </span>
            <span className="text-slate-500 text-xs">•</span>
            <span className="text-xs font-mono text-slate-400">18 Node Types • 13 Edge Types</span>
          </div>
          <h1 className="text-2xl font-black text-white tracking-tight">
            Causal Property Evidence Graph
          </h1>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl">
            Cryptographically anchored DAG connecting mandates, vendor invoices, purchase orders, MFA approvals, PayPal captures, digital telemetry, and dispute defense claims.
          </p>
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1 max-w-full">
          <Filter className="w-4 h-4 text-slate-400 shrink-0" />
          <select
            value={activeFilter}
            onChange={(e) => setActiveFilter(e.target.value as NodeType | "ALL")}
            className="bg-sentinel-card border border-sentinel-border text-xs rounded-lg px-3 py-1.5 text-slate-200 focus:outline-none focus:border-paypal-cyan font-mono"
          >
            {SUBGRAPH_FILTERS.map((f) => (
              <option key={f.id} value={f.id}>
                {f.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Main Canvas & Side Inspector Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: React Flow Interactive Canvas */}
        <div className="lg:col-span-2 h-[680px]">
          <CausalGraphCanvas
            graphData={graphData}
            selectedNodeId={selectedNode?.id}
            onNodeSelect={(node) => setSelectedNode(node)}
            filterType={activeFilter}
          />
        </div>

        {/* Right 1 Col: Node Fact Inspector */}
        <div className="bg-sentinel-card border border-sentinel-border rounded-xl p-5 shadow-lg flex flex-col gap-4 overflow-y-auto max-h-[680px]">
          <div className="flex items-center justify-between border-b border-sentinel-border pb-3">
            <div className="flex items-center gap-2">
              <Network className="w-4 h-4 text-paypal-cyan" />
              <h3 className="text-sm font-bold text-slate-100">Node Fact Inspector</h3>
            </div>
            {selectedNode && (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950/80 text-cyan-300 border border-cyan-800">
                {selectedNode.type}
              </span>
            )}
          </div>

          {selectedNode ? (
            <div className="flex flex-col gap-4">
              {/* Header Info */}
              <div className="flex flex-col gap-1">
                <span className="text-sm font-bold text-white">{selectedNode.label}</span>
                <span className="text-xs font-mono text-slate-400">{selectedNode.id}</span>
              </div>

              {/* SHA-256 Hash Badge & Timestamp */}
              <div className="p-3 bg-sentinel-bg border border-sentinel-border rounded-lg flex flex-col gap-2 text-xs font-mono">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Content Hash:</span>
                  <span className="text-paypal-cyan truncate max-w-[160px]" title={selectedNode.sha256_hash}>
                    {selectedNode.sha256_hash}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Timestamp:</span>
                  <span className="text-slate-300">{new Date(selectedNode.timestamp).toLocaleString()}</span>
                </div>
                <div className="flex items-center gap-1.5 text-emerald-400 text-[11px] pt-1 border-t border-slate-800">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Cryptographically Anchored to Merkle Ledger</span>
                </div>
              </div>

              {/* Inbound & Outbound Relationships */}
              <div className="flex flex-col gap-2">
                <span className="text-xs font-bold text-slate-300 uppercase tracking-wider text-[10px]">
                  Causal Connections
                </span>
                <div className="flex flex-col gap-1 text-[11px] font-mono">
                  {relatedEdges.inbound.length > 0 && (
                    <div className="flex flex-col gap-1">
                      <span className="text-slate-500 text-[10px]">Inbound Causes:</span>
                      {relatedEdges.inbound.map((e) => (
                        <div key={e.id} className="p-1.5 rounded bg-sentinel-bg border border-slate-800 text-slate-300 flex items-center justify-between">
                          <span>{e.source}</span>
                          <span className="text-[10px] text-cyan-400">[{e.type}]</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {relatedEdges.outbound.length > 0 && (
                    <div className="flex flex-col gap-1 mt-1">
                      <span className="text-slate-500 text-[10px]">Outbound Effects:</span>
                      {relatedEdges.outbound.map((e) => (
                        <div key={e.id} className="p-1.5 rounded bg-sentinel-bg border border-slate-800 text-slate-300 flex items-center justify-between">
                          <span>{e.target}</span>
                          <span className="text-[10px] text-emerald-400">[{e.type}]</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {relatedEdges.inbound.length === 0 && relatedEdges.outbound.length === 0 && (
                    <div className="text-slate-500 text-[11px]">No direct edges configured in this view.</div>
                  )}
                </div>
              </div>

              {/* Raw JSON Facts Payload */}
              <div className="flex flex-col gap-1.5">
                <span className="text-xs font-bold text-slate-300 uppercase tracking-wider text-[10px]">
                  Structured Facts Payload
                </span>
                <pre className="p-3 bg-sentinel-bg border border-sentinel-border rounded-lg text-[11px] font-mono text-cyan-300 overflow-x-auto max-h-48 leading-relaxed">
                  {JSON.stringify(selectedNode.data, null, 2)}
                </pre>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-16 text-slate-500 text-xs">
              <Info className="w-5 h-5 mb-2 opacity-50" />
              Click any node in the causal canvas to inspect its structured facts.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
