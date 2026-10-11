"use client";

import React, { useState, useRef, useCallback, useMemo } from "react";
import { AgGridReact } from "ag-grid-react";
import type { ColDef, RowClickedEvent, GridReadyEvent } from "ag-grid-community";
import { Search, Download, RefreshCw, Layers } from "lucide-react";

export interface AgGridGovernanceTableProps<T> {
  rowData: T[];
  columnDefs: ColDef<T>[];
  onRowClicked?: (row: T) => void;
  title?: string;
  searchPlaceholder?: string;
  height?: string;
  onRefresh?: () => void;
}

// Custom Cell Renderers exported for reusability across tables

export function StatusBadgeRenderer(params: { value?: string }) {
  const status = params.value || "UNKNOWN";
  let bgClass = "bg-slate-800 text-slate-300 border-slate-700";
  let dotClass = "bg-slate-400";

  if (["AUTO_APPROVED", "CAPTURED", "RECONCILED", "VERIFIED", "APPROVED"].includes(status)) {
    bgClass = "bg-emerald-950/70 text-emerald-400 border-emerald-800/80";
    dotClass = "bg-emerald-400 shadow-[0_0_8px_rgba(16,185,129,0.8)]";
  } else if (["HUMAN_REVIEW", "DISPUTE_OPEN", "PENDING"].includes(status)) {
    bgClass = "bg-amber-950/70 text-amber-400 border-amber-800/80";
    dotClass = "bg-amber-400 animate-pulse shadow-[0_0_8px_rgba(245,158,11,0.8)]";
  } else if (["BLOCKED", "EXPIRED", "TAMPERED", "KILL_SWITCH_ACTIVE", "REJECTED"].includes(status)) {
    bgClass = "bg-rose-950/70 text-rose-400 border-rose-800/80";
    dotClass = "bg-rose-400 shadow-[0_0_8px_rgba(239,68,68,0.8)]";
  } else if (["PROPOSED", "POLICY_CHECK", "EVIDENCE_VALIDATION", "EXECUTING", "AUTHORIZED", "EVIDENCE_SUBMITTED"].includes(status)) {
    bgClass = "bg-cyan-950/70 text-cyan-400 border-cyan-800/80";
    dotClass = "bg-cyan-400 animate-pulse shadow-[0_0_8px_rgba(6,182,212,0.8)]";
  }

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-medium border ${bgClass}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dotClass}`} />
      {status}
    </span>
  );
}

export function RiskGaugeRenderer(params: { value?: number }) {
  const score = params.value !== undefined ? Number(params.value) : 0;
  const pct = Math.min(Math.max(score * 100, 0), 100);

  let barColor = "bg-emerald-500";
  let textColor = "text-emerald-400";
  if (score >= 0.5) {
    barColor = "bg-rose-500";
    textColor = "text-rose-400";
  } else if (score >= 0.2) {
    barColor = "bg-amber-500";
    textColor = "text-amber-400";
  }

  return (
    <div className="flex items-center gap-2.5 w-full h-full">
      <div className="flex-1 bg-slate-900 border border-slate-800 rounded-full h-2 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${barColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className={`font-mono text-xs font-semibold w-9 text-right ${textColor}`}>
        {score.toFixed(2)}
      </span>
    </div>
  );
}

export function CurrencyRenderer(params: { value?: number }) {
  const amount = params.value !== undefined ? Number(params.value) : 0;
  const formatted = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(amount);

  return <span className="font-mono text-xs font-medium text-slate-100">{formatted}</span>;
}

export function MonospaceHashRenderer(params: { value?: string }) {
  const hash = params.value || "";
  const short = hash.length > 14 ? `${hash.slice(0, 7)}...${hash.slice(-7)}` : hash;

  const copyToClipboard = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (hash && navigator.clipboard) {
      navigator.clipboard.writeText(hash);
    }
  };

  return (
    <span
      onClick={copyToClipboard}
      title={`Click to copy: ${hash}`}
      className="font-mono text-xs text-slate-400 hover:text-paypal-cyan cursor-pointer transition-colors inline-flex items-center gap-1"
    >
      <span>{short}</span>
    </span>
  );
}

export function AgGridGovernanceTable<T>({
  rowData,
  columnDefs,
  onRowClicked,
  title,
  searchPlaceholder = "Filter records...",
  height = "420px",
  onRefresh,
}: AgGridGovernanceTableProps<T>) {
  const [quickFilterText, setQuickFilterText] = useState("");
  const gridApiRef = useRef<any>(null);

  const onGridReady = useCallback((params: GridReadyEvent) => {
    gridApiRef.current = params.api;
  }, []);

  const handleExportCSV = useCallback(() => {
    if (gridApiRef.current) {
      gridApiRef.current.exportDataAsCsv({
        fileName: `${(title || "governance-export").toLowerCase().replace(/\s+/g, "-")}-${Date.now()}.csv`,
      });
    }
  }, [title]);

  const defaultColDef = useMemo<ColDef>(
    () => ({
      sortable: true,
      filter: true,
      resizable: true,
      cellClass: "flex items-center text-xs text-slate-200",
    }),
    []
  );

  const handleRowClick = useCallback(
    (event: RowClickedEvent<T>) => {
      if (onRowClicked && event.data) {
        onRowClicked(event.data);
      }
    },
    [onRowClicked]
  );

  return (
    <div className="w-full bg-sentinel-card border border-sentinel-border rounded-xl shadow-lg flex flex-col overflow-hidden">
      {/* Top Controls Toolbar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 px-4 py-3 border-b border-sentinel-border bg-sentinel-card/80">
        <div className="flex items-center gap-2">
          {title && (
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-paypal-cyan" />
              <h3 className="text-sm font-semibold tracking-tight text-slate-100">{title}</h3>
            </div>
          )}
          <span className="px-2 py-0.5 rounded-full text-xs font-mono bg-slate-800 text-slate-300 border border-slate-700">
            {rowData.length} rows
          </span>
        </div>

        <div className="flex items-center gap-2">
          <div className="relative flex-1 sm:w-64">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={quickFilterText}
              onChange={(e) => setQuickFilterText(e.target.value)}
              placeholder={searchPlaceholder}
              className="w-full bg-sentinel-bg border border-sentinel-border text-xs rounded-lg pl-8 pr-3 py-1.5 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-paypal-cyan transition-colors"
            />
          </div>

          <button
            onClick={handleExportCSV}
            title="Export CSV"
            className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-slate-300 bg-sentinel-elevated hover:bg-slate-700 border border-sentinel-border rounded-lg transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            <span className="hidden md:inline">Export</span>
          </button>

          {onRefresh && (
            <button
              onClick={onRefresh}
              title="Refresh Data"
              className="p-1.5 text-slate-300 bg-sentinel-elevated hover:bg-slate-700 border border-sentinel-border rounded-lg transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Grid Container */}
      <div className="w-full ag-theme-quartz-dark" style={{ height }}>
        <AgGridReact<T>
          rowData={rowData}
          columnDefs={columnDefs}
          defaultColDef={defaultColDef}
          quickFilterText={quickFilterText}
          onGridReady={onGridReady}
          onRowClicked={handleRowClick}
          rowSelection={{ mode: "singleRow", checkboxes: false, enableClickSelection: true }}
          pagination={true}
          paginationPageSize={10}
          paginationPageSizeSelector={[10, 25, 50]}
          animateRows={true}
        />
      </div>
    </div>
  );
}

export default AgGridGovernanceTable;
