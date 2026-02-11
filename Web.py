import io
import re
import zipfile
import pandas as pd
import streamlit as st

# ---------- Configuration ----------
st.set_page_config(page_title="Schneider Proof Checklist", page_icon="⚡", layout="wide")

# ---------- Modern CSS (Schneider Brand Theme) ----------
st.markdown(
    """
    <style>
    /* Global Cleanups */
    .block-container { padding-top: 2rem; padding-bottom: 5rem; max-width: 1200px; }
    header { visibility: hidden; }
    footer { visibility: hidden; }
    
    /* Typography */
    h1 { font-family: 'Arial', sans-serif; font-weight: 800; }
    h3 { font-family: 'Arial', sans-serif; font-weight: 600; color: #888; font-size: 1rem; text-transform: uppercase; margin-top: 2rem; margin-bottom: 0.5rem; letter-spacing: 1px;}
    
    /* SCHNEIDER GREEN: #3dcd58 */
    
    /* Custom Progress Bar */
    .stProgress > div > div > div > div {
        background-color: #3dcd58;
    }

    /* Expander Styling - Make them look like list items */
    .streamlit-expanderHeader {
        background-color: transparent;
        border-radius: 5px;
        font-weight: 500;
        font-size: 1rem;
        border: 0px;
    }
    .streamlit-expanderHeader:hover {
        background-color: rgba(61, 205, 88, 0.1); /* Slight green tint on hover */
        color: #3dcd58;
    }
    .streamlit-expanderContent {
        background-color: rgba(255,255,255,0.02);
        border-radius: 0 0 5px 5px;
        border-left: 3px solid #3dcd58;
        margin-bottom: 10px;
    }
    
    /* Input Fields styling */
    .stTextInput input, .stTextArea textarea {
        background-color: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1);
        color: #fff;
    }
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #3dcd58;
        box-shadow: 0 0 0 1px #3dcd58;
    }

    /* Checkbox alignment correction */
    div[data-testid="stCheckbox"] {
        padding-top: 4px; 
    }
    
    /* Primary Buttons (Schneider Green) */
    button[kind="primary"] {
        background-color: #3dcd58;
        color: #000; /* Black text on green for contrast */
        border: none;
        transition: all 0.2s;
        font-weight: 600;
    }
    button[kind="primary"]:hover {
        background-color: #32a848;
        box-shadow: 0 4px 12px rgba(61, 205, 88, 0.4);
        color: #fff;
    }
    
    /* Metrics */
    div[data-testid="metric-container"] {
        background-color: rgba(255,255,255,0.03);
        padding: 15px;
        border-radius: 8px;
        border: 1px solid rgba(255,255,255,0.05);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- Data & Logic ----------
DEFAULT_LIST = [
    ("Product Information", False),
    ("Description", False),
    ("Documentation : identification of the product", False),
    ("Documentation : disassembly plan", False),
    ("Documentation : exploded view", False),
    ("Documentation : Wiring & connexion diagram", False),
    ("Documentation : Circuit board diagram / synoptic diagram", False),
    ("Documentation : List of tool & list of tests necessary for repair", False),
    ("Documentation : Repair instructions technical manual", False),
    ("Documentation : error code & diagnosis", False),
    ("Documentation : information about components & diagnosis", False),
    ("Documentation : software instructions (including reset)", False),
    ("Documentation : access to incident reported & recorded", False),
    ("Documentation : technical bulletins", False),
    ("Documentation : specific supervision of self-repair", False),
    ("Price : Price of expensive spare part / average price", False),
    ("Working environment : for functional parts", False),
    ("Working environment : for weakest parts", False),
    ("Skill level necessary for repair : for weakest parts", False),
    ("Disassembly depth : for weakest parts", False),
    ("Tools necessary for repair : for weakest parts", False),
    ("Return options", False),
    ("Remote assistance", False),
]

def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_") or "report"

def init_state():
    if "items" not in st.session_state:
        st.session_state["items"] = []
        for i, (task, is_header) in enumerate(DEFAULT_LIST, start=1):
            st.session_state["items"].append({
                "id": i,
                "is_header": is_header,
                "done": False,
                "name": task,
                "link": "",
                "comment": "",
                "uploads": [],
            })
        st.session_state["next_id"] = len(st.session_state["items"]) + 1

def add_row():
    st.session_state["items"].append({
        "id": st.session_state["next_id"],
        "is_header": False,
        "done": False,
        "name": "New Task",
        "link": "",
        "comment": "",
        "uploads": [],
    })
    st.session_state["next_id"] += 1

def delete_row(item_id):
    st.session_state["items"] = [x for x in st.session_state["items"] if x["id"] != item_id]

def build_excel(report_name):
    rows = []
    for it in st.session_state["items"]:
        file_names = [u['name'] for u in it['uploads']]
        rows.append({
            "Section": "HEADER" if it["is_header"] else "TASK",
            "Status": "Done" if it["done"] else "Pending",
            "Task Name": it["name"],
            "Link": it["link"],
            "Comment": it["comment"],
            "Files": ", ".join(file_names)
        })
    df = pd.DataFrame(rows)
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Checklist")
    return out.getvalue()

def build_zip(report_name):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        # Add Excel to zip
        excel_data = build_excel(report_name)
        z.writestr(f"{slugify(report_name)}_report.xlsx", excel_data)
        
        # Add evidence files
        for idx, it in enumerate(st.session_state["items"], start=1):
            if it["uploads"]:
                folder_name = f"{idx}_{slugify(it['name'])[:30]}"
                for f in it["uploads"]:
                    z.writestr(f"evidence/{folder_name}/{f['name']}", f["bytes"])
    return buf.getvalue()

# ---------- UI Structure ----------
init_state()

# 1. HEADER AREA
c1, c2 = st.columns([3, 1])
with c1:
    # SCHNEIDER LOGO URL
    logo_url = "https://upload.wikimedia.org/wikipedia/commons/9/95/Schneider_Electric_2007.svg"
    st.image(logo_url, width=300)
    st.caption("Global Compliance & Repairability Audit Tool")
    
with c2:
    # Live Progress Calculation
    tasks = [i for i in st.session_state["items"] if not i["is_header"]]
    done_count = sum(1 for i in tasks if i["done"])
    total_count = len(tasks) if tasks else 1
    progress = done_count / total_count
    st.metric("Completion", f"{int(progress*100)}%", f"{done_count}/{total_count} Tasks")

st.progress(progress)
st.markdown("---")

# 2. CONTROLS
with st.container():
    col_rep, col_act1, col_act2 = st.columns([2, 1, 1])
    with col_rep:
        report_name = st.text_input("Project / Report Name", value=" ", help="This will be used as the base name for your exported files. Make it descriptive!")
    with col_act1:
        st.write("") # Spacer
        st.write("") 
        if st.button("➕ Add Custom Task", use_container_width=True):
            add_row()
            st.rerun()
    with col_act2:
        st.write("") 
        st.write("") 
        if st.button("🔄 Reset List", use_container_width=True):
            st.session_state.clear()
            st.rerun()

# 3. THE LIST
st.markdown("<br>", unsafe_allow_html=True)

for it in st.session_state["items"]:
    
    # --- SECTION HEADERS ---
    if it["is_header"]:
        st.markdown(f"### {it['name']}")
        continue

    # --- TASK ROWS ---
    # We use columns: Checkbox | Expander (containing details) | Delete
    row_cols = st.columns([0.5, 10, 0.5])
    
    with row_cols[0]:
        # Vertical align checkbox attempt
        st.write("")
        it["done"] = st.checkbox("Done", value=it["done"], key=f"chk_{it['id']}", label_visibility="collapsed")

    with row_cols[1]:
        # Dynamic Title Logic
        icons = []
        if it["link"]: icons.append("🔗")
        if it["uploads"]: icons.append("📎")
        if it["comment"]: icons.append("📝")
        
        display_name = it["name"] if it["name"] else "(Untitled Task)"
        icon_str = f"&nbsp; <span style='opacity:0.6; font-size:0.8em'>{' '.join(icons)}</span>" if icons else ""
        
        # We put the inputs inside an expander to keep UI clean
        with st.expander(label=f"{display_name}  {icon_str}", expanded=False):
            
            # Use a form-like grid inside the expander
            ec1, ec2 = st.columns(2)
            with ec1:
                it["name"] = st.text_input("Task Name", value=it["name"], key=f"n_{it['id']}")
                it["link"] = st.text_input("Proof Link (URL)", value=it["link"], placeholder="https://...", key=f"l_{it['id']}")
            with ec2:
                it["comment"] = st.text_area("Notes / Observations", value=it["comment"], height=107, key=f"c_{it['id']}")
            
            # File Uploader full width
            uploaded_files = st.file_uploader(
                "Attach Evidence (Images/PDF)", 
                type=['png','jpg','pdf'], 
                accept_multiple_files=True,
                key=f"u_{it['id']}"
            )
            
            # Handle Uploads
            if uploaded_files:
                # Append new files to existing state
                for uf in uploaded_files:
                    if not any(f['name'] == uf.name for f in it['uploads']):
                        it["uploads"].append({"name": uf.name, "bytes": uf.getvalue()})
            
            # Show current attachments
            if it["uploads"]:
                st.markdown("**Attached:**")
                for i, f in enumerate(it["uploads"]):
                    st.text(f"📄 {f['name']}")

    with row_cols[2]:
        st.write("")
        if st.button("✕", key=f"del_{it['id']}", help="Delete Task"):
            delete_row(it["id"])
            st.rerun()

st.markdown("<br><br>", unsafe_allow_html=True)

# 4. EXPORT FOOTER
st.markdown("---")
f1, f2, f3 = st.columns([2, 1, 1])

with f1:
    st.markdown(
        """
        <div style='font-size:0.9rem; opacity:0.7;'>
        <b>Audit Complete?</b><br>
        Exporting will generate a .zip file containing the Excel summary 
        and folders organized by task for all your evidence files.
        </div>
        """, unsafe_allow_html=True
    )

with f3:
    has_content = any(len(x['uploads']) > 0 for x in st.session_state['items'])
    if st.download_button(
        label="📥 Download Export Package",
        data=build_zip(report_name),
        file_name=f"{slugify(report_name)}_COMPLETE.zip",
        mime="application/zip",
        use_container_width=True,
        type="primary"
    ):
        st.toast("Export generated successfully!", icon="🚀")