"""
app.py - Streamlit frontend for LegalEase.

Run from the project root (with the backend already running):
    streamlit run frontend/app.py
"""

import sys
from pathlib import Path

# Make the project root importable (config, ai_core)
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import requests  # noqa: E402
import streamlit as st  # noqa: E402

import config  # noqa: E402
from ai_core.generator import (PREVIEW_CSS, format_docx, format_html_preview,  # noqa: E402
                               format_pdf, format_txt, safe_filename, sanitize_text)

BACKEND_URL = config.BACKEND_URL
CUSTOM_TYPE = "Other (type your own)..."

EXAMPLE = {
    "doc_type_choice": "Freelance Work Contract",
    "custom_type": "",
    "parties": "Jane Doe (Service Provider), TechNova Inc. (Client)",
    "terms": ("Work must be delivered by May 15, 2025; "
              "Payment of Rs. 75,000 will be made within 7 days of invoice; "
              "The client retains intellectual property rights; "
              "Confidentiality must be maintained at all times; "
              "Either party may terminate with 15 days notice"),
    "dates": "April 15, 2025",
    "jurisdiction": "Tamil Nadu, India",
}

# ---------------------------------------------------------------------------
# Page configuration & session state
# ---------------------------------------------------------------------------
st.set_page_config(page_title="LegalEase", page_icon="⚖️", layout="centered")

defaults = {
    "generated_text": "",
    "document_type": "",
    "terms_used": "",
    "show_edit": False,
    "gen_id": 0,
    "model_used": "",
    "doc_type_choice": config.DOCUMENT_TYPES[0],
    "custom_type": "",
    "parties": "",
    "terms": "",
    "dates": "",
    "jurisdiction": "",
    "extra": "",
}
for k, v in defaults.items():
    st.session_state.setdefault(k, v)


def load_example():
    for k, v in EXAMPLE.items():
        st.session_state[k] = v


def clear_form():
    for k in ("parties", "terms", "dates", "jurisdiction", "extra", "custom_type"):
        st.session_state[k] = ""


def toggle_edit():
    st.session_state.show_edit = not st.session_state.show_edit
    if st.session_state.show_edit:
        st.session_state[f"editor_{st.session_state.gen_id}"] = st.session_state.generated_text


def backend_health(url: str) -> dict:
    """Ask the backend for its status. Returns {"ok": bool, ...} with the reason on failure."""
    try:
        r = requests.get(f"{url}/health", timeout=15)
    except requests.ConnectionError:
        return {"ok": False, "reason": "not_running"}
    except requests.Timeout:
        return {"ok": False, "reason": "timeout"}
    except requests.RequestException as exc:
        return {"ok": False, "reason": "other", "error": str(exc)}
    try:
        data = r.json()
    except ValueError:
        data = {}
    if not r.ok:
        return {"ok": False, "reason": "http", "error": f"HTTP {r.status_code}: {r.text[:300]}"}
    if data.get("status") != "ok":
        return {"ok": False, "reason": "backend_error", "error": data.get("error", "unknown error")}
    return {"ok": True, **data}


@st.cache_data(show_spinner=False, max_entries=20)
def build_files(text: str, doc_type: str, terms: str, logo_bytes, footer: str):
    """Create TXT / DOCX / PDF bytes (cached so reruns stay fast)."""
    logo = logo_bytes if logo_bytes else None
    txt = format_txt(text).encode("utf-8")
    docx = format_docx(text, doc_type, terms=terms, logo=logo, footer_text=footer)
    pdf = format_pdf(text, doc_type, terms=terms, logo=logo, footer_text=footer)
    return txt, docx, pdf


# ---------------------------------------------------------------------------
# Sidebar: status and branding
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Settings")
    # Only re-check while not connected (or when the button is clicked)
    if not st.session_state.get("health", {}).get("ok"):
        with st.spinner("Checking backend..."):
            st.session_state.health = backend_health(BACKEND_URL)
    health = st.session_state.health

    if health["ok"]:
        mode = ("Mock mode (no API key)" if health.get("mock_mode")
                else f"Gemini: `{health.get('model')}`")
        st.success(f"Backend connected\n\n{mode}")
    elif health["reason"] == "not_running":
        st.error(f"Backend not running at {BACKEND_URL}.\n\n"
                 "Start it in another terminal:\n"
                 "`python -m uvicorn legalEaseAPI.main:app --reload`")
    elif health["reason"] == "timeout":
        st.warning("Backend is starting up (slow response). Click Recheck in a few seconds.")
    else:
        st.error(f"Backend is running but reported a problem:\n\n{health.get('error')}")

    if st.button("🔄 Recheck backend"):
        st.session_state.health = backend_health(BACKEND_URL)
        st.rerun()

    st.subheader("🎨 Branding")
    uploaded_logo = st.file_uploader("Company logo (PNG/JPG)", type=["png", "jpg", "jpeg"])
    company = st.text_input("Company name", value=config.COMPANY_NAME)
    email = st.text_input("Contact email", value=config.COMPANY_EMAIL)
    footer_text = f"{company} | {email} | All Rights Reserved."
    st.caption("The logo and footer appear in the DOCX and PDF downloads.")

    st.divider()
    st.caption("⚠️ " + config.DISCLAIMER)

# ---------------------------------------------------------------------------
# Header: logo + title
# ---------------------------------------------------------------------------
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if Path(config.WEB_LOGO_PATH).exists():
        st.image(config.WEB_LOGO_PATH, width=260)
