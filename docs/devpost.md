# Devpost Project Submission: Sentinel & ProofLayer

**Tagline**: Autonomous Agent Mandate Control Plane (Sentinel) & Causal Pre-Dispute Evidence Auto-Defense Engine (ProofLayer) for Enterprise PayPal Commerce.

---

## 1. Inspiration

As generative AI and agentic frameworks (AutoGPT, LangGraph, CrewAI) mature, enterprises are transitioning from conversational bots to autonomous economic agents. AI agents are now negotiating software licenses, buying datasets, managing cloud compute clusters, and reordering physical inventory.

However, enterprise CFOs and risk teams face an existential dilemma:
**How do you give an autonomous agent the authority to spend company capital without risking financial catastrophe?**
- LLM agents can hallucinate payment amounts, fall prey to prompt injection attacks from adversarial vendor invoices, get trapped in recursive execution loops, or pay unauthorized merchants.
- On the post-payment side, autonomous transactions are uniquely vulnerable to chargebacks and disputes. When a customer or vendor disputes an AI-initiated transaction, human risk teams spend hours hunting across disparate databases (ERP, Jira, Slack, PayPal dashboard, server telemetry) trying to assemble a defense package before PayPal's dispute SLA deadline expires.

We built **Sentinel & ProofLayer** to solve both sides of this equation:
1. **Sentinel**: Mathematical pre-payment mandate governance that intercepts agent payment requests, performs deterministic PO-to-invoice matching and transparent risk scoring, enforces human escalation thresholds, and provides a 3-tier emergency kill switch before any PayPal payment executes.
2. **ProofLayer**: A post-payment causal property graph engine that tracks the complete provenance of every transaction and autonomously compiles cited defense dossiers to win PayPal disputes within seconds.

---

## 2. What It Does

`sentinel-prooflayer` is an institutional-grade full-stack platform comprising two synchronized engines:

### 🛡️ Sentinel: Pre-Payment Mandate Control Plane
- **Natural Language Mandate Compiler & Simulator**: Translates executive procurement policies (e.g., *"Allow Atlas to auto-spend up to $1,000 on cloud infrastructure with PO variance within 2%; require CFO review up to $5,000; block crypto"*) into JSON ASTs and CEL predicates. Simulates policies against historical transactions to project friction reduction and budget savings.
- **Deterministic 4-Factor PO Matching Score ($M \in [0, 1]$)**: Eliminates hallucination by deterministically verifying vendor legal identities, purchase order numbers, line items, and financial variance tolerance ($\le 2\%$).
- **Transparent 5-Factor Weighted Risk Score ($R \in [0, 1]$)**: Assesses vendor legitimacy, duplicate invoice fingerprinting (via SHA-256), amount caps, blocked category risk, and historical dispute rates. Never returns an opaque float; always returns full dimensional breakdowns and human-readable diagnostic reasons.
- **Canonical 12-State Lifecycle & 3-Tier Kill Switch**: Enforces strict transitions from `PROPOSED` to `RECONCILED`. The 3-tier kill switch provides surgical blast-radius containment: Level 1 halts a single intent, Level 2 revokes an agent, and Level 3 freezes an entire organizational mandate while strictly preserving already-captured PayPal transactions to maintain double-entry accounting truth.
- **Real PayPal Sandbox Integration**: Executes Orders v2 creation, authorizations, and captures with atomic idempotency locking (`idempotency_key` and `PayPal-Request-Id`). Includes a deterministic Sandbox Twin fallback for offline and hermetic testing.

