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

    for question_key, folder_name in config["questions"]["section_a_cont"].items():
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

def q11_answer_approach():
    match st.session_state["q11_approach"]:
        case "Volume":
            st.session_state.update({
                "q11_mr_a" : str(23.8007),
                "q11_mr_b" : str(19.8468)
            })

        case "Migration Rate":
            st.session_state.update({
                "q11_mr_a" : "",
                "q11_mr_b" : ""
            })
    
def grade_submission(solutions, img, emplid, surname, name):
    # question 9
    q9_grd = 0.0
    
    q9_sol = solutions["question_9"]["solution"]
    
    q9_ata_sub = safe_float(st.session_state["q9_ata_val"])
    q9_ata_ai = q9_sol["desert_1"]["aridity_index"]
    q9_ata_fc = q9_sol["desert_1"]["full_credit"]
    q9_ata_pc = q9_sol["desert_1"]["partial_credit"]

    q9_kal_sub = safe_float(st.session_state["q9_kal_val"])
    q9_kal_ai = q9_sol["desert_2"]["aridity_index"]
    q9_kal_fc = q9_sol["desert_2"]["full_credit"]
    q9_kal_pc = q9_sol["desert_2"]["partial_credit"]

    q9_sub_ans = st.session_state["q9_sub_ans"]
    q9_sub_mot = st.session_state["q9_sub_mot"]

    q9_ata_range = [
        (q9_ata_ai - q9_ata_fc, q9_ata_ai + q9_ata_fc, 1.0),
        (q9_ata_ai - q9_ata_pc, q9_ata_ai + q9_ata_pc, 0.5)
    ]

    q9_kal_range = [
        (q9_kal_ai - q9_kal_fc, q9_kal_ai + q9_kal_fc, 1.0),
        (q9_kal_ai - q9_kal_pc, q9_kal_ai + q9_kal_pc, 0.5)
    ]

    q9_grd += next((grade for lower, upper, grade in q9_ata_range if lower <= q9_ata_sub <= upper),0.0)

    q9_grd += next((grade for lower, upper, grade in q9_kal_range if lower <= q9_kal_sub <= upper),0.0)

    if q9_sub_ans == "Atacama":
        q9_grd += 1.0

    match q9_sub_mot:
        case "Full Credit":
            q9_grd += 1.0
        case "Partial Credit":
            q9_grd += 0.5
        case "No Credit":
            q9_grd += 0.0

    # question 10
    q10a_grd = 0.0
    q10b_grd = 0.0

    q10_sol = solutions["question_10"]["solution"]

    q10a_sub = safe_float(st.session_state["q10_sub_val"])
    q10a_ans = q10_sol["ac_ratio"]
    q10a_fc = q10_sol["full_credit"]
    q10a_pc = q10_sol["partial_credit"]
    q10b_sub = st.session_state["q10_sub_shape"]

    q10a_range = [
        (q10a_ans - q10a_fc, q10a_ans + q10a_fc, 10.0),
        (q10a_ans - q10a_pc, q10a_ans + q10a_pc, 5.0)
    ]

    q10a_grd += next((grade for lower, upper, grade in q10a_range if lower <= q10a_sub <= upper), 0.0)

    if q10b_sub == "Pudgy":
        q10b_grd += 2.0

    q10_grd = q10a_grd + q10b_grd
    
    # question 11
    q11_grd = 0.0
    q11_sol = solutions["question_11"]["solution"]

    q11_mr_a_sub = safe_float(st.session_state["q11_mr_a"])
    q11_mrate_a = q11_sol["barchan_1"]["migration_rate"]
    q11_mrate_a_fc = q11_sol["barchan_1"]["full_credit"]
    q11_mrate_a_pc = q11_sol["barchan_1"]["partial_credit"]

    q11_mr_b_sub = safe_float(st.session_state["q11_mr_b"])
    q11_mrate_b = q11_sol["barchan_2"]["migration_rate"]
    q11_mrate_b_fc = q11_sol["barchan_2"]["full_credit"]
    q11_mrate_b_pc = q11_sol["barchan_2"]["partial_credit"]

    q11_sub_ans = st.session_state["q11_sub_ans"]
    q11_sub_mot = st.session_state["q11_sub_mot"]

    q11_ba_range = [
        (q11_mrate_a - q11_mrate_a_fc, q11_mrate_a + q11_mrate_a_fc, 1.0),
        (q11_mrate_a - q11_mrate_a_pc, q11_mrate_a + q11_mrate_a_pc, 0.5)
    ]

    q11_bb_range = [
        (q11_mrate_b - q11_mrate_b_fc, q11_mrate_b + q11_mrate_b_fc, 1.0),
        (q11_mrate_b - q11_mrate_b_pc, q11_mrate_b + q11_mrate_b_pc, 0.5)
    ]

    q11_grd += next((grade for lower, upper, grade in q11_ba_range if lower <= q11_mr_a_sub <= upper), 0.0)

    q11_grd += next((grade for lower, upper, grade in q11_bb_range if lower <= q11_mr_b_sub <= upper), 0.0)

    if q11_sub_ans == "Barchan A":
        q11_grd += 2.0

    match q11_sub_mot:
        case "Full Credit":
            q11_grd += 2.0
        case "Partial Credit":
            q11_grd += 1.0
        case "No Credit":
            q11_grd += 0.0

    # question 12
    q12a_grd = 0.0
    q12b_grd = 0.0
    q12_wrk_grd = 0.0

    q12_sol = solutions["question_12"]["solution"]
    q12_str_ans = q12_sol["strahler"]
    q12_shr_ans = q12_sol["shreve"]

    q12_sub_str = safe_float(st.session_state["q12_sub_str"])
    q12_sub_shr = safe_float(st.session_state["q12_sub_shr"])

    if q12_sub_str == q12_str_ans:
        q12a_grd += 1

    if q12_sub_shr == q12_shr_ans:
        q12b_grd += 1.0

    match st.session_state["q12_str_wrk"]:
        case "Full Credit":
            q12_wrk_grd += 1.0
        case "Partial Credit":
            q12_wrk_grd += 0.5
        case "No Credit":
            q12_wrk_grd += 0.0

    match st.session_state["q12_shr_wrk"]:
        case "Full Credit":
            q12_wrk_grd += 1.0
        case "Partial Credit":
            q12_wrk_grd += 0.5
        case "No Credit":
            q12_wrk_grd += 0.0

    q12_grd = q12a_grd + q12b_grd + q12_wrk_grd
    # final processing
    final_grade = q9_grd + q10_grd + q11_grd + q12_grd
    
    ws = get_gsheet()

    if "usernames" not in st.session_state:
        st.session_state["usernames"] = ws.col_values(3)
        headers = ws.row_values(1)
        st.session_state["target_col"] = headers.index("Exam (Section A - cont) [Total Pts: 26 Score] |2992933")

    row_idx = st.session_state["usernames"].index(emplid) + 1
    col_idx = st.session_state["target_col"] + 1
    ws.update_cell(row_idx, col_idx, safe_float(final_grade))
    st.toast(f"Successfully updated mark for {name}: {final_grade}",
             icon="\u2705")

    cv.putText(img, f"{name} {surname}",(88,70), cv.FONT_HERSHEY_SIMPLEX, 1.0, (0,0,255), 1)
    cv.putText(img, str(emplid),(962,71), cv.FONT_HERSHEY_SIMPLEX, 1.0, (0,0,255), 1)
    cv.putText(img, str(final_grade),(425,227), cv.FONT_HERSHEY_SIMPLEX, 1.5, (0,0,255), 1)

    cv.putText(img, str(q9_grd),(1158,202), cv.FONT_HERSHEY_SIMPLEX, 1.0, (0,0,255), 1)
    cv.putText(img, str(q10a_grd),(1158,392), cv.FONT_HERSHEY_SIMPLEX, 1.0, (0,0,255), 1)
    cv.putText(img, str(q10b_grd),(1158,442), cv.FONT_HERSHEY_SIMPLEX, 1.0, (0,0,255), 1)
    cv.putText(img, str(q11_grd),(1158,514), cv.FONT_HERSHEY_SIMPLEX, 1.0, (0,0,255), 1)
    cv.putText(img, str(q12a_grd),(617,708), cv.FONT_HERSHEY_SIMPLEX, 1.0, (0,0,255), 1)
    cv.putText(img, str(q12b_grd),(1158,710), cv.FONT_HERSHEY_SIMPLEX, 1.0, (0,0,255), 1)
    cv.putText(img, str(q12_wrk_grd),(1158,856), cv.FONT_HERSHEY_SIMPLEX, 1.0, (0,0,255), 1)

    final_img_rgb = cv.cvtColor(img, cv.COLOR_BGR2RGB)
    final_img_pil = Image.fromarray(final_img_rgb)

    filename = f"graded-{surname}-{name}-{emplid}.png"
    st.session_state["graded_filename"] = filename
    grader_timestamp = datetime.now().isoformat()
    meta_info = PngInfo()
    meta_info.add_text("Grader", grader.strip())
    meta_info.add_text("GradedAt", grader_timestamp)
    meta_info.add_text("final", str(final_grade))
    meta_info.add_text("q9", str(q9_grd))
    meta_info.add_text("q10a", str(q10a_grd))
    meta_info.add_text("q10b", str(q10b_grd))
    meta_info.add_text("q11", str(q11_grd))
    meta_info.add_text("q12a", str(q12a_grd))
    meta_info.add_text("q12b", str(q12b_grd))
    meta_info.add_text("q12wrk", str(q12_wrk_grd))
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
    st.session_state.update({
        "q9_ata_val": "",
        "q9_kal_val": "",
        "q9_sub_ans": None,
        "q9_sub_mot": None,
        "q10_sub_val" : "",
        "q10_sub_shape" : None,
        "q11_sub_ans" : None,
        "q11_sub_mot" : None,
        "q11_mr_a" : "",
        "q11_mr_b" : "",
        "q12_sub_str" : "",
        "q12_sub_shr" : "",
        "q12_str_wrk" : None,
        "q12_shr_wrk" : None,
        "download_complete": False,
        "q11_approach" : "Migration Rate",
        "q11_blank" : False
    })
    # ==============================
    #st.rerun()

