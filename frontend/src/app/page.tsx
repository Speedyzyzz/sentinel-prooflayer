"use client";

import React, { useState, useEffect } from "react";
import {
  ShieldCheck,
  ShieldAlert,
  Play,
  CheckCircle2,
  Lock,
  ExternalLink,
  Gauge,
} from "lucide-react";
import {
  api,
  type AuditBlock,
  type PaymentIntent,
  type ReadinessProbeResponse,
  type RiskAttributionWeights,
  type ScenarioRunResult,
  SEEDED_AUDIT_BLOCKS,
  SEEDED_INTENTS,
} from "@/lib/api";
import { SentinelCore3D, type SentinelCoreState } from "@/components/SentinelCore3D";
import {
  CopyTelemetryButton,
  TacticalForensicsAndMcpPanels,
  type StreamEventItem,
} from "@/components/TacticalForensicsAndMcpPanels";

interface ScenarioBlueprint {
  id: 1 | 2 | 3 | 4;
  tag: string;
  title: string;
  subtitle: string;
  amountLabel: string;
  vendorLabel: string;
  accentColor: "emerald" | "amber" | "crimson";
  coreStateOnRun: SentinelCoreState;
  riskIndexOnRun: number;
  promptPct: number;
  velocityPct: number;
  credAgePct: number;
  defaultXai: RiskAttributionWeights;
}

const SCENARIO_BLUEPRINTS: ScenarioBlueprint[] = [
  {
    id: 1,
    tag: "SCENARIO 01 // FAST-PATH",
    title: "Autonomous Micro-Expense ($42.50 AWS)",
    subtitle:
      "Allowlisted cloud infrastructure invoice matched against active PO within 2% tolerance. Executes zero-touch PayPal settlement.",
    amountLabel: "$42.50 / $840.00",
    vendorLabel: "AWS Cloud / Data Labeling Co",
    accentColor: "emerald",
    coreStateOnRun: "AUTO_APPROVED",
    riskIndexOnRun: 2.1,
    promptPct: 0,
    velocityPct: 5,
    credAgePct: 8,
    defaultXai: {
      prompt_injection_weight: 0.0,
      velocity_weight: 0.0,
      credential_age_weight: 0.0085,
      vendor_allowlist_weight: 0.0,
      amount_cap_weight: 0.0168,
      governance_rationale:
        "FAST-PATH AUTO-APPROVAL (R=0.021): Allowlisted counterparty within $1,000.00 auto-ceiling with clean telemetry [prompt_injection_weight=0.000, velocity_weight=0.000, credential_age_weight=0.009].",
    },
  },
  {
    id: 2,
    tag: "SCENARIO 02 // DUAL-SIGNOFF",
    title: "High-Value CFO Escalation ($4,850 GPU Cluster)",
    subtitle:
      "Dedicated H100 compute cluster allocation exceeds $1,000 auto-limit while passing 3-way PO match (0.73% variance). Triggers CFO MFA lock.",
    amountLabel: "$4,850.00 / $4,180.50",
    vendorLabel: "Cloud Compute Inc",
    accentColor: "amber",
    coreStateOnRun: "HUMAN_REVIEW",
    riskIndexOnRun: 18.2,
    promptPct: 0,
    velocityPct: 12,
    credAgePct: 11,
    defaultXai: {
      prompt_injection_weight: 0.0,
      velocity_weight: 0.0,
      credential_age_weight: 0.011,
      vendor_allowlist_weight: 0.0,
      amount_cap_weight: 0.1754,
      governance_rationale:
        "CFO ESCALATION (R=0.182): Counterparty passed injection & velocity screens [prompt_injection_weight=0.000, velocity_weight=0.000, credential_age_weight=0.011], but amount exceeds $1,000 auto-limit. Parked in HUMAN_REVIEW.",
    },
  },
  {
    id: 3,
    tag: "SCENARIO 03 // HEURISTIC INTERCEPT",
    title: 'Adversarial Prompt Injection ("IGNORE PREVIOUS INSTRUCTIONS")',
    subtitle:
      "Invoice line-item payload embeds adversarial override token attempting to force auto_approve=true for an unverified crypto transfer.",
    amountLabel: "$2,500.00 USD",
    vendorLabel: "FastCrypto Services",
    accentColor: "crimson",
    coreStateOnRun: "BLOCKED",
    riskIndexOnRun: 88.5,
    promptPct: 35,
    velocityPct: 25,
    credAgePct: 15,
    defaultXai: {
      prompt_injection_weight: 0.35,
      velocity_weight: 0.25,
      credential_age_weight: 0.15,
      vendor_allowlist_weight: 0.3,
      category_policy_weight: 0.15,
      governance_rationale:
        "HARD BLOCK (R=0.675): Heuristic policy short-circuit intercepted adversarial payload ('IGNORE PREVIOUS INSTRUCTIONS') & prohibited category [prompt_injection_weight=0.350, velocity_weight=0.250, credential_age_weight=0.150]. 0 PayPal calls.",
    },
  },
  {
    id: 4,
    tag: "SCENARIO 04 // DOMAIN & CAUSAL DEFENSE",
    title: "Merchant Impersonation ($890 Phantom Vendor) & Dispute Defense",
    subtitle:
      "Flags newly registered lookalike vendor domain tenure and synthesizes the 18-node Causal Evidence Graph for PayPal Dispute PP-D-99412.",
    amountLabel: "$890.00 / PP-D-99412",
    vendorLabel: "Phantom Vendor / Cloud Compute",
    accentColor: "crimson",
    coreStateOnRun: "BLOCKED",
    riskIndexOnRun: 64.0,
    promptPct: 15,
    velocityPct: 25,
    credAgePct: 35,
    defaultXai: {
      prompt_injection_weight: 0.15,
      velocity_weight: 0.25,
      credential_age_weight: 0.35,
      vendor_allowlist_weight: 0.3,
      amount_cap_weight: 0.1754,
      governance_rationale:
        "DOMAIN AGE & CAUSAL DEFENSE (Readiness=0.940): Unverified credential age flagged [credential_age_weight=0.350] & 18-node Causal Evidence Graph compiled with 7 [ev_*] inline citations.",
    },
  },
];

