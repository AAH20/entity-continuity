# Entity Continuity Network: system architecture

This is the proposed architecture for a cross-border entity operating network. The repository currently implements only the **local synthetic reference engine and offline verifier**. The engine evaluates one entity and a `SYNTHETIC_REFERENCE` jurisdiction pack, returns `open` or `overdue` obligations and `deny` or `reviewable` intent decisions, and emits a deterministic digest. The verifier recomputes that exact local result. Neither authenticates identities, verifies evidence origin, connects to registries or providers, completes filings, or provides legal or tax advice.

The first proposed production corridor is an Egypt-based founder operating a defined US entity type. Other countries require their own reviewed rules, provider authority, data-handling design, and operating tests. No global coverage is claimed by this document.

## 1. Product context and responsibility

```mermaid
flowchart TB
  Customer["Founder, board and authorized officers"] --> Workspace["Private entity workspace - proposed"]
  Registry["Official register"] --> Source["Source and provenance adapter - proposed"]
  RegisteredAgent["Formation or registered-agent provider"] --> Source
  Accounting["Accounting and tax records"] --> Source
  Contracts["Contracts and corporate documents"] --> Source
  Source --> Workspace
  Workspace --> Engine["Entity Continuity reference kernel - local synthetic code"]
  Expert["Qualified local rule reviewer - proposed"] --> Pack["Versioned jurisdiction pack"]
  Pack --> Engine
  Engine --> Queue["Obligations and evidence gaps"]
  Engine --> Gate["Scoped action decision"]
  Queue --> Provider["Qualified local service provider - proposed"]
  Gate --> Provider
  Provider --> Authority["Official filing or service channel - proposed"]
  Authority --> Confirm["Official result and evidence - proposed"]
  Confirm --> Workspace
  Workspace --> Diligence["Permissioned diligence Passport - proposed"]
  Confirm --> Outcomes["Outcome Network cost, timeliness and quality - proposed"]
```

The registry or other official authority determines whether a filing is effective. A provider owns its professional work. The customer retains corporate decision rights. The platform records, coordinates and checks the flow; an AI assistant may prepare a recommendation but cannot supply legal authority or professional sign-off.

## 2. Open-source monorepo modules

```mermaid
flowchart LR
  Events["Entity events"] --> Validation["Strict schema and reference checks"]
  Evidence["Evidence references"] --> Validation
  Grants["Scoped grants and approvals"] --> Validation
  Rules["Versioned jurisdiction pack"] --> Validation
  Intent["Proposed action"] --> Validation
  Validation --> Replay["Deterministic entity replay - proposed"]
  Replay --> Obligations["Obligation evaluator - local reference"]
  Replay --> Authority["Authority evaluator - local reference"]
  Obligations --> Receipt["Evidence-labeled decision receipt"]
  Authority --> Receipt
  Receipt --> Verify["Independent offline verifier - local reference"]
  Fixtures["Synthetic boundary cases"] --> Validation
  Adapters["Read-only adapter contracts - proposed"] --> Validation
```

The stable OSS contract should contain the entity/event schema, pack schema and effective-date rules, grant and approval semantics, evidence labels, receipt format, verifier, synthetic regression cases, and connector interfaces. Versioned entity replay and real adapters are **roadmap items**. The current verifier detects changed local inputs or receipt fields; it is not a signature or source attestation.

## 3. Commercial service and compartments

```mermaid
flowchart TB
  subgraph Access["Identity and authority plane - proposed"]
    SSO["Customer SSO and MFA"] --> Roles["Entity-scoped roles"]
    Roles --> Grant["Time-limited action grant"]
    Grant --> Approval["Independent approval"]
    ProviderIdentity["Provider organization and staff verification"]
  end
  subgraph Workspace["Tenant-isolated workspace - proposed"]
    Entity["Versioned entity state"] --> Queue["Obligation and exception queue"]
    Vault["Encrypted evidence vault"] --> Queue
    Queue --> Audit["Append-only action history"]
  end
  subgraph Execution["Controlled execution - proposed"]
    Agent["AI drafts and extracts"] --> Policy["Rule and authority gate"]
    Policy --> Reviewer["Customer or qualified professional"]
    Reviewer --> Handoff["Minimum-necessary provider handoff"]
    Handoff --> Reconcile["Official result reconciliation"]
  end
  Queue --> Agent
  Approval --> Policy
  ProviderIdentity --> Handoff
  Reconcile --> Entity
  Reconcile --> Vault
  Reconcile --> Audit
```

Tenant isolation means a provider assignment sees only the entity, action and records needed for that assignment. Provider access expires at completion or revocation. Credentials for a registry, bank or filing channel must remain with the authorized party, not an unsupervised agent. Publication and diligence sharing are separate, explicit grants.

## 4. Evidence and authority data model — high contrast

This deliberately uses a flowchart instead of Mermaid `erDiagram` rows. Every record has an explicit dark fill and white text, so field labels remain readable in GitHub's light and dark appearances.

