# streamlit run app.py --server.address 0.0.0.0 --server.port=8080

import streamlit as st
from streamlit_ace import st_ace
import httpx
from openai import OpenAI
import os
import tempfile
import tempfile
import os
from src.pdf_utilities import (
    extract_full_text,
    extract_title_and_abstract,
    extract_and_merge_images,
    summarize_text_hierarchical,
)
from src.rag_pipeline_run import run_pipeline
from datetime import datetime
import json


# --------------------------------------------------------------
# Session state
# --------------------------------------------------------------
for k in ("api_key", "client", "api_ok", "paper_title", "review", "todo_items"):
    if k not in st.session_state:
        st.session_state[k] = None

st.session_state.paper_title = st.session_state.paper_title or "Untitled Manuscript"


# --------------------------------------------------------------
# CACHED FUNCTIONS
# --------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def get_client(key, url=""): 
    return OpenAI(base_url=url, api_key=key, http_client=httpx.Client(follow_redirects=True))

# --------------------------------------------------------------
# UI – Instant load, clear flow
# --------------------------------------------------------------
st.set_page_config(page_title="Pre-submission Multimodal Peer Review Simulation",
                   layout="wide")  # wide page layout


st.markdown(
    """
    <style>
    div.stButton > button:first-child {
        height: 3em;               /* 🧱 Increase height here */
        font-size: 1.1em;          /* Slightly larger text */
        background-color: #0F52BA; /* Optional - a nicer blue */
        color: white;
        border-radius: 6px;
        font-weight: 600;
    }
    div.stButton > button:hover {
        background-color: #1446A0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)



st.title("Pre-submission Peer Review Simulation")
st.caption("Multimodal Peer Review Simulation with Actionable To-Do Suggestions for Community-Aware Pre-Submission Revisions")

left_col, right_col = st.columns(2)

with left_col:
    default_latex = r"""\documentclass{article}
\usepackage{amsmath}
\title{Sample LaTeX Document}
\author{Author Name}
\date{\today}

\begin{document}
\maketitle

\section{Introduction}
This is a sample LaTeX article document. You can write text, add lists, and include equations.

\section{Mathematical Example}
Here is an inline formula: $E = mc^2$.

Here is a displayed equation:
\[
\int_{0}^{\infty} e^{-x^2} \, dx = \frac{\sqrt{\pi}}{2}
\]

\section{Conclusion}
LaTeX allows you to create structured, professional documents.

\end{document}
"""

    # Streamlit Ace editor
    latex_code = st_ace(
        value=default_latex,
        language="latex",
        theme="monokai",
        font_size=14,
        tab_size=4,
        height=770,
        show_gutter=True,
        show_print_margin=False,
        wrap=True,  # 👈 Enable text wrapping here
    )

with right_col:

    # Settings (API key)
    with st.expander("⚙️ Settings", expanded=False):
        st.subheader("OpenAI Configuration")
    
        # API Key input
        api_key_input = st.text_input(
            "Enter your OpenAI API Key", 
            key="api_key", 
            type="password"
        )
    
        # Optional Base URL input
        base_url_input = st.text_input(
            "Optional: Enter a custom Base URL", 
            key="base_url", 
            placeholder="https://api.openai.com/v1"
        )
    
        if st.button("Save Settings"):
            if api_key_input:
                try:
                    # Pass the base URL if provided
                    st.session_state.client = get_client(
                        api_key_input, 
                        url=base_url_input if base_url_input else ""
                    )
                    st.session_state.api_ok = True
                    st.success("Settings saved successfully!")
                except Exception as e:
                    st.session_state.api_ok = False
                    st.error(f"Invalid configuration: {e}")
            else:
                st.warning("Please enter your API key.")


    # Upload and review logic

    if not st.session_state.get("api_ok"):
        st.error("⚠️ Please save your API key first in Settings.")
    else:
        uploaded = st.file_uploader("**Upload your PDF manuscript**", type="pdf")

        if uploaded:
            temp_fd, temp_pdf_path = tempfile.mkstemp(suffix=".pdf")
            os.write(temp_fd, uploaded.read())
            os.close(temp_fd)

            st.session_state.uploaded_pdf_path = temp_pdf_path
            st.session_state.paper_title = os.path.splitext(uploaded.name)[0]

            st.markdown("<div style='height: 4px'></div>", unsafe_allow_html=True)
            venue = st.selectbox(
                "Select conference venue for paper submission:",
                ["International World Wide Web Conference (WWW)", "Annual Conference on Neural Information Processing Systems (NeurIPS)", "International Conference on Learning Representations (ICLR)", "Annual Meeting of the Association for Computational Linguistics (ACL)"],
                key="venue_choice",
            )
            
            review_clicked = st.button("🌐 Review Manuscript", use_container_width=True)
                

            if review_clicked:

                with st.spinner("Reviewing..."):
                    full_text = extract_full_text(temp_pdf_path)
                    title, abstract = extract_title_and_abstract(full_text)
                    merged_image_path = extract_and_merge_images(temp_pdf_path)

                    summary = summarize_text_hierarchical(
                        long_text=full_text,
                        client=st.session_state.client,
                        model="gpt-4o",
                    )

                    ref, rev, todo = run_pipeline(st.session_state.client, title, abstract, summary, merged_image_path, 2)

                    st.session_state.review = rev
                    st.session_state.todo_items = todo

                    st.success("✅ Manuscript reviewed successfully!")
        else:
            st.info("Please upload a PDF file to enable the summary button.")


# Review + To‑Do layout
col1, col2 = st.columns([4, 2])

with col1:
    st.subheader("📄 Review")
    if st.session_state.review:
        st.markdown(
            f"""
            <div style="
                height:400px; 
                overflow-y:auto; 
                border:1px solid #CCC; 
                padding:15px; 
                border-radius:8px; 
                font-size:18px;
                line-height:1.6;
            ">
                {st.session_state.review}
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.info("Upload PDF and proceed.")

with col2:
    st.subheader("✅ To‑Do List")
    if st.session_state.todo_items:
        todo_html = "".join(
            f"""
            <label style="
                display:block; 
                margin-bottom:8px; 
                font-size:18px; 
                cursor:pointer;
            ">
                <input type="checkbox" style="margin-right:6px;">
                {item.strip()}
            </label>
            """
            for item in st.session_state.todo_items
        )
        st.markdown(
            f"""
            <div style="
                height:400px; 
                overflow-y:auto; 
                border:1px solid #CCC; 
                padding:15px; 
                border-radius:8px; 
                font-size:14px;
            ">
                {todo_html}
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.info("Upload PDF and proceed.")