def clear_files():
     st.session_state["uploader_key"] += 1
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
    st.subheader("Section A (Continued)")

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
              st.session_state["script_index"] + 1)
    uploaded_files = st.file_uploader("Select the student submission",
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
            custom_functions.submission_viewer(img_url, height = 800)

        with col2:
            with st.container(height = 800, border = False):
                st.markdown("**Quetion 9**")

                q9_col1, q9_col2 = st.columns(2)

                with q9_col1:
                    st.text_input("AI (Atacama)",
                                  key = "q9_ata_val")

                    st.text_input("AI (Kalahari)",
                                  key = "q9_kal_val")

                with q9_col2:
                    st.selectbox("Answer",
                                 ("Atacama", "Kalahari", "Blank"),
                                 index = None,
                                 placeholder = "Make a selection..",
                                 key = "q9_sub_ans")
                    st.selectbox("Motivation",
                                 ("Full Credit","Partial Credit","No Credit"),
                                 index = None,
                                 placeholder = "Make a selection...",
                                 key = "q9_sub_mot")

                st.markdown("**Question 10**")

                q10_col1, q10_col2 = st.columns(2)

                with q10_col1:
                    st.text_input("a/c ratio",
                                  key = "q10_sub_val")
                with q10_col2:
                    st.selectbox("Shape",
                                 ("Slim","Normal","Pudgy","Fat","Blank"),
                                 index = None,
                                 placeholder = "Make a selection...",
                                 key = "q10_sub_shape")

                st.markdown("**Question 11**")

                st.toggle("Blank",
                          value = False,
                          key = "q11_blank")

                if st.session_state["q11_blank"]:
                    st.session_state.update({
                        "q11_mr_a" : "0",
                        "q11_mr_b" : "0",
                        "q11_sub_ans" : "Blank",
                        "q11_sub_mot" : "No Credit"
                    })

                st.radio("Answer based on",
                         ["Migration Rate", "Volume"],
                         key = "q11_approach",
                         on_change = q11_answer_approach)

                q11_col1, q11_col2 = st.columns(2)

                with q11_col1:
                    st.text_input("Migration Rate A",
                                  key = "q11_mr_a")
                    st.text_input("Migration Rate B",
                                  key = "q11_mr_b")
                with q11_col2:
                    st.selectbox("Answer",
                                 ("Barchan A", "Barchan B", "Blank"),
                                 index = None,
                                 placeholder = "Make a selection...",
                                 key = "q11_sub_ans")
                    st.selectbox("Motivation",
                                 ("Full Credit","Partial Credit","No Credit"),
                                 index = None,
                                 placeholder = "Make a selection...",
                                 key = "q11_sub_mot")

                st.markdown("**Question 12**")

                q12_col1, q12_col2 = st.columns(2)

                with q12_col1:
                    st.text_input("Strahler",
                                  key = "q12_sub_str")
                    st.text_input("Shreve",
                                  key = "q12_sub_shr")

                with q12_col2:
                    st.selectbox("Work shown (Strahler)",
                                 ("Full Credit","Partial Credit","No Credit"),
                                 index = None,
                                 placeholder = "Make a selection...",
                                 key = "q12_str_wrk")
                    st.selectbox("Work shown (Shreve)",
                                 ("Full Credit","Partial Credit","No Credit"),
                                 index = None,
                                 placeholder = "Make a selection...",
                                 key = "q12_shr_wrk")

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
                
