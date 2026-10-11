"use client";

import React, { useState, useEffect } from "react";
import {
  ShieldCheck,
  History,
  CheckCircle2,
  FileCode2,
  Sparkles,
  Layers,
  ArrowUpRight,
  Hash,
} from "lucide-react";
import { api, type Mandate, SEEDED_MANDATE } from "@/lib/api";
import { PolicyCompilerWidget } from "@/components/PolicyCompilerWidget";

export default function MandateStudioPage() {
  const [activeMandate, setActiveMandate] = useState<Mandate>(SEEDED_MANDATE);
  const [mandateList, setMandateList] = useState<Mandate[]>([SEEDED_MANDATE]);
  const [selectedVersionId, setSelectedVersionId] = useState<string>(SEEDED_MANDATE.id);

  useEffect(() => {
    async function loadData() {
      try {
        const active = await api.getActiveMandate();
        setActiveMandate(active);
        const list = await api.getMandates();
        setMandateList(list);
      } catch (err) {
        console.error("Failed to load mandates:", err);
      }
    }
    loadData();
  }, []);

  const handleSaveMandate = async (newMandate: Mandate) => {
    setActiveMandate(newMandate);
    setMandateList((prev) => [
      newMandate,
      ...prev.filter((m) => m.id !== newMandate.id),
    ]);
  };

  return (
    <div className="flex flex-col gap-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-sentinel-border pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded text-[11px] font-mono font-bold bg-cyan-950/80 text-cyan-300 border border-cyan-800">
              SCREEN 1 — MANDATE STUDIO
            </span>
            <span className="text-slate-500 text-xs">•</span>
            <span className="text-xs font-mono text-slate-400">Agent Atlas Procurement Rules</span>
          </div>
          <h1 className="text-2xl font-black text-white tracking-tight">
            Mandate Studio & Policy Compiler
          </h1>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl">
            Define natural language financial boundaries for autonomous agents, compile into CEL AST rules, simulate against historical volume, and anchor cryptographic Merkle commitments.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex flex-col items-end">
            <span className="text-[10px] font-mono text-slate-400">Active Merkle Root:</span>
            <span className="font-mono text-xs text-cyan-300">
              {activeMandate.merkle_root.slice(0, 10)}...{activeMandate.merkle_root.slice(-6)}
            </span>
          </div>
        </div>
      </div>

      {/* Main 2-Stage Policy Compiler & What-If Simulator Widget */}
      <PolicyCompilerWidget
        initialMandate={activeMandate}
        onSaveMandate={handleSaveMandate}
      />

      {/* Bottom Panel — Mandate Version History & Merkle Anchors */}
      <div className="bg-sentinel-card border border-sentinel-border rounded-xl p-5 shadow-lg flex flex-col gap-4">
        <div className="flex items-center justify-between border-b border-sentinel-border pb-3">
          <div className="flex items-center gap-2">
            <History className="w-4 h-4 text-paypal-cyan" />
            <h3 className="text-sm font-bold text-slate-100">Mandate Version History & Cryptographic Commitments</h3>
          </div>
          <span className="text-xs text-slate-400 font-mono">
            {mandateList.length} Versions Recorded
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-sentinel-border text-slate-400 text-[11px] uppercase">
                <th className="pb-2">Version</th>
                <th className="pb-2">Mandate ID</th>
                <th className="pb-2">Status</th>
                <th className="pb-2">Auto Limit</th>
                <th className="pb-2">Max Cap</th>
                <th className="pb-2">Variance Tolerance</th>
                <th className="pb-2">Merkle Root Hash</th>
                <th className="pb-2 text-right">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {mandateList.map((m) => {
                const isActive = m.status === "ACTIVE";
                return (
                  <tr
                    key={m.id}
                    onClick={() => {
                      setSelectedVersionId(m.id);
                      setActiveMandate(m);
                    }}
                    className={`cursor-pointer transition-colors ${
                      selectedVersionId === m.id
                        ? "bg-sentinel-elevated"
                        : "hover:bg-sentinel-elevated/40"
                    }`}
                  >
                    <td className="py-3 font-bold text-slate-200">{m.version}</td>
                    <td className="py-3 text-slate-400">{m.id}</td>
                    <td className="py-3">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                          isActive
                            ? "bg-emerald-950/80 text-emerald-300 border-emerald-800"
                            : "bg-slate-800 text-slate-400 border-slate-700"
                        }`}
                      >
                        {m.status}
                      </span>
                    </td>
                    <td className="py-3 text-paypal-cyan font-bold">${m.auto_approve_limit}</td>
                    <td className="py-3 text-slate-200 font-bold">${m.max_transaction_cap}</td>
                    <td className="py-3 text-amber-400 font-bold">
                      {(m.po_variance_tolerance * 100).toFixed(1)}%
                    </td>
                    <td className="py-3 text-slate-400">
                      <span className="flex items-center gap-1">
                        <Hash className="w-3 h-3 text-slate-500" />
                        {m.merkle_root.slice(0, 8)}...{m.merkle_root.slice(-6)}
                      </span>
                    </td>
                    <td className="py-3 text-right text-slate-400">
                      {new Date(m.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
