"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  ShieldCheck,
  UserCheck,
  CreditCard,
  Network,
  Scale,
  FileCode,
  ShieldAlert,
  Activity,
  CheckCircle2,
  Building2,
  AlertOctagon,
  X,
  Zap,
} from "lucide-react";
import { api, type PayPalStatus, type KillSwitchStatus } from "@/lib/api";

const NAV_LINKS = [
  { href: "/", label: "Executive Command", icon: LayoutDashboard, badge: "Scenarios 1–4" },
  { href: "/mandates", label: "Mandate Studio", icon: ShieldCheck, badge: "NL Engine" },
  { href: "/approvals", label: "Approval Queue", icon: UserCheck, badge: "CFO Console" },
  { href: "/transactions", label: "Ledger & Receipts", icon: CreditCard, badge: "Reconciled" },
  { href: "/evidence", label: "Evidence Graph", icon: Network, badge: "18-Node DAG" },
  { href: "/disputes", label: "Dispute Defense", icon: Scale, badge: "SLA Ready" },
  { href: "/audit", label: "Cryptographic Audit", icon: FileCode, badge: "SHA-256" },
];

export function InstitutionalAppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [paypalStatus, setPaypalStatus] = useState<PayPalStatus>({
    mode: "SANDBOX",
    healthy: true,
    latency_ms: 42,
    client_id_configured: true,
    active_access_token: true,
  });

  // Kill Switch Modal State
  const [activeKillTier, setActiveKillTier] = useState<1 | 2 | 3 | null>(null);
  const [killTargetId, setKillTargetId] = useState("");
  const [killStatus, setKillStatus] = useState<KillSwitchStatus | null>(null);
  const [killFeedback, setKillFeedback] = useState<string | null>(null);
  const [isExecutingKill, setIsExecutingKill] = useState(false);

  useEffect(() => {
    async function loadStatus() {
      try {
        const s = await api.getPayPalStatus();
        setPaypalStatus(s);
        const ks = await api.getKillSwitchStatus();
        setKillStatus(ks);
      } catch (err) {
        console.error("Status fetch error:", err);
      }
    }
    loadStatus();
  }, []);

  const openKillModal = (tier: 1 | 2 | 3) => {
    setActiveKillTier(tier);
    setKillFeedback(null);
    if (tier === 1) setKillTargetId("int_2026_0918");
    if (tier === 2) setKillTargetId("agent_atlas_procurement");
    if (tier === 3) setKillTargetId("mdt_9f21ac");
  };

  const handleExecuteKillSwitch = async () => {
    if (!activeKillTier || !killTargetId) return;
    setIsExecutingKill(true);
    try {
      const res = await api.triggerKillSwitch(activeKillTier, killTargetId);
      setKillStatus(res);
      setKillFeedback(
        `SUCCESS: Level ${activeKillTier} Kill Switch triggered on ${killTargetId}. Immediate halt enforced.`
      );
      setTimeout(() => {
        setActiveKillTier(null);
        setKillFeedback(null);
      }, 2500);
    } catch (err) {
      setKillFeedback(`Error triggering Kill Switch: ${(err as Error).message}`);
    } finally {
      setIsExecutingKill(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-sentinel-bg text-sentinel-text">
      {/* Top Header */}
      <header className="h-16 border-b border-sentinel-border bg-sentinel-card/90 backdrop-blur-md px-4 sm:px-6 flex items-center justify-between sticky top-0 z-40">
        {/* Brand System */}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-paypal-blue to-paypal-cyan flex items-center justify-center shadow-lg shadow-paypal-blue/30">
            <Zap className="w-4 h-4 text-white fill-current" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-sm tracking-wide text-white">SENTINEL</span>
              <span className="text-slate-500 text-xs">{"//"}</span>
              <span className="font-bold text-sm tracking-wide text-paypal-cyan">PROOFLAYER</span>
            </div>
            <span className="text-[10px] font-mono text-slate-400 block -mt-0.5">
              INSTITUTIONAL AGENT CONTROL PLANE
            </span>
          </div>
        </div>

        {/* Live Status + 3-Tier Kill Switch + Org Badge */}
        <div className="flex items-center gap-3 sm:gap-4">
          {/* PayPal Sandbox Status Indicator */}
          <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-full bg-sentinel-bg border border-sentinel-border text-xs font-mono">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="text-slate-300 font-medium">PAYPAL {paypalStatus.mode}</span>
            <span className="text-slate-500">•</span>
            <span className="text-emerald-400 font-semibold">{paypalStatus.latency_ms}ms</span>
          </div>

          {/* 3-Tier Kill Switch Triggers */}
          <div className="flex items-center gap-1.5 p-1 rounded-lg bg-rose-950/40 border border-rose-900/60">
            <ShieldAlert className="w-4 h-4 text-rose-400 ml-1.5 mr-0.5 hidden sm:inline" />
            <span className="text-[11px] font-mono font-bold text-rose-300 mr-1 hidden sm:inline">
              KILL SWITCH:
            </span>
            <button
              onClick={() => openKillModal(1)}
              title="Level 1: Halt Single Intent"
              className="px-2 py-1 text-[11px] font-mono font-semibold rounded bg-rose-900/60 hover:bg-rose-800 text-rose-200 transition-colors"
            >
              T1: INTENT
            </button>
            <button
              onClick={() => openKillModal(2)}
              title="Level 2: Revoke Agent ID"
              className="px-2 py-1 text-[11px] font-mono font-semibold rounded bg-rose-900/80 hover:bg-rose-700 text-rose-100 transition-colors"
            >
              T2: AGENT
            </button>
            <button
              onClick={() => openKillModal(3)}
              title="Level 3: Freeze Entire Mandate"
              className="px-2 py-1 text-[11px] font-mono font-bold rounded bg-rose-700 hover:bg-rose-600 text-white transition-colors"
            >
              T3: FREEZE
            </button>
          </div>

          {/* Organization Identity */}
          <div className="hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-sentinel-elevated border border-sentinel-border">
            <Building2 className="w-4 h-4 text-paypal-cyan" />
            <div className="text-left">
              <span className="text-xs font-semibold text-slate-100 block leading-tight">Acme AI Ops</span>
              <span className="text-[10px] font-mono text-slate-400 block leading-tight">usr_acme_finance</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Workspace Body */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Navigation Sidebar */}
        <aside className="w-64 border-r border-sentinel-border bg-sentinel-card/70 flex flex-col justify-between shrink-0 hidden md:flex p-3">
          <div className="flex flex-col gap-1">
            <span className="text-[10px] font-mono uppercase tracking-wider text-slate-500 px-3 py-2">
              Command Modules
            </span>
            {NAV_LINKS.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-medium transition-all ${
                    isActive
                      ? "bg-gradient-to-r from-paypal-blue/30 to-paypal-cyan/20 text-paypal-cyan border border-paypal-cyan/50 font-semibold"
                      : "text-slate-300 hover:text-white hover:bg-sentinel-elevated"
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <Icon className={`w-4 h-4 ${isActive ? "text-paypal-cyan" : "text-slate-400"}`} />
                    <span>{item.label}</span>
                  </div>
                  {item.badge && (
                    <span
                      className={`text-[9px] font-mono px-1.5 py-0.5 rounded ${
                        isActive
                          ? "bg-paypal-cyan/20 text-paypal-cyan border border-paypal-cyan/40"
                          : "bg-slate-800 text-slate-400"
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </div>

          {/* Sidebar Footer Info */}
          <div className="p-3 rounded-lg bg-sentinel-bg border border-sentinel-border text-xs flex flex-col gap-1.5">
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Agent In Charge:</span>
              <span className="font-mono text-emerald-400 font-medium">Atlas</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Active Mandate:</span>
              <span className="font-mono text-slate-300">mdt_9f21ac</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Merkle Tip:</span>
              <span className="font-mono text-cyan-400">#142</span>
            </div>
          </div>
        </aside>

        {/* Dynamic Screen View */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">{children}</main>
      </div>

      {/* 3-Tier Kill Switch Modal */}
      {activeKillTier && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="w-full max-w-lg bg-sentinel-card border-2 border-rose-600 rounded-2xl p-6 shadow-2xl flex flex-col gap-4 animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between border-b border-rose-900/60 pb-3">
              <div className="flex items-center gap-2.5 text-rose-400">
                <AlertOctagon className="w-6 h-6 animate-pulse" />
                <h3 className="text-base font-bold tracking-tight">
                  LEVEL {activeKillTier} EMERGENCY KILL SWITCH
                </h3>
              </div>
              <button
                onClick={() => setActiveKillTier(null)}
                className="text-slate-400 hover:text-white p-1 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="bg-rose-950/40 border border-rose-900/80 rounded-xl p-3.5 text-xs text-rose-200 leading-relaxed">
              {activeKillTier === 1 &&
                "Tier 1 (Intent Halt): Halts the specified proposed or executing intent immediately. Prevents further PayPal authorization or capture attempts."}
              {activeKillTier === 2 &&
                "Tier 2 (Agent Revocation): Revokes autonomous agent authority. Atlas will be barred from proposing or executing payments under any mandate."}
              {activeKillTier === 3 &&
                "Tier 3 (Mandate Freeze): Freezes all agents operating under this mandate. Aborts uncaptured authorizations while preserving settled PayPal transactions."}
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-slate-300">
                Target Identifier ({activeKillTier === 1 ? "Intent ID" : activeKillTier === 2 ? "Agent ID" : "Mandate ID"}):
              </label>
              <input
                type="text"
                value={killTargetId}
                onChange={(e) => setKillTargetId(e.target.value)}
                className="w-full bg-sentinel-bg border border-rose-800 rounded-lg p-2.5 text-xs font-mono text-white focus:outline-none focus:border-rose-500"
              />
            </div>

            {killFeedback && (
              <div className="p-3 bg-emerald-950/70 border border-emerald-800 text-emerald-300 rounded-lg text-xs font-mono">
                {killFeedback}
              </div>
            )}

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-sentinel-border">
              <button
                onClick={() => setActiveKillTier(null)}
                className="px-4 py-2 text-xs font-medium text-slate-300 hover:text-white bg-sentinel-elevated rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleExecuteKillSwitch}
                disabled={isExecutingKill}
                className="px-5 py-2 text-xs font-bold text-white bg-rose-600 hover:bg-rose-700 rounded-lg shadow-lg shadow-rose-900/50 transition-colors disabled:opacity-50"
              >
                {isExecutingKill ? "Executing Emergency Halt..." : "CONFIRM EMERGENCY HALT"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default InstitutionalAppShell;
