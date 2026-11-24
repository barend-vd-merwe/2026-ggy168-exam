import streamlit as st
import cv2 as cv
import pandas as pd
import numpy as np
from PIL import Image
from PIL.PngImagePlugin import PngInfo
import io
from io import BytesIO
from streamlit_image_zoom import image_zoom
import base64
from datetime import datetime
import yaml
from streamlit_gsheets import GSheetsConnection
from pathlib import Path
import custom_functions
import gc
from google.oauth2 import service_account
from googleapiclient.discovery import build
import textwrap
import gspread

BASE_DIR = Path(__file__).resolve().parent.parent
IMG_DIR = BASE_DIR / "images"

@st.cache_resource(show_spinner="Establishing credentials...", max_entries=3, scope = "session")
def get_drive_service():
    credentials_dict = dict(st.secrets["gcp_service_account"])
    
    scopes = ["https://www.googleapis.com/auth/drive.readonly"]
    creds = service_account.Credentials.from_service_account_info(
        credentials_dict, scopes=scopes
    )
    return build("drive", "v3", credentials=creds)

@st.cache_data(show_spinner="Loading submission...", max_entries=3, scope = "session")
def process_submission(file_bytes):
    img_bytes = np.frombuffer(file_bytes, dtype=np.uint8)
    cv_img = cv.imdecode(img_bytes, cv.IMREAD_COLOR)

    _, disp_img = cv.imencode(".jpg", cv_img, [int(cv.IMWRITE_JPEG_QUALITY), 80])
    b64_str = base64.b64encode(disp_img).decode("utf-8")
    img_url = f"data:image/jpg;base64,{b64_str}"

    del disp_img
    gc.collect()

    return cv_img, img_url

def find_item_id(service, name, parent_id, is_folder):
    query = f"name = '{name}' and '{parent_id}' in parents and trashed = false"
    
    if is_folder:
        query += " and mimeType = 'application/vnd.google-apps.folder'"
        
    results = service.files().list(
        q=query,
        fields="files(id, name)",
        pageSize=1
    ).execute()
    
    files = results.get("files", [])
    return files[0]["id"] if files else None
   
@st.cache_data(show_spinner="Processing solutions...", max_entries=3, scope = "session")
def process_solutions():
    with open(BASE_DIR / "config.yaml", "r", encoding = "utf-8") as config_file:
        config = yaml.safe_load(config_file)

    service = get_drive_service()
    root_folder = st.secrets["question_pool_folder"]

    solutions = {}

    for question_key, folder_name in config["questions"]["section_b"].items():
        question_folder_id = find_item_id(service, folder_name, root_folder, is_folder = True)

        if question_folder_id:
            meta_file_id = find_item_id(service, "meta.yaml", question_folder_id, False)

            if meta_file_id:
                raw_bytes = service.files().get_media(fileId=meta_file_id).execute()
                solutions[question_key] = yaml.safe_load(raw_bytes)
    return solutions

@st.cache_resource(scope="session")
def get_gsheet():
    credentials_dict = dict(st.secrets["gcp_service_account"])
    client = gspread.service_account_from_dict(credentials_dict)
    sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    sheet = client.open_by_url(sheet_url)
    return sheet.sheet1

def safe_float(val):
    try:
        return float(str(val).strip())
    except:
        return float("nan")