### 🔍 ProofLayer: Post-Payment Causal Pre-Dispute Evidence Graph & Auto-Defense
- **18-Node Causal Property Graph**: Maps 18 node types (`AGENT_MANDATE`, `PURCHASE_ORDER`, `INVOICE`, `APPROVAL_RECORD`, `PAYPAL_CAPTURE`, `CUSTOMER_SESSION`, etc.) and 13 edge types (`AUTHORIZED_BY`, `MATCHES`, `SUPPORTS`, `CITES`, etc.) to preserve the end-to-end provenance of every cent spent.
- **6-Dimension Evidence Readiness Score**: Evaluates dispute defense readiness ($Readiness = 0.94$) across Completeness, Freshness, Provenance, Consistency, Relevance, and Verifiability.
- **Grounded Defense Narrative Generator**: Generates formal dispute response briefs where **100% of factual sentences** contain verified inline citations (`[ev_*]`) grounded in immutable graph facts.
- **Digital Telemetry Substitution**: For intangible software and compute services where physical tracking does not exist, ProofLayer deterministically substitutes authenticated user session telemetry (`[ev_session_118]`) as valid `PROOF_OF_FULFILLMENT`.
- **Direct PayPal Disputes API Submission**: Submits evidence packages directly via `POST /v1/customer/disputes/{id}/provide-evidence`.
- **Append-Only Merkle Audit Ledger**: Chains all governance decisions and financial receipts in a SHA-256 Merkle block ledger with automated `verify_chain()` tamper detection.

---

## 3. How We Built It

We engineered `sentinel-prooflayer` as a unified monorepo:
- **Backend Core**: Python 3.11+ with **FastAPI**, **Pydantic v2**, and **SQLAlchemy 2.0** running SQLite in Write-Ahead Logging (`PRAGMA journal_mode=WAL;`) mode.
- **PayPal Client & Twin**: Async HTTP client using **HTTPX** targeting the PayPal Sandbox REST API (`https://api-m.sandbox.paypal.com`), backed by a deterministic Sandbox Twin state engine.
- **MCP Server**: Implements the official **Model Context Protocol (MCP)** JSON-RPC standard in `backend/mcp_server/server.py`, exposing 12 Sentinel and ProofLayer tools for autonomous AI agents.
- **Frontend Institutional Command Center**: Built with **Next.js 15 (App Router)**, **TypeScript**, **Tailwind CSS**, **AG Grid Community**, and **@xyflow/react** for interactive 18-node causal graph exploration. Includes a live PayPal Sandbox status indicator, global 3-tier kill switch header, and a 1-click Judge Scenario Runner.
- **DevOps**: Complete **Render Blueprint** (`render.yaml`) for 1-click cloud deployment and multi-container **Docker Compose** orchestration (`docker-compose.yml`).

---

## 4. Mathematical Specifications

### Invoice-to-PO Matching Score
$$M = 0.35 \cdot S_{vendor} + 0.25 \cdot S_{total} + 0.25 \cdot S_{line\_items} + 0.15 \cdot S_{terms}$$

### Transparent Weighted Risk Score
$$R = 0.30 \cdot V + 0.25 \cdot D + 0.20 \cdot A + 0.15 \cdot C + 0.10 \cdot H$$

Where:
- $V$: Vendor verification risk ($0.0$ for allowlisted vendors).
- $D$: Duplicate invoice fingerprint ($FP = \text{SHA256}(V_{id} \parallel \text{InvoiceNumber} \parallel \text{Amount})$).
- $A$: Amount deviation and single-transaction cap ratio.
- $C$: Blocked category risk ($1.0$ for crypto, gambling, gift cards).
- $H$: Historical vendor dispute/refund rate.

### Evidence Readiness Score
$$\text{Readiness} = \frac{\sum_{i=1}^6 w_i \cdot q_i}{\sum_{i=1}^6 w_i} = 0.94$$
Weighted across Completeness ($0.25$), Freshness ($0.15$), Provenance ($0.20$), Consistency ($0.15$), Relevance ($0.15$), and Verifiability ($0.10$).

---

## 5. The 4 Deterministic Judge Scenarios

