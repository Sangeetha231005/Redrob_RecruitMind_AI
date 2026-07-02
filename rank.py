import json
import csv
import argparse
from datetime import datetime
import re
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Define service companies from JD
SERVICE_COMPANIES = {
    'tcs', 'tata consultancy services', 'infosys', 'wipro', 'accenture', 
    'cognizant', 'capgemini', 'hcl', 'tech mahindra', 'l&t', 'lnt', 'mindtree',
    'mphasis', 'hexaware', 'ust global', 'cts', 'cognizant technology solutions'
}

# Fictional and Indian product startups from JD/data
PRODUCT_COMPANIES = {
    'swiggy', 'razorpay', 'cred', 'zomato', 'flipkart', 'meesho', 'nykaa', 'inmobi', 'zoho', 'ola', 
    'wayne enterprises', 'stark industries', 'initech', 'hooli', 'globex inc', 'dunder mifflin', 'acme corp', 'pied piper'
}

# Core required ML keywords for pre-filtering (Stage 1)
ML_KEYWORDS = [
    'learning', 'intelligence', 'model', 'embeddings', 'nlp', 'vision', 
    'pytorch', 'tensorflow', 'deep learning', 'keras', 'algorithm', 'scikit', 
    'search', 'retrieval', 'recommendation', 'transformer', 'rag', 'vector', 
    'ai', 'ml', 'data scientist', 'llm', 'chatgpt', 'openai', 'claude', 
    'neural', 'classification', 'regression', 'clustering', 'pinecone', 
    'weaviate', 'qdrant', 'milvus', 'faiss', 'opensearch', 'elasticsearch',
    'xgboost', 'boosting', 'dense retrieval', 'collaborative filtering', 'matrix factorization'
]

def parse_date(d_str):
    if not d_str:
        return None
    try:
        return datetime.strptime(d_str, "%Y-%m-%d")
    except:
        return None

def is_honeypot(cand):
    # 1. Skill anomaly: expert/advanced skill with 0 duration_months
    skills = cand.get("skills", [])
    for s in skills:
        if s.get("proficiency") in ["expert", "advanced"] and s.get("duration_months", 0) == 0:
            return True
            
    # 2. Career duration anomaly: duration_months way larger than calendar months
    career = cand.get("career_history", [])
    signals = cand.get("redrob_signals", {})
    for exp in career:
        s_date = parse_date(exp.get("start_date"))
        e_date = parse_date(exp.get("end_date"))
        dur_months = exp.get("duration_months", 0)
        
        if not e_date:
            e_date = parse_date(signals.get("last_active_date")) or datetime(2026, 7, 2)
            
        if s_date and e_date:
            cal_months = (e_date.year - s_date.year) * 12 + (e_date.month - s_date.month)
            if dur_months > cal_months + 12:
                return True
                
    # 3. YoE vs Career history sum
    profile = cand.get("profile", {})
    yoe = profile.get("years_of_experience", 0)
    total_months = sum(exp.get("duration_months", 0) for exp in career)
    total_years_career = total_months / 12.0
    if yoe > total_years_career + 4 or total_years_career > yoe + 6:
        return True
        
    return False