def grade_submission(solutions, img, emplid, surname, name):
    q13a_grd_1 = 0.0
    q13a_grd_2 = 0.0
    q13a_grd_3 = 0.0
    q13a_grd_4 = 0.0
    q13b_grd = 0.0
    q13c_grd = 0.0
    if st.session_state["strip_orientation"] == "Horizontal":
        q13 = solutions["question_13"]["solution"]["horizontal_strips"]
    else:
        q13 = solutions["question_13"]["solution"]["vertical_strips"]
    # strip 1
    l1_ans = q13["strip_1"]["length"]["answer"]
    l1_fc = q13["strip_1"]["length"]["full_credit"]
    l1_pc = q13["strip_1"]["length"]["partial_credit"]

    w1_ans = q13["strip_1"]["width"]["answer"]
    w1_fc = q13["strip_1"]["width"]["full_credit"]
    w1_pc = q13["strip_1"]["width"]["partial_credit"]

    a1_ans = q13["strip_1"]["area"]["answer"]
    a1_fc = q13["strip_1"]["area"]["full_credit"]
    a1_pc = q13["strip_1"]["area"]["partial_credit"]

    # strip 2
    l2_ans = q13["strip_2"]["length"]["answer"]
    l2_fc = q13["strip_2"]["length"]["full_credit"]
    l2_pc = q13["strip_2"]["length"]["partial_credit"]

    w2_ans = q13["strip_2"]["width"]["answer"]
    w2_fc = q13["strip_2"]["width"]["full_credit"]
    w2_pc = q13["strip_2"]["width"]["partial_credit"]

    a2_ans = q13["strip_2"]["area"]["answer"]
    a2_fc = q13["strip_2"]["area"]["full_credit"]
    a2_pc = q13["strip_2"]["area"]["partial_credit"]

    # strip 3
    l3_ans = q13["strip_3"]["length"]["answer"]
    l3_fc = q13["strip_3"]["length"]["full_credit"]
    l3_pc = q13["strip_3"]["length"]["partial_credit"]

    w3_ans = q13["strip_3"]["width"]["answer"]
    w3_fc = q13["strip_3"]["width"]["full_credit"]
    w3_pc = q13["strip_3"]["width"]["partial_credit"]

    a3_ans = q13["strip_3"]["area"]["answer"]
    a3_fc = q13["strip_3"]["area"]["full_credit"]
    a3_pc = q13["strip_3"]["area"]["partial_credit"]

    # strip 4
    l4_ans = q13["strip_4"]["length"]["answer"]
    l4_fc = q13["strip_4"]["length"]["full_credit"]
    l4_pc = q13["strip_4"]["length"]["partial_credit"]

    w4_ans = q13["strip_4"]["width"]["answer"]
    w4_fc = q13["strip_4"]["width"]["full_credit"]
    w4_pc = q13["strip_4"]["width"]["partial_credit"]

    a4_ans = q13["strip_4"]["area"]["answer"]
    a4_fc = q13["strip_4"]["area"]["full_credit"]
    a4_pc = q13["strip_4"]["area"]["partial_credit"]

    # total area
    tot_ans = q13["total_area"]["answer"]
    tot_fc = q13["total_area"]["full_credit"]
    tot_pc = q13["total_area"]["partial_credit"]

    l1_sub = safe_float(edited_df.loc[edited_df["strip"] == 1, "length"].item())
    w1_sub = safe_float(edited_df.loc[edited_df["strip"] == 1, "width"].item())
    a1_sub = safe_float(edited_df.loc[edited_df["strip"] == 1, "area"].item())

    l1_range = [
        (l1_ans - l1_fc, l1_ans + l1_fc, 1.0),
        (l1_ans - l1_pc, l1_ans + l1_pc, 0.5)
    ]

    q13a_grd_1 += next((grade for lower, upper, grade in l1_range if lower <= l1_sub <= upper),0.0)

    w1_range = [
        (w1_ans - w1_fc, w1_ans + w1_fc, 1.0),
        (w1_ans - w1_pc, w1_ans + w1_pc, 0.5)
    ]

    q13a_grd_1 += next((grade for lower, upper, grade in w1_range if lower <= w1_sub <= upper),0.0)

    a1_range = [
        (a1_ans - a1_fc, a1_ans + a1_fc, 1.0),
        (a1_ans - a1_pc, a1_ans + a1_pc, 0.5)
    ]

    q13a_grd_1 += next((grade for lower, upper, grade in a1_range if lower <= a1_sub <= upper),0.0)

    l2_sub = safe_float(edited_df.loc[edited_df["strip"] == 2, "length"].item())
    w2_sub = safe_float(edited_df.loc[edited_df["strip"] == 2, "width"].item())
    a2_sub = safe_float(edited_df.loc[edited_df["strip"] == 2, "area"].item())

    l2_range = [
        (l2_ans - l2_fc, l2_ans + l2_fc, 1.0),
        (l2_ans - l2_pc, l2_ans + l2_pc, 0.5)
    ]

    q13a_grd_2 += next((grade for lower, upper, grade in l2_range if lower <= l2_sub <= upper),0.0)

    w2_range = [
        (w2_ans - w2_fc, w2_ans + w2_fc, 1.0),
        (w2_ans - w2_pc, w2_ans + w2_pc, 0.5)
    ]

    q13a_grd_2 += next((grade for lower, upper, grade in w2_range if lower <= w2_sub <= upper),0.0)

    a2_range = [
        (a2_ans - a2_fc, a2_ans + a2_fc, 1.0),
        (a2_ans - a2_pc, a2_ans + a2_pc, 0.5)
    ]

    q13a_grd_2 += next((grade for lower, upper, grade in a2_range if lower <= a2_sub <= upper),0.0)

    l3_sub = safe_float(edited_df.loc[edited_df["strip"] == 3, "length"].item())
    w3_sub = safe_float(edited_df.loc[edited_df["strip"] == 3, "width"].item())
    a3_sub = safe_float(edited_df.loc[edited_df["strip"] == 3, "area"].item())

    l3_range = [
        (l3_ans - l3_fc, l3_ans + l3_fc, 1.0),
        (l3_ans - l3_pc, l3_ans + l3_pc, 0.5)
    ]

    q13a_grd_3 += next((grade for lower, upper, grade in l3_range if lower <= l3_sub <= upper),0.0)

    w3_range = [
        (w3_ans - w3_fc, w3_ans + w3_fc, 1.0),
        (w3_ans - w3_pc, w3_ans + w3_pc, 0.5)
    ]

    q13a_grd_3 += next((grade for lower, upper, grade in w3_range if lower <= w3_sub <= upper),0.0)

    a3_range = [
        (a3_ans - a3_fc, a3_ans + a3_fc, 1.0),
        (a3_ans - a3_pc, a3_ans + a3_pc, 0.5)
    ]

    q13a_grd_3 += next((grade for lower, upper, grade in a3_range if lower <= a3_sub <= upper),0.0)

    l4_sub = safe_float(edited_df.loc[edited_df["strip"] == 4, "length"].item())
    w4_sub = safe_float(edited_df.loc[edited_df["strip"] == 4, "width"].item())
    a4_sub = safe_float(edited_df.loc[edited_df["strip"] == 4, "area"].item())

    l4_range = [
        (l4_ans - l4_fc, l4_ans + l4_fc, 1.0),
        (l4_ans - l4_pc, l4_ans + l4_pc, 0.5)
    ]

    q13a_grd_4 += next((grade for lower, upper, grade in l4_range if lower <= l4_sub <= upper),0.0)

    w4_range = [
        (w4_ans - w4_fc, w4_ans + w4_fc, 1.0),
        (w4_ans - w4_pc, w4_ans + w4_pc, 0.5)
    ]

    q13a_grd_4 += next((grade for lower, upper, grade in w4_range if lower <= w4_sub <= upper),0.0)

    a4_range = [
        (a4_ans - a4_fc, a4_ans + a4_fc, 1.0),
        (a4_ans - a4_pc, a4_ans + a4_pc, 0.5)
    ]

    q13a_grd_4 += next((grade for lower, upper, grade in a4_range if lower <= a4_sub <= upper),0.0)

    q13a_grd = q13a_grd_1 + q13a_grd_2 + q13a_grd_3 + q13a_grd_4 

    tot_sub_val = safe_float(st.session_state["sub_ta"])
    tot_sub_unt = st.session_state["sub_ta_unt"]

    tot_area_range = [
        (tot_ans - tot_fc, tot_ans + tot_fc, 1.0),
        (tot_ans - tot_pc, tot_ans + tot_pc, 0.5)
    ]

    q13b_grd += next((grade for lower, upper, grade in tot_area_range if lower <= tot_sub_val <= upper),0.0)

    if tot_sub_unt == "Full Credit":
        q13b_grd += 1.0

    wrk_1 = st.session_state["wrk_strip1"]

    match wrk_1:
        case "Full Credit":
            q13c_grd += 2.0
        case "Partial Credit":
            q13c_grd += 1.0
        case "No Credit":
            q13c_grd += 0.0
    
    wrk_2 = st.session_state["wrk_strip2"]

    match wrk_2:
        case "Full Credit":
            q13c_grd += 2.0
        case "Partial Credit":
            q13c_grd += 1.0
        case "No Credit":
            q13c_grd += 0.0
            
    wrk_3 = st.session_state["wrk_strip3"]

    match wrk_3:
        case "Full Credit":
            q13c_grd += 2.0
        case "Partial Credit":
            q13c_grd += 1.0
        case "No Credit":
            q13c_grd += 0.0
            
    wrk_4 = st.session_state["wrk_strip4"]

    match wrk_4:
        case "Full Credit":
            q13c_grd += 2.0
        case "Partial Credit":
            q13c_grd += 1.0
        case "No Credit":
            q13c_grd += 0.0

    final_grade = q13a_grd + q13b_grd + q13c_grd

    ws = get_gsheet()

    if "usernames" not in st.session_state:
        st.session_state["usernames"] = ws.col_values(3)
        headers = ws.row_values(1)
        st.session_state["target_col"] = headers.index("Exam (Section B) [Total Pts: 22 Score] |2992934")

    row_idx = st.session_state["usernames"].index(emplid) + 1
    col_idx = st.session_state["target_col"] + 1
    ws.update_cell(row_idx, col_idx, safe_float(final_grade))
    st.toast(f"Successfully updated mark for {name}: {final_grade}",
             icon="\u2705")

    cv.putText(img, f"{name} {surname}",(88,70), cv.FONT_HERSHEY_SIMPLEX, 1.0, (0,0,255), 1)
    cv.putText(img, str(emplid),(962,71), cv.FONT_HERSHEY_SIMPLEX, 1.0, (0,0,255), 1)
    cv.putText(img, str(final_grade),(425,227), cv.FONT_HERSHEY_SIMPLEX, 1.5, (0,0,255), 1)

    cv.putText(img, str(q13a_grd_1),(1153,283), cv.FONT_HERSHEY_SIMPLEX, 1.0, (0,0,255), 1)
    cv.putText(img, str(q13a_grd_2),(1153,313), cv.FONT_HERSHEY_SIMPLEX, 1.0, (0,0,255), 1)
    cv.putText(img, str(q13a_grd_3),(1153,345), cv.FONT_HERSHEY_SIMPLEX, 1.0, (0,0,255), 1)
    cv.putText(img, str(q13a_grd_4),(1153,376), cv.FONT_HERSHEY_SIMPLEX, 1.0, (0,0,255), 1)

    cv.putText(img, str(q13b_grd),(1153,420), cv.FONT_HERSHEY_SIMPLEX, 1.0, (0,0,255), 1)
    cv.putText(img, str(q13c_grd),(981,821), cv.FONT_HERSHEY_SIMPLEX, 1.0, (0,0,255), 1)

    final_img_rgb = cv.cvtColor(img, cv.COLOR_BGR2RGB)
    final_img_pil = Image.fromarray(final_img_rgb)

    filename = f"graded-{surname}-{name}-{emplid}.png"
    st.session_state["graded_filename"] = filename
    grader_timestamp = datetime.now().isoformat()
    meta_info = PngInfo()
    meta_info.add_text("Grader", grader.strip())
    meta_info.add_text("GradedAt", grader_timestamp)
    meta_info.add_text("final", str(final_grade))
    meta_info.add_text("q13a", str(q13a_grd))
    meta_info.add_text("q13b", str(q13b_grd))
    meta_info.add_text("q13c", str(q13c_grd))
    buffer = io.BytesIO()
    final_img_pil.save(buffer, format="PNG",
                       pnginfo=meta_info,
                       compress_level=1)

    st.session_state["graded_submission"] = buffer.getvalue()

