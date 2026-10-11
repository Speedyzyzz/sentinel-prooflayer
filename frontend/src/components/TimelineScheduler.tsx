"use client";

import React, { useState, useEffect, useMemo } from "react";
import { Clock, ShieldCheck, CheckCircle2, AlertCircle, ArrowRight, Hourglass } from "lucide-react";

export interface TimelineSchedulerProps {
  deadlineDate: string; // ISO 8601
  currentStage: "INGESTION" | "GRAPH_COMPILED" | "BRIEF_READY" | "SUBMITTED" | "RESOLVED";
  title?: string;
  onDeadlineExpiring?: () => void;
}

interface Milestone {
  key: "INGESTION" | "GRAPH_COMPILED" | "BRIEF_READY" | "SUBMITTED" | "RESOLVED";
  title: string;
  subtitle: string;
}

const MILESTONES: Milestone[] = [
  { key: "INGESTION", title: "1. Webhook Ingested", subtitle: "HMAC verified & deduplicated" },
  { key: "GRAPH_COMPILED", title: "2. Causal Graph", subtitle: "18-node DAG constructed" },
  { key: "BRIEF_READY", title: "3. Defense Brief", subtitle: "Bracketed citations & readiness" },
  { key: "SUBMITTED", title: "4. PayPal Submission", subtitle: "Disputes API v1 dispatched" },
  { key: "RESOLVED", title: "5. Final Adjudication", subtitle: "PayPal settlement confirmed" },
];

