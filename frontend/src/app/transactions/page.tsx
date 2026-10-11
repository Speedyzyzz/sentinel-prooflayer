"use client";

import React, { useState, useMemo } from "react";
import {
  CreditCard,
  CheckCircle2,
  Receipt,
  FileCheck,
  TrendingUp,
  Clock,
  Layers,
  ExternalLink,
  ShieldCheck,
  X,
  Server,
  Activity,
  Hash,
} from "lucide-react";
import type { ColDef } from "ag-grid-community";
import {
  PaymentIntent,
  SEEDED_INTENTS,
} from "@/lib/api";
import {
  AgGridGovernanceTable,
  StatusBadgeRenderer,
  CurrencyRenderer,
  MonospaceHashRenderer,
} from "@/components/AgGridGovernanceTable";

interface TransactionRow {
  txn_id: string;
  intent_id: string;
  paypal_order_id: string;
  paypal_capture_id: string;
  vendor_name: string;
  vendor_category: string;
  amount: number;
  fee: number;
  net_amount: number;
  status: string;
  timestamp: string;
  audit_hash: string;
  telemetry_ip: string;
}

const SEEDED_TRANSACTIONS: TransactionRow[] = [
  {
    txn_id: "txn_2026_0918_settled",
    intent_id: "int_2026_0918",
    paypal_order_id: "5O190127TN364715T",
    paypal_capture_id: "2GG279541U053982Y",
    vendor_name: "Cloud Compute Inc",
    vendor_category: "cloud_compute",
    amount: 4180.5,
    fee: 121.23,
    net_amount: 4059.27,
    status: "RECONCILED",
    timestamp: "2026-10-10T16:19:05Z",
    audit_hash: "c7118490fa2b67d5e49208a09f8723bba120489501a4e289f0129cdba128a881",
    telemetry_ip: "198.51.100.44",
  },
  {
    txn_id: "txn_2026_0840_settled",
    intent_id: "int_2026_0840",
    paypal_order_id: "7B280199TN441209P",
    paypal_capture_id: "8HH119541U019283Z",
    vendor_name: "Data Labeling Co",
    vendor_category: "data_labeling",
    amount: 840.0,
    fee: 24.36,
    net_amount: 815.64,
    status: "RECONCILED",
    timestamp: "2026-10-10T14:32:15Z",
    audit_hash: "a49f82d1c67843e990c8e239a045bbd7812eac430198f45a78c129e47190ad3f",
    telemetry_ip: "198.51.100.44",
  },
  {
    txn_id: "txn_2026_0415_settled",
    intent_id: "int_2026_0415",
    paypal_order_id: "9C441288TN991823K",
    paypal_capture_id: "4KK992812U112938W",
    vendor_name: "Master Services Corp",
    vendor_category: "saas",
    amount: 415.0,
    fee: 12.04,
    net_amount: 402.96,
    status: "RECONCILED",
    timestamp: "2026-10-09T11:20:00Z",
    audit_hash: "88cd011234455667788990011223344556677889900112233445566778899001",
    telemetry_ip: "203.0.113.19",
  },
];

