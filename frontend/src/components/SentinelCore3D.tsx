"use client";

import React, { useEffect, useRef, useState } from "react";
import { Copy, Check, ShieldAlert, ShieldCheck, Clock, Activity } from "lucide-react";

export type SentinelCoreState = "IDLE" | "AUTO_APPROVED" | "HUMAN_REVIEW" | "BLOCKED";

export interface SentinelCore3DProps {
  coreState: SentinelCoreState;
  activeHash: string;
  riskIndex: number; // 0 to 100
  activeScenarioLabel?: string;
  onSelectState?: (state: SentinelCoreState) => void;
}

interface Vec3 {
  x: number;
  y: number;
  z: number;
}

interface Particle3D {
  theta: number;
  phi: number;
  radius: number;
  baseRadius: number;
  speed: number;
  size: number;
  phase: number;
}

function createGeodesicWireframe(): { vertices: Vec3[]; edges: [number, number][]; innerVertices: Vec3[] } {
  const t = (1 + Math.sqrt(5)) / 2;
  const rawVerts: [number, number, number][] = [
    [-1, t, 0], [1, t, 0], [-1, -t, 0], [1, -t, 0],
    [0, -1, t], [0, 1, t], [0, -1, -t], [0, 1, -t],
    [t, 0, -1], [t, 0, 1], [-t, 0, -1], [-t, 0, 1],
  ];

  const normalize = (v: Vec3, scale = 1): Vec3 => {
    const len = Math.sqrt(v.x * v.x + v.y * v.y + v.z * v.z) || 1;
    return { x: (v.x / len) * scale, y: (v.y / len) * scale, z: (v.z / len) * scale };
  };

  const baseVertices: Vec3[] = rawVerts.map(([x, y, z]) => normalize({ x, y, z }, 1.0));

  const faces: [number, number, number][] = [
    [0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11],
    [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8],
    [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9],
    [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1],
  ];

  const vertices: Vec3[] = [...baseVertices];
  const midpointCache = new Map<string, number>();

  const getMidpoint = (i1: number, i2: number): number => {
    const key = i1 < i2 ? `${i1}_${i2}` : `${i2}_${i1}`;
    const cached = midpointCache.get(key);
    if (cached !== undefined) return cached;
    const v1 = vertices[i1];
    const v2 = vertices[i2];
    const mid = normalize({
      x: (v1.x + v2.x) * 0.5,
      y: (v1.y + v2.y) * 0.5,
      z: (v1.z + v2.z) * 0.5,
    });
    const idx = vertices.length;
    vertices.push(mid);
    midpointCache.set(key, idx);
    return idx;
  };

  const subFaces: [number, number, number][] = [];
  for (const [a, b, c] of faces) {
    const ab = getMidpoint(a, b);
    const bc = getMidpoint(b, c);
    const ca = getMidpoint(c, a);
    subFaces.push([a, ab, ca], [b, bc, ab], [c, ca, bc], [ab, bc, ca]);
  }

  const edgeSet = new Set<string>();
  const edges: [number, number][] = [];
  const addEdge = (u: number, v: number) => {
    const key = u < v ? `${u}_${v}` : `${v}_${u}`;
    if (!edgeSet.has(key)) {
      edgeSet.add(key);
      edges.push([u, v]);
    }
  };

  for (const [a, b, c] of subFaces) {
    addEdge(a, b);
    addEdge(b, c);
    addEdge(c, a);
  }

  const innerVertices = baseVertices.map((v) => normalize(v, 0.52));
  return { vertices, edges, innerVertices };
}

const GEOMETRY = createGeodesicWireframe();

