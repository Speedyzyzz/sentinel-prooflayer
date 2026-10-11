# Sentinel & ProofLayer: System Architecture Blueprint

## 1. Executive Overview

**Sentinel & ProofLayer** is an institutional-grade governance, control plane, and causal evidence infrastructure designed for autonomous AI agents executing commercial transactions over the PayPal network. Built for the **PayPal AI Hackathon 2026**, the system solves two fundamental vulnerabilities that prevent enterprises from granting real financial autonomy to AI agents:

1. **The Pre-Payment Control Problem (Sentinel)**: Autonomous procurement agents can suffer from hallucinations, prompt injections, unbounded spending loops, duplicate invoice submission, and unauthorized vendor interaction. Sentinel enforces a mathematical, multi-tier mandate control plane, deterministic purchase-order matching, granular risk assessment, an atomic state machine, and a multi-level kill switch *before* any PayPal payment call can be initiated.
2. **The Post-Payment Dispute Vulnerability (ProofLayer)**: When transactions result in chargebacks, disputes, or audit investigations, merchants traditionally struggle to compile cross-system evidence within strict SLA countdowns. ProofLayer constructs an immutable 18-node causal property graph linking governance mandates, purchase orders, contracts, invoices, human approvals, PayPal capture receipts, and real-time digital access telemetry. Upon receiving PayPal dispute webhooks, ProofLayer automatically synthesizes grounded defense dossiers with verified inline citations and submits them directly to the PayPal Disputes API.

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 SENTINEL & PROOFLAYER ARCHITECTURE                          │
└─────────────────────────────────────────────────────────────────────────────────────────────┘

       [ Autonomous AI Agents ] (e.g. Atlas Procurement Agent, ERP Subagents)
                  │
                  ▼
   ┌──────────────────────────────┐
   │ 12-Tool Model Context Server │ (MCP JSON-RPC Protocol / REST API)
   └──────────────┬───────────────┘
                  │
══════════════════╪═══════════════════════════════════════════════════════════════════════════
 SENTINEL         │ PRE-PAYMENT MANDATE CONTROL PLANE
══════════════════╪═══════════════════════════════════════════════════════════════════════════
                  ▼
   ┌──────────────────────────────┐
   │ Policy Compiler & Simulator  │ ──► AST / CEL Mandate Evaluation & Historical What-If Simulation
   └──────────────┬───────────────┘
                  ▼
   ┌──────────────────────────────┐     Deterministic PO Matching Score:
   │    Dual-Stage Risk Engine    │ ──► M = 0.35·S_vendor + 0.25·S_total + 0.25·S_line_items + 0.15·S_terms
   │                              │     Transparent Weighted Risk Score:
   │                              │ ──► R = 0.30·V + 0.25·D + 0.20·A + 0.15·C + 0.10·H
   └──────────────┬───────────────┘
                  ▼
   ┌──────────────────────────────┐     [Tier 1: Intent Halt]
   │ 12-State Canonical Machine   │ ◄── [Tier 2: Agent Revocation]  (3-Tier Kill Switch)
   │     & Governance Gates       │ ◄── [Tier 3: Mandate Freeze]
   └──────────────┬───────────────┘
                  │
         ┌────────┴────────┐
         │                 │
         ▼                 ▼
   [ AUTO_APPROVED ]  [ HUMAN_REVIEW ]
         │                 │ (CFO Maya / Daniel Approval)
         └────────┬────────┘
                  ▼
   ┌──────────────────────────────┐
   │ PayPal REST Client & Twin    │ ──► OAuth2 / Orders v2 (Authorize -> Capture)
   └──────────────┬───────────────┘     Atomic Idempotency Locking (PayPal-Request-Id)
                  │
══════════════════╪═══════════════════════════════════════════════════════════════════════════
 PROOFLAYER       │ POST-PAYMENT CAUSAL EVIDENCE GRAPH & AUTO-DEFENSE ENGINE