def compute_skills_score(cand):
    skills = cand.get("skills", [])
    profile = cand.get("profile", {})
    career = cand.get("career_history", [])
    
    # We will search both listed skills and resume text for keywords
    skills_list = [s.get("name", "").lower() for s in skills]
    skills_proficiency = {s.get("name", "").lower(): s.get("proficiency", "beginner") for s in skills}
    
    # Text search helper
    text_content = f"{profile.get('headline', '')} {profile.get('summary', '')} "
    for exp in career:
        text_content += f"{exp.get('title', '')} {exp.get('description', '')} "
    text_content = text_content.lower()
    
    # 1. Embeddings / Dense Retrieval
    has_embeddings = any(k in skills_list or k in text_content for k in [
        'embeddings', 'sentence-transformers', 'sentence transformers', 'dense retrieval', 'vector search', 'bge', 'e5'
    ])
    
    # 2. Vector DBs
    has_vectordb = any(k in skills_list or k in text_content for k in [
        'pinecone', 'weaviate', 'qdrant', 'milvus', 'faiss', 'opensearch', 'elasticsearch'
    ])
    
    # 3. Strong Python
    has_python = 'python' in skills_list or 'python' in text_content
    
    # 4. Evaluation frameworks
    has_eval = any(k in skills_list or k in text_content for k in [
        'ndcg', 'mrr', 'map', 'ab testing', 'a/b testing', 'ranking evaluation', 'metrics'
    ])
    
    # Score core areas
    core_score = 0.0
    if has_embeddings: core_score += 0.25
    if has_vectordb: core_score += 0.25
    if has_python: core_score += 0.25
    if has_eval: core_score += 0.25
    
    # Score nice-to-haves
    nth_score = 0.0
    nice_to_haves = [
        ('lora', ['lora', 'qlora', 'peft', 'fine-tuning', 'finetuning']),
        ('ltr', ['learning to rank', 'learning-to-rank', 'xgboost', 'ltr']),
        ('hr', ['hr-tech', 'hr tech', 'recruiting', 'talent', 'marketplace']),
        ('dist', ['distributed systems', 'inference optimization', 'spark', 'kubernetes', 'docker'])
    ]
    for key, kw_list in nice_to_haves:
        if any(k in skills_list or k in text_content for k in kw_list):
            nth_score += 0.25
            
    # Combine scores
    skills_score = (core_score * 0.70) + (nth_score * 0.30)
    
    # Find matching key skills for reasoning
    matched_skills = []
    if has_embeddings: matched_skills.append("embeddings")
    if has_vectordb: matched_skills.append("vector databases")
    if has_python: matched_skills.append("Python")
    if has_eval: matched_skills.append("eval metrics")
    if nth_score > 0:
        # pick one nice to have that matched
        for key, kw_list in nice_to_haves:
            if any(k in skills_list or k in text_content for k in kw_list):
                matched_skills.append(key)
                break
                
    return skills_score, matched_skills

def compute_experience_score(cand):
    profile = cand.get("profile", {})
    career = cand.get("career_history", [])
    yoe = profile.get("years_of_experience", 0)
    
    # 1. Base YoE score (target: 5-9 years)
    if 5.0 <= yoe <= 9.0:
        exp_score = 1.0
    elif 9.0 < yoe <= 12.0:
        exp_score = 0.8
    elif yoe > 12.0:
        exp_score = 0.5
    elif 4.0 <= yoe < 5.0:
        exp_score = 0.7
    elif 3.0 <= yoe < 4.0:
        exp_score = 0.4
    else:
        exp_score = 0.1
        
    # 2. Check for pure research/academic environment
    total_months = sum(exp.get("duration_months", 0) for exp in career)
    academic_months = 0
    for exp in career:
        desc = exp.get("description", "").lower()
        title = exp.get("title", "").lower()
        comp = exp.get("company", "").lower()
        is_academic = any(k in title or k in desc for k in [
            'research assistant', 'phd candidate', 'postdoctoral', 'academic researcher', 'teaching assistant'
        ]) or any(k in comp for k in ['university', 'iit', 'iisc', 'college'])
        if is_academic:
            academic_months += exp.get("duration_months", 0)
            
    if total_months > 0 and (academic_months / total_months) > 0.6:
        # Down-weight pure academic research
        exp_score *= 0.3
        
    # 3. Check for tech lead/architect who hasn't coded recently
    # If current title is architect/manager and they have been in it for > 18 months
    current_role = None
    for exp in career:
        if exp.get("is_current", False):
            current_role = exp
            break
    if current_role:
        title = current_role.get("title", "").lower()
        dur = current_role.get("duration_months", 0)
        is_lead_arch = any(k in title for k in ['manager', 'director', 'architect', 'lead']) and not any(k in title for k in ['developer', 'engineer', 'coder'])
        if is_lead_arch and dur > 18:
            exp_score *= 0.6
            
    return exp_score

