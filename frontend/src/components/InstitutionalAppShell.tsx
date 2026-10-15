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
  Building2,
  AlertOctagon,
  X,
  Terminal,
} from "lucide-react";
import { api, type PayPalStatus, type KillSwitchStatus } from "@/lib/api";

const NAV_LINKS = [
  { href: "/", label: "Executive Command", icon: LayoutDashboard, badge: "CORE HUD" },
  { href: "/mandates", label: "Mandate Studio", icon: ShieldCheck, badge: "NL->CEL" },
  { href: "/approvals", label: "Approval Queue", icon: UserCheck, badge: "CFO MFA" },
  { href: "/transactions", label: "Ledger & Receipts", icon: CreditCard, badge: "SETTLED" },
  { href: "/evidence", label: "Evidence Graph", icon: Network, badge: "18-NODE" },
  { href: "/disputes", label: "Dispute Defense", icon: Scale, badge: "0.94 SLA" },
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
  const [, setKillStatus] = useState<KillSwitchStatus | null>(null);
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
        `CONTAINMENT CONFIRMED: Level ${activeKillTier} Kill Switch enforced on ${killTargetId}.`
      );
      setTimeout(() => {
        setActiveKillTier(null);
        setKillFeedback(null);
      }, 2400);
    } catch (err) {
      setKillFeedback(`Error triggering Kill Switch: ${(err as Error).message}`);
    } finally {
      setIsExecutingKill(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#050507] text-[#F9FAFB]">
      {/* Tactical Hardware Top Bar */}
      <header className="h-14 border-b border-white/[0.07] bg-[#0B0C0E]/95 backdrop-blur-md px-4 sm:px-6 flex items-center justify-between sticky top-0 z-40">
        {/* Brand System */}
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-md bg-[#111317] border border-white/[0.12] flex items-center justify-center shadow-bezel">
            <Terminal className="w-3.5 h-3.5 text-[#10B981]" />
          </div>
          <div className="flex items-center gap-2">
            <span className="font-mono font-bold text-xs tracking-widest text-[#F9FAFB]">
              SENTINEL
            </span>
            <span className="text-[#4B5563] font-mono text-xs">/</span>
            <span className="font-mono font-bold text-xs tracking-widest text-[#06B6D4]">
              PROOFLAYER
            </span>
            <span className="hidden sm:inline-block ml-2 px-2 py-0.5 rounded bg-[#111317] border border-white/[0.07] text-[10px] font-mono text-[#9CA3AF]">
              v1.0.0-PROD
            </span>
          </div>
        </div>

        {/* Live Status + 3-Tier Kill Switch + Org Badge */}
        <div className="flex items-center gap-2.5 sm:gap-3">
          <div className="hidden md:flex items-center gap-2 px-2.5 py-1 rounded-md bg-[#050507] border border-white/[0.07] text-[11px] font-mono">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#10B981] opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-[#10B981]"></span>
            </span>
            <span className="text-[#9CA3AF]">PAYPAL_{paypalStatus.mode}</span>
            <span className="text-[#4B5563]">|</span>
            <span className="text-[#10B981] font-semibold">{paypalStatus.latency_ms}ms</span>
          </div>

          {/* 3-Tier Kill Switch Hardware Triggers */}
          <div className="flex items-center gap-1 p-1 rounded-md bg-[#111317] border border-[#EF4444]/30">
            <ShieldAlert className="w-3.5 h-3.5 text-[#EF4444] ml-1.5 mr-0.5 hidden sm:inline" />
            <span className="text-[10px] font-mono font-semibold text-[#EF4444] mr-1 hidden sm:inline">
              KILL_SWITCH:
            </span>
            <button
              onClick={() => openKillModal(1)}
              title="Level 1: Halt Single Intent"
              className="px-2 py-0.5 text-[10px] font-mono font-semibold rounded bg-[#0B0C0E] hover:bg-[#EF4444]/20 border border-white/[0.07] text-[#F9FAFB] tactical-push-btn"
            >
              T1:INTENT
            </button>
            <button
              onClick={() => openKillModal(2)}
              title="Level 2: Revoke Agent ID"
              className="px-2 py-0.5 text-[10px] font-mono font-semibold rounded bg-[#0B0C0E] hover:bg-[#EF4444]/20 border border-white/[0.07] text-[#F9FAFB] tactical-push-btn"
            >
              T2:AGENT
            </button>
            <button
              onClick={() => openKillModal(3)}
              title="Level 3: Freeze Entire Mandate"
              className="px-2 py-0.5 text-[10px] font-mono font-bold rounded bg-[#EF4444]/20 hover:bg-[#EF4444]/30 border border-[#EF4444]/40 text-[#EF4444] tactical-push-btn"
            >
              T3:FREEZE
            </button>
          </div>

          {/* Organization Identity */}
          <div className="hidden lg:flex items-center gap-2 px-2.5 py-1 rounded-md bg-[#111317] border border-white/[0.07]">
            <Building2 className="w-3.5 h-3.5 text-[#06B6D4]" />
            <span className="text-[11px] font-mono text-[#F9FAFB]">usr_acme_finance</span>
          </div>
        </div>
      </header>

      {/* Main Workspace Body */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Navigation Sidebar */}
        <aside className="w-60 border-r border-white/[0.07] bg-[#0B0C0E] flex flex-col justify-between shrink-0 hidden xl:flex p-3">
          <div className="flex flex-col gap-1">
            <span className="text-[10px] font-mono uppercase tracking-widest text-[#4B5563] px-3 py-2">
              Control Plane Modules
            </span>
            {NAV_LINKS.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                    isActive
                      ? "bg-[#111317] text-[#F9FAFB] border border-white/[0.1] shadow-bezel font-semibold"
                      : "text-[#9CA3AF] hover:text-[#F9FAFB] hover:bg-[#111317]/60 border border-transparent"
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <Icon className={`w-3.5 h-3.5 ${isActive ? "text-[#10B981]" : "text-[#4B5563]"}`} />
                    <span>{item.label}</span>
                  </div>
                  {item.badge && (
                    <span
                      className={`text-[9px] font-mono px-1.5 py-0.5 rounded ${
                        isActive
                          ? "bg-[#10B981]/15 text-[#10B981] border border-[#10B981]/30"
                          : "bg-[#050507] text-[#4B5563] border border-white/[0.05]"
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </div>

          {/* Sidebar Hardware Telemetry Footer */}
          <div className="p-3 rounded-xl bg-[#050507] border border-white/[0.07] text-[11px] font-mono flex flex-col gap-1.5">
            <div className="flex items-center justify-between">
              <span className="text-[#4B5563]">AGENT_ID</span>
              <span className="text-[#10B981]">atlas_v4</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[#4B5563]">MANDATE</span>
              <span className="text-[#F9FAFB]">mdt_9f21ac</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[#4B5563]">SLA_P99</span>
              <span className="text-[#06B6D4]">1.75 ms</span>
            </div>
          </div>
        </aside>

        {/* Dynamic Screen View */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">{children}</main>
      </div>

      {/* 3-Tier Kill Switch Modal */}
      {activeKillTier && (
        <div className="fixed inset-0 bg-black/85 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div className="w-full max-w-lg bg-[#0B0C0E] border border-[#EF4444]/60 rounded-2xl p-6 shadow-glow-crimson flex flex-col gap-4">
            <div className="flex items-center justify-between border-b border-white/[0.07] pb-3">
              <div className="flex items-center gap-2.5 text-[#EF4444]">
                <AlertOctagon className="w-5 h-5 animate-pulse" />
                <h3 className="text-sm font-mono font-bold tracking-wider">
                  LEVEL_{activeKillTier} // EMERGENCY CONTAINMENT BREAKER
                </h3>
              </div>
              <button
                onClick={() => setActiveKillTier(null)}
                className="text-[#9CA3AF] hover:text-[#F9FAFB] p-1 rounded-lg"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="bg-[#EF4444]/10 border border-[#EF4444]/30 rounded-xl p-3.5 text-xs text-[#F9FAFB] leading-relaxed">
              {activeKillTier === 1 &&
                "Tier 1 (Intent Halt): Halts the specified proposed or executing intent immediately. Prevents further PayPal authorization or capture attempts."}
              {activeKillTier === 2 &&
                "Tier 2 (Agent Revocation): Revokes autonomous agent authority. Atlas will be barred from proposing or executing payments under any mandate."}
              {activeKillTier === 3 &&
                "Tier 3 (Mandate Freeze): Freezes all agents operating under this mandate. Aborts uncaptured authorizations while preserving settled PayPal transactions."}
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-[11px] font-mono uppercase tracking-wider text-[#9CA3AF]">
                Target Identifier ({activeKillTier === 1 ? "Intent ID" : activeKillTier === 2 ? "Agent ID" : "Mandate ID"}):
              </label>
              <input
                type="text"
                value={killTargetId}
                onChange={(e) => setKillTargetId(e.target.value)}
                className="w-full bg-[#050507] border border-white/[0.12] rounded-lg p-2.5 text-xs font-mono text-[#F9FAFB] focus:outline-none focus:border-[#EF4444]"
              />
            </div>

            {killFeedback && (
              <div className="p-3 bg-[#10B981]/15 border border-[#10B981]/40 text-[#10B981] rounded-lg text-xs font-mono">
                {killFeedback}
              </div>
            )}

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-white/[0.07]">
              <button
                onClick={() => setActiveKillTier(null)}
                className="px-4 py-2 text-xs font-mono text-[#9CA3AF] hover:text-[#F9FAFB] bg-[#111317] border border-white/[0.07] rounded-lg tactical-push-btn"
              >
                CANCEL
              </button>
              <button
                onClick={handleExecuteKillSwitch}
                disabled={isExecutingKill}
                className="px-5 py-2 text-xs font-mono font-bold text-[#F9FAFB] bg-[#EF4444] hover:bg-[#EF4444]/90 rounded-lg tactical-push-btn disabled:opacity-50"
              >
                {isExecutingKill ? "EXECUTING HALT..." : "CONFIRM EMERGENCY HALT"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default InstitutionalAppShell;