def next_submission():
    st.session_state["script_index"] += 1
    st.session_state["editor_version"] += 1
    del st.session_state["graded_submission"]
    gc.collect()
    # ==============================
    st.session_state["sub_ta"] = ""
    st.session_state["sub_ta_unt"] = None
    st.session_state["wrk_strip1"] = None
    st.session_state["wrk_strip2"] = None
    st.session_state["wrk_strip3"] = None
    st.session_state["wrk_strip4"] = None
    st.session_state["strip_orientation"] = "Horizontal"
    st.session_state["download_complete"] = False
    # ==============================
    #st.rerun()

def clear_files():
     st.session_state["uploader_key"] += 1
     st.session_state["download_complete"] = False
     del st.session_state["script_index"]
     if "graded_submission" in st.session_state:
         del st.session_state["graded_submission"]
# ------------------------------------------------------------
    
st.set_page_config(layout="wide")

st.markdown(
    """
    <style>
    /* 1. Add Tuks Red border strip across the top of the app */
    header[data-testid="stHeader"] {
        border-top: 5px solid #D12631 !important;
    }

    /* 2. Style primary headers with UP Navy Blue */
    h1, h2, h3 {
        color: #002B49 !important;
    }

    /* 3. Style Sidebar header with a Gold bottom accent */
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2 {
        border-bottom: 2px solid #E8A800;
        padding-bottom: 5px;
    }

    /* Custom utility classes */
    .tuks-red { color: #D12631; font-weight: bold; }
    .up-gold { color: #E8A800; font-weight: bold; }
    </style>
""",
    unsafe_allow_html=True,
)