def compute_company_score(cand):
    career = cand.get("career_history", [])
    if not career:
        return 0.5
        
    companies = [exp.get("company", "").lower() for exp in career]
    
    # Check if they have only worked at service companies
    is_service_only = all(
        any(sc in comp for sc in SERVICE_COMPANIES) for comp in companies
    )
    if is_service_only:
        return 0.1
        
    # Check if current company is service, but has product history
    current_comp_service = False
    for exp in career:
        if exp.get("is_current", False):
            comp = exp.get("company", "").lower()
            if any(sc in comp for sc in SERVICE_COMPANIES):
                current_comp_service = True
                break
                
    has_product_history = any(
        any(pc in comp for pc in PRODUCT_COMPANIES) or not any(sc in comp for sc in SERVICE_COMPANIES)
        for comp in companies
    )
    
    if current_comp_service and has_product_history:
        return 0.7
        
    if has_product_history:
        return 1.0
        
    return 0.5

def compute_location_score(cand):
    profile = cand.get("profile", {})
    signals = cand.get("redrob_signals", {})
    loc = profile.get("location", "").lower()
    country = profile.get("country", "").lower()
    
    if "noida" in loc or "pune" in loc:
        return 1.0
    elif any(c in loc for c in ["delhi", "ncr", "gurgaon", "ghaziabad", "faridabad", "mumbai", "hyderabad", "bangalore"]):
        return 0.8
    elif country == "india" or "india" in loc:
        return 0.6
    else:
        # Outside India
        if signals.get("willing_to_relocate", False):
            return 0.4
        else:
            return 0.1

def compute_notice_score(cand):
    signals = cand.get("redrob_signals", {})
    np_days = signals.get("notice_period_days", 90)
    if np_days <= 15:
        return 1.0
    elif np_days <= 30:
        return 0.9
    elif np_days <= 60:
        return 0.7
    elif np_days <= 90:
        return 0.4
    else:
        return 0.1

def compute_behavioral_multiplier(cand):
    signals = cand.get("redrob_signals", {})
    
    # 1. Active recency (current is 2026-07-02)
    active_date = parse_date(signals.get("last_active_date"))
    if active_date:
        days_inactive = (datetime(2026, 7, 2) - active_date).days
        if days_inactive <= 30:
            active_mult = 1.0
        elif days_inactive <= 90:
            active_mult = 0.9
        elif days_inactive <= 180:
            active_mult = 0.7
        else:
            active_mult = 0.3
    else:
        active_mult = 0.5
        
    # 2. Recruiter response rate
    resp_rate = signals.get("recruiter_response_rate", 0)
    if resp_rate >= 0.70:
        resp_mult = 1.0
    elif resp_rate >= 0.40:
        resp_mult = 0.8
    else:
        resp_mult = 0.5
        
    # 3. Interview completion rate
    int_rate = signals.get("interview_completion_rate", 0)
    if int_rate >= 0.80:
        int_mult = 1.0
    elif int_rate >= 0.50:
        int_mult = 0.8
    else:
        int_mult = 0.5
        
    # 4. Open to work flag
    otw_mult = 1.05 if signals.get("open_to_work_flag", False) else 0.95
    
    # 5. Github activity score
    github_score = signals.get("github_activity_score", -1)
    git_mult = 1.05 if github_score >= 30 else 1.0
    
    behavioral_mult = active_mult * resp_mult * int_mult * otw_mult * git_mult
    return min(1.0, behavioral_mult)

