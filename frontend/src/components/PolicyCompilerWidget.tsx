"use client";

import React, { useState } from "react";
import {
  Sparkles,
  Sliders,
  Code2,
  Play,
  Save,
  CheckCircle,
  AlertTriangle,
  Clock,
  ShieldAlert,
  ArrowRight,
  TrendingUp,
} from "lucide-react";
import { api, type Mandate, type WhatIfSimulationResult } from "@/lib/api";

export interface PolicyCompilerWidgetProps {
  initialMandate: Mandate;
  onSaveMandate: (mandate: Mandate) => Promise<void>;
  onRunSimulation?: (mandate: Mandate) => void;
}

const PRESET_PROMPTS = [
  {
    name: "Standard SaaS & Compute",
    text: "Allow Atlas to auto-approve procurement up to $1,000 for cloud compute and data labeling with PO variance <= 2%. Require human review up to $5,000 cap. Strictly block crypto and gambling.",
  },
  {
    name: "Strict Micro-Ops ($500)",
    text: "Allow Atlas to auto-approve expenses up to $500 for saas and productivity tools with strict 0% PO variance. Require CFO review up to $2,500. Block crypto, gambling, and gift cards.",
  },
  {
    name: "Enterprise High-Trust",
    text: "Auto-approve cloud infrastructure up to $2,500 with PO variance <= 3%. Require CFO review up to $15,000 cap. Strictly forbid crypto, gaming, and unauthorized hardware.",
  },
];

