# Sentinel & ProofLayer: 3-Minute Video Demo Script

**Project**: Sentinel & ProofLayer — Agent Mandate Control Plane & Causal Evidence Auto-Defense Engine  
**Event**: PayPal AI Hackathon 2026  
**Format**: 180-second (3-minute) high-energy video walkthrough with live product capture  
**Presenters**: Product Architect / AI Governance Lead  

---

## Visual & Audio Production Breakdown

```
Timeline:
[00:00 - 00:25] THE ENTERPRISE PROBLEM & INTRODUCING SENTINEL
[00:25 - 00:55] SCENARIO 1: AUTONOMOUS PROCUREMENT FAST-PATH ($840.00)
[00:55 - 01:30] SCENARIO 2: HIGH-VALUE CFO ESCALATION & IDEMPOTENCY LOCK ($4,180.50)
[01:30 - 01:55] SCENARIO 3: ROGUE AGENT POLICY BLOCK & 3-TIER KILL SWITCH
[01:55 - 02:35] SCENARIO 4: PROOFLAYER CAUSAL GRAPH & AUTONOMOUS DISPUTE DEFENSE
[02:35 - 03:00] MERKLE AUDIT LEDGER, MCP TOOLS & CLOSING VISION
```

---

### Act 1: The Enterprise Dilemma & Architecture Overview (00:00 – 00:25)

- **[00:00 – 00:10] Visual**: High-resolution zoom into the Executive Dashboard (`/`) showing the Sentinel institutional dark interface, active Mandate pill (`mdt_9f21ac`), live PayPal Sandbox indicator, and the 1-Click Judge Scenario Runner.
  - **Voiceover**: *"Enterprise AI agents are negotiating contracts, hiring vendors, and provisioning cloud resources. But giving an autonomous LLM an unrestricted corporate credit card or direct PayPal API key is terrifying: hallucinations, duplicate invoice attacks, prompt injections, and chargebacks can wipe out enterprise budgets."*
- **[00:10 – 00:25] Visual**: Split screen showing the Sentinel pre-payment control pipeline and the ProofLayer post-payment causal graph architecture.
  - **Voiceover**: *"Meet **Sentinel & ProofLayer**. Sentinel acts as the pre-payment mandate control plane, intercepting every payment intent with deterministic PO matching and transparent risk scoring. ProofLayer acts as the post-payment causal defense engine, automatically resolving PayPal disputes with verifiable evidence graphs."*

---

### Act 2: Scenario 1 — Autonomous Fast-Path Procurement (00:25 – 00:55)

- **[00:25 – 00:35] Visual**: Click on **"Scenario 1: Auto-Approved Procurement ($840.00)"** in the 1-Click Scenario Runner.
  - **Voiceover**: *"Let's test our procurement agent, Atlas. Atlas needs to pay Data Labeling Co for 20,000 dataset annotations under Mandate 9f21ac."*
- **[00:35 – 00:45] Visual**: Trace steps animating in real-time: `PROPOSED -> POLICY_CHECK -> EVIDENCE_VALIDATION -> AUTO_APPROVED -> EXECUTING -> AUTHORIZED -> CAPTURED -> RECONCILED`.
  - **Voiceover**: *"Watch Sentinel evaluate the invoice against Purchase Order 4410. Our deterministic matching formula computes an alignment score of 0.97. The weighted risk score is just 0.08. Because $840 is under the $1,000 auto-approval threshold, Sentinel clears the transaction autonomously."*
- **[00:45 – 00:55] Visual**: Navigate to Transactions Ledger (`/transactions`). Show the live PayPal Authorize and Capture receipts (`2GG279541U053982Y`) with green "RECONCILED" status badge.
  - **Voiceover**: *"Within milliseconds, PayPal Orders v2 executes the authorization and capture, locking the receipt into an append-only Merkle audit block. Zero human latency."*

---

### Act 3: Scenario 2 — High-Value CFO Escalation & Atomic Idempotency (00:55 – 01:30)

- **[00:55 – 01:05] Visual**: Click **"Scenario 2: High-Value Escalation ($4,180.50)"**. Intent transitions from `PROPOSED` to `HUMAN_REVIEW`.
  - **Voiceover**: *"Now, Atlas attempts a high-value purchase: $4,180.50 for GPU cluster compute from Cloud Compute Inc. The PO baseline was $4,150.00."*
- **[01:05 – 01:15] Visual**: Zoom in on the Risk Gauge and PO Matching card. Variance is flagged at `+0.73%` (well within the 2% policy tolerance), matching score is `0.96`. But because the amount exceeds $1,000, it parks safely in the Approval Queue (`/approvals`).
  - **Voiceover**: *"Sentinel detects that the invoice amount exceeds the $1,000 autonomous threshold while staying under the $5,000 maximum cap. Sentinel parks the transaction in the executive approval queue."*
