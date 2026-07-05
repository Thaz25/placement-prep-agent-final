"""
📚 Session History — View and manage past analysis sessions.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from src.memory.session_store import SessionStore

st.set_page_config(page_title="Session History", page_icon="📚", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .metric-card {
        background: linear-gradient(145deg, #1e1e3a 0%, #16213e 100%);
        border: 1px solid #2d2d5e;
        border-radius: 12px;
        padding: 1.2rem;
        margin: 0.5rem 0;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

st.markdown("# 📚 Session History")
st.markdown("View and manage your past placement prep sessions.")

# Initialize store
if "session_store" not in st.session_state:
    st.session_state.session_store = SessionStore()

store = st.session_state.session_store
sessions = store.list_sessions(limit=50)

if not sessions:
    st.info("No sessions yet. Go to the main page and run your first analysis!")
    st.stop()

st.markdown(f"**{len(sessions)}** session(s) found")
st.markdown("---")

for session in sessions:
    score = session.get("overall_score", 0)
    if score >= 75:
        color = "#10b981"
    elif score >= 50:
        color = "#f59e0b"
    else:
        color = "#ef4444"

    col1, col2, col3 = st.columns([3, 1, 1])

    with col1:
        st.markdown(
            f'<div class="metric-card">'
            f'<strong style="font-size:1.1rem;">{session["session_name"]}</strong><br>'
            f'<small style="color:#94a3b8;">{session["company"]} · {session["role"]}</small><br>'
            f'<small style="color:#64748b;">{session["created_at"][:19]}</small>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f'<div style="text-align:center;padding-top:1rem;">'
            f'<span style="font-size:2rem;font-weight:700;color:{color};">{score}</span>'
            f'<br><small style="color:#94a3b8;">Score</small>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with col3:
        if st.button("🗑️ Delete", key=f"del_{session['id'][:8]}"):
            store.delete_session(session["id"])
            st.rerun()

    # Expandable detail view
    with st.expander(f"View details — {session['session_name']}"):
        full = store.get_session(session["id"])
        if full:
            tab_jd, tab_gap, tab_prac, tab_int = st.tabs(["JD", "Gaps", "Practice", "Interview"])

            with tab_jd:
                jd_parsed = full.get("jd_parsed", {})
                st.json(jd_parsed)

            with tab_gap:
                gap = full.get("gap_analysis", {})
                st.markdown(f"**Summary:** {gap.get('summary', 'N/A')}")
                for g in gap.get("gaps", []):
                    sev = g.get("severity", "?")
                    emoji = {"missing": "🔴", "weak": "🟡", "strong": "🟢"}.get(sev, "⚪")
                    st.markdown(f"{emoji} **{g['jd_requirement']}** — {sev}")

            with tab_prac:
                practice = full.get("practice_set", {})
                for p in practice.get("problems", []):
                    st.markdown(f"- [{p.get('title', '?')}]({p.get('url', '#')}) ({p.get('difficulty', '?')})")

            with tab_int:
                interview = full.get("interview_questions", {})
                for q in interview.get("questions", []):
                    badge = "🔧" if q.get("type") == "technical" else "💬"
                    st.markdown(f"{badge} {q.get('question', '?')}")