export function TimelineScheduler({
  deadlineDate,
  currentStage,
  title = "PayPal Dispute Resolution SLA Timeline",
  onDeadlineExpiring,
}: TimelineSchedulerProps) {
  const [timeLeft, setTimeLeft] = useState<{
    days: number;
    hours: number;
    minutes: number;
    seconds: number;
    totalSeconds: number;
    expired: boolean;
  }>({
    days: 0,
    hours: 0,
    minutes: 0,
    seconds: 0,
    totalSeconds: 0,
    expired: false,
  });

  useEffect(() => {
    const calculateTime = () => {
      const target = new Date(deadlineDate).getTime();
      const now = Date.now();
      const difference = target - now;

      if (difference <= 0) {
        setTimeLeft({
          days: 0,
          hours: 0,
          minutes: 0,
          seconds: 0,
          totalSeconds: 0,
          expired: true,
        });
        if (onDeadlineExpiring) onDeadlineExpiring();
        return;
      }

      const days = Math.floor(difference / (1000 * 60 * 60 * 24));
      const hours = Math.floor((difference % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
      const minutes = Math.floor((difference % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((difference % (1000 * 60)) / 1000);

      setTimeLeft({
        days,
        hours,
        minutes,
        seconds,
        totalSeconds: Math.floor(difference / 1000),
        expired: false,
      });
    };

    calculateTime();
    const interval = setInterval(calculateTime, 1000);
    return () => clearInterval(interval);
  }, [deadlineDate, onDeadlineExpiring]);

  // Urgency styling: Green (>5 days), Amber (2-5 days), Crimson (<48 hours)
  const urgencyStatus = useMemo(() => {
    if (timeLeft.expired) {
      return {
        badge: "SLA EXPIRED",
        badgeClass: "bg-rose-950/80 text-rose-400 border-rose-800",
        clockClass: "text-rose-500",
        boxBorder: "border-rose-900/60",
      };
    }
    const days = timeLeft.days;
    if (days >= 5) {
      return {
        badge: "ON SCHEDULE",
        badgeClass: "bg-emerald-950/80 text-emerald-400 border-emerald-800",
        clockClass: "text-emerald-400",
        boxBorder: "border-emerald-900/60",
      };
    }
    if (days >= 2) {
      return {
        badge: "URGENT (2–5 DAYS)",
        badgeClass: "bg-amber-950/80 text-amber-400 border-amber-800",
        clockClass: "text-amber-400",
        boxBorder: "border-amber-900/60",
      };
    }
    return {
      badge: "CRITICAL (<48 HOURS)",
      badgeClass: "bg-rose-950/80 text-rose-400 border-rose-800 animate-pulse",
      clockClass: "text-rose-400",
      boxBorder: "border-rose-900/60",
    };
  }, [timeLeft]);

  const currentStageIndex = useMemo(() => {
    const idx = MILESTONES.findIndex((m) => m.key === currentStage);
    return idx >= 0 ? idx : 0;
  }, [currentStage]);

  return (
    <div className={`w-full bg-sentinel-card border ${urgencyStatus.boxBorder} rounded-xl p-5 shadow-lg flex flex-col gap-5 transition-colors`}>
      {/* Header and Countdown */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-sentinel-border pb-4">
        <div>
          <div className="flex items-center gap-2">
            <Clock className={`w-4 h-4 ${urgencyStatus.clockClass}`} />
            <h3 className="text-sm font-semibold text-slate-100">{title}</h3>
            <span className={`px-2 py-0.5 rounded-full text-xs font-mono font-semibold border ${urgencyStatus.badgeClass}`}>
              {urgencyStatus.badge}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            PayPal Evidence Submission Window closes:{" "}
            <span className="font-mono text-slate-300">
              {new Date(deadlineDate).toLocaleString("en-US", {
                year: "numeric",
                month: "short",
                day: "numeric",
                hour: "2-digit",
                minute: "2-digit",
                timeZoneName: "short",
              })}
            </span>
          </p>
        </div>

        {/* Live Countdown Display */}
        <div className="flex items-center gap-2 font-mono">
          <div className="flex flex-col items-center bg-sentinel-bg border border-sentinel-border px-3 py-1.5 rounded-lg min-w-14">
            <span className={`text-base font-bold ${urgencyStatus.clockClass}`}>
              {String(timeLeft.days).padStart(2, "0")}
            </span>
            <span className="text-[10px] text-slate-500 uppercase tracking-wider">Days</span>
          </div>
          <span className="text-slate-600 font-bold">:</span>
          <div className="flex flex-col items-center bg-sentinel-bg border border-sentinel-border px-3 py-1.5 rounded-lg min-w-14">
            <span className={`text-base font-bold ${urgencyStatus.clockClass}`}>
              {String(timeLeft.hours).padStart(2, "0")}
            </span>
            <span className="text-[10px] text-slate-500 uppercase tracking-wider">Hours</span>
          </div>
          <span className="text-slate-600 font-bold">:</span>
          <div className="flex flex-col items-center bg-sentinel-bg border border-sentinel-border px-3 py-1.5 rounded-lg min-w-14">
            <span className={`text-base font-bold ${urgencyStatus.clockClass}`}>
              {String(timeLeft.minutes).padStart(2, "0")}
            </span>
            <span className="text-[10px] text-slate-500 uppercase tracking-wider">Mins</span>
          </div>
          <span className="text-slate-600 font-bold">:</span>
          <div className="flex flex-col items-center bg-sentinel-bg border border-sentinel-border px-3 py-1.5 rounded-lg min-w-14">
            <span className={`text-base font-bold ${urgencyStatus.clockClass}`}>
              {String(timeLeft.seconds).padStart(2, "0")}
            </span>
            <span className="text-[10px] text-slate-500 uppercase tracking-wider">Secs</span>
          </div>
        </div>
      </div>

      {/* Checkpoints Flow */}
      <div className="grid grid-cols-1 sm:grid-cols-5 gap-3 relative">
        {MILESTONES.map((milestone, index) => {
          const isCompleted = index < currentStageIndex;
          const isCurrent = index === currentStageIndex;
          const isPending = index > currentStageIndex;

          let cardBorder = "border-slate-800 bg-sentinel-bg/50 text-slate-500";
          let icon = <Hourglass className="w-4 h-4 text-slate-500" />;

          if (isCompleted) {
            cardBorder = "border-emerald-800/80 bg-emerald-950/30 text-emerald-300";
            icon = <CheckCircle2 className="w-4 h-4 text-emerald-400" />;
          } else if (isCurrent) {
            cardBorder = "border-paypal-cyan bg-cyan-950/40 text-cyan-200 ring-1 ring-paypal-cyan";
            icon = <ShieldCheck className="w-4 h-4 text-paypal-cyan animate-pulse" />;
          }

          return (
            <div
              key={milestone.key}
              className={`p-3 rounded-lg border ${cardBorder} flex flex-col justify-between gap-2 transition-all relative`}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold">{milestone.title}</span>
                {icon}
              </div>
              <p className="text-[11px] text-slate-400 leading-tight">{milestone.subtitle}</p>
              <div className="text-[10px] font-mono uppercase tracking-wider font-semibold">
                {isCompleted && <span className="text-emerald-400">Completed</span>}
                {isCurrent && <span className="text-paypal-cyan font-bold">Active Stage</span>}
                {isPending && <span className="text-slate-500">Upcoming</span>}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default TimelineScheduler;