- **[01:15 – 01:30] Visual**: Log in as CFO Maya Lin (`usr_maya`, $100k authority). Click "Approve & Execute". Show the atomic idempotency lock (`idempotency_key` and `PayPal-Request-Id`) preventing double charges, transitioning to `CAPTURED`.
  - **Voiceover**: *"Analyst Daniel only has a $2,500 limit and is blocked. But CFO Maya provides cryptographic approval. Sentinel acquires an atomic idempotency lock, executes Authorize -> Capture against PayPal, and settles the funds. No risk of accidental double charges."*

---

### Act 4: Scenario 3 — Blocked Vendor & 3-Tier Kill Switch (01:30 – 01:55)

- **[01:30 – 01:42] Visual**: Click **"Scenario 3: Blocked Vendor ($2,500.00)"**. Intent attempts to pay `FastCrypto Services`. Immediate red transition to `BLOCKED`.
  - **Voiceover**: *"What happens if Atlas is compromised or hallucinates? Atlas proposes a $2,500 payment to FastCrypto Services. Sentinel instantly blocks it at the policy gate: FastCrypto is non-allowlisted and crypto is a blocked category. Crucially: exactly ZERO PayPal API calls are made."*
- **[01:42 – 01:55] Visual**: Click the **3-Tier Kill Switch** header in `layout.tsx`. Show Level 1 (Intent halt), Level 2 (Agent revocation), and Level 3 (Mandate freeze). Trigger Mandate freeze.
  - **Voiceover**: *"Need an emergency stop? Our 3-tier kill switch lets operators halt a single intent, revoke an agent, or freeze an entire mandate. And Sentinel guarantees our core accounting invariant: freezing a mandate voids uncaptured authorizations, but preserves all already-captured PayPal transactions."*

---

### Act 5: Scenario 4 — ProofLayer Causal Graph & Auto-Dispute Defense (01:55 – 02:35)

- **[01:55 – 02:10] Visual**: Click **"Scenario 4: Dispute Webhook Simulation"**. An inbound `CUSTOMER.DISPUTE.CREATED` webhook arrives for dispute `PP-D-99412` claiming "Item Not Received". Show deduplication test: sending the webhook twice ignores the duplicate event.
  - **Voiceover**: *"Post-payment, a customer opens a PayPal dispute: Item Not Received on our GPU compute transaction. Traditional merchants have days of panic. ProofLayer responds autonomously in seconds."*
- **[02:10 – 02:22] Visual**: Transition to the **Evidence Graph Explorer** (`/evidence`). Interactive 18-node causal graph rendered with `@xyflow/react` showing the connections between Mandate, PO, Invoice, CFO Approval, PayPal Capture, and Customer Session.
  - **Voiceover**: *"ProofLayer traverses our 18-node causal property graph. Because this is cloud compute with no physical shipping, ProofLayer deterministically substitutes authenticated digital session telemetry — node session_118 — proving 84 hours of active cluster access."*
- **[02:22 – 02:35] Visual**: Navigate to Dispute Command Center (`/disputes`). Show Evidence Readiness Score calculated at `0.94` across 6 dimensions. Inspect the defense narrative: every single sentence contains verified inline citations (`[ev_*]`). Click "Submit to PayPal Disputes API".
  - **Voiceover**: *"With an Evidence Readiness score of 0.94, ProofLayer synthesizes a grounded defense brief where 100% of factual sentences include verified inline citations, and submits it directly to PayPal's Disputes API."*

---

### Act 6: Merkle Ledger, MCP Server & Conclusion (02:35 – 03:00)

- **[02:35 – 02:48] Visual**: Open Cryptographic Audit Trail (`/audit`). Click "Verify Hash Chain Integrity". Show green checkmark: 100% of blocks verified via SHA-256 Merkle root. Show the 12 tools exposed by the Model Context Protocol (MCP) server.
  - **Voiceover**: *"Every action, decision, and signature is chained in an append-only SHA-256 Merkle audit ledger with automated tamper detection. Plus, our complete 12-tool MCP server allows any LLM agent to interact with Sentinel natively."*
- **[02:48 – 03:00] Visual**: Return to Executive Dashboard with all 4 scenarios checked green. Display GitHub repository, Devpost link, and team logo.
  - **Voiceover**: *"Sentinel & ProofLayer: Giving enterprise AI agents the autonomy to transact on PayPal, with the governance, safety, and evidence guarantees CFOs demand. Thank you!"*

---

## Documentation Cross-References

- [Root Project README](../README.md): System architecture, mathematical formulas, API reference, and quickstart.
- [System Architecture & Security Blueprint](architecture.md): Dual-engine specifications, 18-node causal graph, 7 PayPal dispute reasons mapping, and Merkle ledger.
- [Canonical 12-State Machine & 3-Tier Kill Switch](state-machine.md): Formal state transition matrices and emergency kill switch rules.
- [Devpost Submission Narrative](devpost.md): Official Devpost hackathon submission narrative.
