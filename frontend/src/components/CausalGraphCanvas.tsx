"use client";

import React, { useMemo, useCallback } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
  MarkerType,
  Node,
  Edge,
  NodeProps,
} from "@xyflow/react";
import {
  Shield,
  CreditCard,
  Scale,
  UserCheck,
  Building,
  FileSpreadsheet,
  FileText,
  Receipt,
  DollarSign,
  RotateCcw,
  Package,
  Truck,
  Laptop,
  HelpCircle,
  AlertTriangle,
  FolderArchive,
  Award,
  Hash,
} from "lucide-react";
import type { EvidenceGraphData, EvidenceNode, NodeType, EdgeType } from "@/lib/api";

export interface CausalGraphCanvasProps {
  graphData: EvidenceGraphData;
  selectedNodeId?: string;
  onNodeSelect: (node: EvidenceNode) => void;
  filterType?: NodeType | "ALL";
}

// Map each of the 18 node types to institutional icons and color palettes
function getNodeVisuals(type: NodeType) {
  switch (type) {
    case "AGENT_MANDATE":
      return { icon: Shield, borderColor: "border-cyan-500", tagBg: "bg-cyan-950/80 text-cyan-300", accent: "text-cyan-400" };
    case "PAYMENT_INTENT":
      return { icon: CreditCard, borderColor: "border-sky-500", tagBg: "bg-sky-950/80 text-sky-300", accent: "text-sky-400" };
    case "POLICY_DECISION":
      return { icon: Scale, borderColor: "border-purple-500", tagBg: "bg-purple-950/80 text-purple-300", accent: "text-purple-400" };
    case "APPROVAL_RECORD":
      return { icon: UserCheck, borderColor: "border-emerald-500", tagBg: "bg-emerald-950/80 text-emerald-300", accent: "text-emerald-400" };
    case "VENDOR":
      return { icon: Building, borderColor: "border-indigo-500", tagBg: "bg-indigo-950/80 text-indigo-300", accent: "text-indigo-400" };
    case "PURCHASE_ORDER":
      return { icon: FileSpreadsheet, borderColor: "border-blue-500", tagBg: "bg-blue-950/80 text-blue-300", accent: "text-blue-400" };
    case "CONTRACT":
      return { icon: FileText, borderColor: "border-slate-500", tagBg: "bg-slate-900 text-slate-300", accent: "text-slate-400" };
    case "INVOICE":
      return { icon: Receipt, borderColor: "border-teal-500", tagBg: "bg-teal-950/80 text-teal-300", accent: "text-teal-400" };
    case "PAYPAL_ORDER":
      return { icon: CreditCard, borderColor: "border-paypal-blue", tagBg: "bg-blue-950/80 text-blue-300", accent: "text-paypal-cyan" };
    case "PAYPAL_CAPTURE":
      return { icon: DollarSign, borderColor: "border-emerald-400", tagBg: "bg-emerald-950/80 text-emerald-300", accent: "text-emerald-400" };
    case "PAYPAL_REFUND":
      return { icon: RotateCcw, borderColor: "border-amber-500", tagBg: "bg-amber-950/80 text-amber-300", accent: "text-amber-400" };
    case "SHIPMENT":
      return { icon: Package, borderColor: "border-zinc-500", tagBg: "bg-zinc-900 text-zinc-300", accent: "text-zinc-400" };
    case "DELIVERY_CONFIRMATION":
      return { icon: Truck, borderColor: "border-lime-500", tagBg: "bg-lime-950/80 text-lime-300", accent: "text-lime-400" };
    case "CUSTOMER_SESSION":
      return { icon: Laptop, borderColor: "border-violet-500", tagBg: "bg-violet-950/80 text-violet-300", accent: "text-violet-400" };
    case "SUPPORT_TICKET":
      return { icon: HelpCircle, borderColor: "border-orange-500", tagBg: "bg-orange-950/80 text-orange-300", accent: "text-orange-400" };
    case "DISPUTE":
      return { icon: AlertTriangle, borderColor: "border-rose-500", tagBg: "bg-rose-950/80 text-rose-300", accent: "text-rose-400" };
    case "EVIDENCE_DOCUMENT":
      return { icon: FolderArchive, borderColor: "border-fuchsia-500", tagBg: "bg-fuchsia-950/80 text-fuchsia-300", accent: "text-fuchsia-400" };
    case "EVIDENCE_CLAIM":
      return { icon: Award, borderColor: "border-amber-400", tagBg: "bg-amber-950/80 text-amber-300", accent: "text-amber-400" };
    default:
      return { icon: FileText, borderColor: "border-slate-500", tagBg: "bg-slate-900 text-slate-300", accent: "text-slate-400" };
  }
}

