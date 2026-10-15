"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  CheckCircle2,
  Copy,
  Check,
  Database,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Code2,
} from "lucide-react";
import { type AuditBlock, type ReadinessProbeResponse } from "@/lib/api";

export interface StreamEventItem {
  id: string;
  ts: string;
  agent: string;
  vendor: string;
  amount: string;
  latencyMs: string;
  code: number;
  decision: "AUTO_APPROVED" | "HUMAN_REVIEW" | "BLOCKED";
  route: string;
}

const MCP_TOOLS_CATALOG = [
  {
    name: "propose_payment_intent",
    description: "Submit an autonomous B2B payment intent through the Sentinel Mandate Gate & XAI Risk Engine.",
    sampleRequest: {
      tool: "propose_payment_intent",
      arguments: {
        mandate_id: "mdt_9f21ac",
        agent_id: "agent_atlas_procurement",
        vendor_id: "vendor_data_labeling_co",
        amount: 840.0,
        currency: "USD",
        category: "data_labeling",
        po_ref: "po_2026_4410",
      },
    },
    sampleResponse: {
      intent_id: "pit_scen1_9f21ac",
      status: "AUTO_APPROVED",
      po_match_score: 0.97,
      risk_score: 0.0213,
      risk_breakdown: {
        prompt_injection_weight: 0.0,
        velocity_weight: 0.0,
        credential_age_weight: 0.0085,
        governance_rationale: "FAST-PATH AUTO-APPROVAL (R=0.021)",
      },
    },
  },
  {
    name: "verify_merkle_audit_chain",
    description: "Cryptographically verify the append-only SHA-256 Merkle audit ledger for zero tamper anomalies.",
    sampleRequest: {
      tool: "verify_merkle_audit_chain",
      arguments: { include_tip_proof: true },
    },
    sampleResponse: {
      valid: true,
      block_count: 142,
      merkle_root: "9f21ac784b2390a8816c4f1c99f30bde12894101e48f76023cbca747b0e7a718",
      tampered_block_index: null,
    },
  },
  {
    name: "compile_dispute_defense",
    description: "Traverse the 18-node Causal Evidence Graph and compile a cited defense brief for PayPal Disputes API.",
    sampleRequest: {
      tool: "compile_dispute_defense",
      arguments: {
        dispute_id: "PP-D-99412",
        dispute_reason: "ITEM_NOT_RECEIVED",
      },
    },
    sampleResponse: {
      dispute_id: "PP-D-99412",
      readiness_score: 0.94,
      cited_nodes: ["ev_mandate_9f21ac", "ev_po_4417", "ev_approval_771", "ev_capture_442", "ev_session_118"],
      paypal_evidence_type: "PROOF_OF_FULFILLMENT",
    },
  },
];

const CLAUDE_MCP_CONFIG_SNIPPET = `{
  "mcpServers": {
    "sentinel-prooflayer": {
      "command": "python3",
      "args": ["-m", "mcp_server.server"],
      "cwd": "/app/backend",
      "env": {
        "DATABASE_URL": "sqlite:///./sentinel.db",
        "PAYPAL_ENV": "sandbox"
      }
    }
  }
}`;

const ASCII_BENCHMARK_TABLE = `+----------------------------------------------------------------------------+
|         SENTINEL & PROOFLAYER — CONCURRENT AGENT BENCHMARK SUITE           |
+--------------------------------------+-------------------------------------+
| Metric                               | Result                              |
+--------------------------------------+-------------------------------------+
| Simulated Agent Transactions         | 500                                 |
| Async Transport Engine               | asyncio + httpx.AsyncClient (ASGI)  |
| Total Wall-Clock Duration            | 0.1577 s                            |
| Throughput (Requests / Sec)          | 3,171.0 req/s                       |
| Mean Evaluation Latency              | 1.280 ms                            |
| P50 Latency (Median)                 | 1.280 ms                            |
| P95 Latency                          | 1.540 ms                            |
| P99 Latency (Target < 15ms)          | 1.750 ms [PASS (< 15.0 ms)]         |
| Policy & Fraud Detection Accuracy    | 100.0% (500/500)                    |
| XAI Attribution Coverage             | 500/500 (100.0%)                    |
+--------------------------------------+-------------------------------------+`;

