"""Investor chat (Hebrew, right to left) over the agent system.

    streamlit run src/app/streamlit_app.py

Three tabs:
* שיחה: the chat. Under every answer: the work rail (which agents and tools ran), the
  verification result, and the evidence behind each [E#] reference.
* הזדמנויות: the deterministic opportunity table, usable without the agents (charter).
* יומן ראיות: every tool result of the session and the running groundedness (criterion 7).
"""
from __future__ import annotations

import html
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

st.set_page_config(page_title="חוקר ההזדמנויות", page_icon="🏘️", layout="wide",
                   initial_sidebar_state="expanded")

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Frank+Ruhl+Libre:wght@500;700&family=IBM+Plex+Sans+Hebrew:wght@400;500;600&display=swap');
:root{--canal:#24566B;--canal-soft:#E3EDF0;--ink:#1C2430;--muted:#5D6874;--paper:#F5F6F3;
      --line:#D9DED9;--ochre:#B8862B;--ochre-soft:#F6EBD3;--ok:#2F7D4F;--ok-soft:#E1F0E6;
      --stop:#B23B3B;--stop-soft:#F6E0DE;}
body, p, li, td, th, label, input, textarea, button, .stMarkdown, [data-testid="stCaptionContainer"]{
  font-family:'IBM Plex Sans Hebrew', system-ui, sans-serif;}
[data-testid="stIconMaterial"], .material-symbols-rounded, [class*="material-symbols"]{
  font-family:'Material Symbols Rounded' !important; direction:ltr;}
.stApp{background:var(--paper); color:var(--ink);}
.main .block-container{max-width:1080px; padding-top:1.6rem;}
/* right to left for everything we write; data grids keep their own direction */
.stMarkdown, .stChatMessage, [data-testid="stSidebar"], .stTabs, .stAlert, .stExpander,
[data-testid="stChatInput"] textarea, .stTextInput input, .stRadio, .stSelectbox{direction:rtl; text-align:right;}
[data-testid="stChatMessage"]{background:#fff; border:1px solid var(--line); border-radius:10px; padding:.9rem 1.1rem;}
[data-testid="stChatMessage"] p, [data-testid="stChatMessage"] li{line-height:1.75; max-width:72ch;}
h1,h2,h3{font-family:'Frank Ruhl Libre', Georgia, serif !important; color:var(--ink); letter-spacing:0;}
.hero h1{font-size:2.15rem; margin:0 0 .15rem 0; font-weight:700;}
.hero p{color:var(--muted); margin:0; font-size:1.02rem; max-width:62ch;}
code{direction:ltr; unicode-bidi:isolate;}
.stMarkdown ul, .stMarkdown ol{padding-right:1.3rem; padding-left:0;}
table{font-variant-numeric:tabular-nums; border-collapse:collapse;}
th{background:var(--canal-soft); font-weight:600;} td,th{border:1px solid var(--line)!important; padding:.3rem .55rem!important; unicode-bidi:plaintext;}
.ref{display:inline-block; background:var(--ochre-soft); color:#6E4E12; border:1px solid #E3CD98;
     border-radius:5px; padding:0 .32rem; font-size:.78em; font-weight:600; direction:ltr; margin:0 .1rem;}
.banner{border-radius:8px; padding:.55rem .85rem; margin:.6rem 0 0 0; font-size:.93rem; border:1px solid;}
.banner.synthetic{background:var(--ochre-soft); border-color:#E3CD98; color:#5E4410;}
.banner.provisional{background:var(--canal-soft); border-color:#BFD4DA; color:var(--canal);}
.banner.nokey{background:#fff; border-color:var(--line); color:var(--muted);}
/* the work rail: the path the question took */
.rail{display:flex; flex-wrap:wrap; align-items:center; gap:.3rem; margin:.75rem 0 .2rem 0; direction:rtl;}
.step{font-size:.8rem; border-radius:999px; padding:.14rem .62rem; border:1px solid var(--line); background:#fff; color:var(--ink); white-space:nowrap;}
.step.agent{background:var(--canal); color:#fff; border-color:var(--canal);}
.step.tool{background:var(--canal-soft); border-color:#BFD4DA; color:var(--canal);}
.step.web{background:#fff; border-style:dashed; border-color:var(--canal); color:var(--canal);}
.step.ok{background:var(--ok-soft); border-color:#B5D8C1; color:var(--ok);}
.step.stop{background:var(--stop-soft); border-color:#E5B5B0; color:var(--stop);}
.join{color:#9AA5AE; font-size:.8rem;}
.facts{color:var(--muted); font-size:.82rem; margin:.15rem 0 .35rem 0; direction:rtl;}
.facts b{color:var(--ink); font-weight:600;}
.evi{border-right:3px solid var(--ochre); padding:.15rem .7rem; margin:.45rem 0; background:#fff; direction:rtl;}
.evi .meta{color:var(--muted); font-size:.8rem; direction:ltr; text-align:right;}
[data-testid="stSidebar"]{background:#fff; border-left:1px solid var(--line);}
[data-testid="stSidebar"] h3{font-size:1.05rem; margin-top:.6rem;}
.stButton>button{border-radius:8px; border:1px solid var(--line);}
[data-testid="stSidebar"] .stButton>button{text-align:right; width:100%; justify-content:flex-start;}
.stButton>button:hover{border-color:var(--canal); color:var(--canal);}
.stButton>button:focus-visible{outline:2px solid var(--canal); outline-offset:2px;}
.status-line{font-size:.88rem; margin:.15rem 0;}
.dot{display:inline-block; width:.55rem; height:.55rem; border-radius:50%; margin-left:.4rem;}
.dot.on{background:var(--ok);} .dot.off{background:#C5CCD2;}
@media (prefers-reduced-motion: reduce){*{transition:none!important; animation:none!important;}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

EXAMPLES = [
    "מהן 5 ההזדמנויות המובילות באמסטרדם, ולמה?",
    "מה הראיות בעד ונגד ההזדמנות שבמקום הראשון?",
    "כמה תכניס ללילה דירה שלמה עם 2 חדרי שינה ב-De Pijp ל-4 אורחים?",
    "אם אקנה דירה כזו ב-450,000 EUR עם עלויות של 9,000 בשנה, מה התשואה?",
    "אילו ערים יש בנתונים, ומה מצב ברצלונה?",
    "מה הרגולציה על השכרה לטווח קצר באמסטרדם?",
]
TOOL_HE = {"rank_opportunities": "דירוג הזדמנויות", "predict_listing_price": "מודל מחיר",
           "neighbourhood_stats": "סטטיסטיקת שכונה", "review_signals": "ביקורות אורחים",
           "data_availability": "זמינות נתונים", "roi_calculator": "מחשבון תשואה",
           "web_search": "חיפוש ברשת", "web_source": "מקור מהרשת"}
GUARD_HE = {"input": "חסימת קלט", "allow_list": "כלי לא מורשה", "schema": "קלט לא תקין לכלי",
            "budget": "תקציב קריאות", "policy": "מדיניות", "max_rounds": "מגבלת סבבים",
            "agent_unavailable": "סוכן לא זמין"}


# ---------------------------------------------------------------------- setup
def default_root() -> str:
    env = os.environ.get("PIIS_DATA_ROOT")
    if env:
        return env
    if any((ROOT / p).exists() for p in ["reports", "models"]) and list(ROOT.glob("reports/*/opportunities.json")):
        return str(ROOT)
    return str(ROOT / "demo_repo") if (ROOT / "demo_repo").exists() else str(ROOT)


@st.cache_resource(show_spinner="טוען מודלים ונתונים…")
def get_orchestrator(data_root: str, api_key: str, agent_model: str, router_model: str) -> Orchestrator:
    if api_key:
        os.environ["ANTHROPIC_API_KEY"] = api_key
    cfg = AgentConfig(data_root=Path(data_root), agent_model=agent_model, router_model=router_model)
    return Orchestrator(cfg, api_key=api_key or None)


@st.cache_data(show_spinner=False)
def data_status(data_root: str, _orch_id: int) -> dict:
    return st.session_state["orch"].ctx.status()


ss = st.session_state
ss.setdefault("messages", [])
ss.setdefault("pending", None)
ss.setdefault("data_root", default_root())

# ---------------------------------------------------------------------- sidebar
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
    ss["orch"] = orch
    status = data_status(ss.data_root, id(orch))

    st.markdown("### מצב הנתונים")
    def line(ok: bool, label: str):
        st.markdown(f'<div class="status-line"><span class="dot {"on" if ok else "off"}"></span>{label}</div>',
                    unsafe_allow_html=True)
    tables = status["opportunity_tables"]
    line(bool(tables), "טבלת הזדמנויות: " + (", ".join(f"{c} ({t['label']}, {t['snapshot_date']})"
                                                       for c, t in tables.items()) or "לא נמצאה"))
    line(bool(status["price_models"]), "מודל מחיר: " + (", ".join(status["price_models"]) or "לא נמצא"))
    line(status["listings_rows"] > 0, f"נכסים בנתונים: {status['listings_rows']:,}")
    line(bool(status["reviews_file"]), "ביקורות אורחים: " + ("זמינות" if status["reviews_file"] else "לא נמצאו"))
    line(orch.llm is not None, "סוכנים: " + ("פעילים" if orch.llm is not None else "כבויים (אין מפתח API)"))

    if not tables:
        st.info("לא נמצאו קבצי המודל והדירוג בתיקייה הזו. אפשר לפרוס כאן את חבילת הנתונים של הצוות, "
                "או לבנות נתוני הדגמה סינתטיים.")
        if st.button("בנה נתוני הדגמה (כחצי דקה)"):
            from agents.demo_data import build
            with st.spinner("בונה נתוני הדגמה…"):
                build(ROOT / "demo_repo", verbose=False)
            ss.data_root = str(ROOT / "demo_repo")
            st.cache_resource.clear(); st.cache_data.clear(); st.rerun()

    st.markdown("### שאלות לדוגמה")
    for q in EXAMPLES:
        if st.button(q, key=f"ex_{q}"):
            ss.pending = q
    if ss.messages and st.button("נקה שיחה"):
        ss.messages = []
        st.rerun()

# ---------------------------------------------------------------------- header
labels = {t["label"] for t in status["opportunity_tables"].values()}
st.markdown('<div class="hero"><h1>חוקר ההזדמנויות</h1>'
            '<p>שאלו איזה נכס לחקור ואיפה. סוכנים מתמחים אוספים ראיות מהמודלים ומהנתונים, '
            'וכל מספר בתשובה נבדק מול המקור שלו.</p></div>', unsafe_allow_html=True)
if "SYNTHETIC" in labels:
    st.markdown('<div class="banner synthetic">נתוני הדגמה סינתטיים: המבנה והחישובים אמיתיים, '
                'המספרים לא. לתוצאות אמיתיות פרסו את חבילת הנתונים של הצוות.</div>', unsafe_allow_html=True)
elif "PROVISIONAL" in labels:
    st.markdown('<div class="banner provisional">טבלת ההזדמנויות מסומנת PROVISIONAL: מבחן המודל היה '
                'exploratory, וקבוצת המבחן לא נכללה בדירוג.</div>', unsafe_allow_html=True)
if orch.llm is None:
    st.markdown('<div class="banner nokey">אין מפתח API: המערכת עונה במצב ללא סוכן (טבלת ההזדמנויות). '
                'הוסיפו מפתח בסרגל הצד כדי להפעיל את הסוכנים.</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------- rendering helpers
REF_RE = re.compile(r"\[(E\d+(?:\s*,\s*E\d+)*)\]")


def render_answer_text(text: str) -> str:
    safe = text.replace("<", "&lt;")
    return REF_RE.sub(lambda m: "".join(f'<span class="ref">{r.strip()}</span>' for r in m.group(1).split(",")), safe)


def rail_html(r: dict) -> str:
    steps, seen_agents = [], []
    for e in r["events"]:
        t = e["type"]
        if t == "agent_start" and e["agent"] not in ("router",):
            steps.append(f'<span class="step agent">{html.escape(e.get("title") or e["agent"])}</span>')
            seen_agents.append(e["agent"])
        elif t == "route":
            steps.append(f'<span class="step agent">{TITLES["router"]}</span>')
        elif t == "tool_result" and e.get("tool") != "web_source":
            cls = "web" if e.get("server") else ("tool" if e.get("status") in ("ok", None) else "stop")
            ref = f' <b>{e["ref"]}</b>' if e.get("ref") else ""
            steps.append(f'<span class="step {cls}">{TOOL_HE.get(e["tool"], e["tool"])}{ref}</span>')
        elif t == "guardrail":
            steps.append(f'<span class="step stop">🛡 {GUARD_HE.get(e.get("guard"), e.get("guard"))}</span>')
        elif t == "verify":
            ok = e.get("passed")
            g = e.get("groundedness")
            txt = "אומת" if ok else "תוקן" if not e.get("after_revision") else "אומת חלקית"
            pct = f" {g:.0%}" if g is not None else ""
            steps.append(f'<span class="step {"ok" if ok else "stop"}">{TITLES["verifier"]}: {txt}{pct}</span>')
    if not steps:
        return ""
    return '<div class="rail">' + '<span class="join">←</span>'.join(steps) + "</div>"


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
    tool = TOOL_HE.get(ev["tool"], ev["tool"])
    status = res.get("status")
    head = res.get("url") if ev["tool"] == "web_search" else (res.get("status_reason") or "")
    return (f'<div class="evi"><span class="ref">{ev["ref"]}</span> <b>{tool}</b> '
            f'({html.escape(str(status))}){" · external" if ev.get("external") else ""}'
            f'<div class="meta">{html.escape(str(ev.get("evidence_id")))}</div>'
            f'{"<div>" + html.escape(str(head)) + "</div>" if head else ""}</div>')


def render_turn(r: dict):
    st.markdown(render_answer_text(r["answer"]), unsafe_allow_html=True)
    st.markdown(rail_html(r) + facts_html(r), unsafe_allow_html=True)
    if r["evidence"]:
        with st.expander(f"ראיות ({len(r['evidence'])})"):
            for ev in r["evidence"]:
                st.markdown(evidence_block(ev), unsafe_allow_html=True)
                with st.popover("הצג את תוצאת הכלי"):
                    st.json(ev["result"], expanded=1)
    with st.expander("איך הגיעה התשובה"):
        v = r.get("verification")
        st.markdown(f"**נתב:** כוונה `{r['intent']}`, עיר `{r['city']}` — {r.get('route_reason') or ''}")
        for e in r["events"]:
            t = e["type"]
            if t == "agent_start":
                st.markdown(f"- 🤖 **{e.get('title') or e['agent']}** · מודל `{e.get('model')}` · פרומפט `{e.get('prompt_version')}`")
            elif t == "tool_call":
                st.markdown(f"  - קריאה ל-`{e['tool']}` עם `{e.get('args')}`")
            elif t == "tool_result":
                st.markdown(f"  - תוצאה `{e.get('ref') or ''}` · סטטוס `{e.get('status')}` · {e.get('ms', '–')} ms")
            elif t == "tool_cached":
                st.markdown(f"  - קריאה זהה, שימוש חוזר ב-`{e['ref']}`")
            elif t == "delegate":
                st.markdown(f"  - ↪ העברה לסוכן אחר: `{e.get('args')}`")
            elif t == "guardrail":
                st.markdown(f"- 🛡 **{GUARD_HE.get(e.get('guard'), e.get('guard'))}**: {e.get('reason')}")
            elif t == "verify":
                st.markdown(f"- ✅ **מאמת ראיות**{' (אחרי תיקון)' if e.get('after_revision') else ''}: "
                            f"עבר={e.get('passed')}, מספרים={e.get('claims')}, לא מבוססים={e.get('ungrounded')}, "
                            f"ללא ציטוט={e.get('uncited')}, הפרות={e.get('violations')}")
            elif t == "error":
                st.markdown(f"- ⚠️ שגיאה: `{e.get('error')}`")
        if v and (v.get("ungrounded") or v.get("violations")):
            st.json(v, expanded=False)


# ---------------------------------------------------------------------- tabs
prompt = st.chat_input("שאלו על הזדמנויות, מחירים, שכונות או נתונים…") or ss.pending
ss.pending = None
tab_chat, tab_table, tab_log = st.tabs(["שיחה", "הזדמנויות", "יומן ראיות"])

with tab_chat:
    if not ss.messages and not prompt:
        st.markdown("שאלו שאלה בתיבה למטה, או בחרו שאלה לדוגמה בסרגל הצד. הסוכנים יציגו כל מספר עם הראיה שלו.")
    for m in ss.messages:
        with st.chat_message(m["role"], avatar="🧑‍💼" if m["role"] == "user" else "🏘️"):
            if m["role"] == "user":
                st.markdown(m["content"])
            else:
                render_turn(m["result"])

    if prompt:
        history = [{"role": m["role"], "content": m["content"]} for m in ss.messages]
        ss.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="🧑‍💼"):
            st.markdown(prompt)
        with st.chat_message("assistant", avatar="🏘️"):
            with st.status("הסוכנים עובדים…", expanded=True) as box:
                def on_event(e):
                    t = e["type"]
                    if t == "route":
                        box.write(f"הנתב בחר: {e.get('intent')}" + (f" · {e['city']}" if e.get("city") else ""))
                    elif t == "agent_start" and e["agent"] != "router":
                        box.update(label=f"{e.get('title')} עובד…")
                        box.write(f"🤖 {e.get('title')}")
                    elif t == "tool_call":
                        box.write(f"↳ {TOOL_HE.get(e['tool'], e['tool'])}")
                    elif t == "guardrail":
                        box.write(f"🛡 {GUARD_HE.get(e.get('guard'), e.get('guard'))}")
                    elif t == "verify":
                        box.write("✅ בודק את המספרים מול הראיות")
                result = orch.handle(prompt, history, on_event=on_event)
                box.update(label="מוכן", state="complete", expanded=False)
            r = result.__dict__
            render_turn(r)
        ss.messages.append({"role": "assistant", "content": result.answer, "result": r})

with tab_table:
    tool = orch.ctx.opportunity_tool()
    if tool is None:
        st.info("אין טבלת הזדמנויות בתיקיית הנתונים. הריצו את מחברת 06 או פרסו את חבילת הנתונים.")
    else:
        city = st.selectbox("עיר", sorted(tool.cities)) if len(tool.cities) > 1 else next(iter(tool.cities))
        ct = tool.cities[city]
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
        cur = ct.currency
        view = pd.DataFrame({
            "דירוג": f["rank"], "שכונה": f["neighbourhood_cleansed"], "סוג": f["room_type"],
            "חדרי שינה": f["bedroom_band"], f"ציון ({cur}/שנה)": f["score"].round(0),
            f"מחיר צפוי ({cur}/לילה)": f["expected_price"].round(0), "לילות מוזמנים": f["booked_nights"].round(0),
            "ודאות": f["price_certainty"].round(2), "נכסים": f["n_listings"], "סטטוס": f["status"]})
        st.caption(f"{ct.meta.get('ranked_segments')} הזדמנויות מדורגות, תמונת מצב {ct.meta.get('snapshot_date')}, "
                   f"תווית {ct.meta.get('label')}. ציון = לילות × מחיר צפוי × ודאות; הכנסה שמרנית מהשכרה, לא תשואה.")
        st.dataframe(view, hide_index=True, width="stretch",
                     column_config={f"ציון ({cur}/שנה)": st.column_config.ProgressColumn(
                         f"ציון ({cur}/שנה)", format="%.0f", min_value=0,
                         max_value=float(t["score"].max() or 1))})

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