title_col1, title_col2= st.columns(2)
with title_col1:
    st.image(IMG_DIR / "ggy168-module-banner.png")

with title_col2:
    st.title("GGY 168 — Introduction to Physical Geography")
    st.header("Normal Exam")
    st.subheader("Section B")

with st.expander("Instructions", expanded = False):
    st.markdown("""
    1. Enter your name in the provided space.
    2. Load the student submission.
    3. If there is an error during loading, refresh your browser window and try again.
    4. If it still doesn't work, send me an email with the student's details and move on to the next submission.
    5. Verify that the name on the submission matches the name of the file.
    6. Transfer the answers on the submission to the spaces provided.
    7. **DON'T** use commas for decimal marks. Please use a full-stop.
    9. When you are done, press the grade button.
    10. Download the graded submission and store it in a separate folder. **DON'T** change the filename.
    """)

if "script_index" not in st.session_state:
    st.session_state["script_index"] = 0

if "uploader_key" not in st.session_state:
    st.session_state["uploader_key"] = 100

if "editor_version" not in st.session_state:
    st.session_state["editor_version"] = 200

if "download_complete" not in st.session_state:
    st.session_state["download_complete"] = False

# load class list and submission
with st.sidebar:
    grader = st.text_input("Name of grader", key="graderName")
    pin = st.text_input("Enter PIN number",
                        type = "password",
                        key = "user_pin")
    st.metric("Busy marking script",
              st.session_state["script_index"])
    uploaded_files = st.file_uploader("Select the student submission(s)",
                                      type = ["png"],
                                      accept_multiple_files = True,
                                      key = str(st.session_state["uploader_key"]))
    st.button("Clear", on_click = clear_files)

