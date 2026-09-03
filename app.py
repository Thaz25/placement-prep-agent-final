"""
🎯 Placement Prep Agent — Main Streamlit Application
Turns any job description into a personalized placement prep kit.
"""

import sys
import os
import logging
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st

from src import config
from src.guardrails import check_guardrails
from src.pipeline.parse_jd import parse_jd
from src.pipeline.parse_resume import parse_resume
from src.pipeline.gap_analysis import gap_analysis
from src.pipeline.practice_set import generate_practice_set
from src.pipeline.interview_questions import generate_interview_questions
from src.pipeline.compile_report import compile_report
from src.memory.session_store import SessionStore
from src.llm_client import chat_with_tools
from src.agent_tools import TOOLS_SCHEMA, TOOLS_MAP

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ─── Page Config ──────────────────────────────────────────────────────
st.set_page_config(
    page_title="Placement Prep Agent",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ───────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Import Google Font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* Global font */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Header gradient */
    .main-header {
        background: linear-gradient(135deg, #6366f1 0%, #0d9488 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 0;
    }

    .sub-header {
        color: var(--text-color);
        opacity: 0.7;
        font-size: 1.1rem;
        font-weight: 300;
        margin-top: -10px;
        margin-bottom: 1.5rem;
    }

    /* Cards */
    .metric-card {
        background: var(--secondary-background-color);
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-radius: 12px;
        padding: 1.2rem;
        margin: 0.5rem 0;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }

    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(99, 102, 241, 0.15);
    }

    /* Severity badges */
    .badge-missing {
        background: linear-gradient(135deg, #ef4444, #dc2626);
        color: white;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
    }

    .badge-weak {
        background: linear-gradient(135deg, #f59e0b, #d97706);
        color: white;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
    }

    .badge-strong {
        background: linear-gradient(135deg, #10b981, #059669);
        color: white;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
    }

    /* Pipeline step indicators */
    .step-active {
        color: #6366f1;
        font-weight: 600;
    }

    .step-done {
        color: #10b981;
    }

    .step-pending {
        color: #475569;
    }

    /* Problem difficulty badges */
    .diff-easy { color: #10b981; font-weight: 600; }
    .diff-medium { color: #f59e0b; font-weight: 600; }
    .diff-hard { color: #ef4444; font-weight: 600; }

    /* Section dividers */
    .section-divider {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, #6366f1, transparent);
        margin: 2rem 0;
    }

    /* Guardrail warning */
    .guardrail-warning {
        background: rgba(239, 68, 68, 0.1);
        border: 1px solid #ef4444;
        border-radius: 12px;
        padding: 1rem;
        margin: 1rem 0;
    }

    /* Score ring */
    .score-container {
        text-align: center;
        padding: 1rem;
    }

    .score-value {
        font-size: 3rem;
        font-weight: 700;
        line-height: 1;
    }

    .score-label {
        color: var(--text-color);
        opacity: 0.7;
        font-size: 0.85rem;
        margin-top: 0.3rem;
    }

    /* Animate appearance */
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .animate-in {
        animation: fadeInUp 0.5s ease-out forwards;
    }

    /* Rewrite suggestion diff style */
    .rewrite-before {
        background: rgba(239, 68, 68, 0.1);
        border-left: 3px solid #ef4444;
        padding: 8px 12px;
        border-radius: 0 8px 8px 0;
        margin: 4px 0;
        font-size: 0.9rem;
    }

    .rewrite-after {
        background: rgba(16, 185, 129, 0.1);
        border-left: 3px solid #10b981;
        padding: 8px 12px;
        border-radius: 0 8px 8px 0;
        margin: 4px 0;
        font-size: 0.9rem;
    }

    /* Hide default Streamlit elements for cleaner look */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# ─── Initialize Session State ─────────────────────────────────────────
if "report" not in st.session_state:
    st.session_state.report = None
if "pipeline_step" not in st.session_state:
    st.session_state.pipeline_step = 0
if "session_store" not in st.session_state:
    st.session_state.session_store = SessionStore()


def _get_score_color(score: int) -> str:
    """Get color based on match score."""
    if score >= 75:
        return "#10b981"
    elif score >= 50:
        return "#f59e0b"
    else:
        return "#ef4444"


def _severity_badge(severity: str) -> str:
    """Render a severity badge."""
    return f'<span class="badge-{severity}">{severity.upper()}</span>'


def _difficulty_badge(difficulty: str) -> str:
    """Render a difficulty badge."""
    cls = f"diff-{difficulty.lower()}"
    return f'<span class="{cls}">{difficulty}</span>'


# ─── Sidebar ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<p class="main-header" style="font-size:1.8rem;">🎯 Placement Prep Agent</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header" style="font-size:0.9rem;">Turn any JD into your personalized prep kit</p>', unsafe_allow_html=True)

    st.markdown("---")

    # Mode indicator
    if config.MOCK_MODE or not config.API_KEY:
        st.warning("⚠️ **Mock Mode** — Using sample data. Add your API key to `.env` for real analysis.", icon="🔧")
    else:
        st.success(f"✅ Connected to **{config.MODEL_NAME}**", icon="🤖")

    st.markdown("### 📝 Job Description")
    jd_input_method = st.radio("Input method:", ["Paste text", "Upload file"], key="jd_method", horizontal=True, label_visibility="collapsed")

    def extract_text_from_file(uploaded_file):
        if uploaded_file is None:
            return ""
        uploaded_file.seek(0)
        if uploaded_file.name.lower().endswith(".pdf"):
            try:
                import fitz
                doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
                text = ""
                for page in doc:
                    text += page.get_text()
                
                if not text.strip():
                    st.warning(f"⚠️ Could not extract any text from '{uploaded_file.name}'. It might be a scanned image or formatting issue. Please use the 'Paste text' option instead.", icon="⚠️")
                return text
            except Exception as e:
                st.error(f"Error reading PDF: {e}")
                return ""
        else:
            try:
                return uploaded_file.read().decode("utf-8")
            except UnicodeDecodeError:
                uploaded_file.seek(0)
                return uploaded_file.read().decode("latin-1", errors="replace")

    if jd_input_method == "Paste text":
        jd_text = st.text_area(
            "Paste the Job Description",
            height=200,
            placeholder="Paste the full job description here...",
            key="jd_text",
        )
    else:
        jd_file = st.file_uploader("Upload JD", type=["txt", "md", "pdf"], key="jd_file")
        jd_text = extract_text_from_file(jd_file)

    st.markdown("### 📄 Your Resume")
    resume_input_method = st.radio("Input method:", ["Paste text", "Upload file"], key="resume_method", horizontal=True, label_visibility="collapsed")

    if resume_input_method == "Paste text":
        resume_text = st.text_area(
            "Paste your Resume",
            height=200,
            placeholder="Paste your resume text here...",
            key="resume_text",
        )
    else:
        resume_file = st.file_uploader("Upload Resume", type=["txt", "md", "pdf"], key="resume_file")
        resume_text = extract_text_from_file(resume_file)

    st.markdown("### ⚙️ Options")
    company_name = st.text_input("Company Name (optional)", placeholder="e.g., Unisys, ZopSmart", key="company_name")
    role_level = st.selectbox("Role Level", ["entry", "intern", "mid", "senior"], key="role_level")
    focus_preference = st.selectbox(
        "Practice Focus",
        ["mixed", "DSA", "system_design", "behavioral"],
        key="focus_pref",
    )

    st.markdown("---")

    # Analyze button
    analyze_clicked = st.button(
        "🚀 Analyze & Generate Prep Kit",
        use_container_width=True,
        type="primary",
        disabled=not (jd_text and resume_text),
    )

    # Past sessions
    st.markdown("---")
    st.markdown("### 📚 Past Sessions")
    sessions = st.session_state.session_store.list_sessions(limit=5)
    if sessions:
        for session in sessions:
            score = session.get("overall_score", 0)
            color = _get_score_color(score)
            st.markdown(
                f"**{session['session_name']}**  \n"
                f"Score: <span style='color:{color};font-weight:600;'>{score}/100</span> · "
                f"{session['created_at'][:10]}",
                unsafe_allow_html=True,
            )
            if st.button(f"📋 View", key=f"view_{session['id'][:8]}"):
                full = st.session_state.session_store.get_session(session["id"])
                if full:
                    st.session_state.report = {
                        "company": full["company"],
                        "role": full["role"],
                        "overall_score": full.get("overall_score", 0),
                        "parsed_jd": full["jd_parsed"],
                        "parsed_resume": full["resume_parsed"],
                        "gap_analysis": full["gap_analysis"],
                        "practice_set": full["practice_set"],
                        "interview_questions": full["interview_questions"],
                        "markdown_report": "_(Loaded from session history)_",
                    }
                    st.rerun()
    else:
        st.caption("No past sessions yet. Run your first analysis!")


# ─── Main Content Area ────────────────────────────────────────────────

if analyze_clicked and jd_text and resume_text:
    # ─── PIPELINE EXECUTION ──────────────────────────────────────

    # Step 0: Guardrails
    st.markdown("---")
    pipeline_status = st.empty()
    progress_bar = st.progress(0)

    pipeline_status.markdown("### 🛡️ Step 0/6 — Running guardrail checks...")
    jd_guard = check_guardrails(jd_text, "jd")
    resume_guard = check_guardrails(resume_text, "resume")

    if not jd_guard.is_safe or not resume_guard.is_safe:
        all_flags = jd_guard.flags + resume_guard.flags
        st.markdown('<div class="guardrail-warning">', unsafe_allow_html=True)
        st.error("⛔ **Input Rejected — Potential Prompt Injection Detected**")
        for flag in all_flags:
            st.markdown(f"- 🚩 {flag}")
        st.markdown(
            "Please review your input and remove any suspicious content. "
            "If you believe this is a false positive, try rephrasing the flagged section."
        )
        st.markdown('</div>', unsafe_allow_html=True)
        st.stop()

    progress_bar.progress(10)
    clean_jd = jd_guard.sanitized_text
    clean_resume = resume_guard.sanitized_text

    # Step 1: Parse JD
    pipeline_status.markdown("### 📋 Step 1/6 — Parsing job description...")
    parsed_jd_result = parse_jd(clean_jd)
    progress_bar.progress(25)

    # Step 2: Parse Resume
    pipeline_status.markdown("### 📄 Step 2/6 — Parsing your resume...")
    parsed_resume_result = parse_resume(clean_resume)
    progress_bar.progress(40)

    # Step 3: Gap Analysis
    pipeline_status.markdown("### 🔍 Step 3/6 — Analyzing gaps...")

    # Check for prior session (session memory!)
    detected_company = company_name or parsed_jd_result.get("company", "")
    prior_session = None
    prior_gaps = None
    if detected_company and detected_company != "Not Specified":
        prior_session = st.session_state.session_store.find_prior_session(detected_company)
        if prior_session:
            prior_gaps = prior_session.get("gap_analysis")
            st.info(f"📝 Found prior session for **{detected_company}** — comparing against previous analysis!", icon="🔄")

    gap_result = gap_analysis(parsed_jd_result, parsed_resume_result, prior_gaps)
    progress_bar.progress(60)

    # Step 4: Practice Set
    pipeline_status.markdown("### 💻 Step 4/6 — Building practice set...")
    practice_result = generate_practice_set(
        parsed_jd_result, gap_result, role_level, focus_preference
    )
    progress_bar.progress(75)

    # Step 5: Interview Questions
    pipeline_status.markdown("### 🎤 Step 5/6 — Generating interview questions...")
    interview_result = generate_interview_questions(
        parsed_jd_result, parsed_resume_result, gap_result
    )
    progress_bar.progress(90)

    # Step 6: Compile Report
    pipeline_status.markdown("### 📊 Step 6/6 — Compiling your prep kit...")
    report = compile_report(
        jd_raw=clean_jd,
        resume_raw=clean_resume,
        parsed_jd=parsed_jd_result,
        parsed_resume=parsed_resume_result,
        gap_analysis_result=gap_result,
        practice_set=practice_result,
        interview_questions=interview_result,
        company_name=detected_company if detected_company != "Not Specified" else None,
    )

    # Save to session memory
    st.session_state.session_store.save_session(
        company=report["company"],
        role=report["role"],
        jd_raw=clean_jd,
        resume_raw=clean_resume,
        jd_parsed=parsed_jd_result,
        resume_parsed=parsed_resume_result,
        gap_analysis=gap_result,
        practice_set=practice_result,
        interview_questions=interview_result,
        overall_score=report.get("overall_score", 0),
    )

    progress_bar.progress(100)
    pipeline_status.markdown("### ✅ Prep Kit Ready!")
    time.sleep(0.5)
    pipeline_status.empty()
    progress_bar.empty()

    st.session_state.report = report
    st.rerun()


# ─── Display Report ───────────────────────────────────────────────────
if st.session_state.report:
    report = st.session_state.report

    # Header
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown(f'<p class="main-header">🎯 Prep Kit: {report["company"]}</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="sub-header">{report["role"]} · Generated {report.get("timestamp", "")}</p>', unsafe_allow_html=True)
    with col2:
        score = report.get("overall_score", 0)
        color = _get_score_color(score)
        st.markdown(
            f'<div class="score-container">'
            f'<div class="score-value" style="color:{color};">{score}</div>'
            f'<div class="score-label">Match Score / 100</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with col3:
        st.download_button(
            label="📥 Download Prep Kit",
            data=report.get("markdown_report", ""),
            file_name=f"prep_kit_{report['company'].replace(' ', '_').lower()}.md",
            mime="text/markdown",
            use_container_width=True,
        )

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    # Tabs
    tab_jd, tab_gaps, tab_practice, tab_interview = st.tabs([
        "📋 JD Breakdown",
        "🔍 Gap Analysis",
        "💻 Practice Set",
        "🎤 Interview Questions",
    ])

    # ─── Tab 1: JD Breakdown ─────────────────────────────────────
    with tab_jd:
        parsed_jd_data = report["parsed_jd"]

        col_must, col_nice = st.columns(2)

        with col_must:
            st.markdown("### Must-Have Skills")
            for skill in parsed_jd_data.get("must_have_skills", []):
                st.markdown(
                    f'<div class="metric-card">'
                    f'<strong>{skill["skill"]}</strong><br>'
                    f'<em style="color:var(--text-color);opacity:0.7;">"{skill["jd_citation"]}"</em><br>'
                    f'<small style="color:var(--text-color);opacity:0.6;">Line {skill.get("line_number", "?")}</small>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        with col_nice:
            st.markdown("### Nice-to-Have Skills")
            for skill in parsed_jd_data.get("nice_to_have_skills", []):
                st.markdown(
                    f'<div class="metric-card">'
                    f'<strong>{skill["skill"]}</strong><br>'
                    f'<em style="color:var(--text-color);opacity:0.7;">"{skill["jd_citation"]}"</em><br>'
                    f'<small style="color:var(--text-color);opacity:0.6;">Line {skill.get("line_number", "?")}</small>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        st.markdown("### 🎯 Inferred Evaluation Focus")
        eval_focus = parsed_jd_data.get("evaluation_focus", {})
        areas = eval_focus.get("primary_areas", [])
        if areas:
            cols = st.columns(len(areas))
            for i, area in enumerate(areas):
                with cols[i]:
                    st.markdown(
                        f'<div class="metric-card" style="text-align:center;">'
                        f'<strong style="color:#6366f1;">{area.replace("_", " ").title()}</strong>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
        st.markdown(f"**Reasoning:** {eval_focus.get('reasoning', 'N/A')}")

        if eval_focus.get("supporting_citations"):
            with st.expander("📎 Supporting Citations"):
                for cite in eval_focus["supporting_citations"]:
                    st.markdown(f"- _\"{cite}\"_")

    # ─── Tab 2: Gap Analysis ─────────────────────────────────────
    with tab_gaps:
        gap_data = report["gap_analysis"]

        # Summary
        st.markdown(f"_{gap_data.get('summary', '')}_")

        # Improvements since last session
        improvements = gap_data.get("improvements_since_last_session")
        if improvements:
            st.success("### ✅ Improvements Since Last Session")
            for imp in improvements:
                st.markdown(f"- {imp}")

        # Gap counts
        gaps = gap_data.get("gaps", [])
        missing_count = sum(1 for g in gaps if g.get("severity") == "missing")
        weak_count = sum(1 for g in gaps if g.get("severity") == "weak")
        strong_count = sum(1 for g in gaps if g.get("severity") == "strong")

        col_m, col_w, col_s = st.columns(3)
        with col_m:
            st.markdown(
                f'<div class="metric-card" style="text-align:center;">'
                f'<span class="badge-missing" style="font-size:1.5rem;padding:8px 16px;">{missing_count}</span><br>'
                f'<small style="color:var(--text-color);opacity:0.7;margin-top:8px;display:block;">Missing</small>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with col_w:
            st.markdown(
                f'<div class="metric-card" style="text-align:center;">'
                f'<span class="badge-weak" style="font-size:1.5rem;padding:8px 16px;">{weak_count}</span><br>'
                f'<small style="color:var(--text-color);opacity:0.7;margin-top:8px;display:block;">Weak</small>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with col_s:
            st.markdown(
                f'<div class="metric-card" style="text-align:center;">'
                f'<span class="badge-strong" style="font-size:1.5rem;padding:8px 16px;">{strong_count}</span><br>'
                f'<small style="color:var(--text-color);opacity:0.7;margin-top:8px;display:block;">Strong</small>'
                f'</div>',
                unsafe_allow_html=True,
            )

        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

        # Individual gaps
        for gap in gaps:
            severity = gap.get("severity", "unknown")
            emoji = {"missing": "🔴", "weak": "🟡", "strong": "🟢"}.get(severity, "⚪")

            with st.expander(f"{emoji} **{gap['jd_requirement']}** — {severity.upper()}", expanded=(severity != "strong")):
                st.markdown(f"**JD says:** _\"{gap.get('jd_citation', 'N/A')}\"_")
                evidence = gap.get("resume_evidence") or "_Not found in resume_"
                st.markdown(f"**Resume shows:** {evidence}")

                if gap.get("rewrite_suggestions"):
                    st.markdown("**✏️ Suggested Rewrites:**")
                    for i, sugg in enumerate(gap["rewrite_suggestions"], 1):
                        st.markdown(
                            f'<div class="rewrite-before">❌ <strong>Before:</strong> {sugg["before"]}</div>'
                            f'<div class="rewrite-after">✅ <strong>After:</strong> {sugg["after"]}</div>',
                            unsafe_allow_html=True,
                        )
                        if i < len(gap["rewrite_suggestions"]):
                            st.markdown("")

    # ─── Tab 3: Practice Set ─────────────────────────────────────
    with tab_practice:
        practice_data = report["practice_set"]

        # Focus topics
        st.markdown("### 🎯 Focus Topics")
        for topic in practice_data.get("focus_topics", []):
            priority = topic.get("priority", "medium")
            icon = "🔥" if priority == "high" else "📌"
            st.markdown(
                f'<div class="metric-card">'
                f'{icon} <strong>{topic["topic"].replace("_", " ").title()}</strong> '
                f'({_severity_badge("missing" if priority == "high" else "weak")})<br>'
                f'<em style="color:var(--text-color);opacity:0.7;">{topic.get("reasoning", "")}</em>'
                f'</div>',
                unsafe_allow_html=True,
            )

        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

        # Practice problems table
        st.markdown("### 📝 Practice Problems")
        problems = practice_data.get("problems", [])
        if problems:
            for i, prob in enumerate(problems, 1):
                diff = prob.get("difficulty", "?")
                diff_color = {"Easy": "#10b981", "Medium": "#f59e0b", "Hard": "#ef4444"}.get(diff, "#94a3b8")
                url = prob.get("url", "#")
                title = prob.get("title", "Unknown")

                st.markdown(
                    f'<div class="metric-card">'
                    f'<strong>#{i}.</strong> '
                    f'<a href="{url}" target="_blank" style="color:#6366f1;text-decoration:none;">{title}</a> '
                    f'<span style="color:{diff_color};font-weight:600;margin-left:8px;">[{diff}]</span><br>'
                    f'<small style="color:var(--text-color);opacity:0.6;">Topics: {", ".join(prob.get("topics", []))}</small><br>'
                    f'<em style="color:var(--text-color);opacity:0.7;font-size:0.85rem;">💡 {prob.get("reason_selected", "")}</em>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.info("No problems matched — try broadening your focus area.")

        # Study plan
        st.markdown("### 📅 Study Plan")
        st.info(practice_data.get("study_order_suggestion", "N/A"))

    # ─── Tab 4: Interview Questions ──────────────────────────────
    with tab_interview:
        interview_data = report["interview_questions"]
        questions = interview_data.get("questions", [])

        tech_qs = [q for q in questions if q.get("type") == "technical"]
        behav_qs = [q for q in questions if q.get("type") == "behavioral"]

        col_tech, col_behav = st.columns(2)
        with col_tech:
            st.markdown(f"### 🔧 Technical ({len(tech_qs)})")
        with col_behav:
            st.markdown(f"### 💬 Behavioral ({len(behav_qs)})")

        for i, q in enumerate(questions, 1):
            q_type = q.get("type", "technical")
            emoji = "🔧" if q_type == "technical" else "💬"
            badge_class = "badge-weak" if q_type == "technical" else "badge-strong"

            with st.expander(f"{emoji} Q{i}: {q['question'][:80]}{'...' if len(q.get('question', '')) > 80 else ''}"):
                st.markdown(f"**Full Question:** {q['question']}")
                st.markdown(f"**Type:** {_severity_badge('weak' if q_type == 'technical' else 'strong')}", unsafe_allow_html=True)


else:
    # ─── Landing Page ─────────────────────────────────────────────
    st.markdown('<p class="main-header">🎯 Placement Prep Agent</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Turn any job description into your personalized placement prep kit — powered by AI</p>', unsafe_allow_html=True)

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    features = [
        ("📋", "JD Breakdown", "Extracts must-have & nice-to-have skills with exact JD citations"),
        ("🔍", "Gap Analysis", "Side-by-side comparison with severity flags and rewrite suggestions"),
        ("💻", "Practice Set", "8-12 curated problems matched to the JD's evaluation focus"),
        ("🎤", "Mock Interview", "6-10 questions tied to specific JD requirements"),
    ]
    for col, (icon, title, desc) in zip([col1, col2, col3, col4], features):
        with col:
            st.markdown(
                f'<div class="metric-card" style="text-align:center;min-height:160px;">'
                f'<div style="font-size:2.5rem;margin-bottom:8px;">{icon}</div>'
                f'<strong style="color:var(--text-color);">{title}</strong><br>'
                f'<small style="color:var(--text-color);opacity:0.7;">{desc}</small>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    st.markdown("""
    ### 🚀 How to Use
    1. **Paste your Job Description** in the sidebar (or upload a text file)
    2. **Paste your Resume** (or upload)
    3. _(Optional)_ Set company name, role level, and practice focus
    4. Click **"🚀 Analyze & Generate Prep Kit"**
    5. Review your personalized prep kit across 4 tabs
    6. **Download** the full report as Markdown

    ### 🧠 Session Memory
    The agent remembers your past analyses! If you come back with a revised resume or a new JD from the same company,
    it will compare against your previous session and show what's improved.

    ### 🛡️ Guardrails
    All inputs are scanned for prompt injection attempts before processing.
    The agent only references information explicitly present in your text — it never fabricates claims.
    """)

if __name__ == "__main__":
    import os
    import sys
    import streamlit.runtime as st_runtime
    
    if not st_runtime.exists():
        from streamlit.web import cli as stcli
        sys.argv = ["streamlit", "run", os.path.abspath(__file__)]
        sys.exit(stcli.main())
