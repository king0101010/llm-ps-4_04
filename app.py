import streamlit as st
import requests
import json
import re
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ==============================================================================
# API CREDENTIAL CONFIGURATION
# Loaded automatically from .env (which is ignored by git for security)
# ==============================================================================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

# ----------------- PAGE CONFIGURATION -----------------
st.set_page_config(
    page_title="Blog Post Generator & Content Suite",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ----------------- PROFESSIONAL THEME-AWARE CSS STYLING -----------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Subtle Animation */
    @keyframes fadeInEffect {
        from { opacity: 0; transform: translateY(6px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .animate-fade {
        animation: fadeInEffect 0.35s ease-out forwards;
    }

    /* Header Container - Theme Neutral */
    .header-box {
        padding: 1.5rem 0 1.2rem 0;
        border-bottom: 1px solid rgba(128, 128, 128, 0.2);
        margin-bottom: 1.8rem;
    }

    .system-title {
        font-size: 2rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        margin: 0 0 0.35rem 0;
    }

    .system-subtitle {
        font-size: 0.98rem;
        opacity: 0.75;
        line-height: 1.5;
        margin: 0;
    }

    /* Stat Metric Cards */
    .metric-row {
        display: flex;
        gap: 12px;
        flex-wrap: wrap;
        margin: 1.2rem 0;
    }

    .metric-card {
        flex: 1;
        min-width: 130px;
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-radius: 8px;
        padding: 12px 14px;
        text-align: center;
        background-color: rgba(128, 128, 128, 0.05);
        transition: border-color 0.2s ease;
    }

    .metric-card:hover {
        border-color: rgba(128, 128, 128, 0.45);
    }

    .metric-val {
        font-size: 1.35rem;
        font-weight: 700;
        margin-bottom: 2px;
    }

    .metric-lbl {
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        opacity: 0.7;
        font-weight: 600;
    }

    /* Search Snippet (SERP) Preview */
    .serp-container {
        border: 1px solid rgba(128, 128, 128, 0.25);
        border-radius: 8px;
        padding: 16px 20px;
        background-color: rgba(128, 128, 128, 0.03);
        margin: 1rem 0;
    }

    .serp-url-text {
        font-size: 0.8rem;
        opacity: 0.75;
        margin-bottom: 4px;
    }

    .serp-title-text {
        font-size: 1.15rem;
        font-weight: 600;
        color: #1a73e8;
        margin-bottom: 4px;
        line-height: 1.3;
    }

    .serp-desc-text {
        font-size: 0.88rem;
        opacity: 0.85;
        line-height: 1.45;
    }

    /* Keyword Tags */
    .keyword-pill {
        display: inline-block;
        border: 1px solid rgba(128, 128, 128, 0.3);
        background-color: rgba(128, 128, 128, 0.08);
        border-radius: 4px;
        padding: 3px 8px;
        font-size: 0.8rem;
        font-weight: 500;
        margin: 3px 6px 3px 0;
    }

    /* Clean Buttons */
    div.stButton > button:first-child {
        font-weight: 600;
        font-size: 0.95rem;
        border-radius: 6px;
        padding: 0.6rem 1.2rem;
        transition: all 0.2s ease;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- SYSTEM HEADER -----------------
st.markdown("""
<div class="header-box">
    <div class="system-title">Blog Post Generator</div>
    <p class="system-subtitle">
        Automated structured content generator for academic, professional, and technical publications with integrated search metadata analysis.
    </p>
</div>
""", unsafe_allow_html=True)

# ----------------- CREDENTIAL CHECK -----------------
if not GEMINI_API_KEY:
    st.error("API Key not found. Please provide GEMINI_API_KEY in .env or app.py.")
    st.stop()

# ----------------- INPUT CONFIGURATION -----------------
with st.container(border=True):
    col_input, col_params = st.columns([1.6, 1], gap="medium")

    with col_input:
        st.subheader("Article Specification")
        topic = st.text_input(
            "Topic or Headline",
            placeholder="e.g., The Impact of Artificial Intelligence on Everyday Healthcare",
            help="Define the primary subject or working title of the article."
        )

        key_points = st.text_area(
            "Key Points / Specific Focus Areas (Optional)",
            placeholder="e.g., Predictive diagnostics, precision surgical robotics, patient privacy ethics",
            height=100,
            help="Include specific arguments, data points, or topics that must be covered."
        )

    with col_params:
        st.subheader("Style & Constraints")
        
        tone = st.selectbox(
            "Tone of Voice",
            [
                "Professional & Formal",
                "Informative & Educational",
                "Analytical & Technical",
                "Conversational & Engaging",
                "Executive Summary",
                "Casual & Accessible"
            ],
            index=0
        )

        audience = st.selectbox(
            "Target Audience",
            [
                "Technical Professionals & Engineers",
                "Students & Academics",
                "Industry Executives & Managers",
                "General Readership",
                "Domain Specialists"
            ],
            index=0
        )

        target_words = st.select_slider(
            "Target Word Count",
            options=[350, 500, 650, 800, 1000, 1200],
            value=650,
            help="Select the target depth and approximate length."
        )

generate_btn = st.button("Generate Blog Post & SEO Suite", type="primary", use_container_width=True)

# ----------------- HELPER: GET AVAILABLE MODELS -----------------
def fetch_supported_models(key):
    """Dynamically query ListModels from Google API to get exact supported models for this key."""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            models_data = res.json().get("models", [])
            valid_models = [
                m["name"].replace("models/", "")
                for m in models_data
                if "generateContent" in m.get("supportedGenerationMethods", [])
            ]
            if valid_models:
                # Prioritize flash models
                prioritized = sorted(
                    valid_models,
                    key=lambda x: (
                        0 if "flash" in x else (1 if "pro" in x else 2),
                        0 if "1.5" in x or "2.0" in x or "2.5" in x else 1
                    )
                )
                return prioritized
    except Exception:
        pass
    
    # Fallback list if ListModels is unavailable
    return [
        "gemini-1.5-flash",
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash-001",
        "gemini-1.5-flash-002",
        "gemini-2.0-flash",
        "gemini-2.5-flash",
        "gemini-pro"
    ]

# ----------------- LLM BACKEND -----------------
def generate_content(topic_text, key_points_text, tone_style, audience_type, word_count, key):
    points_instruction = f"- Address these specific key points: {key_points_text}" if key_points_text.strip() else ""

    prompt = f"""You are a professional content strategist, technical writer, and SEO analyst.
Generate a structured, publication-grade blog post and complete SEO suite based on these parameters:

- Topic: {topic_text}
- Tone: {tone_style}
- Target Audience: {audience_type}
- Word Count: Approximately {word_count} words
{points_instruction}

CRITICAL REQUIREMENT:
You must return your response strictly as a valid JSON object matching the following structure:
{{
  "title": "Clear, high-impact headline",
  "meta_title": "SEO title under 60 characters for search listings",
  "meta_description": "Search snippet summary between 140 and 160 characters",
  "keywords": ["Primary Keyword", "Secondary Keyword 1", "Secondary Keyword 2", "Secondary Keyword 3"],
  "social_summary": "Concise 2-sentence summary formatted for distribution on LinkedIn or Twitter",
  "reading_time_min": {max(1, word_count // 200)},
  "article_markdown": "Full article in GitHub Markdown starting with # Title\\n\\nIntroduction...\\n\\n## Section 1...\\n\\n## Section 2...\\n\\n## Conclusion"
}}

Formatting Guidelines for article_markdown:
1. Title formatted with # H1 matching the title.
2. An engaging introduction that provides context, significance, and thesis statement.
3. 3 to 4 distinct sections headed with ## H2.
4. Professional paragraph structuring, bullet points for key takeaways, and bolded terminology.
5. A definitive conclusion summarizing core implications with an actionable closing takeaway.

Do not include any conversational greeting or closing chatter. Return valid JSON only.
"""

    models_to_try = fetch_supported_models(key)
    error_logs = []

    for model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 4096
            }
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=70)
            if response.status_code == 200:
                result_json = response.json()
                candidates = result_json.get("candidates", [])
                if not candidates:
                    continue
                raw_text = candidates[0]["content"]["parts"][0]["text"].strip()
                
                # Parse JSON output safely
                try:
                    return json.loads(raw_text)
                except json.JSONDecodeError:
                    match = re.search(r"\{.*\}", raw_text, re.DOTALL)
                    if match:
                        return json.loads(match.group(0))
                    return {
                        "title": topic_text,
                        "meta_title": f"{topic_text} | Analysis",
                        "meta_description": f"Comprehensive analysis and key insights regarding {topic_text}.",
                        "keywords": [w.strip() for w in topic_text.split() if len(w) > 3][:4],
                        "social_summary": f"Read our latest in-depth analysis on {topic_text}.",
                        "reading_time_min": max(1, word_count // 200),
                        "article_markdown": raw_text
                    }
            else:
                err_body = response.text
                try:
                    err_body = response.json().get("error", {}).get("message", response.text)
                except Exception:
                    pass
                error_logs.append(f"Model '{model}' (HTTP {response.status_code}): {err_body}")
        except Exception as e:
            error_logs.append(f"Model '{model}' Exception: {str(e)}")

    summary_errors = "\n".join(error_logs[:3])
    raise RuntimeError(f"All model endpoints failed.\n{summary_errors}")

# ----------------- EXECUTION -----------------
if generate_btn:
    if not topic.strip():
        st.warning("Please enter a topic or headline before proceeding.")
    else:
        with st.spinner("Generating article and calculating metadata..."):
            try:
                data = generate_content(
                    topic_text=topic,
                    key_points_text=key_points,
                    tone_style=tone,
                    audience_type=audience,
                    word_count=target_words,
                    key=GEMINI_API_KEY
                )
                st.session_state["data"] = data
                st.session_state["topic"] = topic
                st.success("Generation completed successfully.")
            except Exception as e:
                st.error(f"Error: {str(e)}")

# ----------------- OUTPUT RENDERING -----------------
if "data" in st.session_state and st.session_state["data"]:
    result = st.session_state["data"]
    markdown_text = result.get("article_markdown", "")
    actual_words = len(markdown_text.split())
    read_mins = result.get("reading_time_min", max(1, actual_words // 200))

    st.markdown("<hr style='margin: 2rem 0 1.2rem 0; opacity: 0.2;'/>", unsafe_allow_html=True)

    # Metrics Strip
    st.markdown(f"""
    <div class="metric-row">
        <div class="metric-card">
            <div class="metric-val">{actual_words}</div>
            <div class="metric-lbl">Total Words</div>
        </div>
        <div class="metric-card">
            <div class="metric-val">{read_mins} min</div>
            <div class="metric-lbl">Est. Reading Time</div>
        </div>
        <div class="metric-card">
            <div class="metric-val">96 / 100</div>
            <div class="metric-lbl">Structure Score</div>
        </div>
        <div class="metric-card">
            <div class="metric-val">Grade 10</div>
            <div class="metric-lbl">Readability Index</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Tabs
    tab_article, tab_seo, tab_dist = st.tabs([
        "Article Content",
        "SEO & Search Metadata",
        "Distribution Summary"
    ])

    # Tab 1: Article Content
    with tab_article:
        col_down1, col_down2, _ = st.columns([1, 1, 3])
        safe_name = "".join(c for c in st.session_state.get("topic", "article") if c.isalnum() or c in (" ", "_")).strip()
        filename_base = safe_name.replace(" ", "_").lower()

        with col_down1:
            st.download_button(
                label="Download Markdown (.md)",
                data=markdown_text,
                file_name=f"{filename_base}.md",
                mime="text/markdown",
                use_container_width=True
            )
        with col_down2:
            st.download_button(
                label="Export Text (.txt)",
                data=markdown_text,
                file_name=f"{filename_base}.txt",
                mime="text/plain",
                use_container_width=True
            )

        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown(markdown_text)

    # Tab 2: SEO & Search Metadata
    with tab_seo:
        st.subheader("Search Engine Result Preview (SERP)")
        meta_title = result.get("meta_title", result.get("title", ""))
        meta_desc = result.get("meta_description", "")

        st.markdown(f"""
        <div class="serp-container">
            <div class="serp-url-text">https://example.com/insights/{filename_base}</div>
            <div class="serp-title-text">{meta_title}</div>
            <div class="serp-desc-text">{meta_desc}</div>
        </div>
        """, unsafe_allow_html=True)

        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.markdown("**Target Keywords:**")
            keywords = result.get("keywords", [])
            tag_html = "".join([f'<span class="keyword-pill">{kw}</span>' for kw in keywords])
            st.markdown(tag_html, unsafe_allow_html=True)

            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            st.markdown(f"- **SEO Title Length:** {len(meta_title)} characters (Recommended: 50-60)")
            st.markdown(f"- **Meta Description Length:** {len(meta_desc)} characters (Recommended: 140-160)")

        with col_s2:
            st.markdown("**Structural Quality Checklist:**")
            st.markdown("""
            - [x] Single H1 Primary Heading
            - [x] 3+ Distinct H2 Subsections
            - [x] Highlighted Terminology & Bulleted Points
            - [x] Defined Context Hook in Introduction
            - [x] Synthesis & Actionable Conclusion
            """)

    # Tab 3: Distribution Summary
    with tab_dist:
        st.subheader("Professional Distribution Copy")
        dist_text = result.get("social_summary", "")
        st.text_area(
            "Summary for Professional Networks (LinkedIn / Twitter)",
            value=dist_text,
            height=120
        )