usr_pin = st.session_state["user_pin"]
gizelle_pin = st.secrets.get("gizelle_pin")
barend_pin = st.secrets.get("barend_pin")


if uploaded_files and grader.strip() and (usr_pin == gizelle_pin or usr_pin == barend_pin):
    total_scripts = len(uploaded_files)
    current_script = st.session_state["script_index"] + 1
    progress = min(current_script / total_scripts, 1.0)
    st.progress(progress)

    # extract student details from img filename
    image = uploaded_files[st.session_state["script_index"]]
    filename = image.name
    filename = filename.replace(".png","")
    _ , *surname_parts, name, emplid = filename.split("-")
    surname = "-".join(surname_parts)

    img, img_url = process_submission(image.getvalue())

    solutions = process_solutions()

    tab_1, tab_2 = st.tabs(["Grader", "Memo"])

    with tab_1:
    
        col1, col2 = st.columns(2)

        with col1:
            custom_functions.submission_viewer(img_url)

        with col2:
            st.radio("Strip orientation",
                     ["Horizontal","Vertical"],
                     index = 0,
                     key = "strip_orientation")
            
            with st.expander("Student Details", expanded = False):
                st.markdown(f"""
                - *Name*: **{name}**
                - *Surname*: **{surname}**
                - *Student Number*: **{emplid}**
                """)

            raw_table = [
            {"strip": 1, "length": None, "width": None, "area": None},
            {"strip": 2, "length": None, "width": None, "area": None},
            {"strip": 3, "length": None, "width": None, "area": None},
            {"strip": 4, "length": None, "width": None, "area": None}
            ]

            sub_df = pd.DataFrame(raw_table)

            edited_df = st.data_editor(
                sub_df,
                column_config = {
                    "strip": st.column_config.NumberColumn(
                        "Strip",
                        disabled = True
                    ),
                    "length": st.column_config.TextColumn(
                        "Length (km)",
                        disabled = False,
                        required = True
                    ),
                    "width": st.column_config.TextColumn(
                        "Width (km)",
                        disabled = False,
                        required = True
                    ),
                    "area": st.column_config.TextColumn(
                        "Area (km²)",
                        disabled = False,
                        required = True
                    )
                },
                hide_index = True,
                width = "stretch",
                key = str(st.session_state["editor_version"])
            )

            tot_col1, tot_col2 = st.columns(2)

            with tot_col1:
                st.text_input("Total Area", key = "sub_ta")

            with tot_col2:
                st.selectbox("Units (km²)",
                             ("Full Credit", "No Credit"),
                             index = None,
                             placeholder = "Make a selection...",
                             key = "sub_ta_unt")

            st.markdown("**Work Shown**")
            wrk_col1, wrk_col2, wrk_col3, wrk_col4 = st.columns(4)

            with wrk_col1:
                st.selectbox("Strip 1",
                             ("Full Credit", "Partial Credit", "No Credit"),
                             index = None,
                             placeholder = "Make a selection...",
                             key = "wrk_strip1")
            with wrk_col2:
                st.selectbox("Strip 2",
                             ("Full Credit", "Partial Credit", "No Credit"),
                             index = None,
                             placeholder = "Make a selection...",
                             key = "wrk_strip2")

            with wrk_col3:
                st.selectbox("Strip 3",
                             ("Full Credit", "Partial Credit", "No Credit"),
                             index = None,
                             placeholder = "Make a selection...",
                             key = "wrk_strip3")

            with wrk_col4:
                st.selectbox("Strip 4",
                             ("Full Credit", "Partial Credit","No Credit"),
                             index = None,
                             placeholder = "Make a selection...",
                             key = "wrk_strip4")

            col2_a, col2_b, col2_c = st.columns(3)

            with col2_a:
                st.button("Grade",
                          on_click=grade_submission,
                          args=(solutions, img.copy(), emplid, surname, name))

            if "graded_submission" in st.session_state:
                with col2_b:
                    st.download_button(label=f"Download",
                                       data=st.session_state["graded_submission"],
                                       file_name=st.session_state["graded_filename"],
                                       mime="image/png",
                                       on_click = lambda: st.session_state.update({"download_complete" : True}))

                if st.session_state["script_index"] < len(uploaded_files) - 1 and st.session_state["download_complete"]:
                    with col2_c:
                        st.button("Next Submission", on_click = next_submission)