Judges can test the entire platform end-to-end via the Executive Dashboard or API endpoints (`POST /api/scenarios/run/{1..4}`):
1. **Scenario 1 ($840.00 Auto-Approved Procurement)**: Agent Atlas submits invoice `inv_2026_0840` against PO `po_2026_4410` for Data Labeling Co. Matching score $M=0.97$, risk $R=0.016$. Clears auto-approval threshold and executes Authorize -> Capture -> Reconcile autonomously.
2. **Scenario 2 ($4,180.50 High-Value CFO Escalation)**: Agent Atlas submits invoice `inv_2026_0918` against PO `po_2026_4417` ($4,150.00). Variance is $0.735\%$ (within 2% limit), matching score $M=0.96$. Because amount exceeds $1,000, intent parks in `HUMAN_REVIEW`. CFO Maya Lin approves, locks atomic idempotency key, and captures funds on PayPal.
3. **Scenario 3 ($2,500.00 Out-of-Policy / Blocked Vendor)**: Agent Atlas attempts to pay FastCrypto Services. Immediately blocked in `POLICY_CHECK` due to non-allowlisted vendor and crypto category. **Crucial guarantee: exactly 0 PayPal API calls are made**.
4. **Scenario 4 (PayPal Dispute Webhook -> Autonomous Evidence Package)**: Inbound `CUSTOMER.DISPUTE.CREATED` webhook (`PP-D-99412`). Webhook signature verified; duplicate event replay detected and deduplicated. ProofLayer builds the 18-node causal graph, computes Readiness $0.94$, compiles a cited defense brief with `[ev_*]` citations, substitutes digital telemetry `[ev_session_118]`, and auto-submits to the PayPal Disputes API.

---

## 6. Challenges We Ran Into

1. **Atomic Idempotency Under High Concurrency**: In autonomous agent workflows, an agent might re-try a payment request while a previous attempt is in-flight. We implemented dual-layer idempotency locking: storing an atomic lock in SQLite transactions and forwarding a unique `PayPal-Request-Id` to PayPal Orders v2, guaranteeing zero duplicate payments.
2. **Defending Digital Services Without Tracking Numbers**: Standard PayPal dispute forms anticipate physical shipment tracking numbers (UPS/FedEx). For AI agent procurement of SaaS and GPU compute, no physical carrier exists. We implemented automatic telemetry substitution, formatting server session logs (`[ev_session_118]`) and IP auth logs into the `PROOF_OF_FULFILLMENT` payload.
3. **Strict Citation Validation**: To prevent AI hallucinations in dispute briefs, we developed a deterministic AST parser that validates that 100% of factual claim sentences contain at least one bracketed reference (`[ev_*]`) to an immutable graph node.

---

## 7. Accomplishments That We're Proud Of

- **Zero-Placeholder Guarantee**: The entire repository was built with complete algorithmic logic—no stubs, no fake delays, no mock shortcuts.
- **Mathematical Transparency**: Risk and matching calculations return full mathematical breakdowns and diagnostic reasons rather than black-box probabilities.
- **Double-Entry Accounting Invariant**: When Level 3 Kill Switch is pulled, uncaptured authorizations are immediately aborted, but captured transactions are strictly preserved to maintain financial ledger integrity.
- **Dual Mode Resilience**: Operates natively against live PayPal Sandbox credentials, but seamlessly activates a deterministic Sandbox Twin when credentials are not configured, enabling 100% hermetic CI/CD and testing.

---

## 8. What We Learned

We learned that granting financial autonomy to AI agents requires shifting the paradigm from *perimeter security* to *causal financial provenance*. It is not enough to check a prompt; organizations need mathematical invariants, deterministic state machines, and cryptographic audit ledgers that survive post-payment audits and disputes.

---

## 9. What's Next for Sentinel & ProofLayer

- **Multi-Agent Collaborative Mandates**: Hierarchical governance across agent swarms where subagents inherit parent budget slices.
- **Zero-Knowledge Evidence Proofs**: Generating zk-SNARK proofs of customer session telemetry to protect corporate IP while providing irrefutable delivery proof to PayPal dispute arbiters.
- **Streaming Micro-Payments**: Integrating PayPal's streaming payment channels for real-time per-token API inference settlement.

---

## 10. Documentation Cross-References

- [Root Project README](../README.md): System architecture, mathematical formulas, API reference, and quickstart.
- [System Architecture & Security Blueprint](architecture.md): Dual-engine specifications, 18-node causal graph, 7 PayPal dispute reasons mapping, and Merkle ledger.
- [Canonical 12-State Machine & 3-Tier Kill Switch](state-machine.md): Formal state transition matrices and emergency kill switch rules.
- [3-Minute Video Walkthrough Script](demo-script.md): Scripted judging walkthrough across Scenarios 1–4.