// Custom Evidence Node component rendered inside React Flow
function CustomEvidenceNodeComponent({ data, selected }: NodeProps) {
  const nodeData = data as unknown as { raw: EvidenceNode };
  const rawNode = nodeData.raw;
  const visuals = getNodeVisuals(rawNode.type);
  const IconComponent = visuals.icon;

  const shortHash = rawNode.sha256_hash
    ? `${rawNode.sha256_hash.slice(0, 6)}...${rawNode.sha256_hash.slice(-4)}`
    : "";

  return (
    <div
      className={`min-w-[240px] max-w-[280px] bg-sentinel-card/95 border-2 ${
        selected ? "border-paypal-cyan shadow-[0_0_15px_rgba(0,207,222,0.4)]" : visuals.borderColor
      } rounded-xl p-3 shadow-xl backdrop-blur-md transition-all cursor-pointer`}
    >
      <Handle type="target" position={Position.Top} className="!bg-paypal-cyan !w-2.5 !h-2.5" />
      <Handle type="target" position={Position.Left} className="!bg-paypal-cyan !w-2.5 !h-2.5" />

      {/* Header with Type Tag & Icon */}
      <div className="flex items-center justify-between gap-2 mb-2">
        <div className="flex items-center gap-1.5">
          <IconComponent className={`w-4 h-4 ${visuals.accent}`} />
          <span className={`text-[10px] font-mono font-bold uppercase tracking-wider px-2 py-0.5 rounded ${visuals.tagBg}`}>
            {rawNode.type.replace(/_/g, " ")}
          </span>
        </div>
      </div>

      {/* Node Title / Label */}
      <div className="text-xs font-semibold text-slate-100 line-clamp-2 mb-2 leading-snug">
        {rawNode.label}
      </div>

      {/* Footer with Node ID and SHA-256 hash */}
      <div className="flex items-center justify-between pt-2 border-t border-sentinel-border text-[10px] font-mono text-slate-400">
        <span className="text-slate-400 truncate max-w-[120px]">{rawNode.id}</span>
        {shortHash && (
          <span className="inline-flex items-center gap-0.5 text-slate-500">
            <Hash className="w-2.5 h-2.5" />
            {shortHash}
          </span>
        )}
      </div>

      <Handle type="source" position={Position.Bottom} className="!bg-paypal-blue !w-2.5 !h-2.5" />
      <Handle type="source" position={Position.Right} className="!bg-paypal-blue !w-2.5 !h-2.5" />
    </div>
  );
}

const nodeTypes = {
  evidenceNode: CustomEvidenceNodeComponent,
};

// Edge colors based on the 13 causal edge types
function getEdgeColor(type: EdgeType): string {
  switch (type) {
    case "SUPPORTS":
      return "#10B981"; // Emerald
    case "CONTRADICTS":
      return "#EF4444"; // Rose
    case "DISPUTED_BY":
      return "#F43F5E"; // Pink / Red
    case "AUTHORIZED_BY":
      return "#06B6D4"; // Cyan
    case "VALIDATED_BY":
      return "#8B5CF6"; // Purple
    case "MATCHES":
      return "#3B82F6"; // Blue
    case "CAPTURED_AS":
      return "#10B981"; // Green
    case "REQUIRES":
      return "#F59E0B"; // Amber
    case "CITES":
      return "#D946EF"; // Fuchsia
    case "REFERENCES":
    case "PAID_BY":
    case "REFUNDED_BY":
    case "OCCURRED_AT":
    default:
      return "#64748B"; // Slate
  }
}