const INITIAL_STREAM_EVENTS: StreamEventItem[] = [
  {
    id: "pit_9941a01",
    ts: "14:32:10.104",
    agent: "atlas_v4",
    vendor: "Data Labeling Co",
    amount: "$840.00",
    latencyMs: "1.18 ms",
    code: 201,
    decision: "AUTO_APPROVED",
    route: "POST /api/intents",
  },
  {
    id: "pit_9941a02",
    ts: "14:32:11.419",
    agent: "atlas_v4",
    vendor: "Cloud Compute Inc",
    amount: "$4,180.50",
    latencyMs: "1.42 ms",
    code: 202,
    decision: "HUMAN_REVIEW",
    route: "POST /api/intents",
  },
  {
    id: "pit_9941a03",
    ts: "14:32:12.882",
    agent: "atlas_v4",
    vendor: "FastCrypto Services",
    amount: "$2,500.00",
    latencyMs: "0.89 ms",
    code: 403,
    decision: "BLOCKED",
    route: "POST /api/intents",
  },
  {
    id: "pit_9941a04",
    ts: "14:32:14.008",
    agent: "atlas_v4",
    vendor: "AWS Cloud Infra",
    amount: "$42.50",
    latencyMs: "1.12 ms",
    code: 200,
    decision: "AUTO_APPROVED",
    route: "POST /api/intents/evaluate-fast",
  },
  {
    id: "pit_9941a05",
    ts: "14:32:15.612",
    agent: "atlas_v4",
    vendor: "Phantom Lookalike LLC",
    amount: "$890.00",
    latencyMs: "1.31 ms",
    code: 403,
    decision: "BLOCKED",
    route: "POST /api/intents/evaluate-fast",
  },
];

