"""Investor workspace (Hebrew, right to left) over the agent system.

    streamlit run src/app/streamlit_app.py

Tabs:
* סקירה: the dashboard and the chat side by side. A map of Amsterdam (neighbourhoods sized and
  coloured by their best opportunity; click one to filter), the top opportunities as cards with
  their score breakdown and an "investigate" button that hands the opportunity to the agents,
  and the chat, with live agent activity while the agents work.
* כל ההזדמנויות: the full deterministic table with filters (works without the agents).
* יומן ראיות: every tool result of the session and the running groundedness (criterion 7).
"""
from __future__ import annotations

import html
import math
import os
import re
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
warnings.filterwarnings("ignore")

import pandas as pd
import streamlit as st

from agents.config import AgentConfig
from agents.orchestrator import TITLES, Orchestrator

try:                                    # Community Cloud secrets -> environment (root-level keys)
    if "ANTHROPIC_API_KEY" in st.secrets and not os.environ.get("ANTHROPIC_API_KEY"):
        os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]
except Exception:
    pass

st.set_page_config(page_title="חוקר ההזדמנויות", page_icon="🏘️", layout="wide",
                   initial_sidebar_state="collapsed" if os.environ.get("ANTHROPIC_API_KEY") else "expanded")

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Frank+Ruhl+Libre:wght@500;700&family=IBM+Plex+Sans+Hebrew:wght@400;500;600&display=swap');
:root{--canal:#24566B;--canal-2:#3D7A8F;--canal-soft:#E3EDF0;--ink:#1C2430;--muted:#5D6874;--paper:#F5F6F3;
      --card:#FFFFFF;--line:#DCE1DC;--ochre:#B8862B;--ochre-soft:#F6EBD3;--ok:#2F7D4F;--ok-soft:#E1F0E6;
      --stop:#B23B3B;--stop-soft:#F6E0DE;}
body, p, li, td, th, label, input, textarea, button, .stMarkdown, [data-testid="stCaptionContainer"]{
  font-family:'IBM Plex Sans Hebrew', system-ui, sans-serif;}
[data-testid="stIconMaterial"], .material-symbols-rounded, [class*="material-symbols"]{
  font-family:'Material Symbols Rounded' !important; direction:ltr;}
.stApp{background:var(--paper); color:var(--ink);}
.main .block-container, [data-testid="stMainBlockContainer"]{max-width:1440px; padding-top:1.2rem;}
.stMarkdown, .stChatMessage, [data-testid="stSidebar"], .stTabs, .stAlert, .stExpander,
[data-testid="stChatInput"] textarea, .stTextInput input, .stRadio, .stSelectbox, [data-testid="stHorizontalBlock"]{direction:rtl; text-align:right;}
h1,h2,h3{font-family:'Frank Ruhl Libre', Georgia, serif !important; color:var(--ink); letter-spacing:0;}
code{direction:ltr; unicode-bidi:isolate;}
.stMarkdown ul, .stMarkdown ol{padding-right:1.3rem; padding-left:0;}
table{font-variant-numeric:tabular-nums; border-collapse:collapse;}
th{background:var(--canal-soft); font-weight:600;} td,th{border:1px solid var(--line)!important; padding:.3rem .55rem!important; unicode-bidi:plaintext;}
/* header */
.top{display:flex; justify-content:space-between; align-items:flex-end; gap:1rem; flex-wrap:wrap; direction:rtl; margin-bottom:.4rem;}
.top h1{font-size:2.05rem; margin:0; font-weight:700; line-height:1.15;}
.top p{color:var(--muted); margin:.2rem 0 0 0; max-width:64ch;}
.chips{display:flex; gap:.35rem; flex-wrap:wrap; direction:rtl;}
.chip{font-size:.8rem; border:1px solid var(--line); background:var(--card); border-radius:999px; padding:.18rem .65rem; color:var(--ink); white-space:nowrap;}
.chip b{font-weight:600; font-variant-numeric:tabular-nums;}
.chip.warn{background:var(--ochre-soft); border-color:#E3CD98; color:#5E4410;}
.chip.off{background:#fff; color:var(--muted); border-style:dashed;}
.section{font-family:'Frank Ruhl Libre', Georgia, serif; font-size:1.25rem; font-weight:700; margin:.2rem 0 .1rem 0; direction:rtl;}
.hint{color:var(--muted); font-size:.85rem; margin:0 0 .5rem 0; direction:rtl;}
/* opportunity cards */
.opp{direction:rtl;}
.opp-head{display:flex; gap:.6rem; align-items:flex-start;}
.rank{min-width:2.1rem; height:2.1rem; border-radius:8px; background:var(--canal); color:#fff; font-weight:600;
      display:flex; align-items:center; justify-content:center; font-variant-numeric:tabular-nums;}
.hood{font-weight:600; font-size:1.02rem; line-height:1.25; direction:ltr; text-align:right; unicode-bidi:plaintext;}
.seg{color:var(--muted); font-size:.82rem; unicode-bidi:plaintext;}
.score{margin:.55rem 0 .35rem 0; display:flex; align-items:baseline; gap:.45rem;}
.score .num{font-family:'Frank Ruhl Libre', Georgia, serif; font-size:1.65rem; font-weight:700; color:var(--canal); direction:ltr; font-variant-numeric:tabular-nums;}
.score .unit{color:var(--muted); font-size:.8rem;}
.bars{display:grid; grid-template-columns:5.6rem 1fr 4.2rem; gap:.25rem .5rem; align-items:center; font-size:.8rem;}
.bars .lab{color:var(--muted);} .bars .val{text-align:left; direction:ltr; font-variant-numeric:tabular-nums;}
.track{height:6px; background:var(--canal-soft); border-radius:3px; overflow:hidden; direction:rtl;}
.fill{height:100%; background:var(--canal-2); border-radius:3px;}
.flags{display:flex; gap:.3rem; flex-wrap:wrap; margin-top:.5rem;}
.flag{font-size:.74rem; border-radius:5px; padding:.05rem .4rem; background:var(--ochre-soft); color:#6E4E12; border:1px solid #E3CD98;}
/* chat: the chat column follows the page while the dashboard scrolls */
[data-testid="stColumn"]:has(.chat-anchor){position:sticky; top:3.2rem; align-self:flex-start;}
@media (max-width: 900px){[data-testid="stColumn"]:has(.chat-anchor){position:static;}}
/* chat */
[data-testid="stChatMessage"]{background:var(--card); border:1px solid var(--line); border-radius:10px; padding:.8rem 1rem;}
[data-testid="stChatMessage"] p, [data-testid="stChatMessage"] li{line-height:1.7;}
.ref{display:inline-block; background:var(--ochre-soft); color:#6E4E12; border:1px solid #E3CD98;
     border-radius:5px; padding:0 .32rem; font-size:.78em; font-weight:600; direction:ltr; margin:0 .1rem;}
.rail{display:flex; flex-wrap:wrap; align-items:center; gap:.3rem; margin:.7rem 0 .2rem 0; direction:rtl;}
.step{font-size:.78rem; border-radius:999px; padding:.12rem .58rem; border:1px solid var(--line); background:#fff; color:var(--ink); white-space:nowrap;}
.step.agent{background:var(--canal); color:#fff; border-color:var(--canal);}
.step.tool{background:var(--canal-soft); border-color:#BFD4DA; color:var(--canal);}
.step.web{background:#fff; border-style:dashed; border-color:var(--canal); color:var(--canal);}
.step.ok{background:var(--ok-soft); border-color:#B5D8C1; color:var(--ok);}
.step.stop{background:var(--stop-soft); border-color:#E5B5B0; color:var(--stop);}
.join{color:#9AA5AE; font-size:.78rem;}
.facts{color:var(--muted); font-size:.8rem; margin:.15rem 0 .35rem 0; direction:rtl;}
.facts b{color:var(--ink); font-weight:600;}
.evi{border-right:3px solid var(--ochre); padding:.15rem .7rem; margin:.45rem 0; background:#fff; direction:rtl;}
.evi .meta{color:var(--muted); font-size:.8rem; direction:ltr; text-align:right;}
/* live agent activity */
.live{border:1px solid #BFD4DA; background:var(--card); border-radius:10px; padding:.75rem .9rem; direction:rtl;}
.stages{display:flex; align-items:center; gap:.25rem; flex-wrap:wrap;}
.stage{font-size:.8rem; padding:.2rem .6rem; border-radius:999px; border:1px solid var(--line); color:var(--muted); background:#fff;}
.stage.done{background:var(--canal-soft); color:var(--canal); border-color:#BFD4DA;}
.stage.active{background:var(--canal); color:#fff; border-color:var(--canal);}
.stage.alert{background:var(--stop-soft); color:var(--stop); border-color:#E5B5B0;}
.arrow{color:#9AA5AE; font-size:.8rem;}
.log{margin:.55rem 0 0 0; padding:0; list-style:none; font-size:.82rem; color:var(--ink);}
.log li{padding:.12rem 0; border-top:1px dashed var(--line);}
.log li:first-child{border-top:0;}
.log .ms{color:var(--muted); direction:ltr; unicode-bidi:isolate;}
@media (prefers-reduced-motion: no-preference){
  .stage.active{animation:pulse 1.2s ease-in-out infinite;}
  @keyframes pulse{0%,100%{opacity:1} 50%{opacity:.62}}
}
[data-testid="stSidebar"]{background:#fff; border-left:1px solid var(--line);}
[data-testid="stSidebar"] h3{font-size:1.05rem; margin-top:.6rem;}
.stButton>button{border-radius:8px; border:1px solid var(--line);}
.stButton>button:hover{border-color:var(--canal); color:var(--canal);}
.stButton>button:focus-visible{outline:2px solid var(--canal); outline-offset:2px;}
.status-line{font-size:.88rem; margin:.15rem 0;}
.dot{display:inline-block; width:.55rem; height:.55rem; border-radius:50%; margin-left:.4rem;}
.dot.on{background:var(--ok);} .dot.off{background:#C5CCD2;}
.banner{border-radius:8px; padding:.5rem .85rem; margin:.4rem 0 .6rem 0; font-size:.9rem; border:1px solid; direction:rtl;}
.banner.synthetic{background:var(--ochre-soft); border-color:#E3CD98; color:#5E4410;}
.banner.nokey{background:#fff; border-color:var(--line); color:var(--muted);}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

EXAMPLES = {
    "המובילות ולמה": "מהן 5 ההזדמנויות המובילות באמסטרדם, ולמה?",
    "חדר פרטי במקום 1": "למה חדר פרטי ב-Centrum-West נמצא במקום הראשון? מה הראיות בעד ונגד?",
    "מחיר ל-De Pijp": "כמה תכניס ללילה דירה שלמה עם 2 חדרי שינה ב-De Pijp ל-4 אורחים, וכמה לסמוך על ההערכה?",
    "תשואה": "אם אקנה דירה כזו ב-650,000 EUR עם עלויות של 12,000 בשנה, מה התשואה?",
    "אמינות המודל": "עד כמה מודל המחיר אמין, ובאילו מקרים הוא חלש?",
    "רגולציה": "מה הרגולציה על השכרה לטווח קצר באמסטרדם?",
}
TOOL_HE = {"rank_opportunities": "דירוג הזדמנויות", "predict_listing_price": "מודל מחיר",
           "neighbourhood_stats": "סטטיסטיקת שכונה", "review_signals": "ביקורות אורחים",
           "data_availability": "זמינות נתונים", "roi_calculator": "מחשבון תשואה",
           "web_search": "חיפוש ברשת", "web_source": "מקור מהרשת", "model_card": "אמינות המודל",
           "segment_profile": "פרופיל הקטע", "listing_profile": "פרופיל נכסים"}
GUARD_HE = {"input": "חסימת קלט", "allow_list": "כלי לא מורשה", "schema": "קלט לא תקין לכלי",
            "budget": "תקציב קריאות", "policy": "מדיניות", "max_rounds": "מגבלת סבבים",
            "agent_unavailable": "סוכן לא זמין"}
BAND_HE = {"0-1": "0–1 חדרי שינה", "2": "2 חדרי שינה", "3+": "3+ חדרי שינה"}


# ---------------------------------------------------------------------- setup
def default_root() -> str:
    env = os.environ.get("PIIS_DATA_ROOT")
    if env:
        return env
    if list(ROOT.glob("reports/*/opportunities.json")):
        return str(ROOT)
    return str(ROOT / "demo_repo") if (ROOT / "demo_repo").exists() else str(ROOT)


@st.cache_resource(show_spinner="טוען מודלים ונתונים…")
def get_orchestrator(data_root: str, api_key: str, agent_model: str, router_model: str) -> Orchestrator:
    if api_key:
        os.environ["ANTHROPIC_API_KEY"] = api_key
    cfg = AgentConfig(data_root=Path(data_root), agent_model=agent_model, router_model=router_model)
    return Orchestrator(cfg, api_key=api_key or None)


ss = st.session_state
ss.setdefault("messages", [])
ss.setdefault("pending", None)
ss.setdefault("sel_hood", None)
ss.setdefault("data_root", default_root())

# ---------------------------------------------------------------------- sidebar: settings and data status
with st.sidebar:
    st.markdown("### הגדרות")
    env_key = os.environ.get("ANTHROPIC_API_KEY", "")
    api_key = st.text_input("מפתח Anthropic API", value="", type="password",
                            placeholder="מוגדר מהסביבה" if env_key else "sk-ant-…",
                            help="בלי מפתח המערכת עובדת במצב ללא סוכן: טבלת ההזדמנויות בלבד.") or env_key
    ss.data_root = st.text_input("תיקיית הנתונים", value=ss.data_root,
                                 help="תיקייה עם models/, reports/ ו-data/processed/ (שורש הריפו, או demo_repo).")
    with st.expander("מודלים"):
        agent_model = st.text_input("מודל הסוכנים", AgentConfig().agent_model)
        router_model = st.text_input("מודל הנתב והמתקן", AgentConfig().router_model)

    orch = get_orchestrator(ss.data_root, api_key, agent_model, router_model)
    status = orch.ctx.status()

    st.markdown("### מצב הנתונים")

    def line(ok: bool, label: str):
        st.markdown(f'<div class="status-line"><span class="dot {"on" if ok else "off"}"></span>{label}</div>',
                    unsafe_allow_html=True)
    tables = status["opportunity_tables"]
    line(bool(tables), "טבלת הזדמנויות: " + (", ".join(f"{c} ({t['label']}, {t['snapshot_date']})"
                                                       for c, t in tables.items()) or "לא נמצאה"))
    line(bool(status["price_models"]), "מודל מחיר: " + (", ".join(status["price_models"]) or "לא נמצא"))
    line(status["listings_rows"] > 0, f"נכסים בנתונים: {status['listings_rows']:,}")
    line(bool(status["reviews_file"]), "טקסט ביקורות: " + ("זמין" if status["reviews_file"] else
                                                          "לא בריפו (משתמשים בציוני ביקורת ובפעילות)"))
    caps = orch.capabilities
    n_tools = sum(1 for why in caps.values() if why is None)
    line(n_tools == len(caps), f"כלים זמינים לסוכנים: {n_tools} מתוך {len(caps)}")
    line(orch.llm is not None, "סוכנים: " + ("פעילים" if orch.llm is not None else "כבויים (אין מפתח API)"))
    if not tables:
        st.info("לא נמצאו קבצי המודל והדירוג בתיקייה הזו. אפשר לבנות נתוני הדגמה סינתטיים.")
        if st.button("בנה נתוני הדגמה (כחצי דקה)"):
            from agents.demo_data import build
            with st.spinner("בונה נתוני הדגמה…"):
                build(ROOT / "demo_repo", verbose=False)
            ss.data_root = str(ROOT / "demo_repo")
            st.cache_resource.clear()
            st.rerun()
    if ss.messages and st.button("נקה שיחה"):
        ss.messages = []
        st.rerun()


# ---------------------------------------------------------------------- data for the dashboard
opp_tool = orch.ctx.opportunity_tool()
city = next(iter(opp_tool.cities)) if opp_tool else None
ct = opp_tool.cities[city] if opp_tool else None
cur = (ct.currency if ct else None) or "EUR"
SYM = {"EUR": "€", "GBP": "£", "USD": "$"}.get(cur, cur + " ")


@st.cache_data(show_spinner=False)
def model_summary(data_root: str) -> dict:
    out = orch.registry["model_card"].handler({}) if orch.capabilities.get("model_card") is None else {}
    return out if out.get("status") == "ok" else {}


card = model_summary(ss.data_root)


def money(v) -> str:
    return f"{SYM}{v:,.0f}" if v is not None and not (isinstance(v, float) and math.isnan(v)) else "–"


# ---------------------------------------------------------------------- header
chips = []
if ct is not None:
    m = ct.meta
    chips += [f'<span class="chip">{html.escape(city)}</span>',
              f'<span class="chip">תמונת מצב <b>{m.get("snapshot_date")}</b></span>',
              f'<span class="chip"><b>{m.get("ranked_segments")}</b> הזדמנויות מדורגות</span>']
    if m.get("label") in ("PROVISIONAL", "SYNTHETIC"):
        chips.append(f'<span class="chip warn" title="{"נתוני הדגמה" if m.get("label") == "SYNTHETIC" else "קבוצת המבחן לא נכללה בדירוג; מבחן המודל היה exploratory"}">'
                     f'{m.get("label")}</span>')
if card:
    t = card["test"]
    chips.append(f'<span class="chip" title="טעות מוחלטת ממוצעת במבחן, מול קו הבסיס">מודל המחיר: '
                 f'<b>{t["model_MAE"]:.0f}</b> מול <b>{t["baseline_MAE"]:.0f}</b> {cur} טעות ללילה</span>')
chips.append(f'<span class="chip {"" if orch.llm else "off"}">סוכנים {"פעילים" if orch.llm else "כבויים"}</span>')
st.markdown(f'<div class="top"><div><h1>חוקר ההזדמנויות</h1><p>איזה נכס לחקור, ואיפה. הדירוג מחושב בקוד; '
            f'הסוכנים אוספים ראיות בעד ונגד, וכל מספר בתשובה נבדק מול המקור שלו.</p></div>'
            f'<div class="chips">{"".join(chips)}</div></div>', unsafe_allow_html=True)
if ct is not None and ct.meta.get("label") == "SYNTHETIC":
    st.markdown('<div class="banner synthetic">נתוני הדגמה סינתטיים: המבנה והחישובים אמיתיים, המספרים לא.</div>',
                unsafe_allow_html=True)
if orch.llm is None:
    st.markdown('<div class="banner nokey">הסוכנים כבויים כי לא הוגדר מפתח API. הדשבורד והטבלה עובדים; '
                'כדי לשאול את הסוכנים, פתחו את סרגל הצד (החץ בפינה) והדביקו מפתח.</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------- answer rendering
REF_RE = re.compile(r"\[(E\d+(?:\s*,\s*E\d+)*)\]")


def render_answer_text(text: str) -> str:
    safe = text.replace("<", "&lt;")
    return REF_RE.sub(lambda m: "".join(f'<span class="ref">{r.strip()}</span>' for r in m.group(1).split(",")), safe)


def rail_html(r: dict) -> str:
    steps = []
    for e in r["events"]:
        t = e["type"]
        if t == "agent_start" and e["agent"] != "router":
            steps.append(f'<span class="step agent">{html.escape(e.get("title") or e["agent"])}</span>')
        elif t == "route":
            steps.append(f'<span class="step agent">{TITLES["router"]}</span>')
        elif t == "tool_result" and e.get("tool") != "web_source":
            cls = "web" if e.get("server") else ("tool" if e.get("status") in ("ok", None) else "stop")
            ref = f' <b>{e["ref"]}</b>' if e.get("ref") else ""
            steps.append(f'<span class="step {cls}">{TOOL_HE.get(e["tool"], e["tool"])}{ref}</span>')
        elif t == "guardrail":
            steps.append(f'<span class="step stop">{GUARD_HE.get(e.get("guard"), e.get("guard"))}</span>')
        elif t == "verify":
            ok, g = e.get("passed"), e.get("groundedness")
            txt = "אומת" if ok else "תוקן" if not e.get("after_revision") else "אומת חלקית"
            steps.append(f'<span class="step {"ok" if ok else "stop"}">{TITLES["verifier"]}: {txt}'
                         f'{f" {g:.0%}" if g is not None else ""}</span>')
    return '<div class="rail">' + '<span class="join">←</span>'.join(steps) + "</div>" if steps else ""


def facts_html(r: dict) -> str:
    v = r.get("verification") or {}
    parts = []
    if v.get("claims"):
        parts.append(f'<b>{v["claims"]}</b> מספרים נבדקו, <b>{(v["groundedness"] or 0):.0%}</b> מבוססים על כלים')
    calls = sum(1 for e in r["events"] if e["type"] == "tool_result" and e.get("tool") != "web_source")
    if calls:
        parts.append(f'<b>{calls}</b> קריאות לכלים')
    parts.append(f'<b>{r["elapsed_s"]:.1f}</b> שניות')
    u = r.get("usage") or {}
    if u.get("llm_calls"):
        parts.append(f'<b>{u["llm_calls"]}</b> קריאות למודל, {u["input_tokens"] + u["output_tokens"]:,} טוקנים')
    return '<div class="facts">' + " | ".join(parts) + "</div>"


def evidence_block(ev: dict) -> str:
    res = ev.get("result") or {}
    head = res.get("url") if ev["tool"] == "web_search" else (res.get("status_reason") or "")
    return (f'<div class="evi"><span class="ref">{ev["ref"]}</span> <b>{TOOL_HE.get(ev["tool"], ev["tool"])}</b> '
            f'({html.escape(str(res.get("status")))}){", מקור חיצוני" if ev.get("external") else ""}'
            f'<div class="meta">{html.escape(str(ev.get("evidence_id")))}</div>'
            f'{"<div>" + html.escape(str(head)) + "</div>" if head else ""}</div>')


def render_turn(r: dict):
    st.markdown(render_answer_text(r["answer"]), unsafe_allow_html=True)
    st.markdown(rail_html(r) + facts_html(r), unsafe_allow_html=True)
    if r["evidence"]:
        with st.expander(f"ראיות ({len(r['evidence'])})"):
            for ev in r["evidence"]:
                st.markdown(evidence_block(ev), unsafe_allow_html=True)
                with st.popover("תוצאת הכלי"):
                    st.json(ev["result"], expanded=1)
    with st.expander("איך הגיעה התשובה"):
        st.markdown(f"**נתב:** כוונה `{r['intent']}`, עיר `{r['city']}`. {r.get('route_reason') or ''}")
        for e in r["events"]:
            t = e["type"]
            if t == "agent_start":
                st.markdown(f"- **{e.get('title') or e['agent']}**: מודל `{e.get('model')}`, פרומפט `{e.get('prompt_version')}`")
            elif t == "tool_call":
                st.markdown(f"  - קריאה ל-`{e['tool']}` עם `{e.get('args')}`")
            elif t == "tool_result":
                st.markdown(f"  - תוצאה `{e.get('ref') or ''}`, סטטוס `{e.get('status')}`, {e.get('ms', '–')} ms")
            elif t == "tool_cached":
                st.markdown(f"  - קריאה זהה, שימוש חוזר ב-`{e['ref']}`")
            elif t == "delegate":
                st.markdown(f"  - העברה לסוכן ההעשרה: `{e.get('args')}`")
            elif t == "guardrail":
                st.markdown(f"- **{GUARD_HE.get(e.get('guard'), e.get('guard'))}**: {e.get('reason')}")
            elif t == "verify":
                st.markdown(f"- **מאמת ראיות**{' (אחרי תיקון)' if e.get('after_revision') else ''}: "
                            f"עבר={e.get('passed')}, מספרים={e.get('claims')}, לא מבוססים={e.get('ungrounded')}, "
                            f"ללא ציטוט={e.get('uncited')}, הפרות={e.get('violations')}")
            elif t == "error":
                st.markdown(f"- שגיאה: `{e.get('error')}`")


class LiveActivity:
    """The agents at work: the pipeline stages, the active one highlighted, and the latest steps."""

    def __init__(self, slot):
        self.slot, self.agent, self.log = slot, "סוכן", []
        self.state = {"קלט": "active", "נתב": "", "סוכן": "", "כלים": "", "אימות": ""}
        self.render()

    def set(self, stage, value="active"):
        order = list(self.state)
        for s in order[:order.index(stage)]:
            if self.state[s] in ("", "active"):
                self.state[s] = "done"
        self.state[stage] = value

    def __call__(self, e):
        t = e["type"]
        if t == "route":
            self.set("סוכן")
            self.log.append(f"הנתב בחר: <b>{html.escape(str(e.get('intent')))}</b>"
                            + (f", {html.escape(str(e['city']))}" if e.get("city") else ""))
        elif t == "agent_start" and e["agent"] == "router":
            self.set("נתב")
        elif t == "agent_start" and e["agent"] == "reviser":
            self.log.append("המתקן מתקן את הטיוטה")
        elif t == "agent_start":
            if e["agent"] == "enrichment" and self.agent != "סוכן":
                self.log.append("העברה לסוכן העשרת הנתונים")
            else:
                self.agent = e.get("title") or e["agent"]
            self.set("סוכן")
        elif t == "tool_call":
            self.set("כלים")
            self.log.append(f"מפעיל {TOOL_HE.get(e['tool'], e['tool'])}")
        elif t == "tool_result" and e.get("tool") != "web_source":
            ref = f" ← <b>{e['ref']}</b>" if e.get("ref") else ""
            ms = f' <span class="ms">{e["ms"]} ms</span>' if e.get("ms") is not None else ""
            self.log[-1:] = [f"{TOOL_HE.get(e['tool'], e['tool'])}{ref} ({html.escape(str(e.get('status')))}){ms}"]
        elif t == "guardrail":
            self.log.append(f"guardrail: {GUARD_HE.get(e.get('guard'), e.get('guard'))}")
            if e.get("guard") == "input":
                self.state["קלט"] = "alert"
        elif t == "verify":
            self.set("אימות", "done" if e.get("passed") else "active")
            self.log.append(f"בודק {e.get('claims', 0)} מספרים מול הראיות: "
                            + ("עבר" if e.get("passed") else "נדרש תיקון"))
        self.render()

    def render(self):
        names = {**{k: k for k in self.state}, "סוכן": self.agent}
        stages = '<span class="arrow">←</span>'.join(
            f'<span class="stage {v}">{html.escape(names[k])}</span>' for k, v in self.state.items())
        items = "".join(f"<li>{x}</li>" for x in self.log[-6:])
        self.slot.markdown(f'<div class="live"><div class="stages">{stages}</div>'
                           f'<ul class="log">{items}</ul></div>', unsafe_allow_html=True)


def ask(prompt: str, box):
    history = [{"role": m["role"], "content": m["content"]} for m in ss.messages]
    ss.messages.append({"role": "user", "content": prompt})
    with box:
        with st.chat_message("user", avatar="🧑‍💼"):
            st.markdown(prompt)
        with st.chat_message("assistant", avatar="🏘️"):
            slot = st.empty()
            live = LiveActivity(slot)
            result = orch.handle(prompt, history, on_event=live)
            slot.empty()
            r = result.__dict__
            render_turn(r)
    ss.messages.append({"role": "assistant", "content": result.answer, "result": r})


# ---------------------------------------------------------------------- dashboard pieces
@st.cache_data(show_spinner=False)
def map_frames(data_root: str, city: str):
    lst = orch.ctx.listings()
    t = orch.ctx.opportunity_tool().cities[city].table
    pts = lst[(lst["location"] == city)][["neighbourhood_cleansed", "latitude", "longitude"]].dropna()
    pts = pts.astype({"latitude": float, "longitude": float})
    cent = pts.groupby("neighbourhood_cleansed")[["latitude", "longitude"]].median()
    ok = t[t["status"] == "ok"].sort_values("score", ascending=False)
    best = ok.groupby("neighbourhood_cleansed").head(1).set_index("neighbourhood_cleansed")
    hoods = cent.join(best[["score", "room_type", "bedroom_band", "rank"]], how="left")
    hoods["ranked"] = ok.groupby("neighbourhood_cleansed").size().reindex(hoods.index).fillna(0).astype(int)
    hoods = hoods.reset_index().rename(columns={"neighbourhood_cleansed": "hood"})
    return pts, hoods


def draw_map():
    """Dot-density map: every listing a faint dot, every neighbourhood a bubble sized and coloured by
    its best opportunity. Plain SVG (no map tiles or tokens), so it renders the same everywhere."""
    import plotly.graph_objects as go
    pts, hoods = map_frames(ss.data_root, city)
    lat0 = float(pts["latitude"].median())
    smax = float(hoods["score"].max() or 1)
    h = hoods.copy()
    h["score0"] = h["score"].fillna(0)
    h["size"] = h["score0"].map(lambda v: 12 + 40 * math.sqrt(v / smax))
    h["sel"] = h["hood"] == ss.sel_hood
    h["hover"] = h.apply(lambda r: (f"<b>{r['hood']}</b><br>מקום {int(r['rank'])}: {r['room_type']}, "
                                    f"{r['bedroom_band']} חדרי שינה<br>{money(r['score'])} בשנה, "
                                    f"{int(r['ranked'])} הזדמנויות מדורגות")
                         if pd.notna(r["score"]) else f"<b>{r['hood']}</b><br>אין הזדמנות מדורגת", axis=1)
    top = list(h.nlargest(3, "score0")["hood"])
    h["text"] = h["hood"].map(lambda x: x.split(" - ")[0] if x in top else "")
    h["pos"] = h["hood"].map(lambda x: ["top center", "bottom center", "middle left"][top.index(x)]
                             if x in top else "top center")
    sample = pts.sample(min(len(pts), 5000), random_state=1)
    pad = lambda lo, hi: [lo - 0.06 * (hi - lo), hi + 0.06 * (hi - lo)]
    xr = pad(pts["longitude"].quantile(.03), pts["longitude"].quantile(.97))
    yr = pad(pts["latitude"].quantile(.03), pts["latitude"].quantile(.97))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=sample["longitude"], y=sample["latitude"], mode="markers", hoverinfo="skip",
                             marker=dict(size=3, color="rgba(93,104,116,0.16)")))
    fig.add_trace(go.Scatter(
        x=h["longitude"], y=h["latitude"], mode="markers+text", text=h["text"], textposition=h["pos"],
        textfont=dict(size=11, color="#1C2430"), customdata=h[["hood"]].to_numpy(),
        hovertext=h["hover"], hoverinfo="text",
        marker=dict(size=h["size"], color=h["score0"], cmin=0, cmax=smax,
                    colorscale=[[0, "#E9EEF0"], [0.35, "#9DC0CB"], [1, "#24566B"]],
                    line=dict(width=h["sel"].map({True: 3, False: 1.2}),
                              color=h["sel"].map({True: "#B8862B", False: "#FFFFFF"})),
                    opacity=0.92)))
    fig.update_layout(height=430, margin=dict(l=0, r=0, t=0, b=0), showlegend=False,
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#FFFFFF", dragmode="pan",
                      font=dict(family="IBM Plex Sans Hebrew, sans-serif"),
                      hoverlabel=dict(bgcolor="#FFFFFF", bordercolor="#DCE1DC", font=dict(size=12, color="#1C2430")),
                      xaxis=dict(visible=False, range=xr, constrain="domain"),
                      yaxis=dict(visible=False, range=yr, scaleanchor="x", constrain="domain",
                                 scaleratio=1 / math.cos(math.radians(lat0))))
    cfg = {"displayModeBar": False, "scrollZoom": True}
    try:
        ev = st.plotly_chart(fig, config=cfg, on_select="rerun", selection_mode="points", key="amap")
        points = (ev.selection or {}).get("points", []) if ev else []
        hit = next((p for p in points if p.get("curve_number") == 1), None)
        if hit:
            cd = hit.get("customdata")
            hood = cd[0] if isinstance(cd, (list, tuple)) else cd
            if hood and hood != ss.sel_hood:
                ss.sel_hood = hood
                st.rerun()
    except TypeError:                                   # older Streamlit: no selection support
        st.plotly_chart(fig, config=cfg)


def opportunity_card(r, maxima):
    bars = [("מחיר ללילה", r["expected_price"] / maxima["price"], money(r["expected_price"])),
            ("לילות בשנה", r["booked_nights"] / 255, f"{r['booked_nights']:.0f}"),
            ("ודאות מחיר", r["price_certainty"], f"{r['price_certainty']:.2f}")]
    bar_html = "".join(f'<span class="lab">{lab}</span><div class="track"><div class="fill" '
                       f'style="width:{max(3, min(100, 100 * w)):.0f}%"></div></div><span class="val">{val}</span>'
                       for lab, w, val in bars)
    flags = []
    if r["price_certainty"] < 0.6:
        flags.append("ודאות נמוכה")
    if r["n_listings"] < 30:
        flags.append("מעט נכסים")
    if r.get("inside_airbnb_occupancy") and abs(r["inside_airbnb_occupancy"] - r["booked_nights"]) > 50:
        flags.append("פער בלילות מול Inside Airbnb")
    flag_html = "".join(f'<span class="flag">{f}</span>' for f in flags)
    st.markdown(
        f'<div class="opp"><div class="opp-head"><div class="rank">{int(r["rank"])}</div><div>'
        f'<div class="hood">{html.escape(r["neighbourhood_cleansed"])}</div>'
        f'<div class="seg">{html.escape(r["room_type"])}, {BAND_HE.get(r["bedroom_band"], r["bedroom_band"])}, '
        f'{int(r["n_listings"])} נכסים</div></div></div>'
        f'<div class="score"><span class="num">{money(r["score"])}</span><span class="unit">בשנה, הכנסה שמרנית</span></div>'
        f'<div class="bars">{bar_html}</div>'
        f'{"<div class=flags>" + flag_html + "</div>" if flags else ""}</div>', unsafe_allow_html=True)
    if st.button("חקור עם הסוכנים", key=f"inv_{r['segment_key']}", width="stretch",
                 disabled=orch.llm is None,
                 help=None if orch.llm else "נדרש מפתח API"):
        ss.pending = (f"הכן תדריך ראיות על ההזדמנות {r['neighbourhood_cleansed']} / {r['room_type']} / "
                      f"{r['bedroom_band']} חדרי שינה: למה היא מדורגת כך, ראיות בעד ונגד, ומה לבדוק הלאה.")


# ---------------------------------------------------------------------- layout
tab_main, tab_table, tab_log = st.tabs(["סקירה", "כל ההזדמנויות", "יומן ראיות"])

with tab_main:
    col_dash, col_chat = st.columns([1.2, 1], gap="large")

    with col_dash:
        if ct is None:
            st.info("אין טבלת הזדמנויות בתיקיית הנתונים. הריצו את מחברת 06, או בנו נתוני הדגמה מסרגל הצד.")
        else:
            st.markdown('<div class="section">מפת ההזדמנויות</div>'
                        '<div class="hint">כל עיגול הוא שכונה: גודל וצבע לפי ההזדמנות הטובה בה. '
                        'לחיצה על שכונה מסננת את הכרטיסים.</div>', unsafe_allow_html=True)
            try:
                draw_map()
            except Exception as e:                       # the dashboard must not fail on the map
                st.caption(f"המפה לא זמינה: {e}")

            t = ct.table
            ranked = t[t["status"] == "ok"].sort_values("rank")
            room_he = {"הכל": "הכל", "Entire home/apt": "דירה שלמה", "Private room": "חדר פרטי"}
            f1, f2 = st.columns(2)
            room = f1.pills("סוג נכס", list(room_he), default="הכל", key="f_room", format_func=room_he.get)
            band = f2.pills("חדרי שינה", ["הכל", "0-1", "2", "3+"], default="הכל", key="f_band")
            if ss.sel_hood and st.button(f"הסר סינון שכונה: {ss.sel_hood}", key="clear_hood"):
                ss.sel_hood = None
                st.rerun()
            sel = ranked
            if room and room != "הכל":
                sel = sel[sel["room_type"] == room]
            if band and band != "הכל":
                sel = sel[sel["bedroom_band"] == band]
            if ss.sel_hood:
                sel = sel[sel["neighbourhood_cleansed"] == ss.sel_hood]
            st.markdown(f'<div class="section">ההזדמנויות המובילות</div><div class="hint">'
                        f'{len(sel)} מתאימות לסינון. ציון = לילות × מחיר צפוי × ודאות: הכנסה שמרנית מהשכרה, '
                        f'לא תשואה ולא המלצת קנייה.</div>', unsafe_allow_html=True)
            maxima = {"price": float(ranked["expected_price"].max() or 1)}
            rows = list(sel.head(6).to_dict("records"))
            if not rows:
                st.markdown('<div class="hint">אין הזדמנות מדורגת שמתאימה לסינון.</div>', unsafe_allow_html=True)
            for i in range(0, len(rows), 2):
                cols = st.columns(2, gap="small")
                for c, r in zip(cols, rows[i:i + 2]):
                    with c, st.container(border=True):
                        opportunity_card(r, maxima)

    with col_chat:
        st.markdown('<div class="section chat-anchor">שאלו את הסוכנים</div>', unsafe_allow_html=True)
        pick = st.pills("שאלות לדוגמה", list(EXAMPLES), key="ex_pills", label_visibility="collapsed")
        if pick and ss.get("last_pick") != pick:
            ss.last_pick = pick
            ss.pending = EXAMPLES[pick]
        box = st.container(height=560, border=False)
        with box:
            if not ss.messages and not ss.pending:
                st.markdown('<div class="hint">בחרו שאלה לדוגמה, לחצו "חקור" על כרטיס, או כתבו שאלה. '
                            'מתחת לכל תשובה תראו אילו סוכנים וכלים עבדו, ומה מקור כל מספר.</div>',
                            unsafe_allow_html=True)
            for m in ss.messages:
                with st.chat_message(m["role"], avatar="🧑‍💼" if m["role"] == "user" else "🏘️"):
                    if m["role"] == "user":
                        st.markdown(m["content"])
                    else:
                        render_turn(m["result"])
        prompt = st.chat_input("שאלו על הזדמנויות, מחירים, שכונות או נתונים…", key="chat")
        prompt = prompt or ss.pending
        ss.pending = None
        if prompt:
            ask(prompt, box)

with tab_table:
    if ct is None:
        st.info("אין טבלת הזדמנויות בתיקיית הנתונים.")
    else:
        t = ct.table
        c1, c2, c3 = st.columns(3)
        hoods = c1.multiselect("שכונה", sorted(t["neighbourhood_cleansed"].unique()))
        rooms = c2.multiselect("סוג נכס", sorted(t["room_type"].unique()))
        show_all = c3.checkbox("הצג גם ללא מספיק ראיות", value=False)
        f = t if show_all else t[t["status"] == "ok"]
        if hoods:
            f = f[f["neighbourhood_cleansed"].isin(hoods)]
        if rooms:
            f = f[f["room_type"].isin(rooms)]
        view = pd.DataFrame({
            "דירוג": f["rank"], "שכונה": f["neighbourhood_cleansed"], "סוג": f["room_type"],
            "חדרי שינה": f["bedroom_band"], f"ציון ({cur}/שנה)": f["score"].round(0),
            f"מחיר צפוי ({cur}/לילה)": f["expected_price"].round(0), "לילות מוזמנים": f["booked_nights"].round(0),
            "ודאות": f["price_certainty"].round(2), "נכסים": f["n_listings"], "סטטוס": f["status"]})
        st.caption(f"{ct.meta.get('ranked_segments')} הזדמנויות מדורגות, תמונת מצב {ct.meta.get('snapshot_date')}, "
                   f"תווית {ct.meta.get('label')}. ציון = לילות × מחיר צפוי × ודאות; הכנסה שמרנית מהשכרה, לא תשואה.")
        st.dataframe(view, hide_index=True, width="stretch",
                     column_config={f"ציון ({cur}/שנה)": st.column_config.ProgressColumn(
                         f"ציון ({cur}/שנה)", format="%.0f", min_value=0, max_value=float(t["score"].max() or 1))})

with tab_log:
    turns = [m["result"] for m in ss.messages if m["role"] == "assistant"]
    checked = [r["verification"] for r in turns if r.get("verification") and r["verification"].get("claims")]
    if not turns:
        st.markdown("עוד אין ראיות בשיחה הזו.")
    else:
        claims = sum(v["claims"] for v in checked)
        grounded = sum(round(v["groundedness"] * v["claims"]) for v in checked)
        c1, c2, c3 = st.columns(3)
        c1.metric("מספרים שנבדקו", f"{claims:,}")
        c2.metric("מבוססים על כלים", f"{grounded / claims:.0%}" if claims else "–",
                  help="קריטריון 7: לפחות 95% מהמספרים שהסוכן מצטט תואמים את יומן הראיות")
        c3.metric("קריאות לכלים", sum(len(r["evidence"]) for r in turns))
        rows = [{"שאלה": r["question"][:60], "תור": r["turn_id"], "ראיה": e["ref"], "כלי": e["tool"],
                 "סוכן": e["agent"], "סטטוס": e["status"], "evidence_id": e["evidence_id"]}
                for r in turns for e in r["evidence"]]
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        st.caption("כל תוצאה נשמרת גם בקובץ evaluation/agent_evidence.jsonl לבדיקת ה-groundedness.")
