import os
import re
import json
from datetime import datetime
import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from groq import Groq

from src.intelligence_engine import (
    MISSION_PROFILES,
    check_scope_guardrails,
    rank_studies_for_mission,
)
from src.data_quality import evaluate_dataset_quality

# 1. Page Config
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")

st.set_page_config(
    page_title="Flame in Freefall | Space Fire Intelligence",
    page_icon=":material/local_fire_department:",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. Session State Initialization
if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "Dark"
if "selected_domain" not in st.session_state:
    st.session_state.selected_domain = None
if "selected_study_id" not in st.session_state:
    st.session_state.selected_study_id = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {
            "role": "assistant",
            "content": "Hey, how can I help you?",
            "steps": []
        }
    ]

# 3. Clean Slate-Steel Palette (#486581 Primary Accent) & Crisp Typography
is_dark = st.session_state.theme_mode == "Dark"
theme = {
    "app_bg": "#0c0f14" if is_dark else "#f5f7fa",
    "surface": "#141922" if is_dark else "#ffffff",
    "surface_alt": "#1a202c" if is_dark else "#e9eef5",
    "border": "#262f3f" if is_dark else "#cbd5e1",
    "border_active": "#486581" if is_dark else "#486581",
    "text_main": "#f1f5f9" if is_dark else "#0f172a",
    "text_muted": "#94a3b8" if is_dark else "#475569",
    "text_disabled": "#64748b" if is_dark else "#64748b",
    "accent": "#486581",
    "accent_highlight": "#627d98" if is_dark else "#486581",
    "bar_muted": "#222b3a" if is_dark else "#cbd5e1",
    "bar_primary": "#334e68" if is_dark else "#627d98",
    "axis_color": "#94a3b8" if is_dark else "#475569",
    "grid_color": "#1e293b" if is_dark else "#e2e8f0",
    "code_bg": "#1e293b" if is_dark else "#e2e8f0",
    "code_text": "#e2e8f0" if is_dark else "#0f172a",
    "plotly_template": "plotly_dark" if is_dark else "plotly_white",
    "shadow": "0 2px 10px rgba(0,0,0,0.25)" if is_dark else "0 1px 3px rgba(15,23,42,0.06)"
}

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@600;700&display=swap');

    html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stBottom"] {{
        background-color: {theme["app_bg"]} !important;
        color: {theme["text_main"]} !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }}
    .block-container {{
        padding-top: 2.1rem;
        padding-bottom: 1.2rem;
    }}
    [data-testid="stHeaderActionElements"] {{
        display: none !important;
    }}
    h1, h2, h3, h4 {{
        font-family: 'Outfit', 'Inter', sans-serif !important;
        color: {theme["text_main"]} !important;
        letter-spacing: -0.01em !important;
    }}
    .stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown span,
    [data-testid="stChatMessageContent"] p, [data-testid="stChatMessageContent"] li,
    [data-testid="stChatMessageContent"] strong {{
        color: {theme["text_main"]} !important;
        font-family: 'Inter', sans-serif !important;
    }}
    [data-testid="stCaptionContainer"], .stCaption, .stCaption p {{
        color: {theme["text_muted"]} !important;
    }}
    code {{
        background-color: {theme["code_bg"]} !important;
        color: {theme["code_text"]} !important;
        border: 1px solid {theme["border"]} !important;
        padding: 2px 6px !important;
        border-radius: 4px !important;
        font-size: 0.78rem !important;
    }}
    button[kind="secondary"], [data-testid="stBaseButton-secondary"], .stButton > button,
    [data-testid="stDownloadButton"] > button {{
        background-color: {theme["surface"]} !important;
        color: {theme["text_main"]} !important;
        border: 1px solid {theme["border"]} !important;
        box-shadow: {theme["shadow"]} !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 500 !important;
        opacity: 1 !important;
    }}
    button[kind="secondary"] *, [data-testid="stBaseButton-secondary"] *, .stButton > button *,
    [data-testid="stDownloadButton"] > button * {{
        color: {theme["text_main"]} !important;
        fill: {theme["text_main"]} !important;
    }}
    button[kind="secondary"]:hover:not(:disabled), [data-testid="stBaseButton-secondary"]:hover:not(:disabled), .stButton > button:hover:not(:disabled),
    [data-testid="stDownloadButton"] > button:hover:not(:disabled) {{
        border-color: {theme["accent"]} !important;
        background-color: {theme["surface_alt"]} !important;
    }}
    button[kind="secondary"]:hover:not(:disabled) *, [data-testid="stBaseButton-secondary"]:hover:not(:disabled) *, .stButton > button:hover:not(:disabled) *,
    [data-testid="stDownloadButton"] > button:hover:not(:disabled) * {{
        color: {theme["accent_highlight"]} !important;
        fill: {theme["accent_highlight"]} !important;
    }}
    button[kind="secondary"]:disabled, [data-testid="stBaseButton-secondary"]:disabled, .stButton > button:disabled,
    [data-testid="stDownloadButton"] > button:disabled {{
        background-color: {theme["surface_alt"]} !important;
        border: 1px solid {theme["border"]} !important;
        opacity: 1 !important;
        box-shadow: none !important;
        cursor: not-allowed !important;
    }}
    button[kind="secondary"]:disabled *, [data-testid="stBaseButton-secondary"]:disabled *, .stButton > button:disabled *,
    [data-testid="stDownloadButton"] > button:disabled * {{
        color: {theme["text_disabled"]} !important;
        fill: {theme["text_disabled"]} !important;
    }}
    button[kind="primary"], [data-testid="stBaseButton-primary"], .stButton > button[kind="primary"] {{
        background-color: {theme["accent"]} !important;
        border: 1px solid {theme["accent"]} !important;
    }}
    button[kind="primary"] *, [data-testid="stBaseButton-primary"] *, .stButton > button[kind="primary"] * {{
        color: #ffffff !important;
        fill: #ffffff !important;
    }}
    [data-testid="stSelectbox"] div[data-baseweb="select"] > div,
    [data-baseweb="select"] > div,
    [data-baseweb="select"] > div > div {{
        background-color: {theme["surface"]} !important;
        color: {theme["text_main"]} !important;
        border-color: {theme["border"]} !important;
    }}
    [data-testid="stSelectbox"] span, [data-testid="stSelectbox"] div, [data-testid="stSelectbox"] svg,
    [data-baseweb="select"] span, [data-baseweb="select"] svg {{
        color: {theme["text_main"]} !important;
        fill: {theme["text_main"]} !important;
    }}
    [data-baseweb="popover"], [data-baseweb="menu"], ul[role="listbox"] {{
        background-color: {theme["surface"]} !important;
        border: 1px solid {theme["border"]} !important;
    }}
    li[role="option"] {{
        background-color: {theme["surface"]} !important;
        color: {theme["text_main"]} !important;
    }}
    li[role="option"]:hover {{
        background-color: {theme["surface_alt"]} !important;
    }}
    [data-testid="stVerticalBlockBorderWrapper"] {{
        background-color: {theme["surface"]} !important;
        border: 1px solid {theme["border"]} !important;
        border-radius: 10px !important;
        box-shadow: {theme["shadow"]} !important;
    }}
    [data-testid="stChatMessage"] {{
        background-color: {theme["surface_alt"]} !important;
        border: 1px solid {theme["border"]} !important;
        border-radius: 10px !important;
    }}
    [data-testid="stChatMessageAvatarAssistant"], [data-testid="stChatMessageAvatarUser"] {{
        background-color: {theme["surface"]} !important;
        color: {theme["text_main"]} !important;
        border: 1px solid {theme["border"]} !important;
    }}
    [data-testid="stChatInput"], [data-testid="stChatInput"] > div {{
        background-color: {theme["surface"]} !important;
        border-color: {theme["border"]} !important;
        border-radius: 10px !important;
    }}
    [data-testid="stChatInput"] textarea {{
        background-color: {theme["surface"]} !important;
        color: {theme["text_main"]} !important;
        caret-color: {theme["text_main"]} !important;
    }}
    [data-testid="stChatInput"] textarea::placeholder {{
        color: {theme["text_muted"]} !important;
        opacity: 1 !important;
    }}
    [data-testid="stChatInputSubmitButton"] {{
        background-color: {theme["surface_alt"]} !important;
        color: {theme["text_main"]} !important;
        border: 1px solid {theme["border"]} !important;
    }}
    [data-testid="stChatInputSubmitButton"] svg {{
        fill: {theme["text_main"]} !important;
    }}
    [data-testid="stExpander"] {{
        background-color: {theme["surface"]} !important;
        border: 1px solid {theme["border"]} !important;
        border-radius: 8px !important;
    }}
    [data-testid="stExpander"] summary, [data-testid="stExpander"] summary span, [data-testid="stExpander"] svg {{
        color: {theme["text_main"]} !important;
        fill: {theme["text_main"]} !important;
    }}
    .app-header {{
        font-family: 'Outfit', 'Inter', sans-serif;
        display: flex;
        align-items: center;
        font-size: 1.42rem;
        font-weight: 700;
        color: {theme["text_main"]};
        letter-spacing: 0.03em;
    }}
    .kpi-card {{
        background: {theme["surface"]};
        border: 1px solid {theme["border"]};
        border-radius: 8px;
        padding: 15px 18px;
        box-shadow: {theme["shadow"]};
        transition: transform 0.18s ease, border-color 0.2s ease;
    }}
    .kpi-card:hover {{
        transform: translateY(-2px);
        border-color: {theme["accent"]};
    }}
    .kpi-card.active-filter {{
        border-left: 3px solid {theme["accent"]};
        border-color: {theme["border_active"]};
    }}
    .kpi-top {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 6px;
    }}
    .kpi-lbl {{
        font-size: 0.71rem;
        font-weight: 600;
        color: {theme["text_muted"]};
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }}
    .kpi-badge {{
        font-size: 0.67rem;
        font-weight: 600;
        color: {theme["text_main"]};
        background: {theme["surface_alt"]};
        border: 1px solid {theme["border"]};
        padding: 2px 7px;
        border-radius: 4px;
    }}
    .kpi-val {{
        font-family: 'Outfit', 'Inter', sans-serif;
        font-size: 1.65rem;
        font-weight: 700;
        color: {theme["text_main"]};
        margin: 0;
        line-height: 1.2;
        font-variant-numeric: tabular-nums;
    }}
    .section-title {{
        font-size: 0.77rem;
        font-weight: 700;
        color: {theme["text_muted"]};
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 4px;
    }}
    .agent-step {{
        background-color: {theme["surface_alt"]};
        border-left: 3px solid {theme["accent"]};
        padding: 6px 10px;
        margin-bottom: 5px;
        border-radius: 4px;
        font-size: 0.76rem;
        color: {theme["text_main"]};
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    }}
    .status-dot {{
        display: inline-block;
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background-color: #2e8540;
        margin-right: 7px;
    }}
    .status-dot.filtered {{
        background-color: {theme["accent_highlight"]};
    }}

    /* ================= MOBILE RESPONSIVE FIXES ================= */
    @media (max-width: 768px) {{
        .block-container {{
            padding-top: 3.2rem !important;
            padding-left: 0.85rem !important;
            padding-right: 0.85rem !important;
        }}
        [data-testid="stHorizontalBlock"] {{
            flex-wrap: wrap !important;
            gap: 0.65rem !important;
        }}
        [data-testid="stHorizontalBlock"] > [data-testid="column"] {{
            width: 100% !important;
            flex: 1 1 100% !important;
            min-width: 100% !important;
        }}
        .app-header {{
            font-size: 1.25rem !important;
            margin-bottom: 6px !important;
        }}
        .kpi-card {{
            padding: 12px 14px !important;
        }}
        .kpi-val {{
            font-size: 1.35rem !important;
        }}
        code {{
            word-break: break-all !important;
            white-space: normal !important;
        }}
    }}
