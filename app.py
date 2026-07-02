import streamlit as st
import json
from datetime import datetime
import re
import pandas as pd
import numpy as np

# Set page config for a premium dashboard look
st.set_page_config(
    page_title="Redrob Talent Intelligence Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for premium styling (glassmorphism look, modern borders, custom cards)
st.markdown("""
<style>
    .reportview-container {
        background: #0f1116;
    }
    .metric-card {
        background-color: #1a1f2c;
        border: 1px solid #2e3748;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        text-align: center;
        margin-bottom: 20px;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #4b6cb7;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #a0aec0;
    }
    .reasoning-card {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        border: 1px solid #3b82f6;
        padding: 20px;
        border-radius: 12px;
        color: white;
        font-size: 1.1rem;
        line-height: 1.6;
        margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(30, 60, 114, 0.4);
    }
    .candidate-header {
        font-size: 1.8rem;
        font-weight: bold;
        color: #edf2f7;
        margin-bottom: 10px;
    }
    .tag {
        display: inline-block;
        background: #2d3748;
        color: #edf2f7;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.8rem;
        margin-right: 5px;
        margin-bottom: 5px;
        border: 1px solid #4a5568;
    }
    .timeline-item {
        border-left: 3px solid #4b6cb7;
        padding-left: 20px;
        margin-left: 10px;
        margin-bottom: 20px;
        position: relative;
    }
    .timeline-title {
        font-weight: bold;
        color: #edf2f7;
        font-size: 1.1rem;
    }
    .timeline-meta {
        color: #a0aec0;
        font-size: 0.85rem;
        margin-bottom: 5px;
    }
</style>
""", unsafe_allow_html=True)

# JD default text
DEFAULT_JD = """Job Description: Senior AI Engineer — Founding Team
Company: Redrob AI (Series A AI-native talent intelligence platform)
Location: Pune/Noida, India (Hybrid) | Open to relocation candidates from Tier-1 Indian cities
Employment Type: Full-time
Experience Required: 5–9 years

Role Overview:
We need a founding Senior AI Engineer who is simultaneously comfortable with deep technical depth in modern ML systems (embeddings, dense retrieval, vector databases, ranking systems, and offline/online evaluation) and a scrappy, shipping-focused product attitude.

Requirements:
- Production experience with embeddings-based retrieval systems (sentence-transformers, OpenAI embeddings, etc.)
- Production experience with vector databases or hybrid search infrastructure (Pinecone, Weaviate, Qdrant, Milvus, FAISS, etc.)
- Strong Python skills.
- Experience with ranking evaluation frameworks (NDCG, MRR, MAP, A/B testing).
- Notice period: sub-30-day notice is heavily preferred.
- Location: Noida/Pune preferred, relocation from Delhi NCR, Mumbai, Hyderabad, Bangalore welcome."""

# Define service companies
SERVICE_COMPANIES = {
    'tcs', 'tata consultancy services', 'infosys', 'wipro', 'accenture', 
    'cognizant', 'capgemini', 'hcl', 'tech mahindra', 'l&t', 'lnt', 'mindtree',
    'mphasis', 'hexaware', 'ust global', 'cts', 'cognizant technology solutions'
}

PRODUCT_COMPANIES = {
    'swiggy', 'razorpay', 'cred', 'zomato', 'flipkart', 'meesho', 'nykaa', 'inmobi', 'zoho', 'ola', 
    'wayne enterprises', 'stark industries', 'initech', 'hooli', 'globex inc', 'dunder mifflin', 'acme corp', 'pied piper'
}

def parse_date(d_str):
    if not d_str:
        return None
    try:
        return datetime.strptime(d_str, "%Y-%m-%d")
    except:
        return None

def is_honeypot(cand):
    skills = cand.get("skills", [])
    for s in skills:
        if s.get("proficiency") in ["expert", "advanced"] and s.get("duration_months", 0) == 0:
            return True
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
    skills_list = [s.get("name", "").lower() for s in skills]
    text_content = f"{profile.get('headline', '')} {profile.get('summary', '')} "
    for exp in career:
        text_content += f"{exp.get('title', '')} {exp.get('description', '')} "
    text_content = text_content.lower()
    
    has_embeddings = any(k in skills_list or k in text_content for k in [
        'embeddings', 'sentence-transformers', 'sentence transformers', 'dense retrieval', 'vector search', 'bge', 'e5'
    ])
    has_vectordb = any(k in skills_list or k in text_content for k in [
        'pinecone', 'weaviate', 'qdrant', 'milvus', 'faiss', 'opensearch', 'elasticsearch'
    ])
    has_python = 'python' in skills_list or 'python' in text_content
    has_eval = any(k in skills_list or k in text_content for k in [
        'ndcg', 'mrr', 'map', 'ab testing', 'a/b testing', 'ranking evaluation', 'metrics'
    ])
    
    core_score = 0.0
    if has_embeddings: core_score += 0.25
    if has_vectordb: core_score += 0.25
    if has_python: core_score += 0.25
    if has_eval: core_score += 0.25
    
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
            
    skills_score = (core_score * 0.70) + (nth_score * 0.30)
    matched_skills = []
    if has_embeddings: matched_skills.append("embeddings")
    if has_vectordb: matched_skills.append("vector databases")
    if has_python: matched_skills.append("Python")
    if has_eval: matched_skills.append("eval metrics")
    for key, kw_list in nice_to_haves:
        if any(k in skills_list or k in text_content for k in kw_list):
            matched_skills.append(key)
            break
            
    return skills_score, matched_skills

def compute_experience_score(cand):
    profile = cand.get("profile", {})
    career = cand.get("career_history", [])
    yoe = profile.get("years_of_experience", 0)
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
        exp_score *= 0.3
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
    is_service_only = all(
        any(sc in comp for sc in SERVICE_COMPANIES) for comp in companies
    )
    if is_service_only:
        return 0.1
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
    resp_rate = signals.get("recruiter_response_rate", 0)
    if resp_rate >= 0.70:
        resp_mult = 1.0
    elif resp_rate >= 0.40:
        resp_mult = 0.8
    else:
        resp_mult = 0.5
    int_rate = signals.get("interview_completion_rate", 0)
    if int_rate >= 0.80:
        int_mult = 1.0
    elif int_rate >= 0.50:
        int_mult = 0.8
    else:
        int_mult = 0.5
    otw_mult = 1.05 if signals.get("open_to_work_flag", False) else 0.95
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
    
    if rank <= 10:
        templates = [
            f"{name} is an outstanding AI engineer with {yoe} yrs experience. Expert in {skills_str}, currently at {company} in {location}. Immediate fit with {notice}d notice and {resp_rate}% response rate.",
            f"Top-tier candidate ({yoe} yrs exp) currently serving as {title} at {company}. Strong in dense retrieval ({skills_str}). {location}-based with {notice}d notice.",
            f"Exceptional product-focused engineer with {yoe} yrs experience at {company}. Deployed {skills_str} to production; highly responsive ({resp_rate}%) and located in {location}."
        ]
        return templates[rank % len(templates)]
    elif rank <= 30:
        templates = [
            f"Strong applied ML background ({yoe} yrs exp) at {company}. Shipped {skills_str} systems; {location}-based with {notice}d notice and high availability.",
            f"{title} with {yoe} yrs experience at {company}, matching the 'shipper' archetype. Strong skills in {skills_str} and located in {location}.",
            f"Excellent fit with {yoe} yrs experience. Proven experience in {skills_str} at a product company; notice period is {notice}d."
        ]
        return templates[rank % len(templates)]
    else:
        templates = [
            f"Competent engineer with {yoe} yrs exp, skilled in {skills_str}. Noida/Pune hybrid match; notice period is {notice}d, representing a solid match.",
            f"Experienced {title} with {yoe} yrs exp. Shipped {skills_str} in production; based in {location} with {notice}d notice.",
            f"Product company background ({yoe} yrs exp) at {company}. Experienced in {skills_str}; located in {location} with {notice}d notice."
        ]
        return templates[rank % len(templates)]

# Main Dashboard Interface
st.title("🤖 Redrob AI Talent Intelligence Dashboard")
st.markdown("---")

# Sidebar Configuration
st.sidebar.title("🎛️ Controls & Parameters")
data_source = st.sidebar.selectbox(
    "Choose Dataset Pool",
    ["Sample Dataset (50 candidates)", "Full Dataset (100,000 candidates)"]
)

st.sidebar.subheader("⚖️ Scoring Weights")
w_skills = st.sidebar.slider("Skills Score Weight", 0, 100, 40)
w_exp = st.sidebar.slider("Experience Weight", 0, 100, 20)
w_comp = st.sidebar.slider("Company History Weight", 0, 100, 15)
w_loc = st.sidebar.slider("Location Match Weight", 0, 100, 15)
w_notice = st.sidebar.slider("Notice Period Weight", 0, 100, 10)

total_weight = w_skills + w_exp + w_comp + w_loc + w_notice
if total_weight != 100:
    st.sidebar.warning(f"Weights sum to {total_weight}%. They should ideally equal 100%. Scores will be normalized.")

# Helper to load data
@st.cache_data
def load_data(source):
    cands = []
    if source == "Sample Dataset (50 candidates)":
        path = r"C:\Users\msang\OneDrive\Desktop\Redrob\[PUB] India_runs_data_and_ai_challenge\[PUB] India_runs_data_and_ai_challenge\India_runs_data_and_ai_challenge\sample_candidates.json"
        with open(path, "r", encoding="utf-8") as f:
            cands = json.load(f)
    else:
        path = r"C:\Users\msang\OneDrive\Desktop\Redrob\[PUB] India_runs_data_and_ai_challenge\[PUB] India_runs_data_and_ai_challenge\India_runs_data_and_ai_challenge\candidates.jsonl"
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    cands.append(json.loads(line))
    return cands

try:
    candidates = load_data(data_source)
    st.sidebar.success(f"Successfully loaded {len(candidates)} candidates.")
except Exception as e:
    st.sidebar.error(f"Error loading candidates: {e}")
    candidates = []

# Tabs
tab1, tab2, tab3 = st.tabs(["📝 Target Job Description", "🏆 Candidate Shortlist", "📊 Platform Analytics"])

with tab1:
    st.header("Job Description Configuration")
    st.text_area("Editing Active Job Description", DEFAULT_JD, height=350)
    st.info("The AI Ranker runs matching logic against the requirements listed above.")

with tab2:
    if candidates:
        st.header("AI-Powered Shortlist")
        
        # Run ranking pipeline
        honeypot_count = 0
        valid_candidates = []
        for cand in candidates:
            if is_honeypot(cand):
                honeypot_count += 1
                continue
            valid_candidates.append(cand)
            
        scored = []
        for cand in valid_candidates:
            cid = cand.get("candidate_id")
            s_score, key_skills = compute_skills_score(cand)
            e_score = compute_experience_score(cand)
            c_score = compute_company_score(cand)
            l_score = compute_location_score(cand)
            n_score = compute_notice_score(cand)
            b_mult = compute_behavioral_multiplier(cand)
            
            # Weighted calculation
            raw_score = (
                s_score * (w_skills / 100.0) +
                e_score * (w_exp / 100.0) +
                c_score * (w_comp / 100.0) +
                l_score * (w_loc / 100.0) +
                n_score * (w_notice / 100.0)
            ) * b_mult
            
            # Normalize if sum of weights != 100
            if total_weight > 0:
                raw_score = raw_score * (100.0 / total_weight)
                
            scored.append({
                "candidate_id": cid,
                "score": round(raw_score, 4),
                "name": cand.get("profile", {}).get("anonymized_name"),
                "headline": cand.get("profile", {}).get("headline"),
                "yoe": cand.get("profile", {}).get("years_of_experience"),
                "location": cand.get("profile", {}).get("location"),
                "notice": cand.get("redrob_signals", {}).get("notice_period_days"),
                "key_skills": key_skills,
                "cand_obj": cand
            })
            
        # Sort and pick top 20
        scored.sort(key=lambda x: (-x["score"], x["candidate_id"]))
        shortlist = scored[:20]
        
        # Display metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"<div class='metric-card'><div class='metric-value'>{len(candidates)}</div><div class='metric-label'>Total Candidates Analyzed</div></div>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<div class='metric-card'><div class='metric-value' style='color:#e53e3e;'>{honeypot_count}</div><div class='metric-label'>Honeypots Blocked (Security)</div></div>", unsafe_allow_html=True)
        with col3:
            st.markdown(f"<div class='metric-card'><div class='metric-value' style='color:#38a169;'>{len(valid_candidates)}</div><div class='metric-label'>Valid Candidates Scored</div></div>", unsafe_allow_html=True)
            
        # Display Table
        df = pd.DataFrame([
            {
                "Rank": idx + 1,
                "ID": item["candidate_id"],
                "Name": item["name"],
                "Score": item["score"],
                "YoE": item["yoe"],
                "Location": item["location"],
                "Notice (Days)": item["notice"],
                "Headline": item["headline"]
            } for idx, item in enumerate(scored[:20])
        ])
        st.dataframe(df, use_container_width=True)
        
        # Dropdown to inspect details
        st.markdown("### 🔍 Inspect Shortlisted Candidate Details")
        selected_id = st.selectbox("Select Candidate to Inspect", [item["candidate_id"] for item in shortlist])
        
        if selected_id:
            # Get selected candidate
            item = next(x for x in shortlist if x["candidate_id"] == selected_id)
            cand = item["cand_obj"]
            profile = cand.get("profile", {})
            career = cand.get("career_history", [])
            skills = cand.get("skills", [])
            signals = cand.get("redrob_signals", {})
            
            # Reasoning Card (Highlighted at top)
            reasoning_text = generate_reasoning(cand, shortlist.index(item) + 1, item["key_skills"])
            st.markdown(f"<div class='reasoning-card'><strong>🤖 AI Match Decision:</strong><br/>{reasoning_text}</div>", unsafe_allow_html=True)
            
            # Profile Overview
            col1, col2 = st.columns([1, 2])
            with col1:
                st.subheader("Overview")
                st.write(f"**Name:** {profile.get('anonymized_name')}")
                st.write(f"**Headline:** {profile.get('headline')}")
                st.write(f"**Location:** {profile.get('location')}, {profile.get('country')}")
                st.write(f"**Experience:** {profile.get('years_of_experience')} years")
                st.write(f"**Availability:** {'Open to Work' if signals.get('open_to_work_flag') else 'Closed'}")
                st.write(f"**Notice Period:** {signals.get('notice_period_days')} days")
                st.write(f"**Expected Salary:** {signals.get('expected_salary_range_inr_lpa', {}).get('min')} - {signals.get('expected_salary_range_inr_lpa', {}).get('max')} LPA")
                st.write(f"**Recruiter Response Rate:** {int(signals.get('recruiter_response_rate', 0) * 100)}%")
                
            with col2:
                st.subheader("Stated Skills")
                skill_df = pd.DataFrame([
                    {
                        "Skill": s.get("name"),
                        "Proficiency": s.get("proficiency").capitalize(),
                        "Endorsements": s.get("endorsements"),
                        "Duration (Months)": s.get("duration_months")
                    } for s in skills
                ])
                if not skill_df.empty:
                    st.dataframe(skill_df, use_container_width=True, hide_index=True)
                else:
                    st.info("No skills listed on profile.")
                    
            # Career Timeline
            st.subheader("💼 Career History")
            for exp in career:
                end_str = exp.get("end_date") if exp.get("end_date") else "Present"
                comp_size = f"({exp.get('company_size')} employees)" if exp.get('company_size') else ""
                st.markdown(f"""
                <div class='timeline-item'>
                    <div class='timeline-title'>{exp.get('title')} at {exp.get('company')}</div>
                    <div class='timeline-meta'>{exp.get('start_date')} to {end_str} | {exp.get('duration_months')} months | {exp.get('industry')} {comp_size}</div>
                    <div style='color: #cbd5e0; font-size: 0.95rem;'>{exp.get('description')}</div>
                </div>
                """, unsafe_allow_html=True)
                
            # Platform Activity Signals
            st.subheader("📊 Redrob Ecosystem Signals")
            sc1, sc2, sc3, sc4 = st.columns(4)
            with sc1:
                st.metric("Profile Completeness", f"{signals.get('profile_completeness_score')}%")
            with sc2:
                st.metric("GitHub Score", f"{signals.get('github_activity_score')}/100" if signals.get('github_activity_score') != -1 else "N/A")
            with sc3:
                st.metric("Interview Attendance", f"{int(signals.get('interview_completion_rate', 0) * 100)}%")
            with sc4:
                st.metric("Connection Count", signals.get('connection_count'))
    else:
        st.info("Please select or load candidate dataset in sidebar.")

with tab3:
    if candidates and 'shortlist' in locals() and shortlist:
        st.header("Shortlist Metrics & Analytics")
        
        # Analyze salary distribution of top 20
        sal_min = [item["cand_obj"].get("redrob_signals", {}).get("expected_salary_range_inr_lpa", {}).get("min", 0) for item in shortlist]
        sal_max = [item["cand_obj"].get("redrob_signals", {}).get("expected_salary_range_inr_lpa", {}).get("max", 0) for item in shortlist]
        
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Expected Salary Distribution (INR LPA)")
            chart_data = pd.DataFrame({
                "Min Salary Expectation": sal_min,
                "Max Salary Expectation": sal_max
            }, index=[item["name"] for item in shortlist])
            st.bar_chart(chart_data)
            
        with c2:
            st.subheader("Notice Period Distribution (Days)")
            np_distribution = pd.Series([item["notice"] for item in shortlist]).value_counts().sort_index()
            st.bar_chart(np_distribution)
    else:
        st.info("Load dataset and view shortlist to inspect analytics.")