export function PolicyCompilerWidget({
  initialMandate,
  onSaveMandate,
  onRunSimulation,
}: PolicyCompilerWidgetProps) {
  const [prompt, setPrompt] = useState(
    initialMandate.natural_language_prompt ||
      "Allow Atlas to auto-approve procurement up to $1,000 for cloud compute and data labeling with PO variance <= 2%. Require human review up to $5,000 cap. Strictly block crypto and gambling."
  );
  const [mandate, setMandate] = useState<Mandate>(initialMandate);
  const [isCompiling, setIsCompiling] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isSimulating, setIsSimulating] = useState(false);
  const [simulationResult, setSimulationResult] = useState<WhatIfSimulationResult | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Quick category input helpers
  const [newAllowedCat, setNewAllowedCat] = useState("");
  const [newBlockedCat, setNewBlockedCat] = useState("");

  const handleCompile = async () => {
    setIsCompiling(true);
    try {
      const res = await api.compilePolicy(prompt);
      setMandate(res.compiled_mandate);
    } catch (err) {
      console.error("Compilation error:", err);
    } finally {
      setIsCompiling(false);
    }
  };

  const handleSimulate = async () => {
    setIsSimulating(true);
    try {
      const res = await api.runWhatIfSimulation(mandate);
      setSimulationResult(res);
      if (onRunSimulation) onRunSimulation(mandate);
    } catch (err) {
      console.error("Simulation error:", err);
    } finally {
      setIsSimulating(false);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    setSaveSuccess(false);
    try {
      await onSaveMandate(mandate);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err) {
      console.error("Save error:", err);
    } finally {
      setIsSaving(false);
    }
  };

  const removeAllowedCategory = (cat: string) => {
    setMandate((prev) => ({
      ...prev,
      allowed_categories: prev.allowed_categories.filter((c) => c !== cat),
    }));
  };

  const addAllowedCategory = () => {
    if (newAllowedCat.trim() && !mandate.allowed_categories.includes(newAllowedCat.trim())) {
      setMandate((prev) => ({
        ...prev,
        allowed_categories: [...prev.allowed_categories, newAllowedCat.trim().toLowerCase()],
      }));
      setNewAllowedCat("");
    }
  };

  const removeBlockedCategory = (cat: string) => {
    setMandate((prev) => ({
      ...prev,
      blocked_categories: prev.blocked_categories.filter((c) => c !== cat),
    }));
  };

  const addBlockedCategory = () => {
    if (newBlockedCat.trim() && !mandate.blocked_categories.includes(newBlockedCat.trim())) {
      setMandate((prev) => ({
        ...prev,
        blocked_categories: [...prev.blocked_categories, newBlockedCat.trim().toLowerCase()],
      }));
      setNewBlockedCat("");
    }
  };

  return (
    <div className="w-full flex flex-col gap-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Stage 1: NL Policy Compiler Input */}
        <div className="bg-sentinel-card border border-sentinel-border rounded-xl p-5 shadow-lg flex flex-col gap-4">
          <div className="flex items-center justify-between border-b border-sentinel-border pb-3">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-paypal-cyan" />
              <h3 className="text-sm font-semibold text-slate-100">Stage 1: Natural Language Policy Input</h3>
            </div>
            <span className="text-[10px] font-mono text-slate-400">NL-to-CEL Engine</span>
          </div>

          <div className="flex flex-col gap-2">
            <label className="text-xs text-slate-400 font-medium">Select Preset Template or Enter Custom Mandate:</label>
            <div className="flex flex-wrap gap-2">
              {PRESET_PROMPTS.map((p) => (
                <button
                  key={p.name}
                  onClick={() => setPrompt(p.text)}
                  className="px-2.5 py-1 text-[11px] rounded bg-sentinel-elevated border border-sentinel-border text-slate-300 hover:text-paypal-cyan hover:border-paypal-cyan transition-colors"
                >
                  {p.name}
                </button>
              ))}
            </div>
          </div>

          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows={4}
            className="w-full bg-sentinel-bg border border-sentinel-border rounded-lg p-3 text-xs text-slate-200 focus:outline-none focus:border-paypal-cyan leading-relaxed resize-none transition-colors"
            placeholder="Describe your governance policy in plain business English..."
          />

          <div className="flex items-center justify-between pt-2">
            <button
              onClick={handleCompile}
              disabled={isCompiling}
              className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-paypal-blue to-paypal-cyan text-white text-xs font-semibold rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50"
            >
              <Sparkles className="w-3.5 h-3.5" />
              {isCompiling ? "Compiling Policy..." : "Compile Policy into CEL"}
            </button>
            <span className="text-[11px] font-mono text-slate-400">
              Agent: <strong className="text-slate-200">{mandate.agent_id}</strong>
            </span>
          </div>
        </div>

        {/* Stage 2: Compiled Parameter Controls */}
        <div className="bg-sentinel-card border border-sentinel-border rounded-xl p-5 shadow-lg flex flex-col gap-4">
          <div className="flex items-center justify-between border-b border-sentinel-border pb-3">
            <div className="flex items-center gap-2">
              <Sliders className="w-4 h-4 text-paypal-cyan" />
              <h3 className="text-sm font-semibold text-slate-100">Stage 2: Compiled Mandate Parameters</h3>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-400 border border-emerald-800">
              {mandate.status}
            </span>
          </div>

          {/* Limits and Sliders */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="flex flex-col gap-1.5">
              <div className="flex justify-between text-xs">
                <span className="text-slate-400">Auto-Approve Limit:</span>
                <span className="font-mono text-paypal-cyan font-bold">${mandate.auto_approve_limit}</span>
              </div>
              <input
                type="range"
                min="0"
                max="2500"
                step="50"
                value={mandate.auto_approve_limit}
                onChange={(e) =>
                  setMandate((prev) => ({ ...prev, auto_approve_limit: Number(e.target.value) }))
                }
                className="w-full accent-paypal-cyan bg-slate-800"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <div className="flex justify-between text-xs">
                <span className="text-slate-400">Max Transaction Cap:</span>
                <span className="font-mono text-slate-200 font-bold">${mandate.max_transaction_cap}</span>
              </div>
              <input
                type="range"
                min="1000"
                max="10000"
                step="250"
                value={mandate.max_transaction_cap}
                onChange={(e) =>
                  setMandate((prev) => ({ ...prev, max_transaction_cap: Number(e.target.value) }))
                }
                className="w-full accent-paypal-blue bg-slate-800"
              />
            </div>

            <div className="flex flex-col gap-1.5 sm:col-span-2">
              <div className="flex justify-between text-xs">
                <span className="text-slate-400">PO Variance Tolerance:</span>
                <span className="font-mono text-amber-400 font-bold">
                  {(mandate.po_variance_tolerance * 100).toFixed(1)}%
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="0.05"
                step="0.005"
                value={mandate.po_variance_tolerance}
                onChange={(e) =>
                  setMandate((prev) => ({ ...prev, po_variance_tolerance: Number(e.target.value) }))
                }
                className="w-full accent-amber-500 bg-slate-800"
              />
            </div>
          </div>

          {/* Allowed and Blocked Categories */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
            <div>
              <span className="text-[11px] font-medium text-emerald-400 mb-1 block">Allowed Categories:</span>
              <div className="flex flex-wrap gap-1.5 mb-2">
                {mandate.allowed_categories.map((c) => (
                  <span
                    key={c}
                    onClick={() => removeAllowedCategory(c)}
                    className="cursor-pointer text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950/60 text-emerald-300 border border-emerald-800/80 hover:bg-rose-900/40"
                    title="Click to remove"
                  >
                    {c} ×
                  </span>
                ))}
              </div>
              <div className="flex gap-1">
                <input
                  type="text"
                  placeholder="Add category"
                  value={newAllowedCat}
                  onChange={(e) => setNewAllowedCat(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && addAllowedCategory()}
                  className="w-full bg-sentinel-bg border border-sentinel-border text-[11px] rounded px-2 py-1 text-slate-200"
                />
                <button
                  onClick={addAllowedCategory}
                  className="px-2 text-xs bg-sentinel-elevated border border-sentinel-border rounded text-slate-300"
                >
                  +
                </button>
              </div>
            </div>

            <div>
              <span className="text-[11px] font-medium text-rose-400 mb-1 block">Blocked Categories:</span>
              <div className="flex flex-wrap gap-1.5 mb-2">
                {mandate.blocked_categories.map((c) => (
                  <span
                    key={c}
                    onClick={() => removeBlockedCategory(c)}
                    className="cursor-pointer text-[10px] font-mono px-2 py-0.5 rounded bg-rose-950/60 text-rose-300 border border-rose-800/80 hover:bg-slate-800"
                    title="Click to remove"
                  >
                    {c} ×
                  </span>
                ))}
              </div>
              <div className="flex gap-1">
                <input
                  type="text"
                  placeholder="Add blocked"
                  value={newBlockedCat}
                  onChange={(e) => setNewBlockedCat(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && addBlockedCategory()}
                  className="w-full bg-sentinel-bg border border-sentinel-border text-[11px] rounded px-2 py-1 text-slate-200"
                />
                <button
                  onClick={addBlockedCategory}
                  className="px-2 text-xs bg-sentinel-elevated border border-sentinel-border rounded text-slate-300"
                >
                  +
                </button>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between pt-2 border-t border-sentinel-border">
            <button
              onClick={handleSave}
              disabled={isSaving}
              className="flex items-center gap-2 px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-lg transition-colors disabled:opacity-50"
            >
              <Save className="w-3.5 h-3.5" />
              {isSaving ? "Saving..." : "Save Mandate"}
            </button>
            {saveSuccess && (
              <span className="text-xs text-emerald-400 flex items-center gap-1 font-mono">
                <CheckCircle className="w-3.5 h-3.5" /> Mandate Active & Saved
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Center & Bottom: CEL Rule AST Viewer and What-If Simulator */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* CEL Expression & AST Preview */}
        <div className="bg-sentinel-card border border-sentinel-border rounded-xl p-5 shadow-lg flex flex-col gap-3">
          <div className="flex items-center justify-between border-b border-sentinel-border pb-3">
            <div className="flex items-center gap-2">
              <Code2 className="w-4 h-4 text-purple-400" />
              <h3 className="text-sm font-semibold text-slate-100">Compiled CEL & JSON AST Specification</h3>
            </div>
            <span className="text-[10px] font-mono text-slate-500">CEL v1.0 Spec</span>
          </div>

          <pre className="w-full bg-sentinel-bg border border-sentinel-border rounded-lg p-3 text-[11px] font-mono text-cyan-300 overflow-x-auto leading-relaxed max-h-56">
{`// Common Expression Language (CEL) Mandate AST
rule.auto_approve = (
  intent.amount <= ${mandate.auto_approve_limit}.00 &&
  intent.vendor_category in ${JSON.stringify(mandate.allowed_categories)} &&
  intent.matching.variance_pct <= ${(mandate.po_variance_tolerance * 100).toFixed(1)} &&
  !(intent.vendor_category in ${JSON.stringify(mandate.blocked_categories)})
);

rule.require_cfo_escalation = (
  intent.amount > ${mandate.auto_approve_limit}.00 &&
  intent.amount <= ${mandate.max_transaction_cap}.00 &&
  intent.matching.variance_pct <= ${(mandate.po_variance_tolerance * 100).toFixed(1)}
);

rule.blocked = (
  intent.amount > ${mandate.max_transaction_cap}.00 ||
  intent.vendor_category in ${JSON.stringify(mandate.blocked_categories)} ||
  !intent.matching.passed
);`}
          </pre>
        </div>

        {/* What-If Historical Simulator */}
        <div className="bg-sentinel-card border border-sentinel-border rounded-xl p-5 shadow-lg flex flex-col gap-4">
          <div className="flex items-center justify-between border-b border-sentinel-border pb-3">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-paypal-cyan" />
              <h3 className="text-sm font-semibold text-slate-100">Historical What-If Simulator</h3>
            </div>
            <button
              onClick={handleSimulate}
              disabled={isSimulating}
              className="flex items-center gap-1.5 px-3 py-1 bg-sentinel-elevated hover:bg-slate-700 text-paypal-cyan border border-sentinel-border text-xs font-medium rounded-lg transition-colors disabled:opacity-50"
            >
              <Play className="w-3 h-3 fill-current" />
              {isSimulating ? "Replaying..." : "Simulate Against 142 Txns"}
            </button>
          </div>

          {simulationResult ? (
            <div className="flex flex-col gap-4">
              {/* Stat breakdown badges */}
              <div className="grid grid-cols-3 gap-3">
                <div className="bg-emerald-950/40 border border-emerald-800/80 rounded-lg p-3 text-center">
                  <div className="text-lg font-bold font-mono text-emerald-400">
                    {simulationResult.auto_approved_pct.toFixed(1)}%
                  </div>
                  <div className="text-[10px] text-slate-400 font-medium">Auto-Approved ({simulationResult.auto_approved_count})</div>
                </div>

                <div className="bg-amber-950/40 border border-amber-800/80 rounded-lg p-3 text-center">
                  <div className="text-lg font-bold font-mono text-amber-400">
                    {simulationResult.human_review_pct.toFixed(1)}%
                  </div>
                  <div className="text-[10px] text-slate-400 font-medium">CFO Review ({simulationResult.human_review_count})</div>
                </div>

                <div className="bg-rose-950/40 border border-rose-800/80 rounded-lg p-3 text-center">
                  <div className="text-lg font-bold font-mono text-rose-400">
                    {simulationResult.blocked_pct.toFixed(1)}%
                  </div>
                  <div className="text-[10px] text-slate-400 font-medium">Blocked ({simulationResult.blocked_count})</div>
                </div>
              </div>

              {/* Time saved */}
              <div className="flex items-center gap-3 p-3 bg-sentinel-bg border border-sentinel-border rounded-lg">
                <Clock className="w-5 h-5 text-paypal-cyan flex-shrink-0" />
                <div className="text-xs">
                  <strong className="text-slate-100 font-semibold">
                    ~{simulationResult.estimated_review_hours_saved} Hours/Week Saved
                  </strong>
                  <p className="text-slate-400 text-[11px]">
                    Estimated reduction in manual invoice approval burden for CFO Maya.
                  </p>
                </div>
              </div>

              {/* Anomalies detected */}
              {simulationResult.flagged_anomalies.length > 0 && (
                <div className="flex flex-col gap-1.5">
                  <span className="text-[11px] font-semibold text-rose-400 flex items-center gap-1">
                    <ShieldAlert className="w-3.5 h-3.5" /> Flagged Out-of-Policy Anomalies:
                  </span>
                  <div className="flex flex-col gap-1">
                    {simulationResult.flagged_anomalies.map((anom, i) => (
                      <div key={i} className="text-[11px] font-mono text-slate-300 bg-sentinel-bg px-2.5 py-1 rounded border border-slate-800">
                        • {anom}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-8 text-center text-slate-500 text-xs">
              <Play className="w-6 h-6 mb-2 opacity-50" />
              Click &quot;Simulate Against 142 Txns&quot; to test your compiled policy against historical procurement volume.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default PolicyCompilerWidget;
