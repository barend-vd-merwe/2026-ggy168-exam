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

    for question_key, folder_name in config["questions"]["section_a"].items():
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
    pass

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

# load class list and submission
with st.sidebar:
    grader = st.text_input("Name of grader", key="graderName")
    pin = st.text_input("Enter PIN number",
                        type = "password",
                        key = "user_pin")
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
            custom_functions.submission_viewer(img_url)

        with col2:
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
                             ("Slim","Normal","Pudgy","Fat"),
                             index = None,
                             placeholder = "Make a selection...",
                             key = "q10_sub_shape")

            st.markdown("**Question 11**")

            q11_col1, q11_col2 = st.columns(2)

            with q11_col1:
                st.selectbox("Answer",
                             ("Barchan A", "Barchan B"),
                             index = None,
                             placeholder = "Make a selection...",
                             key = "q11_sub_ans")
            with q11_col2:
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
                             key = "q11_str_wrk")
                st.selectbox("Work shown (Shreve)",
                             ("Full Credit","Partial Credit","No Credit"),
                             index = None,
                             placeholder = "Make a selection...",
                             key = "q11_shr_wrk")
                