══════════════════╪═══════════════════════════════════════════════════════════════════════════
                  ▼
   ┌──────────────────────────────┐
   │  Append-Only Merkle Ledger   │ ──► SHA-256 Chained Blocks with verify_chain() Tamper Detection
   └──────────────┬───────────────┘
                  │
                  ▼
   ┌──────────────────────────────┐     18 Node Types (Mandate, PO, Contract, Capture, Session, etc.)
   │  Causal Property Graph Store │ ──► 13 Edge Types (AUTHORIZED_BY, MATCHES, SUPPORTS, CITES, etc.)
   └──────────────┬───────────────┘
                  ▲
                  │ (PayPal Webhook: CUSTOMER.DISPUTE.CREATED)
   ┌──────────────┴───────────────┐
   │    Auto-Defense Compiler     │ ──► Readiness Score = sum(w_i · q_i) / sum(w_i)  [Target: 0.94]
   │                              │ ──► Grounded Defense Narrative with strict [ev_*] Inline Citations
   └──────────────┬───────────────┘     Digital Service Telemetry Substitution ([ev_session_118])
                  │
                  ▼
   ┌──────────────────────────────┐
   │  PayPal Disputes API v1      │ ──► POST /v1/customer/disputes/{id}/provide-evidence
   └──────────────────────────────┘