st.markdown("<h2 style='text-align: center;'>AI Legal Document Generator</h2>",
            unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Input form
# ---------------------------------------------------------------------------
b1, b2, _ = st.columns([1, 1, 2])
b1.button("✨ Load example", on_click=load_example)
b2.button("🧹 Clear", on_click=clear_form)

st.selectbox("Document Type (Ex: Agreement, Contract, NDA)",
             config.DOCUMENT_TYPES + [CUSTOM_TYPE], key="doc_type_choice")
if st.session_state.doc_type_choice == CUSTOM_TYPE:
    st.text_input("Custom document type", key="custom_type",
                  placeholder="e.g. Vehicle Sale Agreement")
st.text_area("Parties Involved", key="parties", height=90,
             placeholder="John Doe (Freelancer), ABC Corp (Client)")
st.text_area("Terms & Conditions (Use semicolons for bullet points)", key="terms", height=130,
             placeholder="Payment within 30 days of invoice; Confidentiality at all times; ...")
c1, c2 = st.columns(2)
c1.text_input("Effective Date", key="dates", placeholder="April 15, 2025")
c2.text_input("Jurisdiction (optional)", key="jurisdiction", placeholder="Tamil Nadu, India")
with st.expander("Additional instructions (optional)"):
    st.text_area("Anything else the AI should include?", key="extra", height=80,
                 placeholder="e.g. Add a non-compete clause for 12 months")

document_type = (st.session_state.custom_type.strip()
                 if st.session_state.doc_type_choice == CUSTOM_TYPE
                 else st.session_state.doc_type_choice)

if st.button("Generate Document", type="primary"):
    missing = [name for name, val in (("Document Type", document_type),
                                      ("Parties Involved", st.session_state.parties),
                                      ("Terms & Conditions", st.session_state.terms),
                                      ("Effective Date", st.session_state.dates))
               if len(val.strip()) < 2]
    if missing:
        st.warning("Please fill in: " + ", ".join(missing))
    else:
        payload = {
            "document_type": document_type,
            "parties": st.session_state.parties,
            "terms": st.session_state.terms,
            "dates": st.session_state.dates,
            "jurisdiction": st.session_state.jurisdiction,
            "additional_instructions": st.session_state.extra,
        }
        with st.spinner("Drafting your document with Gemini... this can take 20-60 seconds."):
            try:
                response = requests.post(f"{BACKEND_URL}/generate", json=payload,
                                         timeout=config.REQUEST_TIMEOUT)
                if response.ok:
                    data = response.json()
                    st.session_state.generated_text = sanitize_text(data["document"])
                    st.session_state.document_type = document_type
                    st.session_state.terms_used = st.session_state.terms
                    st.session_state.model_used = data.get("model", "")
                    st.session_state.gen_id += 1
                    st.session_state.show_edit = False
                    st.success("✅ Document Generated Successfully!")
                else:
                    try:
                        detail = response.json().get("detail")
                    except ValueError:
                        detail = response.text
                    if isinstance(detail, list):  # FastAPI validation errors
                        detail = "; ".join(f"{'.'.join(map(str, d.get('loc', [])[1:]))}: {d.get('msg')}"
                                           for d in detail)
                    st.error(f"Error {response.status_code}: {detail}")
            except requests.ConnectionError:
                st.error(f"Could not connect to the backend at {BACKEND_URL}. "
                         "Is `uvicorn legalEaseAPI.main:app --reload` running?")
            except requests.Timeout:
                st.error("The request timed out. Please try again.")

# ---------------------------------------------------------------------------
# Preview, edit and download
# ---------------------------------------------------------------------------
if not st.session_state.generated_text:
    st.info("Fill in the details and click 'Generate Document' to start.")
    st.stop()

editor_key = f"editor_{st.session_state.gen_id}"
if st.session_state.show_edit and editor_key in st.session_state:
    st.session_state.generated_text = st.session_state[editor_key]
current_text = st.session_state.generated_text
doc_type = st.session_state.document_type

st.markdown("---")
st.subheader("📄 Preview")
words = len(current_text.split())
st.caption(f"{doc_type} · {words:,} words"
           + (f" · model: {st.session_state.model_used}" if st.session_state.model_used else ""))

styled_html = format_html_preview(current_text)
st.markdown(PREVIEW_CSS + f"<div class='le-card'>{styled_html}</div>", unsafe_allow_html=True)

st.button("✏️ Close Editor" if st.session_state.show_edit else "✏️ Click to Edit Document",
          on_click=toggle_edit)

if st.session_state.show_edit:
    st.text_area("Edit Document Below:", key=editor_key, height=420,
                 help="Use '## ' for the title, '### ' for section headings, '- ' for bullets "
                      "and **bold**. Press Ctrl+Enter (or click outside) to apply.")

logo_bytes = uploaded_logo.getvalue() if uploaded_logo else None
try:
    txt_bytes, docx_bytes, pdf_bytes = build_files(current_text, doc_type,
                                                   st.session_state.terms_used,
                                                   logo_bytes, footer_text)
except Exception as exc:  # show the problem instead of crashing the page
    st.error(f"Could not build download files: {exc}")
    st.stop()

d1, d2, d3 = st.columns(3)
d1.download_button("📄 Download as .TXT", data=txt_bytes,
                   file_name=safe_filename(doc_type, "txt"), mime="text/plain")
d2.download_button("📝 Download as .DOCX", data=docx_bytes,
                   file_name=safe_filename(doc_type, "docx"),
                   mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
d3.download_button("📕 Download as .PDF", data=pdf_bytes,
                   file_name=safe_filename(doc_type, "pdf"), mime="application/pdf")