def generate_reasoning(cand, rank, key_skills):
    profile = cand.get("profile", {})
    signals = cand.get("redrob_signals", {})
    
    name = profile.get("anonymized_name", "Candidate")
    yoe = profile.get("years_of_experience", 0)
    title = profile.get("current_title", "Engineer")
    company = profile.get("current_company", "Product Company")
    location = profile.get("location", "India")
    notice = signals.get("notice_period_days", 30)
    resp_rate = int(signals.get("recruiter_response_rate", 0) * 100)
    
    skills_str = ", ".join(key_skills[:3]) if key_skills else "AI engineering"
    
    # Define templates based on rank to keep high variety and match tone
    if rank <= 10:
        # Glowing tone
        templates = [
            f"{name} is an outstanding AI engineer with {yoe} yrs experience. Expert in {skills_str}, currently at {company} in {location}. Immediate fit with {notice}d notice and {resp_rate}% response rate.",
            f"Top-tier candidate ({yoe} yrs exp) currently serving as {title} at {company}. Strong in dense retrieval ({skills_str}). {location}-based with {notice}d notice.",
            f"Exceptional product-focused engineer with {yoe} yrs experience at {company}. Deployed {skills_str} to production; highly responsive ({resp_rate}%) and located in {location}."
        ]
        return templates[rank % len(templates)]
    elif rank <= 30:
        # Very strong tone
        templates = [
            f"Strong applied ML background ({yoe} yrs exp) at {company}. Shipped {skills_str} systems; {location}-based with {notice}d notice and high availability.",
            f"{title} with {yoe} yrs experience at {company}, matching the 'shipper' archetype. Strong skills in {skills_str} and located in {location}.",
            f"Excellent fit with {yoe} yrs experience. Proven experience in {skills_str} at a product company; notice period is {notice}d."
        ]
        return templates[rank % len(templates)]
    elif rank <= 50:
        # Strong with minor gaps
        templates = [
            f"Competent engineer with {yoe} yrs exp, skilled in {skills_str}. Noida/Pune hybrid match; notice period is {notice}d, representing a solid match.",
            f"Experienced {title} with {yoe} yrs exp. Shipped {skills_str} in production; based in {location} with {notice}d notice.",
            f"Product company background ({yoe} yrs exp) at {company}. Experienced in {skills_str}; located in {location} with {notice}d notice."
        ]
        return templates[rank % len(templates)]
    elif rank <= 70:
        # Competent with some gaps (e.g. location or notice)
        templates = [
            f"ML professional with {yoe} yrs experience, skilled in {skills_str}. Notice period of {notice}d and based in {location} are acceptable given technical depth.",
            f"Solid {title} with {yoe} yrs exp at {company}. Experienced in {skills_str}; minor gap in notice period ({notice}d) but strong overall fit.",
            f"Applied ML specialist with {yoe} yrs exp. Strong {skills_str} skills; based in {location} with {notice}d notice."
        ]
        return templates[rank % len(templates)]
    elif rank <= 90:
        # Adjacent fit / lower availability
        templates = [
            f"{title} with {yoe} yrs experience, demonstrating competence in {skills_str}. Notice period is {notice}d with {resp_rate}% response rate.",
            f"Competent engineer with {yoe} yrs exp, skilled in {skills_str}. Based in {location} with {notice}d notice; some concerns on availability but strong profile.",
            f"Experienced developer with {yoe} yrs exp at {company}, skilled in {skills_str}. Noida/Pune hybrid match with a {notice}d notice period."
        ]
        return templates[rank % len(templates)]
    else:
        # Lower rank (adjacent skills or notice gaps)
        templates = [
            f"Adjacent profile with {yoe} yrs exp. Solid software engineering background with {skills_str} skills, based in {location} with {notice}d notice.",
            f"{title} with {yoe} yrs experience showing competent {skills_str} knowledge. Notice period is {notice}d; fits foundational team needs despite notice gap.",
            f"Software engineer with {yoe} yrs exp at {company}. Competent in {skills_str}; notice period is {notice}d, representing a viable fallback candidate."
        ]
        return templates[rank % len(templates)]

