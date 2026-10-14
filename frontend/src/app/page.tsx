"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
  ShieldCheck,
  TrendingUp,
  AlertTriangle,
  Play,
  CheckCircle2,
  Lock,
  ArrowRight,
  Clock,
  Layers,
  FileCheck,
  ExternalLink,
  ChevronRight,
  Database,
  Cpu,
  Sparkles,
} from "lucide-react";
import {
  api,
  type PaymentIntent,
  type RiskAttributionWeights,
  type ScenarioRunResult,
  SEEDED_INTENTS,
} from "@/lib/api";
import { StatusBadgeRenderer, RiskGaugeRenderer } from "@/components/AgGridGovernanceTable";

const DEFAULT_SCENARIO_XAI: Record<number, RiskAttributionWeights> = {
  1: {
    prompt_injection_weight: 0.0,
    velocity_weight: 0.0,
    credential_age_weight: 0.0085,
    vendor_allowlist_weight: 0.0,
    amount_cap_weight: 0.0168,
    governance_rationale:
      "FAST-PATH AUTO-APPROVAL (R=0.021): Allowlisted vendor 'vendor_data_labeling_co' within $1,000.00 auto-ceiling with clean telemetry [prompt_injection_weight=0.000, velocity_weight=0.000, credential_age_weight=0.009].",
  },
  2: {
    prompt_injection_weight: 0.0,
    velocity_weight: 0.0,
    credential_age_weight: 0.011,
    vendor_allowlist_weight: 0.0,
    amount_cap_weight: 0.1754,
    governance_rationale:
      "CFO ESCALATION (R=0.182): Verified vendor 'vendor_cloud_compute' passed injection & velocity screens, but amount $4,180.50 exceeds $1,000.00 auto-limit (amount_cap_weight=0.175). Parked in HUMAN_REVIEW.",
  },
  3: {
    prompt_injection_weight: 0.28,
    velocity_weight: 0.0,
    credential_age_weight: 0.28,
    vendor_allowlist_weight: 0.3,
    category_policy_weight: 0.15,
    governance_rationale:
      "HARD BLOCK (R=0.675): Counterparty 'vendor_fastcrypto' and category 'crypto' violate mandate guardrails [prompt_injection_weight=0.280, credential_age_weight=0.280, category_policy_weight=0.150]. Zero PayPal calls.",
  },
  4: {
    prompt_injection_weight: 0.0,
    velocity_weight: 0.0,
    credential_age_weight: 0.011,
    vendor_allowlist_weight: 0.0,
    amount_cap_weight: 0.1754,
    governance_rationale:
      "CAUSAL AUTO-DEFENSE (Readiness=0.940): Pre-payment XAI attribution anchored to 18-node causal graph with 100% [ev_*] inline citations and digital session telemetry [ev_session_118].",
  },
};

function XaiAttributionBlock({
  scenarioId,
  result,
}: {
  scenarioId: 1 | 2 | 3 | 4;
  result?: ScenarioRunResult;
}) {
  const xai = result?.risk_breakdown || DEFAULT_SCENARIO_XAI[scenarioId];
  const rationale =
    result?.governance_rationale ||
    xai?.governance_rationale ||
    DEFAULT_SCENARIO_XAI[scenarioId].governance_rationale;

  return (
    <div className="bg-slate-950/70 border border-slate-800/90 rounded-lg p-2.5 text-[10px] font-mono flex flex-col gap-1.5">
      <div className="flex items-center justify-between text-slate-300 font-semibold border-b border-slate-800/80 pb-1">
        <span>Explainable AI Risk Attribution</span>
        <span className="text-paypal-cyan">XAI Weights</span>
      </div>
      <div className="grid grid-cols-3 gap-1.5 text-[10px]">
        <div className="bg-slate-900/90 rounded px-1.5 py-1 border border-slate-800/70">
          <div className="text-slate-500 text-[9px]">prompt_inj</div>
          <div className="text-slate-200 font-bold">
            {(xai?.prompt_injection_weight ?? 0).toFixed(3)}
          </div>
        </div>
        <div className="bg-slate-900/90 rounded px-1.5 py-1 border border-slate-800/70">
          <div className="text-slate-500 text-[9px]">velocity</div>
          <div className="text-slate-200 font-bold">
            {(xai?.velocity_weight ?? 0).toFixed(3)}
          </div>
        </div>
        <div className="bg-slate-900/90 rounded px-1.5 py-1 border border-slate-800/70">
          <div className="text-slate-500 text-[9px]">cred_age</div>
          <div className="text-slate-200 font-bold">
            {(xai?.credential_age_weight ?? 0).toFixed(3)}
          </div>
        </div>
      </div>
      {rationale && (
        <div className="text-[10px] font-sans text-slate-400 leading-snug pt-0.5">
          {rationale}
        </div>
      )}
    </div>
  );
}