```

---

## 2. Core Subsystems & Mathematical Specifications

### 2.1 Natural Language Policy Compiler & What-If Simulator

The Policy Compiler operates in two stages:
1. **NL-to-Intermediate Representation (IR)**: Parses natural language procurement directives (e.g., *"Allow Atlas to spend up to $1,000 on cloud infrastructure with PO variance within 2%; require CFO review up to $5,000; block crypto"*).
2. **AST & Predicate Compilation**: Emits an immutable JSON Mandate AST containing:
   - Currency and amount thresholds ($L_{auto}$, $L_{max}$, daily velocity).
   - Commercial tolerance bounds ($\tau \le 0.02$).
   - Category and vendor allowlists / blocklists.
   - Evaluatable Common Expression Language (CEL) / boolean AST predicates.

The **Historical What-If Simulator** replays proposed mandate policies against historical transaction logs $\{T_1, \dots, T_N\}$ to quantify governance impact before deployment:
$$\text{Auto-Approve Rate} = \frac{N_{\text{auto}}}{N}, \quad \text{Review Rate} = \frac{N_{\text{review}}}{N}, \quad \text{Block Rate} = \frac{N_{\text{block}}}{N}$$
$$\text{Friction Hours Saved} = N_{\text{auto}} \times 4.2 \text{ hours}$$

---

### 2.2 Dual-Stage Mathematical Risk Engine

To prevent opaque decision-making, the Risk Engine evaluates every proposed payment intent using two transparent, deterministic scoring models.

#### 1. Invoice-to-PO Matching Score ($M \in [0, 1]$)
$$M = 0.35 \cdot S_{vendor} + 0.25 \cdot S_{total} + 0.25 \cdot S_{line\_items} + 0.15 \cdot S_{terms}$$

- **Vendor Match ($S_{vendor}$)**:
  $$S_{vendor} = \begin{cases}
  1.0 & \text{if } V_{inv} = V_{po} \land \text{PO Reference Valid} \\
  0.95 & \text{if } V_{inv} = V_{po} \\
  \max(0.0, 0.8 \cdot \text{Jaccard}(Tokens(N_{inv}), Tokens(N_{po})) + 0.2) & \text{otherwise}
  \end{cases}$$
- **Amount Variance ($S_{total}$)** with policy tolerance $\tau = 0.02$ and relative variance $\delta = \frac{|A_{inv} - A_{po}|}{A_{po}}$:
  $$S_{total} = \begin{cases}
  1.0 - \left(\frac{\delta}{\tau}\right) \cdot 0.05 & \text{if } \delta \le \tau \\
  \max\left(0.0, 1.0 - \frac{\delta - \tau}{0.10}\right) & \text{if } \delta > \tau
  \end{cases}$$
- **Line Items Similarity ($S_{line\_items}$)**:
  $$Score(L_k) = 0.50 \cdot \text{Sim}_{desc} + 0.25 \cdot \frac{\min(Q_i, Q_p)}{\max(Q_i, Q_p)} + 0.25 \cdot \max\left(0.0, 1.0 - \frac{|U_i - U_p|}{U_p}\right)$$
  $$S_{line\_items} = \frac{1}{|L_{inv}|} \sum_{k=1}^{|L_{inv}|} Score(L_k)$$
- **Commercial Terms ($S_{terms}$)**:
  $$S_{terms} = 0.70 \cdot \mathbb{I}(\text{Curr}_{inv} = \text{Curr}_{po}) + 0.30 \cdot \mathbb{I}(\text{DueDate} \ge \text{InvoiceDate})$$

#### 2. Transparent Weighted Risk Score ($R \in [0, 1]$)
$$R = 0.30 \cdot V + 0.25 \cdot D + 0.20 \cdot A + 0.15 \cdot C + 0.10 \cdot H$$

- **Vendor Verification Risk ($V$)**: $0.0$ for allowlisted/verified roster vendors, $0.50$ for unverified vendors, $1.0$ for non-allowlisted/flagged entities.
- **Duplicate Fingerprint Risk ($D$)**: Evaluates $FP = \text{SHA-256}(V_{id} \parallel \text{InvoiceNumber} \parallel \text{Amount})$. Returns $1.0$ if matching a captured intent within 90 days, $0.70$ if matching identical vendor/amount velocity within 24 hours, $0.0$ if unique.
- **Amount Ratio Risk ($A$)**: Scaled relative to auto-approval cap $L_{auto}$ ($1,000) and max cap $L_{max}$ ($5,000):
  $$A = \begin{cases}
  0.10 \cdot \frac{\text{Amount}}{L_{auto}} & \text{if Amount} \le L_{auto} \\
  \min\left(1.0, 0.40 + 0.60 \cdot \frac{\text{Amount} - L_{auto}}{L_{max} - L_{auto}}\right) & \text{if } L_{auto} < \text{Amount} \le L_{max} \\
  1.0 & \text{if Amount} > L_{max}
  \end{cases}$$
- **Blocked Category Risk ($C$)**: $1.0$ if category $\in \{\text{"crypto"}, \text{"gambling"}, \text{"gift\_cards"}, \text{"adult"}, \text{"weapons"}\}$; $0.0$ for permitted categories.
- **Historical Dispute Rate ($H$)**: $H = \min\left(1.0, 2.0 \cdot \frac{N_{disputes}}{N_{orders}} + 1.0 \cdot \frac{N_{refunds}}{N_{orders}}\right)$.

Every evaluation returns the full granular sub-score dictionary and human-readable diagnostic reasons.

---

### 2.3 The Canonical 12-State Machine & 3-Tier Kill Switch

#### 12-State Lifecycle Matrix
Transitions follow strict guard invariants:
```
PROPOSED ──► POLICY_CHECK ──► EVIDENCE_VALIDATION ──┬──► AUTO_APPROVED ──┐
                                                    ├──► HUMAN_REVIEW ───┼──► APPROVED ──► EXECUTING ──► AUTHORIZED ──► CAPTURED ──► RECONCILED
                                                    └──► BLOCKED         │                                                                   │
                                                                         └───────────────────────────────────────────────────────────────────┼──► DISPUTE_OPEN
                                                                                                                                             │          │
                                                                                                                                             │          ▼
                                                                                                                                             └──► EVIDENCE_SUBMITTED ──► RESOLVED