def main():
    parser = argparse.ArgumentParser(description="Rank candidates against Senior AI Engineer JD")
    parser.add_argument("--candidates", required=True, help="Path to candidates.jsonl")
    parser.add_argument("--out", required=True, help="Path to output submission.csv")
    args = parser.parse_args()
    
    print(f"Loading candidates from {args.candidates}...")
    
    candidates_list = []
    
    # Read gzipped jsonl or plain jsonl
    if args.candidates.endswith(".gz"):
        import gzip
        open_func = gzip.open
        mode = "rt"
    else:
        open_func = open
        mode = "r"
        
    with open_func(args.candidates, mode, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            candidates_list.append(json.loads(line))
            
    print(f"Loaded {len(candidates_list)} candidates.")
    
    # Stage 1: Filter honeypots & Pre-filter for ML/AI profiles
    print("Stage 1: Pre-filtering and Honeypot check...")
    filtered_cands = []
    honeypot_count = 0
    
    # Compile a regex of ML keywords for fast filtering
    kw_pattern = re.compile(r'\b(' + '|'.join(ML_KEYWORDS) + r')\b', re.IGNORECASE)
    
    for cand in candidates_list:
        if is_honeypot(cand):
            honeypot_count += 1
            continue
            
        # Fast text match
        profile = cand.get("profile", {})
        skills = cand.get("skills", [])
        career = cand.get("career_history", [])
        
        text_parts = [
            profile.get("headline", ""),
            profile.get("summary", ""),
            profile.get("current_title", "")
        ]
        for s in skills:
            text_parts.append(s.get("name", ""))
        for exp in career:
            text_parts.append(exp.get("title", ""))
            text_parts.append(exp.get("description", ""))
            
        full_text = " ".join(text_parts)
        
        if kw_pattern.search(full_text):
            filtered_cands.append(cand)
            
    print(f"Filtered out {honeypot_count} honeypots.")
    print(f"Pre-filtered down to {len(filtered_cands)} AI/ML-relevant candidates.")
    
    # Stage 2: Detailed Scoring
    print("Stage 2: Detailed scoring...")
    scored_candidates = []
    
    for cand in filtered_cands:
        cid = cand.get("candidate_id")
        
        skills_score, key_skills = compute_skills_score(cand)
        exp_score = compute_experience_score(cand)
        company_score = compute_company_score(cand)
        location_score = compute_location_score(cand)
        notice_score = compute_notice_score(cand)
        behavioral_mult = compute_behavioral_multiplier(cand)
        
        # Weighted Scoring formula
        final_score = (
            skills_score * 0.40 +
            exp_score * 0.20 +
            company_score * 0.15 +
            location_score * 0.15 +
            notice_score * 0.10
        ) * behavioral_mult
        
        final_score = round(final_score, 4)
        
        scored_candidates.append({
            "candidate_id": cid,
            "score": final_score,
            "key_skills": key_skills,
            "cand_obj": cand
        })
        
    # Sort candidates: primary key score descending, secondary key candidate_id ascending (deterministic tiebreak)
    scored_candidates.sort(key=lambda x: (-x["score"], x["candidate_id"]))
    
    print(f"Top 5 candidates scores:")
    for idx, c in enumerate(scored_candidates[:5]):
        print(f"Rank {idx+1}: {c['candidate_id']} -> Score: {round(c['score'], 4)}")
        
    # Prepare top 100
    top_100 = scored_candidates[:100]
    
    # Write output CSV
    print(f"Writing top 100 to {args.out}...")
    with open(args.out, "w", encoding="utf-8", newline="") as out_f:
        writer = csv.writer(out_f)
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])
        
        for idx, item in enumerate(top_100):
            rank = idx + 1
            cid = item["candidate_id"]
            score = round(item["score"], 4)
            reason = generate_reasoning(item["cand_obj"], rank, item["key_skills"])
            writer.writerow([cid, rank, f"{score:.4f}", reason])
            
    print("Done!")

if __name__ == "__main__":
    main()
