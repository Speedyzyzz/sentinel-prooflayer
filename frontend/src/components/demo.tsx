"use client";

import React, { useState } from "react";
import ResponsiveHeroBanner from "./ui/responsive-hero-banner";
import { SentinelCore3D, type SentinelCoreState } from "./SentinelCore3D";

const HeroDemo = () => {
  const [coreState, setCoreState] = useState<SentinelCoreState>("IDLE");

  return (
    <ResponsiveHeroBanner
      badgeLabel="ACTIVE"
      badgeText="Autonomous B2B Mandate & Causal Proof Engine 2026"
      title="Govern Autonomous Spend"
      titleLine2="With Cryptographic Proof"
      description="Enforce deterministic pre-payment guardrails and compile 18-node causal evidence graphs for instant PayPal dispute defense."
      primaryButtonText="Run Judge Scenarios"
      secondaryButtonText="Inspect 3D Core"
      ctaButtonText="Open Studio"
      partnersTitle="Trusted infrastructure standards for autonomous commerce"
    >
      <SentinelCore3D
        coreState={coreState}
        activeHash="9f21ac784b2390a8816c4f1c99f30bde12894101e48f76023cbca747b0e7a718"
        riskIndex={coreState === "BLOCKED" ? 88.5 : coreState === "HUMAN_REVIEW" ? 18.2 : 2.1}
        activeScenarioLabel="MERKLE STATE ARMED // 3D CORE"
        onSelectState={setCoreState}
      />
    </ResponsiveHeroBanner>
  );
};

export default HeroDemo;
