# ReguGuard: Enterprise Risk & Compliance Intelligence Platform

[![Java](https://img.shields.io/badge/Java-17%20LTS-orange.svg?logo=openjdk)](https://openjdk.org/)
[![Spring Boot](https://img.shields.io/badge/Spring%20Boot-3.x-brightgreen.svg?logo=springboot)](https://spring.io/projects/spring-boot)
[![GraphQL](https://img.shields.io/badge/API-GraphQL-e10098.svg?logo=graphql)](https://graphql.org/)
[![Elasticsearch](https://img.shields.io/badge/Search-Elasticsearch%208.x-005571.svg?logo=elasticsearch)](https://www.elastic.co/)
[![Apache Airflow](https://img.shields.io/badge/Orchestration-Airflow%202.8+-017CEE.svg?logo=apacheairflow)](https://airflow.apache.org/)
[![Keycloak](https://img.shields.io/badge/Security-Keycloak%20OIDC-blue.svg?logo=redhat)](https://www.keycloak.org/)
[![Docker](https://img.shields.io/badge/Infra-Docker%20Compose-2496ED.svg?logo=docker)](https://www.docker.com/)

---

## 1. Executive Summary & Business Case

Financial institutions face severe regulatory pressure under **Anti-Money Laundering (AML)** directives, **Know Your Customer (KYC)** mandates, and **FATF/EU 6AMLD** regulatory frameworks. Failure to detect sanctioned entities or hidden beneficial owners exposes banks to multi-million-euro non-compliance fines, legal prosecution, and reputational collapse.

**ReguGuard** is an end-to-end Regulatory Compliance & Risk Intelligence platform. It automatically ingests internal corporate financials and heterogeneous international sanctions feeds, cross-references corporate structures via an explainable entity resolution engine, indexes enriched risk profiles in real-time, and exposes a secure, high-throughput GraphQL API for regulatory compliance auditors.

---

## 2. High-Level System Architecture

The platform follows a decoupled, cloud-native microservices architecture orchestrated via Docker:

```text
 ┌────────────────────────────────────────────────────────────────────────┐
 │                        DATA ENGINEERING LAYER                          │
 │                                                                        │
 │  ┌──────────────────────┐         ┌─────────────────────────┐          │
 │  │ Corporate Financials │         │ Global Sanctions Feed   │          │
 │  │     (CSV Dataset)    │         │      (JSON Feed)        │          │
 │  └──────────┬───────────┘         └────────────┬────────────┘          │
 │             │                                  │                       │
 │             └───────────────┬──────────────────┘                       │
 │                             ▼                                          │
 │               ┌───────────────────────────┐                            │
 │               │  Apache Airflow Pipeline  │                            │
 │               │  - Data Sanitization      │                            │
 │               │  - Two-Tier Entity Match  │                            │
 │               │  - Composite Risk Engine  │                            │
 │               └─────────────┬─────────────┘                            │
 └─────────────────────────────┼──────────────────────────────────────────┘
                               │ (Batch ETL Ingestion)
                               ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │                      STORAGE & SEARCH LAYER                            │
 │                                                                        │
 │               ┌───────────────────────────┐                            │
 │               │   Elasticsearch Cluster   │                            │
 │               │   (Inverted Index, Fuzzy  │                            │
 │               │    Search, JSON Storage)  │                            │
 │               └─────────────▲─────────────┘                            │
 └─────────────────────────────┼──────────────────────────────────────────┘
                               │ (Spring Data Driver)
 ┌─────────────────────────────┼──────────────────────────────────────────┐
 │                     ENTERPRISE BACKEND LAYER                           │
 │                                                                        │
 │     ┌───────────────────────────────────────────────┐                  │
 │     │ Spring Boot 3.x Enterprise Core               │                  │
 │     │  - Layered Architecture (Clean / Hexagonal)   │                  │
 │     │  - GraphQL API Engine                         │                  │
 │     │  - Actuator Observability & Health Probes     │                  │
 │     └───────────────────────▲───────────────────────┘                  │
 └─────────────────────────────┼──────────────────────────────────────────┘
                               │ (Validated JWT Bearer)
 ┌─────────────────────────────┼──────────────────────────────────────────┐
 │                   IDENTITY & SECURITY (IAM) LAYER                      │
 │                                                                        │
 │               ┌───────────────────────────┐                            │
 │               │  Keycloak Identity Server │                            │
 │               │  (OAuth2 / OIDC / RBAC)   │                            │
 │               └─────────────▲─────────────┘                            │
 └─────────────────────────────┼──────────────────────────────────────────┘
                               │ (Login & Token Exchange)
                       ┌───────┴───────┐
                       │ Bank Auditor  │
                       │ (End User)    │
                       └───────────────┘
```

---

## 3. Technology Stack & Architectural Trade-offs

| Domain | Technology | Enterprise Rationale |
| :--- | :--- | :--- |
| **Backend Framework** | **Java 17 (LTS), Spring Boot 3.x** | Strong static typing, memory safety, thread concurrency, and enterprise ecosystem standards (Spring Data, Spring Security). |
| **API Architecture** | **GraphQL (Spring for GraphQL)** | Solves Over-fetching and Under-fetching. Allows auditors to query exact nested fields (company $\leftrightarrow$ sanctions $\leftrightarrow$ beneficial owners) in a single network request. |
| **Search & Analytics** | **Elasticsearch 8.x** | Inverted Index architecture delivers sub-millisecond retrieval and fuzzy matching across millions of unstructured legal documents and watchlist aliases. |
| **Data Engineering** | **Python, Pandas, Apache Airflow** | Declarative DAG orchestration, automated retry policies, task lineage, and robust vectorized data cleaning with Pandas. |
| **Identity & Access (IAM)**| **Keycloak (OAuth2 / OIDC)** | Decouples authentication from business logic. Employs cryptographically signed JSON Web Tokens (JWT) for Role-Based Access Control (RBAC). |
| **Testing Standards** | **JUnit 5, Mockito, PyTest** | Automated regression guardrails, unit test isolation, and test-driven data transformation contracts. |
| **Infrastructure** | **Docker & Docker Compose** | Reproducible, isolated execution across development, CI/CD pipelines, and multi-cloud environments. |

---

## 4. Core Engineering Highlights

### A. Explainable Risk Scoring Model (Rule-Based & Auditable)
Under European Banking Authority (EBA) regulations, "black-box" risk scoring is legally invalid. ReguGuard implements a deterministic, fully auditable composite scoring algorithm ($0 - 100$ scale):

* **Sanctions Watchlist Match:** `CRITICAL (+50)`, `HIGH (+35)`, `MEDIUM (+20)`.
* **Offshore Jurisdictions:** Tax havens & high-risk countries (`PA`, `KY`, `VG`, `BZ`) $\rightarrow$ **+25 pts**.
* **Governance Anomalies:** Undisclosed beneficial ownership (`NOT_DISCLOSED`) $\rightarrow$ **+20 pts**.
* **Regulatory Anomalies:** Missing corporate registration number $\rightarrow$ **+15 pts**.
* **Financial Health:** Negative Debt-to-Equity balance sheet anomaly $\rightarrow$ **+10 pts**.
* **Shell Indicators:** Operating entity with zero revenue $\rightarrow$ **+15 pts**.

**Regulatory Tiers:**
* `0.0 - 29.9` $\rightarrow$ **LOW RISK** (Standard Onboarding)
* `30.0 - 59.9` $\rightarrow$ **MEDIUM RISK** (Enhanced Due Diligence)
* `60.0 - 79.9` $\rightarrow$ **HIGH RISK** (Senior Management Sign-off)
* `80.0 - 100.0` $\rightarrow$ **CRITICAL RISK** (Immediate Asset Freeze / STR Filing)

---

## 5. End-to-End Execution Trace & Examples

### Example 1: Data Pipeline Risk Evaluation Trace

#### Input Raw Data (`COMP-005: Panama Meridian Trust Co`):
```json
{
  "company_id": "COMP-005",
  "company_name": "Panama Meridian Trust Co",
  "jurisdiction": "PA",
  "registration_number": null,
  "annual_revenue_mil": 5.30,
  "debt_to_equity_ratio": -0.50,
  "beneficial_owner": "Carlos Mendez",
  "industry": "Wealth Management"
}
```

#### Step-by-Step Scoring Engine Output:
```text
  Initial Baseline: score = 0.0, audit_trail = []
  [+] Step 1 (Sanction Hit): Matched US Narcotics Watchlist (HIGH)  -> +35.0 pts
  [+] Step 2 (Jurisdiction): Located in Offshore Jurisdiction (PA)   -> +25.0 pts
  [+] Step 3 (Registry):     Unregistered official tax identifier   -> +15.0 pts
  [+] Step 4 (Solvency):     Negative debt-to-equity ratio (-0.50)  -> +10.0 pts
  -------------------------------------------------------------------------------
  FINAL RISK SCORE:  85.0 / 100.0
  REGULATORY TIER:   CRITICAL
  AUDIT TRAIL:       ["SANCTION_HIT_HIGH (+35)", "OFFSHORE_JURISDICTION_PA (+25)", 
                      "MISSING_REGISTRATION_ID (+15)", "NEGATIVE_DEBT_RATIO (+10)"]
```

---

### Example 2: Auditor GraphQL Query & Response

Auditors query the backend API via a single `POST /graphql` endpoint without over-fetching unneeded operational fields:

#### Request (GraphQL):
```graphql
query GetAuditorRiskReport($companyId: ID!) {
  companyById(id: $companyId) {
    companyName
    jurisdiction
    riskScore
    riskTier
    riskFactors
    matchedSanction {
      sanctionId
      severity
      sanctionProgram
    }
  }
}
```

#### Response (JSON):
```json
{
  "data": {
    "companyById": {
      "companyName": "Panama Meridian Trust Co",
      "jurisdiction": "PA",
      "riskScore": 85.0,
      "riskTier": "CRITICAL",
      "riskFactors": [
        "SANCTION_HIT_HIGH (+35)",
        "OFFSHORE_JURISDICTION_PA (+25)",
        "MISSING_REGISTRATION_ID (+15)",
        "NEGATIVE_DEBT_RATIO (+10)"
      ],
      "matchedSanction": {
        "sanctionId": "SANC-US-2022-441",
        "severity": "HIGH",
        "sanctionProgram": "US_NARCOTICS_AML"
      }
    }
  }
}
```

---

## 6. Local Deployment & Runbook

### Prerequisites
* Docker Engine 24.x+ & Docker Compose v2.x+
* Java Development Kit (OpenJDK 17 LTS)
* Python 3.10+

### Step 1: Bootstrapping Multi-Service Infrastructure
Initialize PostgreSQL (multi-tenant metadata store), Elasticsearch, Keycloak IAM, and Apache Airflow:

```bash
# 1. Provide execute permissions to PostgreSQL multi-db init script
chmod +x config/postgres/init-multi-db.sh

# 2. Boot up all containerized services
docker compose up -d

# 3. Verify healthy running status
docker compose ps
```

| Service | Host Port | Internal Port | URL / Health Probe |
| :--- | :--- | :--- | :--- |
| **Elasticsearch** | `9200` | `9200` | `http://localhost:9200` |
| **Keycloak IAM** | `8180` | `8080` | `http://localhost:8180` |
| **Airflow Webserver** | `8088` | `8080` | `http://localhost:8088` |
| **Spring Boot Core** | `8080` | `8080` | `http://localhost:8080/actuator/health` |
| **PostgreSQL** | `5432` | `5432` | `localhost:5432` |

### Step 2: Executing the Data Engineering Pipeline
Run the modular Python compliance engine to clean, cross-reference, and score datasets:

```bash
cd data-pipeline
pip install -r requirements.txt
python run_pipeline.py
```
*Resulting enriched data is saved to `mock-data/enriched_compliance_data.json`.*

### Step 3: Running the Spring Boot Backend
Start the enterprise Java application via the bundled Maven Wrapper:

```bash
cd backend
chmod +x mvnw
./mvnw clean compile
./mvnw spring-boot:run
```

Verify backend health:
```bash
curl -s http://localhost:8080/actuator/health
# Returns: {"status":"UP"}
```

---

## 7. Agile Roadmap & Delivery Milestones

This project is delivered using **Iterative Scrum Governance**, tracked via GitHub Projects:

- [x] **Sprint 1: Infrastructure & Security Setup**
  - [x] Multi-service Docker Compose orchestration (Postgres, Elasticsearch, Keycloak, Airflow).
  - [x] Spring Boot 3.x layered packaging architecture (`config`, `controller`, `service`, `repository`, `model`).
  - [x] Actuator Observability & Health check verification.
- [ ] **Sprint 2: Data Engineering & Ingestion**
  - [x] Production mock datasets for KYC/AML (`financials.csv`, `sanctions.json`).
  - [x] Modular compliance engine package (`cleaner.py`, `resolver.py`, `scorer.py`).
  - [ ] Apache Airflow DAG orchestration & automated Elasticsearch indexing.
  - [ ] PyTest suite covering data sanitization and scoring boundary conditions.
- [ ] **Sprint 3: Enterprise Backend & GraphQL**
  - [ ] Spring Data Elasticsearch repository integration.
  - [ ] Schema-first GraphQL definition (`schema.graphqls`) & Query Resolvers.
- [ ] **Sprint 4: Security Integration**
  - [ ] Keycloak OIDC Realm configuration & Role-Based Access Control (`AUDITOR` vs `COMPLIANCE_OFFICER`).
  - [ ] Spring Security OAuth2 Resource Server integration with JWT token validation.
- [ ] **Sprint 5: Testing, QA & Production Hardening**
  - [ ] Comprehensive JUnit 5 & Mockito test suites.
  - [ ] Postman API Collections with automated assertions.

---

## 8. Author & Engineering Governance
* **Project Lead:** Software & Data Engineer (Compliance & FinTech Specialist)
* **Methodology:** Agile / Scrum
* **Architecture Pattern:** Domain-Driven Design (DDD) / Modular Monorepo