export default function ExecutiveCommandCenterPage() {
  const [runningScenarioId, setRunningScenarioId] = useState<number | null>(null);
  const [scenarioResults, setScenarioResults] = useState<Record<number, ScenarioRunResult>>({});
  const [cfoApprovedS2, setCfoApprovedS2] = useState(false);
  const [intents, setIntents] = useState<PaymentIntent[]>(SEEDED_INTENTS);

  useEffect(() => {
    async function loadInitial() {
      try {
        const data = await api.getIntents();
        setIntents(data);
      } catch (err) {
        console.error("Failed to fetch intents:", err);
      }
    }
    loadInitial();
  }, []);

  const handleRunScenario = async (id: 1 | 2 | 3 | 4) => {
    setRunningScenarioId(id);
    try {
      const res = await api.runScenario(id);
      setScenarioResults((prev) => ({ ...prev, [id]: res }));
      if (id === 2) setCfoApprovedS2(false);
    } catch (err) {
      console.error(`Error running Scenario ${id}:`, err);
    } finally {
      setRunningScenarioId(null);
    }
  };

  const handleCFOApproveScenario2 = async () => {
    try {
      await api.approveIntent("int_2026_0918", "usr_maya");
      setCfoApprovedS2(true);
      setScenarioResults((prev) => {
        const existing = prev[2];
        if (!existing) return prev;
        return {
          ...prev,
          2: {
            ...existing,
            final_state: "RECONCILED",
            execution_steps: [
              ...existing.execution_steps,
              {
                step: "CFO_MFA_APPROVAL",
                state: "APPROVED",
                timestamp: "00:01.2",
                detail: "CFO Maya signed approval with MFA (idempotency key locked)",
              },
              {
                step: "PAYPAL_CAPTURE",
                state: "CAPTURED",
                timestamp: "00:01.8",
                detail: "PayPal Capture 2GG279541U053982Y confirmed ($4,180.50 USD)",
              },
              {
                step: "RECONCILIATION",
                state: "RECONCILED",
                timestamp: "00:02.1",
                detail: "Reconciliation complete. Merkle Block #141 anchored.",
              },
            ],
          },
        };
      });
    } catch (err) {
      console.error("CFO approval failed:", err);
    }
  };

  return (
    <div className="flex flex-col gap-8 max-w-7xl mx-auto">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-gradient-to-r from-sentinel-card via-sentinel-card to-sentinel-elevated border border-sentinel-border p-6 rounded-2xl shadow-xl">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded text-[11px] font-mono font-bold bg-paypal-cyan/20 text-paypal-cyan border border-paypal-cyan/40">
              MANDATE CONTROL PLANE & CAUSAL EVIDENCE GRAPH
            </span>
            <span className="text-slate-500 text-xs">•</span>
            <span className="text-xs text-slate-400 font-mono">PayPal AI Hackathon 2026</span>
          </div>
          <h1 className="text-2xl font-black text-white tracking-tight">
            Executive Governance Command Center
          </h1>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl">
            Autonomous agent financial guardrails before payment execution, and cryptographic causal evidence defense after execution.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/disputes"
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-sentinel-elevated hover:bg-slate-700 text-xs font-semibold text-slate-200 border border-sentinel-border transition-colors"
          >
            <span>Active Disputes (1)</span>
            <ChevronRight className="w-4 h-4 text-slate-400" />
          </Link>
          <Link
            href="/mandates"
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-gradient-to-r from-paypal-blue to-paypal-cyan hover:opacity-95 text-xs font-bold text-white shadow-lg shadow-paypal-blue/30 transition-opacity"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Open Mandate Studio</span>
          </Link>
        </div>
      </div>

      {/* Top Row — 5 Core Institutional KPI Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <div className="bg-sentinel-card border border-sentinel-border rounded-xl p-4 flex flex-col justify-between shadow-md">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>Spend Governed</span>
            <TrendingUp className="w-4 h-4 text-paypal-cyan" />
          </div>
          <div className="mt-2">
            <div className="text-xl font-bold font-mono text-white">$428,910</div>
            <div className="text-[11px] text-emerald-400 font-medium mt-0.5">+$5,020.50 Today</div>
          </div>
          <div className="text-[10px] text-slate-500 mt-2 border-t border-slate-800 pt-1.5">
            100% within mandate caps
          </div>
        </div>

        <div className="bg-sentinel-card border border-sentinel-border rounded-xl p-4 flex flex-col justify-between shadow-md">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>Auto-Approval Rate</span>
            <Cpu className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="mt-2">
            <div className="text-xl font-bold font-mono text-emerald-400">84.2%</div>
            <div className="text-[11px] text-slate-400 font-medium mt-0.5">15.8% Escalated to CFO</div>
          </div>
          <div className="text-[10px] text-slate-500 mt-2 border-t border-slate-800 pt-1.5">
            Target SLA &lt; 20% review burden
          </div>
        </div>

        <div className="bg-sentinel-card border border-sentinel-border rounded-xl p-4 flex flex-col justify-between shadow-md">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>Active Mandate</span>
            <ShieldCheck className="w-4 h-4 text-paypal-cyan" />
          </div>
          <div className="mt-2">
            <div className="text-lg font-bold font-mono text-slate-100">mdt_9f21ac</div>
            <div className="text-[11px] text-slate-400 font-medium mt-0.5">Auto $1k • Cap $5k</div>
          </div>
          <div className="text-[10px] text-emerald-400 mt-2 border-t border-slate-800 pt-1.5">
            Agent Atlas Authorized
          </div>
        </div>

        <div className="bg-sentinel-card border border-sentinel-border rounded-xl p-4 flex flex-col justify-between shadow-md">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>Evidence Readiness</span>
            <FileCheck className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="mt-2">
            <div className="text-xl font-bold font-mono text-cyan-400">94.0%</div>
            <div className="text-[11px] text-slate-400 font-medium mt-0.5">6 Quality Dimensions</div>
          </div>
          <div className="text-[10px] text-slate-500 mt-2 border-t border-slate-800 pt-1.5">
            Auto-defense generation armed
          </div>
        </div>

        <div className="bg-sentinel-card border border-sentinel-border rounded-xl p-4 flex flex-col justify-between shadow-md">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>Merkle Chain Tip</span>
            <Database className="w-4 h-4 text-purple-400" />
          </div>
          <div className="mt-2">
            <div className="text-xl font-bold font-mono text-purple-300">#142</div>
            <div className="text-[11px] text-emerald-400 font-medium mt-0.5">VERIFIED TAMPER-PROOF</div>
          </div>
          <div className="text-[10px] text-slate-500 mt-2 border-t border-slate-800 pt-1.5">
            SHA-256 Hash Chained
          </div>
        </div>
      </div>

      {/* Middle Section — 1-Click Judge Scenario Runner (Scenarios 1–4) */}
      <div className="flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Play className="w-4 h-4 text-paypal-cyan fill-current" />
            <h2 className="text-base font-bold text-white tracking-tight">
              1-Click Judge Interactive Evaluation Runner
            </h2>
          </div>
          <span className="text-xs text-slate-400">
            Click any scenario to simulate deterministic state machine execution &amp; XAI risk attribution:
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Card 1: Scenario 1 */}
          <div className="bg-sentinel-card border border-sentinel-border rounded-xl p-5 flex flex-col justify-between gap-4 shadow-lg hover:border-paypal-cyan/50 transition-all">
            <div className="flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-950/80 text-emerald-300 border border-emerald-800">
                  SCENARIO 1
                </span>
                <span className="font-mono text-xs font-bold text-slate-200">$840.00 USD</span>
              </div>
              <h3 className="text-sm font-bold text-slate-100">Auto-Approved Procurement</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Data Labeling Co. PO match score 0.97. Seamless progression through auto-approval, PayPal capture, and reconciliation.
              </p>
              <XaiAttributionBlock scenarioId={1} result={scenarioResults[1]} />
            </div>

            <div className="flex flex-col gap-2 pt-2 border-t border-sentinel-border">
              <button
                onClick={() => handleRunScenario(1)}
                disabled={runningScenarioId === 1}
                className="w-full py-2 px-3 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-bold transition-colors flex items-center justify-center gap-1.5 disabled:opacity-50"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                {runningScenarioId === 1 ? "Executing..." : "Execute Scenario 1"}
              </button>

              {scenarioResults[1] && (
                <div className="p-2.5 bg-emerald-950/40 border border-emerald-800/80 rounded-lg text-[11px] font-mono text-emerald-300 flex flex-col gap-1">
                  <div className="font-bold flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3 text-emerald-400" /> State: {scenarioResults[1].final_state}
                  </div>
                  <div className="text-slate-400 text-[10px]">
                    PayPal Capture: 2GG279541U053982Y
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Card 2: Scenario 2 */}
          <div className="bg-sentinel-card border border-sentinel-border rounded-xl p-5 flex flex-col justify-between gap-4 shadow-lg hover:border-amber-500/50 transition-all">
            <div className="flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-950/80 text-amber-300 border border-amber-800">
                  SCENARIO 2
                </span>
                <span className="font-mono text-xs font-bold text-slate-200">$4,180.50 USD</span>
              </div>
              <h3 className="text-sm font-bold text-slate-100">High-Value CFO Escalation</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Cloud Compute Inc. Variance 0.73% &lt;= 2%. Over $1,000 threshold. Parks in HUMAN_REVIEW until CFO Maya approves.
              </p>
              <XaiAttributionBlock scenarioId={2} result={scenarioResults[2]} />
            </div>

            <div className="flex flex-col gap-2 pt-2 border-t border-sentinel-border">
              <button
                onClick={() => handleRunScenario(2)}
                disabled={runningScenarioId === 2}
                className="w-full py-2 px-3 bg-amber-600 hover:bg-amber-500 text-white rounded-lg text-xs font-bold transition-colors flex items-center justify-center gap-1.5 disabled:opacity-50"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                {runningScenarioId === 2 ? "Evaluating..." : "Execute Scenario 2"}
              </button>

              {scenarioResults[2] && (
                <div className="p-2.5 bg-amber-950/40 border border-amber-800/80 rounded-lg text-[11px] font-mono text-amber-300 flex flex-col gap-2">
                  <div className="font-bold flex items-center gap-1">
                    <Clock className="w-3 h-3 text-amber-400" /> State: {scenarioResults[2].final_state}
                  </div>
                  {!cfoApprovedS2 && scenarioResults[2].final_state === "HUMAN_REVIEW" ? (
                    <button
                      onClick={handleCFOApproveScenario2}
                      className="w-full py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-[11px] font-bold transition-colors flex items-center justify-center gap-1"
                    >
                      <Lock className="w-3 h-3" /> Approve as CFO Maya
                    </button>
                  ) : (
                    <div className="text-emerald-400 text-[10px] font-bold flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3" /> Approved &amp; Captured by CFO Maya
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Card 3: Scenario 3 */}
          <div className="bg-sentinel-card border border-sentinel-border rounded-xl p-5 flex flex-col justify-between gap-4 shadow-lg hover:border-rose-500/50 transition-all">
            <div className="flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-rose-950/80 text-rose-300 border border-rose-800">
                  SCENARIO 3
                </span>
                <span className="font-mono text-xs font-bold text-slate-200">$2,500.00 USD</span>
              </div>
              <h3 className="text-sm font-bold text-slate-100">Out-of-Policy Blocked Vendor</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                FastCrypto Services. Non-allowlisted + &apos;crypto&apos; blocked category. Instantly transitions to BLOCKED with 0 PayPal calls.
              </p>
              <XaiAttributionBlock scenarioId={3} result={scenarioResults[3]} />
            </div>

            <div className="flex flex-col gap-2 pt-2 border-t border-sentinel-border">
              <button
                onClick={() => handleRunScenario(3)}
                disabled={runningScenarioId === 3}
                className="w-full py-2 px-3 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-xs font-bold transition-colors flex items-center justify-center gap-1.5 disabled:opacity-50"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                {runningScenarioId === 3 ? "Blocking..." : "Execute Scenario 3"}
              </button>

              {scenarioResults[3] && (
                <div className="p-2.5 bg-rose-950/40 border border-rose-800/80 rounded-lg text-[11px] font-mono text-rose-300 flex flex-col gap-1">
                  <div className="font-bold flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3 text-rose-400" /> State: {scenarioResults[3].final_state}
                  </div>
                  <div className="text-slate-400 text-[10px]">
                    0 PayPal API calls executed
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Card 4: Scenario 4 */}
          <div className="bg-sentinel-card border border-sentinel-border rounded-xl p-5 flex flex-col justify-between gap-4 shadow-lg hover:border-paypal-blue/50 transition-all">
            <div className="flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-cyan-950/80 text-cyan-300 border border-cyan-800">
                  SCENARIO 4
                </span>
                <span className="font-mono text-xs font-bold text-slate-200">PP-D-99412</span>
              </div>
              <h3 className="text-sm font-bold text-slate-100">Dispute Auto-Defense Engine</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Webhook ingestion, 18-node Causal Graph synthesis, Readiness 0.94, and compiled defense brief with bracketed citations.
              </p>
              <XaiAttributionBlock scenarioId={4} result={scenarioResults[4]} />
            </div>

            <div className="flex flex-col gap-2 pt-2 border-t border-sentinel-border">
              <button
                onClick={() => handleRunScenario(4)}
                disabled={runningScenarioId === 4}
                className="w-full py-2 px-3 bg-paypal-blue hover:bg-sky-600 text-white rounded-lg text-xs font-bold transition-colors flex items-center justify-center gap-1.5 disabled:opacity-50"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                {runningScenarioId === 4 ? "Synthesizing..." : "Execute Scenario 4"}
              </button>

              {scenarioResults[4] && (
                <div className="p-2.5 bg-cyan-950/40 border border-cyan-800/80 rounded-lg text-[11px] font-mono text-cyan-300 flex flex-col gap-1">
                  <div className="font-bold flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3 text-cyan-400" /> State: {scenarioResults[4].final_state}
                  </div>
                  <div className="text-slate-400 text-[10px]">
                    Readiness: 0.94 • 7 [ev_*] citations
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Real-Time Agent Activity & Audit Feed */}
      <div className="bg-sentinel-card border border-sentinel-border rounded-xl p-5 shadow-lg flex flex-col gap-4">
        <div className="flex items-center justify-between border-b border-sentinel-border pb-3">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-paypal-cyan" />
            <h3 className="text-sm font-bold text-slate-100">Live Agent Intent Stream</h3>
          </div>
          <Link
            href="/approvals"
            className="text-xs text-paypal-cyan hover:underline flex items-center gap-1"
          >
            <span>View Full Approval Queue</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-sentinel-border text-slate-400 font-mono text-[11px] uppercase">
                <th className="pb-2">Intent ID</th>
                <th className="pb-2">Agent</th>
                <th className="pb-2">Vendor</th>
                <th className="pb-2">Amount</th>
                <th className="pb-2">PO Match (M)</th>
                <th className="pb-2">Risk (R)</th>
                <th className="pb-2">Status</th>
                <th className="pb-2 text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 font-mono">
              {intents.map((intent) => (
                <tr key={intent.id} className="hover:bg-sentinel-elevated/50 transition-colors">
                  <td className="py-3 font-semibold text-slate-200">{intent.id}</td>
                  <td className="py-3 text-slate-400">{intent.agent_id}</td>
                  <td className="py-3 font-sans text-slate-200">{intent.vendor_name}</td>
                  <td className="py-3 text-slate-100 font-bold">${intent.amount.toFixed(2)}</td>
                  <td className="py-3">
                    <span className="text-emerald-400 font-bold">{intent.matching.score.toFixed(2)}</span>
                    <span className="text-[10px] text-slate-500 ml-1">({intent.matching.variance_pct}% var)</span>
                  </td>
                  <td className="py-3 w-32">
                    <RiskGaugeRenderer value={intent.risk.score} />
                  </td>
                  <td className="py-3">
                    <StatusBadgeRenderer value={intent.status} />
                  </td>
                  <td className="py-3 text-right">
                    <Link
                      href="/approvals"
                      className="p-1 rounded bg-sentinel-elevated hover:bg-slate-700 text-slate-300 inline-flex items-center"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