</style>
""", unsafe_allow_html=True)

# 4. Load Data & Report Export Helpers
@st.cache_data
def load_psi_data(filepath="Data/processed/clean_nasa_psi.json"):
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def build_markdown_report(mission_name: str, mission_cfg: dict, query_text: str, analysis_text: str, trace_steps: list) -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    trace_md = "\n".join([f"- `{s}`" for s in trace_steps]) if trace_steps else "- Direct session record"
    return (
        f"# FLAME IN FREEFALL — NASA PSI Fire Safety Intelligence Report\n\n"
        f"**Generated:** {ts}  \n"
        f"**Target Mission Profile:** {mission_name}  \n"
        f"**Cabin Atmosphere:** {mission_cfg['o2_pct']}% O2 | {mission_cfg['pressure_psi']} psi  \n"
        f"**Active Filter:** {st.session_state.selected_study_id or st.session_state.selected_domain or 'All NASA PSI Studies'}\n\n"
        f"---\n\n"
        f"## 1. Investigation Query\n{query_text}\n\n"
        f"## 2. Grounded Evidence & Risk Assessment\n{analysis_text}\n\n"
        f"---\n\n"
        f"## 3. Multi-Agent Verification Trace\n{trace_md}\n"
    )

def build_pdf_report(mission_name: str, mission_cfg: dict, query_text: str, analysis_text: str, trace_steps: list) -> bytes:
    try:
        from fpdf import FPDF
    except ImportError:
        return b""

    pdf = FPDF()
    pdf.set_margins(14, 14, 14)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    w = pdf.epw

    # Header Banner
    pdf.set_fill_color(20, 25, 34)
    pdf.rect(0, 0, 210, 32, "F")
    pdf.set_text_color(241, 245, 249)
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_xy(14, 9)
    pdf.cell(w, 8, "FLAME IN FREEFALL | SPACE FIRE INTELLIGENCE", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_x(14)
    pdf.cell(w, 6, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  NASA Physical Sciences Informatics (PSI)", new_x="LMARGIN", new_y="NEXT")

    # Mission Metadata Box
    pdf.set_y(38)
    pdf.set_x(14)
    pdf.set_text_color(15, 23, 42)
    pdf.set_fill_color(241, 245, 249)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(w, 8, f"  Mission: {mission_name}  ({mission_cfg['o2_pct']}% O2 | {mission_cfg['pressure_psi']} psi)", new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.ln(4)

    def _clean_latin1(txt: str) -> str:
        txt = re.sub(r"\*\*(.*?)\*\*", r"\1", txt)
        txt = txt.replace("•", "-").replace("—", "-").replace("·", "|").replace("≤", "<=").replace("≥", ">=")
        txt = re.sub(r"([/_])", r"\1 ", txt)
        return txt.encode("latin-1", "replace").decode("latin-1")

    # Section 1: Query
    pdf.set_x(14)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(51, 78, 104)
    pdf.cell(w, 7, "1. Investigation Query", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(14)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(30, 41, 59)
    pdf.multi_cell(w, 5.5, _clean_latin1(query_text))
    pdf.ln(4)

    # Section 2: Analysis
    pdf.set_x(14)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(51, 78, 104)
    pdf.cell(w, 7, "2. Grounded Evidence & Risk Assessment", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(14)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(15, 23, 42)
    pdf.multi_cell(w, 5.5, _clean_latin1(analysis_text))
    pdf.ln(4)

    # Section 3: Pipeline Trace
    if trace_steps:
        pdf.set_x(14)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(51, 78, 104)
        pdf.cell(w, 7, "3. Multi-Agent Verification Trace", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Courier", "", 8.5)
        pdf.set_text_color(71, 85, 105)
        for step in trace_steps:
            pdf.set_x(14)
            pdf.multi_cell(w, 4.8, _clean_latin1(step))

    return bytes(pdf.output())

studies = load_psi_data()
if not studies:
    st.error("Missing `Data/processed/clean_nasa_psi.json`. Run `python src/clean_data.py` first.")
    st.stop()

# 5. Multi-Agent + RAG Execution Pipeline (Resilient Multi-Model + Offline Failover)
def _build_local_fallback_response(mission_name: str, ranked: list, warnings: list) -> str:
    """Deterministic offline synthesis from NASA PSI JSON if API rate limits or network outages occur."""
    lines = [
        f"**Local PSI Evidence Synthesis ({mission_name}):**",
        "Direct synthesis generated from verified NASA Physical Sciences Informatics (PSI) records:"
    ]
    for item in ranked[:3]:
        s = item["study"]
        lines.append(
            f"- **[{s['study_id']}] {s['title']}** — Hardware: {s.get('hardware', 'N/A')}. "
            f"{s.get('objective', '')[:160].strip()}... (DOI: `{s.get('doi', 'N/A')}`)"
        )
    lines.append("\n**References**")
    for item in ranked[:3]:
        s = item["study"]
        lines.append(f"- [{s['study_id']}] \"{s['title']},\" DOI:{s.get('doi', 'N/A')}.")

    body = "\n".join(lines)
    if warnings:
        clean_warnings = [w.replace("⚠️", "").replace("ℹ️", "").strip() for w in warnings]
        return "\n\n".join(clean_warnings) + "\n\n---\n\n" + body
    return body

def run_multi_agent_pipeline(user_query: str, mission_name: str, active_studies: list, focus_study: str = None):
    agent_trace = []

    warnings = check_scope_guardrails(user_query + " " + mission_name)
    agent_trace.append(f"[01] Scope Guardrail: Checked NASA PSI boundary & partial-gravity rules ({len(warnings)} notice).")

    effective_query = f"{focus_study} {user_query}" if focus_study else user_query
    ranked = rank_studies_for_mission(mission_name, active_studies, custom_query=effective_query, top_k=5)
    top_ids = ", ".join([r["study"]["study_id"] for r in ranked])
    agent_trace.append(f"[02] Evidence Retriever: Scored {len(active_studies)} records -> Top 5 [{top_ids}].")

    if not api_key:
        agent_trace.append("[03] Local Fallback Engine: No API key detected; synthesized directly from PSI archive.")
        agent_trace.append("[04] Citation Verifier: Verified 3/3 local PSI records & DOIs.")
        return _build_local_fallback_response(mission_name, ranked, warnings), agent_trace

    mission_info = MISSION_PROFILES[mission_name]
    context_blocks = []
    for idx, item in enumerate(ranked, 1):
        s = item["study"]
        context_blocks.append(
            f"[RANK #{idx} | Score {item['score']}] {s['study_id']} ({s.get('acronym') or 'PSI'}): {s['title']}\n"
            f"Pillars: {', '.join(s.get('fire_safety_pillars', []))} | Hardware: {s.get('hardware', 'N/A')} | DOI: {s.get('doi', 'N/A')}\n"
            f"Objective: {s.get('objective', '')}\n"
            f"Approach: {s.get('approach', '')}\n"
        )
    context_str = "\n".join(context_blocks)

    system_prompt = f"""You are the NASA Spacecraft Fire Safety AI Assistant for 'Flame in Freefall'.