export default function TransactionsPage() {
  const [selectedTxn, setSelectedTxn] = useState<TransactionRow | null>(null);

  const columnDefs = useMemo<ColDef<TransactionRow>[]>(
    () => [
      {
        field: "txn_id",
        headerName: "Transaction ID",
        width: 170,
        cellRenderer: MonospaceHashRenderer,
      },
      {
        field: "paypal_order_id",
        headerName: "PayPal Order ID",
        width: 160,
        cellRenderer: (p: any) => (
          <span className="font-mono text-xs text-paypal-cyan font-medium">
            {p.value}
          </span>
        ),
      },
      {
        field: "paypal_capture_id",
        headerName: "PayPal Capture ID",
        width: 170,
        cellRenderer: (p: any) => (
          <span className="font-mono text-xs text-emerald-400 font-medium">
            {p.value}
          </span>
        ),
      },
      {
        field: "vendor_name",
        headerName: "Vendor Entity",
        width: 160,
        cellRenderer: (p: any) => (
          <div className="flex flex-col justify-center">
            <span className="font-semibold text-slate-100">{p.value}</span>
            <span className="text-[10px] text-slate-400 font-mono">{p.data?.vendor_category}</span>
          </div>
        ),
      },
      {
        field: "amount",
        headerName: "Gross Amount",
        width: 130,
        cellRenderer: CurrencyRenderer,
      },
      {
        field: "fee",
        headerName: "PayPal Fee",
        width: 110,
        cellRenderer: (p: any) => (
          <span className="font-mono text-xs text-slate-400">${p.value?.toFixed(2)}</span>
        ),
      },
      {
        field: "status",
        headerName: "Lifecycle State",
        width: 140,
        cellRenderer: StatusBadgeRenderer,
      },
      {
        field: "audit_hash",
        headerName: "Audit Merkle Hash",
        width: 150,
        cellRenderer: MonospaceHashRenderer,
      },
      {
        headerName: "Receipt",
        width: 120,
        cellRenderer: (p: any) => (
          <button
            onClick={() => setSelectedTxn(p.data)}
            className="px-2.5 py-1 text-[11px] font-semibold bg-sentinel-elevated hover:bg-slate-700 text-paypal-cyan border border-sentinel-border rounded transition-colors"
          >
            Receipt
          </button>
        ),
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
            <span className="px-2.5 py-0.5 rounded text-[11px] font-mono font-bold bg-emerald-950/80 text-emerald-300 border border-emerald-800">
              SCREEN 3 — TRANSACTION LEDGER
            </span>
            <span className="text-slate-500 text-xs">•</span>
            <span className="text-xs font-mono text-slate-400">Reconciliation & Settlement Store</span>
          </div>
          <h1 className="text-2xl font-black text-white tracking-tight">
            Transaction & Reconciliation Ledger
          </h1>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl">
            Live reconciliation of autonomous payment authorizations, settled PayPal captures, merchant fee deductions, and digital telemetry telemetry receipts.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-sentinel-card border border-sentinel-border text-xs font-mono">
            <Server className="w-4 h-4 text-emerald-400" />
            <span className="text-slate-300">PayPal Twin: Deterministic</span>
          </div>
        </div>
      </div>

      {/* Spend Velocity Sparklines & Treasury Analytics */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-sentinel-card border border-sentinel-border rounded-xl p-4 flex flex-col justify-between shadow-md">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>24h Settled Volume</span>
            <CreditCard className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="mt-2">
            <div className="text-xl font-bold font-mono text-white">$5,435.50 USD</div>
            <div className="text-[11px] text-slate-400 mt-0.5">3 Transactions Settled</div>
          </div>
          <div className="text-[10px] text-emerald-400 mt-2 border-t border-slate-800 pt-1.5">
            100% matched to PO records
          </div>
        </div>

        <div className="bg-sentinel-card border border-sentinel-border rounded-xl p-4 flex flex-col justify-between shadow-md">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>Hourly Spend Velocity</span>
            <Activity className="w-4 h-4 text-paypal-cyan" />
          </div>
          <div className="mt-2">
            <div className="text-xl font-bold font-mono text-paypal-cyan">$840.00 / hr</div>
            <div className="text-[11px] text-slate-400 mt-0.5">Peak cap: $5,000 / day</div>
          </div>
          <div className="text-[10px] text-slate-400 mt-2 border-t border-slate-800 pt-1.5">
            Velocity within normal bounds (16.8% of daily limit)
          </div>
        </div>

        <div className="bg-sentinel-card border border-sentinel-border rounded-xl p-4 flex flex-col justify-between shadow-md">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>PayPal Merchant Fees</span>
            <Receipt className="w-4 h-4 text-amber-400" />
          </div>
          <div className="mt-2">
            <div className="text-xl font-bold font-mono text-amber-400">$157.63 USD</div>
            <div className="text-[11px] text-slate-400 mt-0.5">Effective rate: 2.90%</div>
          </div>
          <div className="text-[10px] text-slate-400 mt-2 border-t border-slate-800 pt-1.5">
            Standard PayPal commercial interchange
          </div>
        </div>
      </div>

      {/* Main Reconciliation AG Grid */}
      <AgGridGovernanceTable
        rowData={SEEDED_TRANSACTIONS}
        columnDefs={columnDefs}
        onRowClicked={(row) => setSelectedTxn(row)}
        title="Settlement & Reconciliation Archive"
        height="460px"
      />

      {/* PayPal Digital Receipt & Telemetry Modal */}
      {selectedTxn && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="w-full max-w-lg bg-sentinel-card border border-sentinel-border rounded-2xl p-6 shadow-2xl flex flex-col gap-4 animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between border-b border-sentinel-border pb-3">
              <div className="flex items-center gap-2">
                <Receipt className="w-5 h-5 text-paypal-cyan" />
                <h3 className="text-base font-bold text-white">PayPal Digital Receipt & Telemetry</h3>
              </div>
              <button
                onClick={() => setSelectedTxn(null)}
                className="text-slate-400 hover:text-white p-1 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="bg-sentinel-bg border border-sentinel-border rounded-xl p-4 flex flex-col gap-3 font-mono text-xs">
              <div className="flex justify-between border-b border-slate-800 pb-2">
                <span className="text-slate-400">Order ID:</span>
                <span className="text-paypal-cyan font-bold">{selectedTxn.paypal_order_id}</span>
              </div>
              <div className="flex justify-between border-b border-slate-800 pb-2">
                <span className="text-slate-400">Capture ID:</span>
                <span className="text-emerald-400 font-bold">{selectedTxn.paypal_capture_id}</span>
              </div>
              <div className="flex justify-between border-b border-slate-800 pb-2">
                <span className="text-slate-400">Vendor Entity:</span>
                <span className="text-slate-100">{selectedTxn.vendor_name}</span>
              </div>
              <div className="flex justify-between border-b border-slate-800 pb-2">
                <span className="text-slate-400">Gross Settled:</span>
                <span className="text-white font-bold">${selectedTxn.amount.toFixed(2)} USD</span>
              </div>
              <div className="flex justify-between border-b border-slate-800 pb-2">
                <span className="text-slate-400">PayPal Fee:</span>
                <span className="text-rose-400 font-bold">-${selectedTxn.fee.toFixed(2)} USD</span>
              </div>
              <div className="flex justify-between border-b border-slate-800 pb-2">
                <span className="text-slate-400">Net Settled:</span>
                <span className="text-emerald-400 font-bold">${selectedTxn.net_amount.toFixed(2)} USD</span>
              </div>
              <div className="flex justify-between border-b border-slate-800 pb-2">
                <span className="text-slate-400">Timestamp:</span>
                <span className="text-slate-300">{selectedTxn.timestamp}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Telemetry Origin IP:</span>
                <span className="text-violet-400 font-bold">{selectedTxn.telemetry_ip}</span>
              </div>
            </div>

            <div className="flex items-center gap-2 p-3 bg-emerald-950/30 border border-emerald-800/80 rounded-xl text-xs text-emerald-300">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>
                Cryptographically anchored to Merkle Audit Block tip. Fully reconciled with zero discrepancies.
              </span>
            </div>

            <button
              onClick={() => setSelectedTxn(null)}
              className="w-full py-2 bg-sentinel-elevated hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-lg transition-colors"
            >
              Close Receipt
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