export function SentinelCore3D({
  coreState,
  activeHash,
  riskIndex,
  activeScenarioLabel = "MERKLE STATE ARMED",
  onSelectState,
}: SentinelCore3DProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [copiedHash, setCopiedHash] = useState(false);

  const pointerTarget = useRef({ rx: 0.22, ry: 0.35 });
  const springCurrent = useRef({ rx: 0.22, ry: 0.35, vx: 0, vy: 0 });
  const stateRef = useRef<SentinelCoreState>(coreState);
  const flashIntensityRef = useRef<number>(0);

  useEffect(() => {
    stateRef.current = coreState;
    flashIntensityRef.current = 1.0;
  }, [coreState]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const particles: Particle3D[] = Array.from({ length: 96 }, (_, i) => ({
      theta: (i * 2.39996) % (Math.PI * 2),
      phi: Math.acos(1 - (2 * (i + 0.5)) / 96),
      radius: 1.15 + (i % 9) * 0.14,
      baseRadius: 1.15 + (i % 9) * 0.14,
      speed: 0.38 + (i % 7) * 0.08,
      size: 1.3 + (i % 3) * 0.65,
      phase: i * 0.41,
    }));

    let animId = 0;
    let lastTime = performance.now();
    let autoAngleY = 0;
    let autoAngleZ = 0;

    const handleResize = () => {
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.max(300, Math.floor(rect.width * dpr));
      canvas.height = Math.max(260, Math.floor(rect.height * dpr));
    };

    handleResize();
    window.addEventListener("resize", handleResize);

    const rotatePoint = (v: Vec3, rx: number, ry: number, rz: number): Vec3 => {
      const cosX = Math.cos(rx);
      const sinX = Math.sin(rx);
      const y1 = v.y * cosX - v.z * sinX;
      const z1 = v.y * sinX + v.z * cosX;

      const cosY = Math.cos(ry);
      const sinY = Math.sin(ry);
      const x2 = v.x * cosY + z1 * sinY;
      const z2 = -v.x * sinY + z1 * cosY;

      const cosZ = Math.cos(rz);
      const sinZ = Math.sin(rz);
      const x3 = x2 * cosZ - y1 * sinZ;
      const y3 = x2 * sinZ + y1 * cosZ;

      return { x: x3, y: y3, z: z2 };
    };

    const render = (now: number) => {
      const dt = Math.min(0.05, (now - lastTime) / 1000);
      lastTime = now;

      const mode = stateRef.current;
      flashIntensityRef.current = Math.max(0, flashIntensityRef.current - dt * 1.45);
      const flash = flashIntensityRef.current;

      const stiffness = 300;
      const damping = 25;
      const sp = springCurrent.current;
      const ax = (pointerTarget.current.rx - sp.rx) * stiffness - sp.vx * damping;
      const ay = (pointerTarget.current.ry - sp.ry) * stiffness - sp.vy * damping;
      sp.vx += ax * dt;
      sp.vy += ay * dt;
      sp.rx += sp.vx * dt;
      sp.ry += sp.vy * dt;

      const rotSpeed =
        mode === "AUTO_APPROVED"
          ? 1.35
          : mode === "BLOCKED"
          ? 2.2 * (flash > 0.3 ? -0.6 : 0.45)
          : mode === "HUMAN_REVIEW"
          ? 0.25
          : 0.42;

      autoAngleY += dt * rotSpeed;
      autoAngleZ += dt * rotSpeed * 0.35;

      const w = canvas.width;
      const h = canvas.height;
      const cx = w * 0.5;
      const cy = h * 0.48;
      const baseScale = Math.min(w, h) * 0.275;

      ctx.clearRect(0, 0, w, h);

      let primaryRgb = "6, 182, 212";
      let secondaryRgb = "16, 185, 129";
      if (mode === "AUTO_APPROVED") {
        primaryRgb = "16, 185, 129";
        secondaryRgb = "6, 182, 212";
      } else if (mode === "HUMAN_REVIEW") {
        primaryRgb = "245, 158, 11";
        secondaryRgb = "251, 191, 36";
      } else if (mode === "BLOCKED") {
        primaryRgb = "239, 68, 68";
        secondaryRgb = "6, 182, 212";
      }

      const haloGrad = ctx.createRadialGradient(cx, cy, baseScale * 0.08, cx, cy, baseScale * 1.55);
      haloGrad.addColorStop(0, `rgba(${primaryRgb}, ${0.22 + flash * 0.22})`);
      haloGrad.addColorStop(0.45, `rgba(${secondaryRgb}, 0.07)`);
      haloGrad.addColorStop(1, "rgba(5, 5, 7, 0)");
      ctx.fillStyle = haloGrad;
      ctx.beginPath();
      ctx.arc(cx, cy, baseScale * 1.55, 0, Math.PI * 2);
      ctx.fill();

      if (flash > 0.04) {
        const pulseRadius = baseScale * (0.85 + (1 - flash) * 0.95);
        ctx.strokeStyle = `rgba(${primaryRgb}, ${flash * 0.65})`;
        ctx.lineWidth = 1.8;
        ctx.beginPath();
        ctx.arc(cx, cy, pulseRadius, 0, Math.PI * 2);
        ctx.stroke();
      }

      const rx = sp.rx + Math.sin(now * 0.0007) * 0.08;
      const ry = sp.ry + autoAngleY;
      const rz = autoAngleZ;

      const breathScale =
        mode === "BLOCKED" && flash > 0.25
          ? 1.0 + Math.sin(now * 0.06) * 0.07
          : 1.0 + Math.sin(now * 0.0025) * 0.025;

      const project = (v: Vec3): { x: number; y: number; z: number; depthScale: number } => {
        const fov = 3.4;
        const depth = fov / (fov - v.z);
        return {
          x: cx + v.x * baseScale * breathScale * depth,
          y: cy + v.y * baseScale * breathScale * depth,
          z: v.z,
          depthScale: depth,
        };
      };

      const projectedVerts = GEOMETRY.vertices.map((v) => project(rotatePoint(v, rx, ry, rz)));
      const projectedInner = GEOMETRY.innerVertices.map((v) =>
        project(rotatePoint(v, -rx * 0.8, -ry * 1.3, rz * 0.9))
      );

      ctx.lineWidth = 0.9;
      for (let i = 0; i < projectedInner.length; i++) {
        for (let j = i + 1; j < projectedInner.length; j++) {
          const p1 = projectedInner[i];
          const p2 = projectedInner[j];
          const distSq =
            Math.pow(GEOMETRY.innerVertices[i].x - GEOMETRY.innerVertices[j].x, 2) +
            Math.pow(GEOMETRY.innerVertices[i].y - GEOMETRY.innerVertices[j].y, 2) +
            Math.pow(GEOMETRY.innerVertices[i].z - GEOMETRY.innerVertices[j].z, 2);
          if (distSq < 0.42) {
            ctx.strokeStyle = `rgba(${secondaryRgb}, 0.22)`;
            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.stroke();
          }
        }
      }

      const sortedEdges = GEOMETRY.edges
        .map(([u, v]) => {
          const p1 = projectedVerts[u];
          const p2 = projectedVerts[v];
          return { p1, p2, zAvg: (p1.z + p2.z) * 0.5 };
        })
        .sort((a, b) => a.zAvg - b.zAvg);

      const aberrationPx = mode === "BLOCKED" ? 2.5 + flash * 6.5 : 0;

      for (const edge of sortedEdges) {
        const { p1, p2, zAvg } = edge;
        const alpha = Math.max(0.1, Math.min(0.88, (zAvg + 1.25) / 2.2));

        if (aberrationPx > 0.3 && zAvg > -0.2) {
          ctx.strokeStyle = `rgba(239, 68, 68, ${alpha * 0.75})`;
          ctx.lineWidth = 1.3;
          ctx.beginPath();
          ctx.moveTo(p1.x - aberrationPx, p1.y);
          ctx.lineTo(p2.x - aberrationPx, p2.y);
          ctx.stroke();

          ctx.strokeStyle = `rgba(6, 182, 212, ${alpha * 0.55})`;
          ctx.beginPath();
          ctx.moveTo(p1.x + aberrationPx, p1.y);
          ctx.lineTo(p2.x + aberrationPx, p2.y);
          ctx.stroke();
        }

        ctx.strokeStyle = `rgba(${primaryRgb}, ${alpha * (0.65 + flash * 0.35)})`;
        ctx.lineWidth = zAvg > 0.15 ? 1.45 : 0.85;
        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.stroke();
      }

      for (const p of projectedVerts) {
        if (p.z > -0.45) {
          const nodeAlpha = Math.max(0.2, Math.min(0.95, (p.z + 1.1) / 2.0));
          ctx.fillStyle = `rgba(249, 250, 251, ${nodeAlpha})`;
          ctx.beginPath();
          ctx.arc(p.x, p.y, 1.7 * p.depthScale, 0, Math.PI * 2);
          ctx.fill();
        }
      }

      for (const pt of particles) {
        if (mode === "AUTO_APPROVED") {
          pt.radius -= dt * pt.speed * 1.45;
          pt.theta += dt * pt.speed * 1.8;
          if (pt.radius < 0.12) pt.radius = pt.baseRadius + 0.55;
        } else if (mode === "HUMAN_REVIEW") {
          pt.theta += dt * pt.speed * 0.55;
          pt.phi += (Math.PI * 0.5 - pt.phi) * dt * 2.4;
          pt.radius += (1.28 - pt.radius) * dt * 2.0;
        } else if (mode === "BLOCKED") {
          const targetR = pt.baseRadius + 0.45 + flash * 0.55;
          pt.radius += (targetR - pt.radius) * dt * 5.5;
          pt.theta -= dt * pt.speed * 1.6;
        } else {
          pt.radius -= dt * pt.speed * 0.38;
          pt.theta += dt * pt.speed * 0.65;
          if (pt.radius < 0.35) {
            pt.radius = pt.baseRadius + 0.4;
            pt.phi = Math.acos(Math.sin(now * 0.001 + pt.phase));
          }
        }

        const vx = pt.radius * Math.sin(pt.phi) * Math.cos(pt.theta);
        const vy = pt.radius * Math.cos(pt.phi);
        const vz = pt.radius * Math.sin(pt.phi) * Math.sin(pt.theta);

        const rotatedPt = rotatePoint({ x: vx, y: vy, z: vz }, rx * 0.6, ry * 0.7, 0);
        const projPt = project(rotatedPt);
        const pAlpha = Math.max(0.18, Math.min(0.95, (projPt.z + 1.6) / 2.8));

        ctx.fillStyle =
          pt.phase % 2 > 1
            ? `rgba(${primaryRgb}, ${pAlpha})`
            : `rgba(${secondaryRgb}, ${pAlpha * 0.85})`;
        ctx.beginPath();
        ctx.arc(projPt.x, projPt.y, pt.size * projPt.depthScale, 0, Math.PI * 2);
        ctx.fill();
      }

      animId = window.requestAnimationFrame(render);
    };

    animId = window.requestAnimationFrame(render);
    return () => {
      window.cancelAnimationFrame(animId);
      window.removeEventListener("resize", handleResize);
    };
  }, []);

  const handlePointerMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const nx = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    const ny = ((e.clientY - rect.top) / rect.height) * 2 - 1;
    pointerTarget.current = {
      rx: 0.22 + ny * 0.65,
      ry: 0.35 + nx * 0.85,
    };
  };

  const handlePointerLeave = () => {
    pointerTarget.current = { rx: 0.22, ry: 0.35 };
  };

  const copyHash = () => {
    navigator.clipboard?.writeText(activeHash);
    setCopiedHash(true);
    setTimeout(() => setCopiedHash(false), 1600);
  };

  const stateBadgeConfig = {
    IDLE: {
      label: "MONITORING // NOMINAL",
      color: "text-[#06B6D4] border-[#06B6D4]/40 bg-[#06B6D4]/10",
      icon: Activity,
    },
    AUTO_APPROVED: {
      label: "FAST-PATH // AUTO-APPROVED",
      color: "text-[#10B981] border-[#10B981]/40 bg-[#10B981]/10",
      icon: ShieldCheck,
    },
    HUMAN_REVIEW: {
      label: "EQUATORIAL HOLD // CFO REVIEW",
      color: "text-[#F59E0B] border-[#F59E0B]/40 bg-[#F59E0B]/10",
      icon: Clock,
    },
    BLOCKED: {
      label: "CONTAINMENT PULSE // BLOCKED",
      color: "text-[#EF4444] border-[#EF4444]/50 bg-[#EF4444]/15",
      icon: ShieldAlert,
    },
  }[coreState];

  const StateIcon = stateBadgeConfig.icon;

  return (
    <div
      onMouseMove={handlePointerMove}
      onMouseLeave={handlePointerLeave}
      className="relative w-full h-[380px] sm:h-[420px] rounded-2xl tactical-double-bezel overflow-hidden select-none flex flex-col justify-between p-4 sm:p-5 group"
    >
      <div className="relative z-10 flex flex-wrap items-center justify-between gap-2 pointer-events-none">
        <div className="flex items-center gap-2.5">
          <span
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-mono font-semibold border ${stateBadgeConfig.color}`}
          >
            <StateIcon className="w-3.5 h-3.5" />
            {stateBadgeConfig.label}
          </span>
          <span className="hidden sm:inline-block text-[11px] font-mono text-[#9CA3AF]">
            {activeScenarioLabel}
          </span>
        </div>

        {onSelectState && (
          <div className="flex items-center gap-1 pointer-events-auto bg-[#050507]/85 border border-white/[0.07] rounded-lg p-1 backdrop-blur-md">
            {(["IDLE", "AUTO_APPROVED", "HUMAN_REVIEW", "BLOCKED"] as SentinelCoreState[]).map((st) => (
              <button
                key={st}
                onClick={() => onSelectState(st)}
                className={`px-2 py-0.5 rounded text-[10px] font-mono transition-colors ${
                  coreState === st
                    ? st === "BLOCKED"
                      ? "bg-[#EF4444]/25 text-[#EF4444] border border-[#EF4444]/40 font-bold"
                      : st === "HUMAN_REVIEW"
                      ? "bg-[#F59E0B]/25 text-[#F59E0B] border border-[#F59E0B]/40 font-bold"
                      : st === "AUTO_APPROVED"
                      ? "bg-[#10B981]/25 text-[#10B981] border border-[#10B981]/40 font-bold"
                      : "bg-[#06B6D4]/25 text-[#06B6D4] border border-[#06B6D4]/40 font-bold"
                    : "text-[#9CA3AF] hover:text-[#F9FAFB]"
                }`}
              >
                {st === "IDLE" ? "IDLE" : st === "AUTO_APPROVED" ? "APPROVE" : st === "HUMAN_REVIEW" ? "CFO" : "BLOCK"}
              </button>
            ))}
          </div>
        )}
      </div>

      <canvas
        ref={canvasRef}
        className="absolute inset-0 w-full h-full cursor-grab active:cursor-grabbing"
      />

      <div className="relative z-10 grid grid-cols-1 sm:grid-cols-12 gap-3 items-center bg-[#050507]/85 border border-white/[0.08] backdrop-blur-md rounded-xl p-3 shadow-island">
        <div className="sm:col-span-7 flex items-center justify-between gap-2 border-b sm:border-b-0 sm:border-r border-white/[0.07] pb-2 sm:pb-0 sm:pr-3">
          <div className="min-w-0">
            <div className="text-[10px] font-mono uppercase tracking-wider text-[#4B5563]">
              ACTIVE MERKLE ROOT // SHA-256 VERIFIED
            </div>
            <div className="text-xs font-mono text-[#06B6D4] truncate mt-0.5">{activeHash}</div>
          </div>
          <button
            onClick={copyHash}
            title="Copy Merkle Root Hash"
            className="shrink-0 px-2.5 py-1.5 rounded-lg bg-[#111317] hover:bg-white/[0.08] border border-white/[0.07] text-[11px] font-mono text-[#F9FAFB] flex items-center gap-1 tactical-push-btn"
          >
            {copiedHash ? (
              <>
                <Check className="w-3.5 h-3.5 text-[#10B981]" />
                <span className="text-[#10B981]">Copied!</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5 text-[#9CA3AF]" />
                <span>Copy</span>
              </>
            )}
          </button>
        </div>

        <div className="sm:col-span-5 flex flex-col gap-1.5">
          <div className="flex items-center justify-between text-[11px] font-mono">
            <span className="text-[#9CA3AF]">THREAT LEVEL INDEX</span>
            <span
              className={`font-bold ${
                riskIndex >= 50
                  ? "text-[#EF4444]"
                  : riskIndex >= 15
                  ? "text-[#F59E0B]"
                  : "text-[#10B981]"
              }`}
            >
              {riskIndex.toFixed(1)}% RISK
            </span>
          </div>
          <div className="w-full h-2 rounded-full bg-[#111317] border border-white/[0.06] overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                riskIndex >= 50
                  ? "bg-[#EF4444]"
                  : riskIndex >= 15
                  ? "bg-[#F59E0B]"
                  : "bg-[#10B981]"
              }`}
              style={{ width: `${Math.max(4, Math.min(100, riskIndex))}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

export default SentinelCore3D;