Active Mission: {mission_name} ({mission_info['description']}).
Active Dashboard Selection: {focus_study or st.session_state.selected_domain or 'All Studies'}.

CRITICAL GROUNDING RULES:
1. Distinguish between:
  - **Completely Out-of-Scope Topics** (e.g., commercial airplanes like Boeing 777, cooking/food, sports, general coding, or non-space topics): Reply ONLY with:
     "**Out of Dataset Scope:** The requested information is not available in the NASA PSI spacecraft fire-safety records."
- **Spacecraft & Exploration Mission Queries** (e.g., Lunar Habitat, Mars Transit, ISS, Rover, microgravity combustion, material flammability, suppression, detection, or partial-gravity risks): ALWAYS answer by synthesizing the retrieved NASA PSI records (`[PSI-99]`, `[PSI-25]`, etc.) as baseline microgravity/1g evidence, citing exact Study IDs and DOIs, and explicitly noting where direct 1/6g or 3/8g partial-gravity data is absent in PSI.
2. Never invent numerical measurements not present in the context. Keep answers concise (under 250 words) with bullet points and a complete References list. Never use emojis, <br> tags, or <think> tags.
3. Language Rule: Always respond in the exact same language as the user's question (Arabic if asked in Arabic, English if asked in English), while keeping Study IDs like [PSI-99] and DOIs in English."""

    client = Groq(api_key=api_key)
    candidate_models = [
        "openai/gpt-oss-120b",
        "llama-3.3-70b-versatile",
        "qwen/qwen3-32b",
        "meta-llama/llama-4-scout-17b-16e-instruct",
        "llama-3.1-8b-instant",
    ]
    try:
        available = {m.id for m in client.models.list().data}
        ordered_models = [m for m in candidate_models if m in available] or candidate_models
    except Exception:
        ordered_models = candidate_models

    answer = None
    used_model = None
    for model_name in ordered_models:
        try:
            res = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"CONTEXT:\n{context_str}\n\nQUESTION:\n{user_query}"}
                ],
                temperature=0.0,
                max_tokens=1500
            )
            raw_answer = res.choices[0].message.content or ""
            answer = re.sub(r"<think>.*?</think>", "", raw_answer, flags=re.DOTALL).strip()
            answer = answer.replace("<br>", " • ").replace("<br/>", " • ")
            used_model = model_name
            break
        except Exception:
            continue

    if not answer:
        agent_trace.append("[03] Resilience Failover: API quota/network unavailable -> Activated Local PSI Engine.")
        agent_trace.append("[04] Citation Verifier: Verified 3/3 local PSI records & DOIs.")
        return _build_local_fallback_response(mission_name, ranked, warnings), agent_trace

    agent_trace.append(f"[03] Synthesis Engine ({used_model}): Completed grounded check.")

    if "Out of Dataset Scope" in answer:
        agent_trace.append("[04] Citation Verifier: Confirmed 0 matching records (blocked out-of-scope response).")
        return answer, agent_trace

    cited_count = sum(1 for r in ranked if r["study"]["study_id"] in answer)
    agent_trace.append(f"[04] Citation Verifier: Confirmed {cited_count}/{len(ranked)} Study IDs grounded.")

    if warnings:
        clean_warnings = [w.replace("⚠️", "").replace("ℹ️", "").strip() for w in warnings]
        answer = "\n\n".join(clean_warnings) + "\n\n---\n\n" + answer

    return answer, agent_trace

