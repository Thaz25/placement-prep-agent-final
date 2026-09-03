import sys
import os
import streamlit as st

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.llm_client import chat_with_tools
from src.agent_tools import TOOLS_SCHEMA, TOOLS_MAP

st.set_page_config(page_title="Agent Chat", page_icon="💬", layout="wide")

st.markdown('<p class="main-header">💬 Chat with your Agent</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Ask questions, search for practice problems, or look up past sessions without running a full analysis.</p>', unsafe_allow_html=True)
st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

# CSS for styling
st.markdown("""
<style>
.main-header { font-size: 2rem; font-weight: 700; color: var(--text-color); margin-bottom: 0.5rem; }
.sub-header { font-size: 1.1rem; color: var(--text-color); opacity: 0.8; margin-bottom: 2rem; }
.section-divider { border: 0; height: 1px; background: linear-gradient(to right, transparent, rgba(255,255,255,0.2), transparent); margin: 2rem 0; }
</style>
""", unsafe_allow_html=True)

if "chat_messages" not in st.session_state:
    context_str = "You are a helpful Placement Prep Agent. You have access to tools to search for extra coding problems and to look up past session performance for the user."
    
    # If they generated a report recently, include it in the context!
    if "report" in st.session_state and st.session_state.report:
        report = st.session_state.report
        context_str += (
            f"\n\nThe user just generated a prep kit. Context:\n"
            f"Role: {report['role']} at {report['company']}.\n"
            f"Overall Match Score: {report.get('overall_score', 0)}\n"
            f"Gaps identified: {len(report.get('gap_analysis', {}).get('gaps', []))} gaps.\n"
        )
        
    st.session_state.chat_messages = [
        {"role": "system", "content": context_str},
        {"role": "assistant", "content": "Hi! I'm your Placement Prep Agent. You can ask me to search for practice problems by topic, or look up your past session performance at a specific company. How can I help?"}
    ]

# Display chat history (skipping the system message)
for msg in st.session_state.chat_messages:
    if msg["role"] == "system":
        continue
    # Only show user and assistant messages in UI
    if msg["role"] in ["user", "assistant"] and msg.get("content"):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
# Chat input
if prompt := st.chat_input("Ask a question, request a problem, or lookup a past session..."):
    # Display user message
    st.session_state.chat_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
        
    # Get AI response using Tools
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response_content = chat_with_tools(
                    messages=st.session_state.chat_messages,
                    tools_schema=TOOLS_SCHEMA,
                    tools_map=TOOLS_MAP
                )
                st.markdown(response_content)
                st.session_state.chat_messages.append({"role": "assistant", "content": response_content})
            except Exception as e:
                st.error(f"Error communicating with Agent: {e}")