```

#### 3-Tier Kill Switch Blast Radius
1. **Tier 1 (`INTENT`)**: Halts a specific intent ($int\_id$) currently in proposed, policy check, or pending approval states. Prevents payment dispatch.
2. **Tier 2 (`AGENT`)**: Revokes an agent ID (`agent_atlas_procurement`). Rejects all incoming intents submitted by the agent with HTTP 403 and halts active in-flight intents.
3. **Tier 3 (`MANDATE`)**: Freezes the entire mandate boundary ($mdt\_id$). Voids all uncaptured authorizations. **Core Invariant**: Already-`CAPTURED` PayPal transactions are strictly preserved to maintain double-entry bookkeeping consistency.

---

### 2.4 PayPal Sandbox REST Client & Deterministic Sandbox Twin

The payment integration interacts with the real PayPal Sandbox REST API (`https://api-m.sandbox.paypal.com`):
- **OAuth2 Token Exchange** (`/v1/oauth2/token`).
- **Orders v2 Creation** (`POST /v2/checkout/orders` with `intent: "AUTHORIZE"`).
- **Orders v2 Authorization** (`POST /v2/checkout/orders/{id}/authorize`).
- **Payments v2 Capture** (`POST /v2/payments/authorizations/{id}/capture`).
- **Disputes v1 Provide Evidence** (`POST /v1/customer/disputes/{id}/provide-evidence`).
- **Webhook Signature Verification** (`POST /v1/notifications/verify-webhook-signature`).

**Deterministic Sandbox Twin**: When live credentials are not present in `.env`, the system automatically activates a local, deterministic Sandbox Twin. The Twin enforces identical request structures, validates idempotency keys (`PayPal-Request-Id`), emits structured responses matching PayPal Orders v2 schemas, and maintains persistent state across test runs.

---

### 2.5 ProofLayer Causal Evidence Graph & Auto-Defense Compiler

#### 18 Node Types & 13 Edge Types
The causal property graph models the complete provenance of commercial transactions:
- **Node Types**: `AGENT_MANDATE`, `PAYMENT_INTENT`, `POLICY_DECISION`, `APPROVAL_RECORD`, `VENDOR`, `PURCHASE_ORDER`, `CONTRACT`, `INVOICE`, `PAYPAL_ORDER`, `PAYPAL_CAPTURE`, `PAYPAL_REFUND`, `SHIPMENT`, `DELIVERY_CONFIRMATION`, `CUSTOMER_SESSION`, `SUPPORT_TICKET`, `DISPUTE`, `EVIDENCE_DOCUMENT`, `EVIDENCE_CLAIM`.
- **Edge Types**: `AUTHORIZED_BY`, `VALIDATED_BY`, `REFERENCES`, `MATCHES`, `PAID_BY`, `CAPTURED_AS`, `REFUNDED_BY`, `DISPUTED_BY`, `REQUIRES`, `SUPPORTS`, `CONTRADICTS`, `CITES`, `OCCURRED_AT`.

#### Multi-Dimensional Evidence Readiness Score
$$\text{Readiness} = \frac{\sum_{i=1}^6 w_i \cdot q_i}{\sum_{i=1}^6 w_i}$$

| Dimension ($i$) | Weight ($w_i$) | Metric ($q_i$) | Scenario 4 Value | Weighted Contribution |
|-----------------|----------------|----------------|------------------|-----------------------|
| 1. Completeness | 0.25 | Present essential nodes / Required nodes | 1.00 | 0.250 |
| 2. Freshness | 0.15 | Temporal recency: $\max(0, 1 - \Delta t / 30\text{ days})$ | 0.92 | 0.138 |
| 3. Provenance | 0.20 | Cryptographically anchored nodes ratio | 1.00 | 0.200 |
| 4. Consistency | 0.15 | PO vs Invoice variance integrity | 0.98 | 0.147 |
| 5. Relevance | 0.15 | Direct refutation score of disputed claim | 0.80 | 0.120 |
| 6. Verifiability | 0.10 | Fraction of externally anchored IDs | 0.85 | 0.085 |
| **Composite** | **1.00** | **Weighted Sum** | **0.94** | **0.940** |