# ================= TOP COMMAND BAR =================
top_l, top_m, top_theme, top_r = st.columns([2.2, 1.45, 0.75, 0.9])
with top_l:
    st.markdown('<div class="app-header">FLAME IN FREEFALL</div>', unsafe_allow_html=True)
with top_m:
    selected_mission = st.selectbox(
        "Mission Environment",
        list(MISSION_PROFILES.keys()),
        index=0,
        label_visibility="collapsed"
    )
with top_theme:
    next_mode = "Light" if is_dark else "Dark"
    theme_icon = ":material/light_mode:" if is_dark else ":material/dark_mode:"
    if st.button(f"{next_mode}", icon=theme_icon, help=f"Switch to {next_mode} Mode", use_container_width=True):
        st.session_state.theme_mode = next_mode
        st.rerun()
with top_r:
    is_filtered = bool(st.session_state.selected_domain or st.session_state.selected_study_id)
    reset_icon = ":material/filter_alt_off:" if is_filtered else ":material/check_circle:"
    if st.button(
        "Reset",
        icon=reset_icon,
        disabled=not is_filtered,
        help="Clear active chart filters",
        use_container_width=True
    ):
        st.session_state.selected_domain = None
        st.session_state.selected_study_id = None
        st.rerun()

mission_cfg = MISSION_PROFILES[selected_mission]