// Compute deterministic column tier layout for DAG
function computeNodeCoordinates(nodes: EvidenceNode[]): Map<string, { x: number; y: number }> {
  const coords = new Map<string, { x: number; y: number }>();

  const tierMap: Record<NodeType, number> = {
    AGENT_MANDATE: 0,
    PURCHASE_ORDER: 0,
    CONTRACT: 0,
    VENDOR: 0,
    INVOICE: 1,
    PAYMENT_INTENT: 1,
    POLICY_DECISION: 1,
    APPROVAL_RECORD: 2,
    PAYPAL_ORDER: 2,
    PAYPAL_CAPTURE: 3,
    SHIPMENT: 3,
    DELIVERY_CONFIRMATION: 3,
    CUSTOMER_SESSION: 3,
    SUPPORT_TICKET: 4,
    PAYPAL_REFUND: 4,
    DISPUTE: 4,
    EVIDENCE_DOCUMENT: 5,
    EVIDENCE_CLAIM: 5,
  };

  const tierBuckets: Record<number, EvidenceNode[]> = {
    0: [],
    1: [],
    2: [],
    3: [],
    4: [],
    5: [],
  };

  nodes.forEach((node) => {
    const tier = tierMap[node.type] !== undefined ? tierMap[node.type] : 2;
    tierBuckets[tier].push(node);
  });

  const COL_WIDTH = 340;
  const ROW_HEIGHT = 170;

  Object.entries(tierBuckets).forEach(([tierStr, bucketNodes]) => {
    const col = Number(tierStr);
    bucketNodes.forEach((node, row) => {
      coords.set(node.id, {
        x: col * COL_WIDTH + 60,
        y: row * ROW_HEIGHT + 60,
      });
    });
  });

  return coords;
}

export function CausalGraphCanvas({
  graphData,
  selectedNodeId,
  onNodeSelect,
  filterType = "ALL",
}: CausalGraphCanvasProps) {
  // Filter nodes if filterType specified
  const filteredNodes = useMemo(() => {
    if (filterType === "ALL") return graphData.nodes;
    return graphData.nodes.filter((n) => n.type === filterType);
  }, [graphData.nodes, filterType]);

  const activeNodeIds = useMemo(() => new Set(filteredNodes.map((n) => n.id)), [filteredNodes]);

  // Compute Layout Positions
  const coordinates = useMemo(() => computeNodeCoordinates(graphData.nodes), [graphData.nodes]);

  // Transform to React Flow Nodes
  const rfNodes: Node[] = useMemo(() => {
    return filteredNodes.map((n) => {
      const pos = coordinates.get(n.id) || { x: 100, y: 100 };
      return {
        id: n.id,
        type: "evidenceNode",
        position: pos,
        data: { raw: n },
        selected: n.id === selectedNodeId,
      };
    });
  }, [filteredNodes, coordinates, selectedNodeId]);

  // Transform to React Flow Edges
  const rfEdges: Edge[] = useMemo(() => {
    return graphData.edges
      .filter((e) => activeNodeIds.has(e.source) && activeNodeIds.has(e.target))
      .map((e) => {
        const strokeColor = getEdgeColor(e.type);
        return {
          id: e.id,
          source: e.source,
          target: e.target,
          label: e.label,
          type: "smoothstep",
          animated: ["SUPPORTS", "AUTHORIZED_BY", "CAPTURED_AS"].includes(e.type),
          style: {
            stroke: strokeColor,
            strokeWidth: 2,
          },
          labelStyle: {
            fill: "#CBD5E1",
            fontWeight: 500,
            fontSize: 10,
            fontFamily: "monospace",
          },
          labelBgStyle: {
            fill: "#080C15",
            fillOpacity: 0.85,
          },
          labelBgPadding: [4, 2] as [number, number],
          labelBgBorderRadius: 4,
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: strokeColor,
            width: 14,
            height: 14,
          },
        };
      });
  }, [graphData.edges, activeNodeIds]);

  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      const raw = (node.data as any).raw as EvidenceNode;
      if (raw) onNodeSelect(raw);
    },
    [onNodeSelect]
  );

  return (
    <div className="w-full h-full min-h-[560px] bg-sentinel-bg rounded-xl border border-sentinel-border overflow-hidden relative shadow-inner">
      <ReactFlow
        nodes={rfNodes}
        edges={rfEdges}
        nodeTypes={nodeTypes}
        onNodeClick={handleNodeClick}
        fitView
        minZoom={0.2}
        maxZoom={1.5}
        attributionPosition="bottom-right"
      >
        <Background color="#1E2C48" gap={20} size={1} />
        <Controls className="!bg-sentinel-card !border-sentinel-border !text-slate-200 fill-slate-200" />
        <MiniMap
          nodeColor={(n) => {
            const raw = (n.data as any)?.raw as EvidenceNode;
            return raw ? getNodeVisuals(raw.type).borderColor.replace("border-", "#") : "#00CFDE";
          }}
          className="!bg-sentinel-card/90 !border-sentinel-border rounded-lg"
          maskColor="rgba(8, 12, 21, 0.75)"
        />
      </ReactFlow>
    </div>
  );
}

export default CausalGraphCanvas;
