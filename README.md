# 🤖 RecruitMind AI — Intelligent Candidate Discovery & Ranking System

<div align="center">


**India Runs Data & AI Challenge — Redrob AI Hackathon Submission**

*An end-to-end AI-powered candidate ranking engine that processes 100,000 candidate profiles in under 80 seconds on standard CPU — with zero network dependency, zero hallucinations, and full explainability.*


</div>

---

## 📌 Table of Contents

- [Problem Statement](#-problem-statement)
- [Why Not Keyword Matching or Clustering?](#-why-not-keyword-matching-or-clustering)
- [Our Solution](#-our-solution)
- [System Architecture](#-system-architecture)
- [Feature Breakdown](#-feature-breakdown)
  - [Honeypot Detection](#1--honeypot-detection--anti-cheat-security-filter)
  - [Service Company Filter](#2--service-company-filter)
  - [Multi-Factor Scoring Engine](#3--multi-factor-scoring-engine)
  - [Behavioral Signal Modifier](#4--behavioral-signal-modifier)
  - [AI Reasoning Generator](#5--ai-reasoning-generator)
  - [Recruiter Web Dashboard](#6️--recruiter-web-dashboard)
- [Installation & Setup](#️-installation--setup)
- [How to Run](#-how-to-run)
- [Output & Results](#-output--results)
- [Technology Stack](#️-technology-stack)
- [Project Structure](#-project-structure)
- [Declarations](#-declarations)

---

## 🎯 Problem Statement

A company (**Redrob AI**) is hiring a **Senior AI Engineer for the Founding Team**. They have received **100,000 candidate profiles** in a structured database. No human recruiter can evaluate 100,000 resumes manually.

**The challenge:** Build an intelligent system that:
1. Automatically identifies and discards fake/impossible profiles (honeypots)
2. Scores and ranks all valid candidates from most to least suitable
3. Generates a human-readable explanation for every ranking decision
4. Outputs a validated Top-100 shortlist in under 5 minutes on CPU

---

## ❌ Why Not Keyword Matching or Clustering?

### Keyword Matching Fails:
```
JD requires:  "TensorFlow"
Resume says:  "Keras"

Simple match: TensorFlow == Keras? → NO → Score = 0   ← WRONG
```
A candidate who built production CNNs with Keras is highly qualified — keyword matching misses this entirely.

### Clustering is the Wrong Tool:
```
Clustering answers: "Which GROUP does this item belong to?"
Our problem needs: "How well does THIS candidate match THIS job?"
```
K-Means groups similar candidates together — it doesn't compare them to a job description.

### ✅ Our Approach:
**Contextual multi-factor scoring** — evaluating candidates across skills context, career trajectory, company culture fit, location logistics, availability signals, and platform behavior.

---

## 💡 Our Solution

A **Two-Stage Hybrid Ranking Pipeline** that runs fully offline on CPU:

```
┌─────────────────────────────────────────────────────────────────┐
│                    100,000 RAW CANDIDATE PROFILES                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│             STAGE 1: SECURITY & SANITY FILTER                   │
│  ✗ Expert skill + 0 months duration    → Honeypot               │
│  ✗ Job duration > calendar months      → Honeypot               │
│  ✗ Claimed YoE vs actual career gap    → Honeypot               │
│                                                                  │
│  Result: 65 honeypots blocked → 99,935 valid candidates         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│            STAGE 2: MULTI-FACTOR SCORING ENGINE                 │
│                                                                  │
│  Skills Match        ████████████████░░░░  40%                  │
│  Experience Match    ████████░░░░░░░░░░░░  20%                  │
│  Company History     ██████░░░░░░░░░░░░░░  15%                  │
│  Location Match      ██████░░░░░░░░░░░░░░  15%                  │
│  Notice Period       ████░░░░░░░░░░░░░░░░  10%                  │
│                                                                  │
│  × Behavioral Signal Modifier (Multiplicative)                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              STAGE 3: SORT, RANK & EXPLAIN                      │
│  • Sort by Final Score (descending)                             │
│  • Tie-break by candidate_id (ascending)                        │
│  • Generate AI reasoning for each candidate                     │
│  • Output Top 100 to team_submission.csv                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  RECRUITER WEB DASHBOARD                        │
│  • Interactive weight sliders                                   │
│  • Real-time re-ranking                                         │
│  • Candidate profile deep-dive cards                            │
│  • Analytics: Salary & Notice Period charts                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔍 Feature Breakdown

### 1. 🛡️ Honeypot Detection — Anti-Cheat Security Filter

The organizers hid **65 deliberately fake profiles** inside the 100K pool to test if systems blindly rank candidates without validating their data integrity. Our system catches all of them using three logical checks:

| Check | What It Detects | Example |
|:---|:---|:---|
| **Skill Trust Fraud** | Expert/Advanced skill listed with `duration_months = 0` | Claims "Expert in Kafka" but used it for 0 months |
| **Duration Impossibility** | `duration_months` > calendar months since start date + 12 | Claims 14 years at a company founded in 2022 |
| **Experience Mismatch** | Claimed `years_of_experience` vs actual career history total | Claims 13 YoE but career spans only 11 months |

**Result:** All 65 honeypots detected → Score forced to `0.0` → Excluded from shortlist.

---

### 2. 🏢 Service Company Filter

The JD explicitly requires **product-company "shippers"** — not IT consultants. Our system automatically classifies career histories:

**Penalized Service Firms (Score: 0.1):**
> TCS • Wipro • Infosys • Accenture • Cognizant • Capgemini • HCL • Tech Mahindra • Mphasis • Hexaware

**Rewarded Product Companies (Score: 1.0):**
> Swiggy • Razorpay • CRED • Zomato • Flipkart • Meesho • Nykaa • InMobi • Zoho • Ola • Sarvam AI • Krutrim • Mad Street Den + FAANG, etc.

**Nuanced handling:** A candidate currently at a service firm but with prior startup experience gets `0.7` — not a blanket rejection.

---

### 3. 📊 Multi-Factor Scoring Engine

Five scoring dimensions are computed for every valid candidate:

#### Skills Match (40% Weight)
Scans both the structured skills section AND career description text:

**Core Requirements (70% of skills score):**
- Embeddings / Sentence Transformers / Dense Retrieval
- Vector Databases (Pinecone, Weaviate, Qdrant, Milvus, FAISS)
- Python
- Evaluation Metrics (NDCG, MRR, MAP, A/B Testing)

**Nice-to-Haves (30% of skills score):**
- LoRA / QLoRA / PEFT / Fine-tuning
- Learning-to-Rank / XGBoost / LTR
- Distributed Systems / Kubernetes / Docker
- HR-Tech / Talent Marketplace experience

#### Experience Match (20% Weight)
| Years of Experience | Score |
|:---|:---:|
| 5 – 9 years (target band) | 1.0 |
| 9 – 12 years | 0.8 |
| > 12 years | 0.5 |
| 4 – 5 years | 0.7 |
| 3 – 4 years | 0.4 |
| < 3 years | 0.1 |

**Additional penalties:**
- Pure academic/research career (>60% time in research roles) → Score × 0.3
- Management/Director role held for >18 months → Score × 0.6

#### Company History Match (15% Weight)
| Career Profile | Score |
|:---|:---:|
| Entirely product/startup companies | 1.0 |
| Mixed: service + product history | 0.7 |
| Currently at service firm, some product history | 0.7 |
| Entirely at IT consulting firms | 0.1 |

#### Location Match (15% Weight)
| Location | Score |
|:---|:---:|
| Noida / Pune (Hybrid HQ cities) | 1.0 |
| Delhi NCR / Gurgaon / Mumbai / Hyderabad / Bangalore | 0.8 |
| Other Indian cities | 0.6 |
| Outside India — willing to relocate | 0.4 |
| Outside India — not willing to relocate | 0.1 |

#### Notice Period Match (10% Weight)
| Notice Period | Score |
|:---|:---:|
| ≤ 15 days | 1.0 |
| ≤ 30 days | 0.9 |
| ≤ 60 days | 0.7 |
| ≤ 90 days | 0.4 |
| > 90 days | 0.1 |

---

### 4. 🔄 Behavioral Signal Modifier

A candidate can look perfect on paper but be completely unreachable or unresponsive. The behavioral modifier **multiplies** the raw score by real platform engagement data:

```
Final Score = Raw Score × (Active Recency × Response Rate × Interview Rate × Open-to-Work × GitHub)
```

| Signal | Source Field | Logic |
|:---|:---|:---|
| **Login Recency** | `last_active_date` | ≤30 days: 1.0 / ≤90 days: 0.9 / ≤180 days: 0.7 / >180 days: 0.3 |
| **Recruiter Response Rate** | `recruiter_response_rate` | ≥70%: 1.0 / ≥40%: 0.8 / <40%: 0.5 |
| **Interview Attendance** | `interview_completion_rate` | ≥80%: 1.0 / ≥50%: 0.8 / <50%: 0.5 |
| **Open to Work** | `open_to_work_flag` | True: ×1.05 / False: ×0.95 |
| **GitHub Activity** | `github_activity_score` | ≥30/100: ×1.05 |

> Final multiplier is capped at **1.0** to prevent inflation.

---

### 5. 🤖 AI Reasoning Generator

Every ranked candidate receives a **dynamically generated, fact-anchored, hallucination-free** explanation.

**How it works:**
- Uses Python f-string templates — NOT a neural network or LLM
- Pulls only real values from the candidate's structured profile (name, title, company, location, notice period, response rate, matched skills)
- 6 distinct template variations to prevent repetitive text
- Tone automatically adjusts based on rank position

**Example outputs:**

> **Rank 1:** *"Nisha Pillai is an outstanding AI engineer with 7.6 yrs experience. Expert in embeddings, vector databases, currently at Sarvam AI in Gurgaon, Haryana. Immediate fit with 45d notice and 94% response rate."*

> **Rank 15:** *"Strong applied ML background (5.3 yrs exp) at PhonePe. Shipped embeddings, vector databases, Python systems; Bhubaneswar-based with 90d notice and high availability."*

> **Rank 50:** *"Competent engineer with 6.9 yrs exp, skilled in vector databases, Python, LoRA. Notice period is 45d — representing a solid pipeline candidate."*

---

### 6️⃣ 🖥️ Recruiter Web Dashboard

An interactive Streamlit application (`app.py`) connecting recruiters directly to the live backend:

#### Sidebar Controls
- **Dataset Selector** — Switch between 50-candidate sample (instant) or full 100K pool (~78 sec)
- **5 Weight Sliders** — Dynamically adjust the importance of Skills, Experience, Company, Location, and Notice Period

#### Tab 1: Job Description
- View and edit the active Job Description in real-time
- Modify requirements to simulate different hiring scenarios

#### Tab 2: AI-Powered Shortlist
- **KPI Cards** — Total Analyzed / Honeypots Blocked / Valid Scored
- **Interactive Rankings Table** — Searchable top-20 shortlist with rank, score, YoE, location, headline
- **Candidate Inspector** — Select any candidate to view:
  - 🤖 **AI Match Decision Card** (the dynamic reasoning)
  - 📋 **Profile Overview** — Salary expectations (LPA), notice period, availability, response rate
  - 🎯 **Skills Table** — All skills with proficiency level, endorsements, and duration of use
  - 💼 **Career Timeline** — Full chronological work history with descriptions
  - 📊 **Platform Signals** — Profile completeness score, GitHub score, interview rate, connections

#### Tab 3: Platform Analytics
- **Salary Distribution Chart** — Min/Max salary expectations of top shortlisted candidates
- **Notice Period Distribution** — How many candidates have 15 / 30 / 60 / 90-day notices

---

## ⚙️ Installation & Setup

### Prerequisites
- Python 3.10 or higher
- pip

### Install Dependencies
```bash
pip install -r requirements.txt
```

**requirements.txt contains only 3 packages:**
```
streamlit>=1.28.0
pandas>=2.0.0
numpy>=1.24.0
```
> Everything else (`json`, `csv`, `datetime`, `re`) is Python's built-in standard library — no installation needed.

---

## ▶️ How to Run

### Option 1: Generate Ranked CSV (CLI — Official Submission)

```bash
python rank.py \
  --candidates "./[PUB] India_runs_data_and_ai_challenge/India_runs_data_and_ai_challenge/candidates.jsonl" \
  --out team_submission.csv
```

**Console Output:**
```
Loading candidates from candidates.jsonl...
Loaded 100000 candidates.
Stage 1: Pre-filtering and Honeypot check...
Filtered out 65 honeypots.
Pre-filtered down to 99935 AI/ML-relevant candidates.
Stage 2: Detailed scoring...
Top 5 candidates scores:
Rank 1: CAND_0002025 -> Score: 0.9228
Rank 2: CAND_0046064 -> Score: 0.8930
Rank 3: CAND_0064326 -> Score: 0.8732
Rank 4: CAND_0079387 -> Score: 0.8633
Rank 5: CAND_0081846 -> Score: 0.8633
Writing top 100 to team_submission.csv...
Done!
```
⏱️ **Runtime: ~78 seconds on standard CPU**

---

### Option 2: Validate the Submission

```bash
python validate_submission.py team_submission.csv
```

**Output:**
```
Submission is valid.
```

---

### Option 3: Launch the Recruiter Dashboard

```bash
streamlit run app.py
```

Open your browser at: **http://localhost:8501**

---

## 📈 Output & Results

### Submission File: `team_submission.csv`

| Field | Description |
|:---|:---|
| `candidate_id` | Unique candidate identifier |
| `rank` | Position in shortlist (1 = best fit) |
| `score` | Normalized fit score (0.0 – 1.0, 4 decimal places) |
| `reasoning` | AI-generated human-readable match explanation |

### Top 5 Ranked Candidates

| Rank | Candidate | Score | Profile |
|:---:|:---|:---:|:---|
| 🥇 1 | CAND_0002025 | 0.9228 | Senior AI Engineer @ Apple · 5.9 yrs · Trivandrum · 30d notice |
| 🥈 2 | CAND_0046064 | 0.8930 | ML Engineer @ Salesforce · 8.9 yrs · Coimbatore · 78% response |
| 🥉 3 | CAND_0064326 | 0.8732 | AI Engineer @ Sarvam AI · 7.6 yrs · Gurgaon · 94% response |
| 4 | CAND_0079387 | 0.8633 | AI Engineer @ Microsoft · 6.9 yrs · Trivandrum · 30d notice |
| 5 | CAND_0081846 | 0.8633 | ML Engineer @ Razorpay · 6.7 yrs · Jaipur · 73% response |

### Pipeline Performance

| Metric | Value |
|:---|:---:|
| Total Candidates Loaded | 100,000 |
| Honeypots Detected & Blocked | 65 |
| Valid Candidates Scored | 99,935 |
| Top Score | 0.9228 |
| Score Range (Top 100) | 0.63 – 0.92 |
| Average YoE (Top 100) | 6.1 years |
| CPU Runtime | ~78 seconds |
| Validation Status | ✅ **Submission is valid** |

### Compute Constraints Met

| Constraint | Requirement | Our Result |
|:---|:---:|:---:|
| Max Runtime | < 5 minutes | ✅ 78 seconds |
| Network Access | None | ✅ Zero API calls |
| GPU Required | Must use CPU only | ✅ Pure CPU |
| Validator | Must pass | ✅ Passed |
| Tie-breaking | candidate_id ascending | ✅ Implemented |
| Score Monotonicity | Non-increasing ranks | ✅ Enforced |
| Output Rows | Exactly 100 | ✅ 100 rows |

---

## 🛠️ Technology Stack

| Technology | Version | Purpose |
|:---|:---:|:---|
| **Python** | 3.11 | Core language for ranking pipeline and dashboard |
| **Streamlit** | ≥1.28 | Interactive recruiter web dashboard and UI |
| **Pandas** | ≥2.0 | Data tables, shortlist display, analytics charts |
| **NumPy** | ≥1.24 | Score normalization and numerical operations |
| **json / JSONL** | stdlib | Parsing 100K candidate profiles (one per line) |
| **datetime** | stdlib | Login recency calculation, honeypot date validation |
| **re (regex)** | stdlib | Stage 1 keyword pre-filter across candidate text |
| **csv** | stdlib | Writing the official submission output file |

### Deliberately NOT Used (and Why)

| Technology | Reason Rejected |
|:---|:---|
| ❌ Sentence Transformers | Requires GPU — exceeds 5-min CPU time limit for 100K profiles |
| ❌ OpenAI / Gemini API | Network calls disqualified by challenge rules |
| ❌ Scikit-learn ML Models | No labeled training data — supervised learning not possible |
| ❌ K-Means Clustering | Groups data into clusters — cannot compare candidates to a JD |
| ❌ LLM Reasoning | Prone to hallucinations, slow, network-dependent |

---

## 📁 Project Structure

```
Redrob_RecruitMind_AI/
│
├── rank.py                    # Core AI ranking engine (CLI)
│   ├── is_honeypot()          # Security validator — blocks fake profiles
│   ├── compute_skills_score() # Skills matching against JD requirements
│   ├── compute_experience_score() # Seniority band evaluation
│   ├── compute_company_score()    # Product vs service company classifier
│   ├── compute_location_score()   # Geographic fit scorer
│   ├── compute_notice_score()     # Notice period evaluator
│   ├── compute_behavioral_multiplier() # Platform engagement modifier
│   └── generate_reasoning()       # Hallucination-free explanation generator
│
├── app.py                     # Streamlit recruiter web dashboard
│   ├── Sidebar Controls       # Dataset selector + weight sliders
│   ├── Tab 1: JD Editor       # View and edit the Job Description
│   ├── Tab 2: Shortlist       # Live ranked table + candidate detail cards
│   └── Tab 3: Analytics       # Salary and notice period distribution charts
│
├── team_submission.csv        # Final output — Top 100 ranked candidates
├── submission_metadata.yaml   # Team details, compute specs, declarations
├── requirements.txt           # Python dependencies (3 packages only)
└── README.md                  # This file
```

---

## 📜 Declarations

| Declaration | Status |
|:---|:---:|
| Read submission specification in full | ✅ Yes |
| Code is original team work | ✅ Yes |
| AI tools used as assistants only (not for data access) | ✅ Yes |
| No coordination with other teams | ✅ Yes |
| Honeypot detection explicitly implemented | ✅ Yes |
| Reproduce command tested end-to-end | ✅ Yes |
| Zero network calls during ranking | ✅ Yes |
| Runs on CPU only within time limits | ✅ Yes |

---

<div align="center">

**Built for the India Runs Data & AI Challenge — Redrob AI**

[![GitHub](https://img.shields.io/badge/GitHub-Sangeetha231005-181717?style=flat-square&logo=github)](https://github.com/Sangeetha231005/Redrob_RecruitMind_AI)

</div>