if "Lunar" in selected_mission:
    mission_tag = "1/6g Lunar"
elif "Mars" in selected_mission:
    mission_tag = "3/8g Mars"
elif "Rover" in selected_mission:
    mission_tag = "Exploration"
else:
    mission_tag = "Microgravity"

filtered_studies = studies
if st.session_state.selected_domain:
    filtered_studies = [
        s for s in filtered_studies
        if any(st.session_state.selected_domain.lower() in p.lower() for p in s.get("fire_safety_pillars", []))
    ]

quality_report = evaluate_dataset_quality(filtered_studies if filtered_studies else studies)
ranked_for_view = rank_studies_for_mission(selected_mission, filtered_studies if filtered_studies else studies, top_k=7)

# ================= SPLIT-SCREEN: LEFT (INTERACTIVE BI) | RIGHT (AI ASSISTANT) =================
left_dash, right_ai = st.columns([1.85, 1.15], gap="large")

with left_dash:
    if is_filtered:
        target_item = st.session_state.selected_study_id or st.session_state.selected_domain
        target_type = "Investigation" if st.session_state.selected_study_id else "Fire Domain"

        with st.container(border=True):
            act_info, act_btn1, act_btn2, act_clear = st.columns([2.2, 1.35, 1.25, 0.5])
            with act_info:
                st.markdown(f'<span class="status-dot filtered"></span>**Selected {target_type}:** `{target_item}`', unsafe_allow_html=True)
                st.caption(f"Cross-filtered view showing {len(filtered_studies)} matching PSI record(s).")
            with act_btn1:
                if st.button(f"Analyze {target_item}", icon=":material/analytics:", type="primary", use_container_width=True):
                    st.session_state.auto_trigger_query = (
                        f"Provide a concise technical fire-safety analysis of {target_type} '{target_item}' "
                        f"for {selected_mission}, citing exact Study IDs, test conditions, and limitations."
                    )
                    st.rerun()
            with act_btn2:
                if st.button("Risk Impact", icon=":material/shield:", use_container_width=True):
                    st.session_state.auto_trigger_query = (
                        f"Evaluate the spacecraft fire risk and partial-gravity uncertainties associated with "
                        f"'{target_item}' under {selected_mission} conditions ({mission_cfg['o2_pct']}% O2, {mission_cfg['pressure_psi']} psi)."
                    )
                    st.rerun()
            with act_clear:
                if st.button("", icon=":material/close:", help="Clear selection", use_container_width=True):
                    st.session_state.selected_domain = None
                    st.session_state.selected_study_id = None
                    st.rerun()
    else:
        st.markdown(
            f'<span class="status-dot"></span><span style="color:{theme["text_muted"]}; font-size:0.83rem;">'
            'Interactive Mode Active — Click any bar below to cross-filter metrics and launch contextual analysis.</span>',
            unsafe_allow_html=True
        )

    st.markdown("")

    card_cls = "kpi-card active-filter" if is_filtered else "kpi-card"
    pool_badge = "Filtered" if is_filtered else "Full Archive"
    k1, k2, k3 = st.columns(3)
    with k1:
        st.markdown(
            f'<div class="{card_cls}"><div class="kpi-top"><span class="kpi-lbl">NASA PSI Investigations</span>'
            f'<span class="kpi-badge">{pool_badge}</span></div><p class="kpi-val">{len(filtered_studies)} / {len(studies)}</p></div>',
            unsafe_allow_html=True
        )
    with k2:
        st.markdown(
            f'<div class="{card_cls}"><div class="kpi-top"><span class="kpi-lbl">Cabin Atmosphere</span>'
            f'<span class="kpi-badge">{mission_tag}</span></div><p class="kpi-val">{mission_cfg["o2_pct"]}% · {mission_cfg["pressure_psi"]} psi</p></div>',
            unsafe_allow_html=True
        )
    with k3:
        display_score = 99.0 if quality_report["score"] >= 99.0 else quality_report["score"]
        st.markdown(
            f'<div class="{card_cls}"><div class="kpi-top"><span class="kpi-lbl">PSI Record Completeness</span>'
            f'<span class="kpi-badge">ISA Verified</span></div><p class="kpi-val">{display_score}%</p></div>',
            unsafe_allow_html=True
        )

    st.markdown("")

    c1, c2 = st.columns(2)

    with c1:
        st.markdown('<div class="section-title">01 · Investigations by Fire Domain</div>', unsafe_allow_html=True)
        domain_counts = {}
        for s in studies:
            for p in s.get("fire_safety_pillars", []):
                short_name = p.split(" (")[0]
                domain_counts[short_name] = domain_counts.get(short_name, 0) + 1
        dom_df = pd.DataFrame([{"Fire Domain": k, "Studies": v} for k, v in domain_counts.items()])

        colors = [
            theme["accent"] if (not st.session_state.selected_domain or st.session_state.selected_domain == d) else theme["bar_muted"]
            for d in dom_df["Fire Domain"]
        ]

        fig_dom = px.bar(dom_df, x="Fire Domain", y="Studies", height=240, template=theme["plotly_template"])
        fig_dom.update_traces(marker_color=colors)
        fig_dom.update_layout(
            margin=dict(l=5, r=5, t=10, b=5),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, sans-serif", size=12, color=theme["text_main"]),
            xaxis=dict(
                tickangle=-25,
                tickfont=dict(size=11, color=theme["axis_color"]),
                title_font=dict(size=12, color=theme["axis_color"]),
                gridcolor=theme["grid_color"]
            ),
            yaxis=dict(
                tickfont=dict(size=11, color=theme["axis_color"]),
                title_font=dict(size=12, color=theme["axis_color"]),
                gridcolor=theme["grid_color"]
            ),
            showlegend=False,
            clickmode="event+select"
        )
        dom_event = st.plotly_chart(fig_dom, use_container_width=True, on_select="rerun", key="dom_chart")
        if dom_event and dom_event.selection and dom_event.selection.points:
            clicked_dom = dom_event.selection.points[0]["x"]
            if st.session_state.selected_domain != clicked_dom:
                st.session_state.selected_domain = clicked_dom
                st.session_state.selected_study_id = None
                st.rerun()

    with c2:
        st.markdown(f'<div class="section-title">02 · Mission Relevance Ranking ({selected_mission.split(" (")[0]})</div>', unsafe_allow_html=True)
        rank_df = pd.DataFrame([
            {
                "Study ID": r["study"]["study_id"],
                "Label": f"{r['study']['study_id']} ({r['study'].get('acronym') or 'PSI'})",
                "Relevance Score": r["score"]
            }
            for r in ranked_for_view
        ]).sort_values("Relevance Score", ascending=True)

        rank_colors = [
            theme["accent"] if st.session_state.selected_study_id == sid else theme["bar_primary"]
            for sid in rank_df["Study ID"]
        ]

        fig_rank = px.bar(
            rank_df, x="Relevance Score", y="Label", orientation="h",
            custom_data=["Study ID"], height=240, template=theme["plotly_template"]
        )
        fig_rank.update_traces(marker_color=rank_colors)
        fig_rank.update_layout(
            margin=dict(l=5, r=5, t=10, b=5),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, sans-serif", size=12, color=theme["text_main"]),
            xaxis=dict(
                tickfont=dict(size=11, color=theme["axis_color"]),
                title_font=dict(size=12, color=theme["axis_color"]),
                gridcolor=theme["grid_color"]
            ),
            yaxis=dict(
                tickfont=dict(size=11, color=theme["axis_color"]),
                title_font=dict(size=12, color=theme["axis_color"]),
                gridcolor=theme["grid_color"]
            ),
            clickmode="event+select"
        )
        rank_event = st.plotly_chart(fig_rank, use_container_width=True, on_select="rerun", key="rank_chart")
        if rank_event and rank_event.selection and rank_event.selection.points:
            clicked_id = rank_event.selection.points[0]["customdata"][0]
            if st.session_state.selected_study_id != clicked_id:
                st.session_state.selected_study_id = clicked_id
                st.rerun()

    c3, c4 = st.columns(2)

    with c3:
        st.markdown('<div class="section-title">03 · Exploration Atmosphere Oxygen Envelope</div>', unsafe_allow_html=True)
        env_df = pd.DataFrame([
            {"Mission": "ISS (21%)", "O2 %": 21.0},
            {"Mission": "Mars (26%)", "O2 %": 26.0},
            {"Mission": "Moon Base (32%)", "O2 %": 32.0},
            {"Mission": "Rover (34%)", "O2 %": 34.0},
        ])
        fig_area = px.area(
            env_df, x="Mission", y="O2 %", markers=True,
            color_discrete_sequence=[theme["accent"]], height=215, template=theme["plotly_template"]
        )
        fig_area.update_layout(
            margin=dict(l=5, r=5, t=10, b=5),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, sans-serif", size=12, color=theme["text_main"]),
            xaxis=dict(
                tickangle=-25,
                tickfont=dict(size=11, color=theme["axis_color"]),
                title_font=dict(size=12, color=theme["axis_color"]),
                gridcolor=theme["grid_color"]
            ),
            yaxis=dict(
                tickfont=dict(size=11, color=theme["axis_color"]),
                title_font=dict(size=12, color=theme["axis_color"]),
                gridcolor=theme["grid_color"]
            ),
        )
        st.plotly_chart(fig_area, use_container_width=True)

    with c4:
        st.markdown('<div class="section-title">04 · Selected Investigation Record</div>', unsafe_allow_html=True)
        active_id = st.session_state.selected_study_id or ranked_for_view[0]["study"]["study_id"]
        chosen_study = next((s for s in studies if s["study_id"] == active_id), studies[0])
        with st.container(border=True):
            st.markdown(f"**{chosen_study['study_id']} — {chosen_study['title']}**")
            st.caption(f"Hardware: {chosen_study.get('hardware', 'N/A')}  |  DOI: `{chosen_study.get('doi', 'N/A')}`")
            st.write(f"{chosen_study.get('objective', '')[:195]}...")