$$\text{Composite Score} = 0.250 + 0.138 + 0.200 + 0.147 + 0.120 + 0.085 = 0.940$$

#### Grounded Narrative Generation with Inline Citations
ProofLayer generates structured defense briefs where **100% of factual sentences** contain verified bracketed evidence citations (e.g., `[ev_mandate_9f21ac]`, `[ev_po_4417]`, `[ev_invoice_3311]`, `[ev_approval_771]`, `[ev_capture_442]`, `[ev_session_118]`).
- **Digital Service Substitution**: When defending digital SaaS or cloud compute transactions where physical shipment tracking does not exist, ProofLayer automatically substitutes authenticated customer session telemetry `[ev_session_118]` as valid `PROOF_OF_FULFILLMENT`.

#### 2.5.1 PayPal Dispute Reasons Mapping & Evidence Requirements

ProofLayer maps all 7 canonical PayPal dispute reasons to corresponding PayPal `evidence_type` enums, required causal graph nodes, and autonomous defense compiler strategies:

| # | PayPal Dispute Reason | Required PayPal `evidence_type` Artifacts | Mandatory Causal Graph Nodes | Autonomous Evidence & Defense Strategy |
|---|----------------------|-------------------------------------------|------------------------------|-----------------------------------------|
| 1 | `ITEM_NOT_RECEIVED` | `PROOF_OF_FULFILLMENT`, `PROOF_OF_DELIVERY`, `CUSTOMER_COMMUNICATION` | `CUSTOMER_SESSION`, `SHIPMENT`, `DELIVERY_CONFIRMATION`, `PAYPAL_CAPTURE`, `INVOICE`, `PURCHASE_ORDER` | For digital services (compute, SaaS, data labeling), deterministically substitutes authenticated user session telemetry (`[ev_session_118]`) detailing IP access logs, compute cluster IDs, and timestamps. For physical deliveries, compiles carrier tracking (`[ev_shipment_trk901]`) and signed proof (`[ev_delivery_sig77]`). |
| 2 | `UNAUTHORIZED_TRANSACTION` | `PROOF_OF_SIGNIFICANT_NOT_AS_DESCRIBED`, `TERMS_AND_CONDITIONS`, `CUSTOMER_COMMUNICATION` | `AGENT_MANDATE`, `APPROVAL_RECORD`, `POLICY_DECISION`, `CUSTOMER_SESSION`, `CONTRACT`, `PAYPAL_ORDER` | Demonstrates organizational mandate authorization (`[ev_mandate_9f21ac]`), explicit cryptographic CFO sign-off (`[ev_approval_771]`), corporate SSO session telemetry (`[ev_session_118]`), and Merkle audit ledger block verification establishing legitimate procurement origin. |
| 3 | `ITEM_NOT_AS_DESCRIBED` | `TERMS_AND_CONDITIONS`, `ADDITIONAL_INFORMATION_OF_ITEM`, `CUSTOMER_COMMUNICATION` | `CONTRACT`, `PURCHASE_ORDER`, `INVOICE`, `SUPPORT_TICKET`, `EVIDENCE_DOCUMENT` | Proves line-item description and specification congruence ($S_{line\_items}$) between executed master service contract (`[ev_contract_cc_02]`), bilateral purchase order (`[ev_po_4417]`), and vendor invoice (`[ev_invoice_3311]`), accompanied by support ticket resolution history (`[ev_ticket_5501]`). |
| 4 | `DUPLICATE_TRANSACTION` | `PROOF_OF_RECEIPT_COPY`, `OTHER`, `CUSTOMER_COMMUNICATION` | `PAYPAL_ORDER`, `PAYPAL_CAPTURE`, `INVOICE`, `PAYMENT_INTENT`, `PURCHASE_ORDER` | Disproves duplicate billing by proving unique cryptographic invoice fingerprints $FP = \text{SHA-256}(V_{id} \parallel \text{InvoiceNumber} \parallel \text{Amount})$, separate PO reference numbers, independent service period timestamps, and distinct PayPal capture transaction IDs (`[ev_capture_442]`). |
| 5 | `CREDIT_NOT_PROCESSED` | `PROOF_OF_REFUND`, `REFUND_POLICY`, `CANCEL_POLICY`, `CUSTOMER_COMMUNICATION` | `PAYPAL_REFUND`, `CONTRACT`, `SUPPORT_TICKET`, `CUSTOMER_SESSION` | When a refund was executed, submits PayPal refund transaction receipt (`[ev_refund_442]`) and Merkle ledger settlement timestamp. When credit was disputed erroneously, cites executed contract terms governing non-refundable billing cycles or SLA dispute resolution windows. |
| 6 | `CANCELLED_RECURRING_PAYMENT` | `BILLING_AGREEMENT`, `TERMS_AND_CONDITIONS`, `CANCEL_POLICY`, `CUSTOMER_COMMUNICATION` | `CONTRACT`, `AGENT_MANDATE`, `SUPPORT_TICKET`, `CUSTOMER_SESSION` | Compiles executed subscription agreement, renewal terms, and customer session activity logs (`[ev_session_118]`) proving continued service consumption after purported cancellation date, or proves cancellation request was received past the contractual cycle billing cutoff. |
| 7 | `PROBLEM_WITH_REMITTANCE` | `PROOF_OF_RECEIPT_COPY`, `PROOF_OF_FULFILLMENT`, `OTHER` | `PAYPAL_CAPTURE`, `PAYPAL_ORDER`, `INVOICE`, `VENDOR` | Submits complete double-entry settlement trail linking invoice currency, amount, and recipient details to cleared PayPal capture receipt (`[ev_capture_442]`) and Merkle ledger hash verification proving full and final remittance. |