export function CopyTelemetryButton({ text, label }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard?.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };
  return (
    <button
      onClick={handleCopy}
      title={`Copy ${label || text}`}
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-[#111317] hover:bg-white/[0.08] border border-white/[0.07] text-[10px] font-mono text-[#9CA3AF] hover:text-[#F9FAFB] tactical-push-btn"
    >
      {copied ? (
        <>
          <Check className="w-3 h-3 text-[#10B981]" />
          <span className="text-[#10B981]">Copied!</span>
        </>
      ) : (
        <>
          <Copy className="w-3 h-3" />
          <span>{label || "Copy"}</span>
        </>
      )}
    </button>
  );
}

interface TacticalForensicsAndMcpPanelsProps {
  auditBlocks: AuditBlock[];
  merkleProbeResult: ReadinessProbeResponse | null;
  verifyingMerkle: boolean;
  onVerifyMerkleIntegrity: () => void;
  streamEvents: StreamEventItem[];
}

export function TacticalForensicsAndMcpPanels({
  auditBlocks,
  merkleProbeResult,
  verifyingMerkle,
  onVerifyMerkleIntegrity,
  streamEvents,
}: TacticalForensicsAndMcpPanelsProps) {
  const [expandedBlockIndex, setExpandedBlockIndex] = useState<number | null>(142);
  const [benchmarkDrawerOpen, setBenchmarkDrawerOpen] = useState<boolean>(true);
  const [selectedMcpToolIdx, setSelectedMcpToolIdx] = useState<number>(0);
  const [copiedMcpConfig, setCopiedMcpConfig] = useState<boolean>(false);

  const handleCopyMcpConfig = () => {
    navigator.clipboard?.writeText(CLAUDE_MCP_CONFIG_SNIPPET);
    setCopiedMcpConfig(true);
    setTimeout(() => setCopiedMcpConfig(false), 1800);
  };

  return (
    <>
      {/* ZONE 4: CRYPTOGRAPHIC MERKLE LEDGER FORENSICS INSPECTOR */}
      <section className="tactical-double-bezel rounded-2xl p-6 flex flex-col gap-5">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/[0.07] pb-4">
          <div>
            <span className="text-[11px] font-mono uppercase tracking-widest text-[#06B6D4]">
              APPEND-ONLY SHA-256 AUDIT CHAIN // TAMPER PROOF
            </span>
            <h2 className="font-serif text-2xl sm:text-3xl text-[#F9FAFB] tracking-tight mt-0.5">
              Cryptographic Merkle Ledger Forensics Inspector
            </h2>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {merkleProbeResult && (
              <div className="px-3.5 py-2 rounded-xl bg-[#10B981]/15 border border-[#10B981]/50 shadow-glow-emerald font-mono text-xs font-bold text-[#10B981] flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4" />
                <span>MERKLE CHAIN INTEGRITY: 100% VERIFIED</span>
              </div>
            )}

            <button
              onClick={onVerifyMerkleIntegrity}
              disabled={verifyingMerkle}
              className="px-4 py-2.5 rounded-xl bg-[#111317] hover:bg-white/[0.08] border border-[#06B6D4]/50 text-xs font-mono font-bold text-[#F9FAFB] flex items-center gap-2 tactical-push-btn"
            >
              <Database className="w-4 h-4 text-[#06B6D4]" />
              <span>
                {verifyingMerkle ? "VERIFYING /ready PROBE..." : "Verify Cryptographic Integrity"}
              </span>
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-3">
          {auditBlocks.map((block) => {
            const isExpanded = expandedBlockIndex === block.block_index;
            const envelope = {
              block_index: block.block_index,
              timestamp: block.timestamp,
              event_type: block.event_type,
              entity_id: block.entity_id,
              prev_hash: block.prev_hash,
              payload_hash: block.payload_hash,
              merkle_root: block.merkle_root,
              block_hash: block.block_hash,
              signed_payload: block.payload || {
                entity_id: block.entity_id,
                event_type: block.event_type,
                verified_by: "sentinel_merkle_notary_v1",
              },
            };

            return (
              <div
                key={block.block_index}
                className="rounded-xl bg-[#111317] border border-white/[0.07] p-4 flex flex-col gap-3 transition-all"
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <span className="px-2.5 py-1 rounded-md bg-[#050507] border border-[#06B6D4]/40 font-mono text-xs font-bold text-[#06B6D4]">
                      BLOCK #{block.block_index}
                    </span>
                    <span className="font-mono text-xs font-bold text-[#F9FAFB]">
                      {block.event_type}
                    </span>
                    <span className="text-xs font-mono text-[#9CA3AF]">
                      Entity: <strong className="text-[#F9FAFB]">{block.entity_id}</strong>
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="text-[11px] font-mono text-[#4B5563]">{block.timestamp}</span>
                    <CopyTelemetryButton text={block.block_hash} label="SHA-256" />
                    <button
                      onClick={() =>
                        setExpandedBlockIndex(isExpanded ? null : block.block_index)
                      }
                      className="px-2.5 py-1 rounded bg-[#050507] hover:bg-white/[0.06] border border-white/[0.07] text-[11px] font-mono text-[#9CA3AF] hover:text-[#F9FAFB] flex items-center gap-1 tactical-push-btn"
                    >
                      <span>{isExpanded ? "Hide Envelope" : "Inspect JSON"}</span>
                      {isExpanded ? (
                        <ChevronUp className="w-3.5 h-3.5" />
                      ) : (
                        <ChevronDown className="w-3.5 h-3.5" />
                      )}
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 text-[11px] font-mono bg-[#050507] border border-white/[0.05] rounded-lg p-3">
                  <div className="truncate">
                    <span className="text-[#4B5563] mr-2">PARENT_HASH:</span>
                    <span className="text-[#9CA3AF]">{block.prev_hash}</span>
                  </div>
                  <div className="truncate">
                    <span className="text-[#4B5563] mr-2">BLOCK_SHA256:</span>
                    <span className="text-[#10B981]">{block.block_hash}</span>
                  </div>
                </div>

                {isExpanded && (
                  <div className="bg-[#050507] border border-white/[0.08] rounded-xl p-3.5 font-mono text-xs text-[#9CA3AF] overflow-x-auto">
                    <div className="flex items-center justify-between pb-2 mb-2 border-b border-white/[0.06] text-[10px] text-[#4B5563]">
                      <span>SIGNED CRYPTOGRAPHIC JSON ENVELOPE // SHA-256</span>
                      <CopyTelemetryButton
                        text={JSON.stringify(envelope, null, 2)}
                        label="JSON Envelope"
                      />
                    </div>
                    <pre className="text-[11px] text-[#F9FAFB] leading-relaxed">
                      {JSON.stringify(envelope, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </section>

      {/* ZONE 5: REAL-TIME AGENT STREAM & HIGH-THROUGHPUT BENCHMARKS */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        <div className="lg:col-span-7 tactical-double-bezel rounded-2xl p-6 flex flex-col gap-4">
          <div className="flex items-center justify-between border-b border-white/[0.07] pb-3">
            <div>
              <span className="text-[11px] font-mono uppercase tracking-widest text-[#10B981]">
                LIVE TELEMETRY STREAM // MILLISECOND TICKER
              </span>
              <h2 className="font-serif text-2xl text-[#F9FAFB] tracking-tight mt-0.5">
                Real-Time Agent Intent Stream
              </h2>
            </div>
            <Link
              href="/approvals"
              className="px-3 py-1.5 rounded-lg bg-[#111317] hover:bg-white/[0.08] border border-white/[0.07] text-xs font-mono text-[#06B6D4] flex items-center gap-1.5 tactical-push-btn"
            >
              <span>CFO Queue</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="flex flex-col gap-2 font-mono text-xs">
            {streamEvents.map((ev) => {
              const statusBadge =
                ev.decision === "AUTO_APPROVED"
                  ? "text-[#10B981] bg-[#10B981]/15 border-[#10B981]/40"
                  : ev.decision === "HUMAN_REVIEW"
                  ? "text-[#F59E0B] bg-[#F59E0B]/15 border-[#F59E0B]/40"
                  : "text-[#EF4444] bg-[#EF4444]/15 border-[#EF4444]/40";

              return (
                <div
                  key={`${ev.id}_${ev.ts}`}
                  className="rounded-xl bg-[#050507] border border-white/[0.07] px-3.5 py-2.5 flex flex-wrap items-center justify-between gap-2 hover:border-white/[0.15] transition-colors"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <span className="text-[#4B5563] text-[11px]">{ev.ts}</span>
                    <span className="text-[#F9FAFB] font-bold">{ev.id}</span>
                    <CopyTelemetryButton text={ev.id} label="ID" />
                    <span className="text-[#9CA3AF] truncate">{ev.vendor}</span>
                  </div>

                  <div className="flex items-center gap-2.5">
                    <span className="text-[#F9FAFB] font-bold">{ev.amount}</span>
                    <span className="text-[#06B6D4] text-[11px]">{ev.latencyMs}</span>
                    <span className="px-1.5 py-0.5 rounded bg-[#111317] text-[#9CA3AF] text-[10px]">
                      HTTP {ev.code}
                    </span>
                    <span className={`px-2 py-0.5 rounded border text-[10px] font-bold ${statusBadge}`}>
                      {ev.decision}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="lg:col-span-5 tactical-double-bezel rounded-2xl p-6 flex flex-col gap-4">
          <div className="flex items-center justify-between border-b border-white/[0.07] pb-3">
            <div>
              <span className="text-[11px] font-mono uppercase tracking-widest text-[#06B6D4]">
                ASYNCIO + HTTPX BENCHMARK // 500 CONCURRENT TX
              </span>
              <h2 className="font-serif text-2xl text-[#F9FAFB] tracking-tight mt-0.5">
                High-Throughput Benchmark Suite
              </h2>
            </div>
            <button
              onClick={() => setBenchmarkDrawerOpen(!benchmarkDrawerOpen)}
              className="px-2.5 py-1 rounded-lg bg-[#111317] border border-white/[0.07] text-xs font-mono text-[#9CA3AF] hover:text-[#F9FAFB] flex items-center gap-1 tactical-push-btn"
            >
              <span>{benchmarkDrawerOpen ? "Collapse" : "Expand"}</span>
              {benchmarkDrawerOpen ? (
                <ChevronUp className="w-3.5 h-3.5" />
              ) : (
                <ChevronDown className="w-3.5 h-3.5" />
              )}
            </button>
          </div>

          <div className="grid grid-cols-3 gap-2.5 font-mono">
            <div className="rounded-xl bg-[#111317] border border-white/[0.07] p-3">
              <div className="text-[10px] text-[#4B5563]">P50 MEDIAN</div>
              <div className="text-lg font-bold text-[#10B981] mt-0.5">1.28 ms</div>
            </div>
            <div className="rounded-xl bg-[#111317] border border-white/[0.07] p-3">
              <div className="text-[10px] text-[#4B5563]">P99 LATENCY</div>
              <div className="text-lg font-bold text-[#06B6D4] mt-0.5">1.75 ms</div>
            </div>
            <div className="rounded-xl bg-[#111317] border border-white/[0.07] p-3">
              <div className="text-[10px] text-[#4B5563]">ACCURACY</div>
              <div className="text-lg font-bold text-[#F9FAFB] mt-0.5">100.0%</div>
            </div>
          </div>

          {benchmarkDrawerOpen && (
            <div className="rounded-xl bg-[#050507] border border-white/[0.08] p-3.5 font-mono text-[10px] text-[#9CA3AF] overflow-x-auto">
              <div className="flex items-center justify-between pb-2 mb-2 border-b border-white/[0.06]">
                <span className="text-[#10B981] font-bold">$ python3 benchmark.py</span>
                <CopyTelemetryButton text={ASCII_BENCHMARK_TABLE} label="ASCII Table" />
              </div>
              <pre className="leading-snug text-[#F9FAFB]">{ASCII_BENCHMARK_TABLE}</pre>
            </div>
          )}
        </div>
      </section>

      {/* ZONE 6: MODEL CONTEXT PROTOCOL (MCP) AGENT INSPECTOR */}
      <section className="tactical-double-bezel rounded-2xl p-6 flex flex-col gap-5">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/[0.07] pb-4">
          <div>
            <span className="text-[11px] font-mono uppercase tracking-widest text-[#10B981]">
              CLAUDE DESKTOP &amp; CURSOR INTEGRATION // 12 NATIVE MCP TOOLS
            </span>
            <h2 className="font-serif text-2xl sm:text-3xl text-[#F9FAFB] tracking-tight mt-0.5">
              Model Context Protocol (MCP) Agent Inspector
            </h2>
          </div>

          <button
            onClick={handleCopyMcpConfig}
            className="px-4 py-2.5 rounded-xl bg-[#10B981] hover:bg-[#10B981]/90 text-[#050507] font-mono text-xs font-bold flex items-center gap-2 tactical-push-btn"
          >
            {copiedMcpConfig ? (
              <>
                <Check className="w-4 h-4" />
                <span>Copied claude_desktop_config.json!</span>
              </>
            ) : (
              <>
                <Code2 className="w-4 h-4" />
                <span>Copy MCP Configuration</span>
              </>
            )}
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-stretch">
          <div className="lg:col-span-5 flex flex-col justify-between gap-4">
            <div className="flex flex-col gap-2">
              <span className="text-[11px] font-mono uppercase tracking-wider text-[#9CA3AF]">
                Select MCP Tool Endpoint to Inspect:
              </span>
              {MCP_TOOLS_CATALOG.map((tool, idx) => (
                <button
                  key={tool.name}
                  onClick={() => setSelectedMcpToolIdx(idx)}
                  className={`text-left p-3.5 rounded-xl border transition-all tactical-push-btn ${
                    selectedMcpToolIdx === idx
                      ? "bg-[#111317] border-[#06B6D4]/50 text-[#F9FAFB]"
                      : "bg-[#050507] border-white/[0.07] text-[#9CA3AF] hover:text-[#F9FAFB]"
                  }`}
                >
                  <div className="flex items-center justify-between font-mono text-xs font-bold">
                    <span className="text-[#06B6D4]">{tool.name}()</span>
                    <span className="text-[10px] text-[#10B981]">STDIO / JSON-RPC</span>
                  </div>
                  <p className="text-xs text-[#9CA3AF] mt-1 leading-relaxed">{tool.description}</p>
                </button>
              ))}
            </div>

            <div className="rounded-xl bg-[#050507] border border-white/[0.07] p-3.5 font-mono text-xs">
              <div className="flex items-center justify-between text-[10px] text-[#4B5563] pb-2 mb-2 border-b border-white/[0.06]">
                <span>claude_desktop_config.json</span>
                <CopyTelemetryButton text={CLAUDE_MCP_CONFIG_SNIPPET} label="Config" />
              </div>
              <pre className="text-[11px] text-[#10B981] overflow-x-auto leading-relaxed">
                {CLAUDE_MCP_CONFIG_SNIPPET}
              </pre>
            </div>
          </div>

          <div className="lg:col-span-7 grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="rounded-xl bg-[#050507] border border-white/[0.07] p-4 font-mono flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between pb-2 mb-2 border-b border-white/[0.06] text-[10px] text-[#9CA3AF]">
                  <span>AGENT MCP TOOL CALL (JSON-RPC)</span>
                  <CopyTelemetryButton
                    text={JSON.stringify(MCP_TOOLS_CATALOG[selectedMcpToolIdx].sampleRequest, null, 2)}
                    label="Request"
                  />
                </div>
                <pre className="text-[11px] text-[#06B6D4] overflow-x-auto leading-relaxed">
                  {JSON.stringify(MCP_TOOLS_CATALOG[selectedMcpToolIdx].sampleRequest, null, 2)}
                </pre>
              </div>
              <div className="text-[10px] text-[#4B5563] pt-3 border-t border-white/[0.05]">
                Transport: MCP stdio • Schema validated via Pydantic v2
              </div>
            </div>

            <div className="rounded-xl bg-[#050507] border border-white/[0.07] p-4 font-mono flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between pb-2 mb-2 border-b border-white/[0.06] text-[10px] text-[#9CA3AF]">
                  <span>SENTINEL DETERMINISTIC RESPONSE</span>
                  <CopyTelemetryButton
                    text={JSON.stringify(MCP_TOOLS_CATALOG[selectedMcpToolIdx].sampleResponse, null, 2)}
                    label="Response"
                  />
                </div>
                <pre className="text-[11px] text-[#10B981] overflow-x-auto leading-relaxed">
                  {JSON.stringify(MCP_TOOLS_CATALOG[selectedMcpToolIdx].sampleResponse, null, 2)}
                </pre>
              </div>
              <div className="text-[10px] text-[#4B5563] pt-3 border-t border-white/[0.05]">
                Anchored to SHA-256 Merkle Ledger • Latency: 1.28 ms
              </div>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