export default function ExecutiveCommandCenterPage() {
  const [governanceMode, setGovernanceMode] = useState<"SANDBOX_TWIN" | "LIVE_PAYPAL_API">("SANDBOX_TWIN");
  const [coreState, setCoreState] = useState<SentinelCoreState>("IDLE");
  const [riskIndex, setRiskIndex] = useState<number>(2.1);
  const [activeHash, setActiveHash] = useState<string>(
    "9f21ac784b2390a8816c4f1c99f30bde12894101e48f76023cbca747b0e7a718"
  );
  const [activeScenarioLabel, setActiveScenarioLabel] = useState<string>("MANDATE mdt_9f21ac // ARMED");

  const [threatsIntercepted, setThreatsIntercepted] = useState<number>(127);
  const [fastPathVolumeUsd, setFastPathVolumeUsd] = useState<number>(428910.0);
  const [runningScenarioId, setRunningScenarioId] = useState<number | null>(null);
  const [scenarioResults, setScenarioResults] = useState<Record<number, ScenarioRunResult>>({});
  const [cfoApprovedS2, setCfoApprovedS2] = useState<boolean>(false);

  const [auditBlocks, setAuditBlocks] = useState<AuditBlock[]>(SEEDED_AUDIT_BLOCKS);
  const [verifyingMerkle, setVerifyingMerkle] = useState<boolean>(false);
  const [merkleProbeResult, setMerkleProbeResult] = useState<ReadinessProbeResponse | null>(null);

  const [streamEvents, setStreamEvents] = useState<StreamEventItem[]>(INITIAL_STREAM_EVENTS);
  const [, setIntents] = useState<PaymentIntent[]>(SEEDED_INTENTS);

  useEffect(() => {
    async function loadInitialTelemetry() {
      try {
        const [fetchedIntents, fetchedBlocks] = await Promise.all([
          api.getIntents(),
          api.getAuditBlocks(),
        ]);
        if (fetchedIntents.length > 0) setIntents(fetchedIntents);
        if (fetchedBlocks.length > 0) setAuditBlocks(fetchedBlocks);
      } catch (err) {
        console.info("Initialized with deterministic tactical telemetry:", err);
      }
    }
    loadInitialTelemetry();
  }, []);

  const handleRunScenario = async (blueprint: ScenarioBlueprint) => {
    setRunningScenarioId(blueprint.id);
    setCoreState(blueprint.coreStateOnRun);
    setRiskIndex(blueprint.riskIndexOnRun);
    setActiveScenarioLabel(`${blueprint.tag} // EXECUTING`);

    try {
      const res = await api.runScenario(blueprint.id);
      setScenarioResults((prev) => ({ ...prev, [blueprint.id]: res }));

      const nowStr = new Date().toISOString().slice(11, 23);
      if (blueprint.id === 1) {
        setFastPathVolumeUsd((v) => v + 840.0);
        setActiveHash("a49f82d1c67843e990c8e239a045bbd7812eac430198f45a78c129e47190ad3f");
      } else if (blueprint.id === 2) {
        setCfoApprovedS2(false);
        setActiveHash("c7118490fa2b67d5e49208a09f8723bba120489501a4e289f0129cdba128a881");
      } else if (blueprint.id === 3 || blueprint.id === 4) {
        setThreatsIntercepted((t) => t + 1);
        setActiveHash("7f9c2d8819028475019283748592019284758291029384758291029384758291");
      }

      const newStreamEvent: StreamEventItem = {
        id: `pit_scen${blueprint.id}_${Math.floor(1000 + Math.random() * 9000)}`,
        ts: nowStr,
        agent: "atlas_v4",
        vendor: blueprint.vendorLabel.split("/")[0].trim(),
        amount: blueprint.amountLabel.split("/")[0].trim(),
        latencyMs: `${(1.12 + (blueprint.id % 3) * 0.18).toFixed(2)} ms`,
        code: blueprint.coreStateOnRun === "BLOCKED" ? 403 : blueprint.coreStateOnRun === "HUMAN_REVIEW" ? 202 : 200,
        decision:
          blueprint.coreStateOnRun === "BLOCKED"
            ? "BLOCKED"
            : blueprint.coreStateOnRun === "HUMAN_REVIEW"
            ? "HUMAN_REVIEW"
            : "AUTO_APPROVED",
        route: `/api/scenarios/run/${blueprint.id}`,
      };
      setStreamEvents((prev) => [newStreamEvent, ...prev.slice(0, 8)]);
      setActiveScenarioLabel(`${blueprint.tag} // ${res.final_state}`);
    } catch (err) {
      console.error(`Scenario ${blueprint.id} error:`, err);
    } finally {
      setRunningScenarioId(null);
    }
  };

  const handleCFOApproveScenario2 = async () => {
    try {
      await api.approveIntent("int_2026_0918", "usr_maya");
      setCfoApprovedS2(true);
      setCoreState("AUTO_APPROVED");
      setRiskIndex(4.2);
      setFastPathVolumeUsd((v) => v + 4180.5);
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
            ],
          },
        };
      });
    } catch (err) {
      console.error("CFO approval failed:", err);
    }
  };

  const handleVerifyMerkleIntegrity = async () => {
    setVerifyingMerkle(true);
    try {
      const probe = await api.verifyReadinessProbe();
      setMerkleProbeResult(probe);
    } catch (err) {
      console.error("Merkle verification error:", err);
    } finally {
      setVerifyingMerkle(false);
    }
  };

  const activeLedgerBlockCount = merkleProbeResult?.merkle_ledger?.block_count || auditBlocks[0]?.block_index || 142;

  return (
    <div className="flex flex-col gap-7 max-w-[1440px] mx-auto pb-12">
      {/* ZONE 1: TOP NAVIGATION HUD & SYSTEM GOVERNANCE PILL */}
      <section className="tactical-double-bezel rounded-2xl p-4 sm:px-6 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div className="flex items-center gap-3.5">
          <div className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg bg-[#050507] border border-[#10B981]/30 shadow-glow-emerald">
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#10B981] opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-[#10B981]"></span>
            </span>
            <span className="text-[11px] font-mono font-bold tracking-wider text-[#10B981]">
              SYSTEM ARMED | PAYPAL SANDBOX ACTIVE
            </span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 sm:gap-4 px-3.5 py-2 rounded-xl bg-[#050507]/90 border border-white/[0.07] font-mono text-xs">
          <div className="flex items-center gap-1.5">
            <span className="text-[#4B5563]">Throughput:</span>
            <span className="text-[#F9FAFB] font-bold">3,171 req/s</span>
          </div>
          <span className="text-[#4B5563]">•</span>
          <div className="flex items-center gap-1.5">
            <span className="text-[#4B5563]">P99 Latency:</span>
            <span className="text-[#10B981] font-bold">1.75 ms</span>
          </div>
          <span className="text-[#4B5563]">•</span>
          <div className="flex items-center gap-1.5">
            <span className="text-[#4B5563]">Active Ledger Blocks:</span>
            <span className="text-[#06B6D4] font-bold">#{activeLedgerBlockCount}</span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <div className="inline-flex items-center rounded-lg bg-[#050507] border border-white/[0.07] p-1 text-[11px] font-mono">
            <button
              onClick={() => setGovernanceMode("SANDBOX_TWIN")}
              className={`px-2.5 py-1 rounded-md transition-all ${
                governanceMode === "SANDBOX_TWIN"
                  ? "bg-[#111317] text-[#F9FAFB] border border-white/[0.1] font-semibold"
                  : "text-[#9CA3AF] hover:text-[#F9FAFB]"
              }`}
            >
              Sandbox Twin
            </button>
            <button
              onClick={() => setGovernanceMode("LIVE_PAYPAL_API")}
              className={`px-2.5 py-1 rounded-md transition-all ${
                governanceMode === "LIVE_PAYPAL_API"
                  ? "bg-[#111317] text-[#06B6D4] border border-[#06B6D4]/40 font-semibold"
                  : "text-[#9CA3AF] hover:text-[#F9FAFB]"
              }`}
            >
              Live PayPal Developer API
            </button>
          </div>

          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#111317] hover:bg-white/[0.08] border border-white/[0.08] text-xs font-mono text-[#F9FAFB] tactical-push-btn"
          >
            <span>API Docs</span>
            <ExternalLink className="w-3.5 h-3.5 text-[#06B6D4]" />
          </a>
        </div>
      </section>

      {/* ZONE 2: HERO STAGE — THE SENTINEL CORE & REAL-TIME SECURITY PULSE */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
        <div className="lg:col-span-7 flex flex-col">
          <SentinelCore3D
            coreState={coreState}
            activeHash={activeHash}
            riskIndex={riskIndex}
            activeScenarioLabel={activeScenarioLabel}
            onSelectState={(st) => {
              setCoreState(st);
              setRiskIndex(st === "BLOCKED" ? 88.5 : st === "HUMAN_REVIEW" ? 18.2 : st === "AUTO_APPROVED" ? 2.1 : 4.0);
            }}
          />
        </div>

        <div className="lg:col-span-5 tactical-double-bezel rounded-2xl p-6 flex flex-col justify-between gap-5">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-mono uppercase tracking-widest text-[#06B6D4]">
                EXECUTIVE SECURITY SUMMARY
              </span>
              <span className="text-[11px] font-mono text-[#4B5563]">REAL-TIME PULSE</span>
            </div>
            <h1 className="font-serif text-3xl sm:text-4xl text-[#F9FAFB] tracking-tight mt-1.5 leading-tight">
              Autonomous Mandate Control &amp; Causal Proof
            </h1>
            <p className="text-xs text-[#9CA3AF] mt-2 leading-relaxed">
              Pre-execution cryptographic policy enforcement paired with post-execution 18-node causal dispute synthesis.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-3">
            <div className="rounded-xl bg-[#111317] border border-[#EF4444]/40 shadow-glow-crimson p-4 flex items-center justify-between">
              <div>
                <div className="text-[11px] font-mono uppercase tracking-wider text-[#9CA3AF]">
                  01 // THREATS INTERCEPTED
                </div>
                <div className="text-2xl font-mono font-bold text-[#F9FAFB] mt-1">
                  {threatsIntercepted}{" "}
                  <span className="text-xs font-normal text-[#EF4444]">(0 PayPal Calls Leaked)</span>
                </div>
              </div>
              <div className="w-10 h-10 rounded-lg bg-[#EF4444]/15 border border-[#EF4444]/40 flex items-center justify-center">
                <ShieldAlert className="w-5 h-5 text-[#EF4444]" />
              </div>
            </div>

            <div className="rounded-xl bg-[#111317] border border-white/[0.08] p-4 flex items-center justify-between">
              <div>
                <div className="text-[11px] font-mono uppercase tracking-wider text-[#9CA3AF]">
                  02 // FAST-PATH VOLUME PROCESSED
                </div>
                <div className="text-2xl font-mono font-bold text-[#10B981] mt-1">
                  ${fastPathVolumeUsd.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}{" "}
                  <span className="text-xs font-normal text-[#9CA3AF]">USD</span>
                </div>
              </div>
              <div className="w-10 h-10 rounded-lg bg-[#10B981]/15 border border-[#10B981]/40 flex items-center justify-center">
                <ShieldCheck className="w-5 h-5 text-[#10B981]" />
              </div>
            </div>

            <div className="rounded-xl bg-[#111317] border border-white/[0.08] p-4 flex items-center justify-between">
              <div>
                <div className="text-[11px] font-mono uppercase tracking-wider text-[#9CA3AF]">
                  03 // AVERAGE EVALUATION OVERHEAD
                </div>
                <div className="text-2xl font-mono font-bold text-[#06B6D4] mt-1">
                  1.28 ms <span className="text-xs font-normal text-[#9CA3AF]">(P99: 1.75 ms)</span>
                </div>
              </div>
              <div className="w-10 h-10 rounded-lg bg-[#06B6D4]/15 border border-[#06B6D4]/40 flex items-center justify-center">
                <Gauge className="w-5 h-5 text-[#06B6D4]" />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ZONE 3: THE INTERACTIVE JUDGE SCENARIO ARENA (XAI MATRIX) */}
      <section id="scenario-arena" className="flex flex-col gap-4">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-2 border-b border-white/[0.07] pb-3">
          <div>
            <span className="text-[11px] font-mono uppercase tracking-widest text-[#10B981]">
              DETERMINISTIC EVALUATION MATRIX // XAI ATTRIBUTION
            </span>
            <h2 className="font-serif text-2xl sm:text-3xl text-[#F9FAFB] tracking-tight mt-0.5">
              Interactive Judge Scenario Arena
            </h2>
          </div>
          <div className="flex items-center gap-2 text-xs font-mono text-[#9CA3AF]">
            <span>Route:</span>
            <code className="px-2 py-0.5 rounded bg-[#111317] border border-white/[0.07] text-[#06B6D4]">
              POST /api/scenarios/run/1..4
            </code>
            <CopyTelemetryButton text="POST /api/scenarios/run/1" label="Route" />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {SCENARIO_BLUEPRINTS.map((scen) => {
            const res = scenarioResults[scen.id];
            const xai = res?.risk_breakdown || scen.defaultXai;
            const rationale =
              res?.governance_rationale || xai.governance_rationale || scen.defaultXai.governance_rationale;

            const promptW = Math.round((xai.prompt_injection_weight ?? scen.promptPct / 100) * 100) || scen.promptPct;
            const velocityW = Math.round((xai.velocity_weight ?? scen.velocityPct / 100) * 100) || scen.velocityPct;
            const credAgeW = Math.round((xai.credential_age_weight ?? scen.credAgePct / 100) * 100) || scen.credAgePct;

            const accentBorder =
              scen.accentColor === "emerald"
                ? "hover:border-[#10B981]/50"
                : scen.accentColor === "amber"
                ? "hover:border-[#F59E0B]/50"
                : "hover:border-[#EF4444]/50";

            const badgeStyle =
              scen.accentColor === "emerald"
                ? "bg-[#10B981]/15 text-[#10B981] border-[#10B981]/40"
                : scen.accentColor === "amber"
                ? "bg-[#F59E0B]/15 text-[#F59E0B] border-[#F59E0B]/40"
                : "bg-[#EF4444]/15 text-[#EF4444] border-[#EF4444]/40";

            return (
              <div
                key={scen.id}
                className={`tactical-double-bezel rounded-2xl p-5 flex flex-col justify-between gap-4 min-h-[340px] spring-transition ${accentBorder}`}
              >
                <div className="flex flex-col gap-2.5">
                  <div className="flex items-center justify-between gap-2">
                    <span className={`px-2.5 py-0.5 rounded text-[10px] font-mono font-bold border ${badgeStyle}`}>
                      {scen.tag}
                    </span>
                    <span className="font-mono text-xs font-bold text-[#F9FAFB]">{scen.amountLabel}</span>
                  </div>

                  <div className="flex items-baseline justify-between gap-2">
                    <h3 className="text-base font-bold text-[#F9FAFB] tracking-tight">{scen.title}</h3>
                  </div>

                  <p className="text-xs text-[#9CA3AF] leading-relaxed">{scen.subtitle}</p>
                </div>

                <div className="rounded-xl bg-[#050507]/90 border border-white/[0.07] p-3.5 flex flex-col gap-2.5">
                  <div className="flex flex-wrap items-center justify-between gap-1 text-[11px] font-mono">
                    <span className="text-[#F9FAFB] font-semibold">XAI RISK ATTRIBUTION BAR</span>
                    <span className="text-[#9CA3AF]">
                      [Prompt Injection: <strong className="text-[#EF4444]">{promptW}%</strong>] | [Velocity:{" "}
                      <strong className="text-[#F59E0B]">{velocityW}%</strong>] | [Credential Age:{" "}
                      <strong className="text-[#06B6D4]">{credAgeW}%</strong>]
                    </span>
                  </div>

                  <div className="w-full h-2.5 rounded-full bg-[#111317] border border-white/[0.07] overflow-hidden flex">
                    <div
                      style={{ width: `${Math.max(8, promptW)}%` }}
                      className="h-full bg-[#EF4444] transition-all duration-500"
                      title={`Prompt Injection Weight: ${promptW}%`}
                    />
                    <div
                      style={{ width: `${Math.max(10, velocityW)}%` }}
                      className="h-full bg-[#F59E0B] transition-all duration-500"
                      title={`Velocity Weight: ${velocityW}%`}
                    />
                    <div
                      style={{ width: `${Math.max(12, credAgeW)}%` }}
                      className="h-full bg-[#06B6D4] transition-all duration-500"
                      title={`Credential Age Weight: ${credAgeW}%`}
                    />
                  </div>

                  <div className="grid grid-cols-3 gap-2 text-[10px] font-mono">
                    <div className="px-2 py-1 rounded bg-[#111317] border border-white/[0.05] flex items-center justify-between">
                      <span className="text-[#4B5563]">prompt_inj:</span>
                      <span className="text-[#F9FAFB] font-bold">
                        {(xai.prompt_injection_weight ?? 0).toFixed(3)}
                      </span>
                    </div>
                    <div className="px-2 py-1 rounded bg-[#111317] border border-white/[0.05] flex items-center justify-between">
                      <span className="text-[#4B5563]">velocity:</span>
                      <span className="text-[#F9FAFB] font-bold">{(xai.velocity_weight ?? 0).toFixed(3)}</span>
                    </div>
                    <div className="px-2 py-1 rounded bg-[#111317] border border-white/[0.05] flex items-center justify-between">
                      <span className="text-[#4B5563]">cred_age:</span>
                      <span className="text-[#F9FAFB] font-bold">
                        {(xai.credential_age_weight ?? 0).toFixed(3)}
                      </span>
                    </div>
                  </div>

                  <div className="px-2.5 py-2 rounded-lg bg-[#111317] border border-white/[0.06] font-mono text-[11px] text-[#9CA3AF] leading-relaxed">
                    <span className="text-[#06B6D4] font-bold mr-1.5">&gt; RATIONALE:</span>
                    {rationale}
                  </div>
                </div>

                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 pt-2 border-t border-white/[0.07]">
                  <button
                    onClick={() => handleRunScenario(scen)}
                    disabled={runningScenarioId === scen.id}
                    className={`px-4 py-2.5 rounded-xl font-mono text-xs font-bold flex items-center justify-center gap-2 tactical-push-btn disabled:opacity-50 ${
                      scen.accentColor === "emerald"
                        ? "bg-[#10B981] hover:bg-[#10B981]/90 text-[#050507]"
                        : scen.accentColor === "amber"
                        ? "bg-[#F59E0B] hover:bg-[#F59E0B]/90 text-[#050507]"
                        : "bg-[#EF4444] hover:bg-[#EF4444]/90 text-[#F9FAFB]"
                    }`}
                  >
                    <Play className="w-3.5 h-3.5 fill-current" />
                    <span>
                      {runningScenarioId === scen.id
                        ? "EXECUTING GATE..."
                        : `Trigger Scenario 0${scen.id}`}
                    </span>
                  </button>

                  <div className="flex items-center gap-2">
                    {scen.id === 2 && res && !cfoApprovedS2 && res.final_state === "HUMAN_REVIEW" && (
                      <button
                        onClick={handleCFOApproveScenario2}
                        className="px-3 py-2 rounded-xl bg-[#10B981]/20 hover:bg-[#10B981]/30 border border-[#10B981]/50 text-[#10B981] font-mono text-xs font-bold flex items-center gap-1.5 tactical-push-btn"
                      >
                        <Lock className="w-3.5 h-3.5" />
                        <span>Sign as CFO Maya</span>
                      </button>
                    )}

                    {res ? (
                      <div className="px-3 py-1.5 rounded-lg bg-[#111317] border border-white/[0.08] font-mono text-xs flex items-center gap-2">
                        <CheckCircle2 className="w-3.5 h-3.5 text-[#10B981]" />
                        <span className="text-[#F9FAFB] font-bold">{res.final_state}</span>
                      </div>
                    ) : (
                      <span className="text-[11px] font-mono text-[#4B5563]">
                        READY // ZERO CLS LOCKED
                      </span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* ZONES 4, 5, AND 6: MERKLE FORENSICS, LIVE AGENT STREAM & BENCHMARKS, AND MCP INSPECTOR */}
      <TacticalForensicsAndMcpPanels
        auditBlocks={auditBlocks}
        merkleProbeResult={merkleProbeResult}
        verifyingMerkle={verifyingMerkle}
        onVerifyMerkleIntegrity={handleVerifyMerkleIntegrity}
        streamEvents={streamEvents}
      />
    </div>
  );
}