```mermaid
flowchart LR
  Entity["ENTITY<br/>entity_id | jurisdiction | state_version"]
  Event["ENTITY_EVENT<br/>event_id | type | occurred_at"]
  Rule["RULE_VERSION<br/>rule_id | effective_from | source_ref"]
  Obligation["OBLIGATION<br/>rule_id | event_id | due_at | status"]
  Artifact["ARTIFACT_VERSION<br/>artifact_id | digest | custody"]
  Evidence["EVIDENCE_REFERENCE<br/>artifact_id | claim | origin_status"]
  Grant["AUTHORITY_GRANT<br/>principal | actions | expiry"]
  Intent["ACTION_INTENT<br/>actor | action | exact_scope"]
  Approval["ACTION_APPROVAL<br/>reviewer | decision | intent_digest"]
  Work["WORK_ORDER<br/>provider | scope | state"]
  Result["PROVIDER_RESULT<br/>official_ref | result_status"]
  Passport["DILIGENCE_PASSPORT<br/>scope | digest | limitations"]

  Entity --> Event
  Entity --> Grant
  Event --> Obligation
  Rule --> Obligation
  Artifact --> Evidence
  Evidence --> Obligation
  Grant --> Intent
  Intent --> Approval
  Obligation --> Work
  Approval --> Work
  Work --> Result
  Result --> Evidence
  Evidence --> Passport
  Approval --> Passport
  Result --> Passport

  classDef record fill:#111827,stroke:#22D3EE,stroke-width:2px,color:#FFFFFF;
  class Entity,Event,Rule,Obligation,Artifact,Evidence,Grant,Intent,Approval,Work,Result,Passport record;
```

The current case file has `entity`, `events`, `evidence`, `grants`, `approvals` and `intents`; the pack has `obligations`. The normalized, versioned records above are a **target schema**, not a migration already implemented. A SHA-256 digest binds bytes relative to a retained reference; it does not establish who issued those bytes. `origin_status` must distinguish `customer_reported`, `provider_attested`, `registry_confirmed`, and `unverified`. A claimed status must never be silently upgraded to authenticated completion.

## 5. Authority decision and filing lifecycle

```mermaid
stateDiagram-v2
  [*] --> EventObserved
  EventObserved --> SourceHold: Missing or conflicting source
  EventObserved --> RuleCandidate: Entity and event linked
  SourceHold --> HumanTriage
  HumanTriage --> RuleCandidate: Reconciled
  HumanTriage --> ClosedNoAction: Not applicable
  RuleCandidate --> ExpertReview: Interpretation or exception required
  RuleCandidate --> ActionProposed: Reviewed rule applies
  ExpertReview --> ActionProposed: Qualified sign-off
  ExpertReview --> ClosedNoAction: No obligation
  ActionProposed --> AuthorityCheck
  AuthorityCheck --> Blocked: Grant or approval absent
  AuthorityCheck --> Approved: Exact scope approved
  Approved --> ProviderAccepted
  ProviderAccepted --> Submitted
  Submitted --> RejectedByAuthority
  Submitted --> ConfirmedByAuthority
  RejectedByAuthority --> Correction
  Correction --> AuthorityCheck: Material change needs new approval
  ConfirmedByAuthority --> EvidenceReconciled
  EvidenceReconciled --> EntityStateUpdated
  EntityStateUpdated --> Closed
  Closed --> [*]
```

Each transition should retain actor identity, timestamp, entity and action versions, rule version, approval reference, provider, and resulting evidence. `Submitted` is not `ConfirmedByAuthority`. The current engine stops at a local `deny` or `reviewable` advisory receipt; it does not execute this state machine.

## 6. Jurisdiction pack release and rollback

```mermaid
flowchart LR
  Official["Official source and effective date"] --> Draft["Draft rule pack"]
  Draft --> LocalExpert["Qualified local applicability review"]
  LocalExpert --> Cases["Positive, negative and boundary fixtures"]
  Cases --> Replay["Regression replay"]
  Replay --> Signoff["Named professional sign-off"]
  Signoff --> Version["Immutable pack version"]
  Version --> Pilot["Read-only local pilot"]
  Pilot --> Observe["False alerts, missed obligations, exceptions"]
  Observe --> Change["Change proposal and impact analysis"]
  Change --> LocalExpert
  Version --> Retire["Supersede or withdraw with notice"]
```

The present `US-DE-SYNTHETIC` pack has invented deadlines and cannot be promoted by merely changing its status field. Production packs need official sources that actually support each rule, applicability tests for entity types, effective dates, exceptions, a named reviewer, and a way to withdraw a wrong version without deleting its history.

## 7. Outcome and commercial asset loop

```mermaid
flowchart LR
  Workflow["One completed, confirmed workflow"] --> History["Richer entity history"]
  History --> Diligence["Faster permissioned diligence"]
  Diligence --> Retention["Recurring customer use"]
  Retention --> Workflow
  Workflow --> Measurement["Outcome Network: time, cost, rework, acceptance"]
  Measurement --> Improvement["Better rule tests and provider routing"]
  Improvement --> Reliability["Higher confirmed completion"]
  Reliability --> Referrals["Qualified referrals"]
  Referrals --> Workflow
```

This is a hypothesis to test, not guaranteed exponential growth. Use contribution margin per entity-year as the commercial unit: workspace and coordination revenue less provider delivery, professional review, connector maintenance, storage, support and payment costs. Government charges and professional fees are pass-through or separately disclosed. Key pilot metrics are missed obligations, false reminders, review minutes, time to confirmed result, provider on-time rate, evidence gaps, customer renewal and second-customer onboarding effort.

## Release gates

| Gate | Required evidence | Current status |
| --- | --- | --- |
| Reference engine | Synthetic replay, conservative evidence labels, denial of self-approval and expired grants, offline receipt recomputation | Implemented locally |
| Reviewed rule pack | Official-source mapping, local professional review, effective-date and exception tests | Not implemented |
| Read-only customer pilot | Permissioned source import, reconciliation against source counts, private diligence view | Not implemented |
| Authenticated handoff | Customer/provider identity, scoped signed approval, separation of duties, official confirmation | Not implemented |
| Repeatable network | Second customer and provider served without custom rule logic; measured contribution margin | Not implemented |

The architecture scales across jurisdictions by adding separately reviewed packs and qualified local partners. It does not assume one registered-agent license, one legal interpretation, or one data-residency rule applies worldwide.