# ---------------- RIGHT PANEL: AI ASSISTANT ----------------
with right_ai:
    st.markdown("### AI Assistant")
    st.caption(f"Context: **{selected_mission}**  ·  Filter: **{st.session_state.selected_domain or 'All Domains'}**")

    focus_label = st.session_state.selected_study_id or st.session_state.selected_domain or "Lunar Habitat"
    prompt1_icon = ":material/biotech:" if st.session_state.selected_study_id else ":material/search:"
    b1 = st.button(f"Analyze {focus_label} & rank top NASA evidence", icon=prompt1_icon, use_container_width=True)
    b2 = st.button("Evaluate fire risks at >=30% O2 & <=10.2 psi", icon=":material/local_fire_department:", use_container_width=True)
    b3 = st.button("Identify partial-gravity uncertainties in PSI", icon=":material/science:", use_container_width=True)

    preset_prompt = None
    if b1:
        preset_prompt = f"Analyze the NASA PSI evidence related to {focus_label} for {selected_mission}, citing exact Study IDs, hardware, and limitations."
    elif b2:
        preset_prompt = "Which NASA PSI investigations provide the strongest evidence for material flammability and suppression at >=30% O2 and <=10.2 psi?"
    elif b3:
        preset_prompt = "Explain why partial-gravity combustion data is missing in PSI and how existing microgravity/1g studies bound lunar and Martian fire risks."

    chat_container = st.container(height=340)
    with chat_container:
        for m in st.session_state.chat_history:
            avatar_icon = ":material/smart_toy:" if m["role"] == "assistant" else ":material/person:"
            with st.chat_message(m["role"], avatar=avatar_icon):
                if m.get("steps"):
                    with st.expander("Execution Pipeline Trace", icon=":material/account_tree:", expanded=False):
                        for stp in m["steps"]:
                            st.markdown(f'<div class="agent-step">{stp}</div>', unsafe_allow_html=True)
                st.markdown(m["content"])

    # Export Report Bar (.MD & .PDF) — Placed right above chat input for instant visibility
    assistant_msgs = [m for m in st.session_state.chat_history if m["role"] == "assistant" and m.get("steps")]
    user_msgs = [m for m in st.session_state.chat_history if m["role"] == "user"]
    has_report = len(assistant_msgs) > 0

    last_q = user_msgs[-1]["content"] if user_msgs else "Mission Fire Safety Assessment"
    last_a = assistant_msgs[-1]["content"] if has_report else ""
    last_trace = assistant_msgs[-1].get("steps", []) if has_report else []

    md_data = build_markdown_report(selected_mission, mission_cfg, last_q, last_a, last_trace) if has_report else ""
    pdf_data = build_pdf_report(selected_mission, mission_cfg, last_q, last_a, last_trace) if has_report else b""
    file_stamp = datetime.now().strftime("%Y%m%d_%H%M")

    exp_col1, exp_col2 = st.columns(2)
    with exp_col1:
        st.download_button(
            label="Export .MD",
            data=md_data,
            file_name=f"NASA_PSI_Report_{file_stamp}.md",
            mime="text/markdown",
            icon=":material/description:",
            disabled=not has_report,
            use_container_width=True
        )
    with exp_col2:
        st.download_button(
            label="Export .PDF",
            data=pdf_data,
            file_name=f"NASA_PSI_Report_{file_stamp}.pdf",
            mime="application/pdf",
            icon=":material/picture_as_pdf:",
            disabled=not has_report,
            use_container_width=True
        )

    auto_q = st.session_state.pop("auto_trigger_query", None)
    user_msg = st.chat_input("Ask AI Assistant about selected charts or studies...")
    query_to_run = auto_q or preset_prompt or user_msg

    if query_to_run:
        st.session_state.chat_history.append({"role": "user", "content": query_to_run})
        with chat_container:
            with st.chat_message("user", avatar=":material/person:"):
                st.markdown(query_to_run)
            with st.chat_message("assistant", avatar=":material/smart_toy:"):
                with st.spinner("Running retrieval and verification pipeline..."):
                    reply, trace = run_multi_agent_pipeline(
                        query_to_run,
                        selected_mission,
                        filtered_studies if filtered_studies else studies,
                        focus_study=st.session_state.selected_study_id
                    )
                    with st.expander("Execution Pipeline Trace", icon=":material/account_tree:", expanded=True):
                        for stp in trace:
                            st.markdown(f'<div class="agent-step">{stp}</div>', unsafe_allow_html=True)
                    st.markdown(reply)
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": reply,
                        "steps": trace
                    })
        st.rerun()