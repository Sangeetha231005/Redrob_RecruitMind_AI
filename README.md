# Redrob Candidate Ranking System - Founding Team Senior AI Engineer

This repository contains the candidate ranking engine developed for the **Redrob Intelligent Candidate Discovery & Ranking Challenge**.

## Approach & Architecture

Our system implements a **hybrid rule-based scoring engine with an activity modifier**, designed to run completely offline on CPU within the memory and time limits (5 minutes on CPU).

### Key Features:
1. **Honeypot Filter**: Detects and eliminates exactly 65 logically impossible candidate profiles (e.g. expert proficiency in 0 months, impossible employment durations, and major years of experience mismatches) by forcing their scores to `0.0`.
2. **Service Company Penalty**: Identifies and heavily down-weights candidates who have only worked at service/consulting IT firms (TCS, Infosys, Wipro, Accenture, Cognizant, etc.) to match the JD's strict preference for product-company shippers.
3. **Structured Feature Scoring**:
   - **Skills Match (40%)**: Core requirements (embeddings, vector DBs, Python, eval metrics) and nice-to-haves (LoRA, learning-to-rank, distributed systems).
   - **Experience Match (20%)**: Target band 5-9 years, penalizing pure research profiles and management-only roles.
   - **Company Match (15%)**: Bonus for product/startups.
   - **Location Match (15%)**: Noida/Pune hybrid preference.
   - **Notice Period Match (10%)**: Prefer sub-30-day notice.
4. **Behavioral Signal Modifier (Multiplicative)**: Modifies scores based on platform engagement (`last_active_date` recency, `recruiter_response_rate`, `interview_completion_rate`, and `open_to_work_flag`).
5. **Hallucination-Free Reasoning Generator**: Generates 1-2 sentence descriptions using 6 distinct templates (tailored to candidate rank) referencing exact profile facts.
6. **Deterministic Tie-Breaking**: Ensures that any candidates with equal rounded scores in the CSV are sorted ascending by `candidate_id`.

## Installation & Setup

1. Install Python 3.10+
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Ranker

To reproduce the submission CSV, execute the following command from the repository root:

```bash
python rank.py --candidates "./[PUB] India_runs_data_and_ai_challenge/[PUB] India_runs_data_and_ai_challenge/India_runs_data_and_ai_challenge/candidates.jsonl" --out team_submission.csv
```

*Note: The script processes 100K candidates in approximately **78 seconds** on standard CPU.*

## Submission Validation

To validate the generated CSV format against challenge specs:

```bash
python "./[PUB] India_runs_data_and_ai_challenge/[PUB] India_runs_data_and_ai_challenge/India_runs_data_and_ai_challenge/validate_submission.py" team_submission.csv
```