---

### 2.6 Cryptographic Append-Only Merkle Audit Ledger

The audit store maintains a cryptographic hash chain:
$$H_0 = \text{SHA-256}(\text{Genesis})$$
$$H_i = \text{SHA-256}(\text{Index}_i \parallel \text{Timestamp}_i \parallel \text{EventType}_i \parallel \text{Actor}_i \parallel \text{PayloadHash}_i \parallel H_{i-1} \parallel \text{MerkleRoot}_i)$$

The `verify_chain()` verification algorithm traverses the entire block sequence, recalculating payload hashes, previous hash linkages, and block hashes to detect retroactive record tampering.

---

## 3. Threat Model & Security Invariants

1. **Rogue Agent Containment**: An AI agent cannot execute payments without an active mandate. If risk score $R > 0.25$ or amount exceeds auto-approval limits, execution halts in `HUMAN_REVIEW`.
2. **Double-Spend & Replay Protection**: Enforced by composite unique constraints on `idempotency_key` and SHA-256 invoice fingerprints. Replays return cached results without re-initiating PayPal API calls.
3. **Webhook Replay Protection**: Inbound webhooks record `event_id` in a dedicated registry. Duplicate events are acknowledged with HTTP 200 `status: "ignored"` and trigger zero duplicate state transitions.
4. **Zero-Call Guarantee on Policy Violations**: Blocked categories or unauthorized vendors short-circuit immediately in `POLICY_CHECK -> BLOCKED`, with mathematically zero PayPal network traffic.

---

## 4. Architectural Cross-References

For additional specifications and operational walkthroughs across the Sentinel & ProofLayer repository:
- [Root Project README](../README.md): Quickstart, Docker setup, 12 MCP tools, and institutional frontend routes.
- [Canonical 12-State Machine & 3-Tier Kill Switch](state-machine.md): Formal state transition matrices, guard equations, and emergency halt procedures.
- [3-Minute Video Walkthrough Script](demo-script.md): Second-by-second judge demonstration script covering Scenarios 1–4.
- [Devpost Submission Narrative](devpost.md): Complete hackathon narrative covering business problem, architecture, and live PayPal integration.
