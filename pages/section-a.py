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

BASE_DIR = Path(__file__).resolve().parent.parent


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
    img_bytes = np.frombuffer(image.getvalue(), dtype=np.uint8)
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

    for question_key, folder_name in config["questions"]["section_a"].items():
        if question_key in st.session_state:
            continue
        question_folder_id = find_item_id(service, folder_name, root_folder, is_folder = True)

        if question_folder_id:
            meta_file_id = find_item_id(service, "meta.yaml", question_folder_id, False)

            if meta_file_id:
                raw_bytes = service.files().get_media(fileId=meta_file_id).execute()
                st.session_state[question_key] = yaml.safe_load(raw_bytes)
                print(f"{question_key} created")

def grade_submission():
    pass

def next_submission():
    st.session_state["script_index"] += 1
    del st.session_state["graded_submission"]
    # ==============================
    st.session_state["q1_val"] = ""
    st.session_state["q1_unt"] = None
    st.session_state["q2a_val"] = ""
    st.session_state["q2a_unt"] = None
    st.session_state["q2b"] = None
    st.session_state["q2c"] = None
    st.session_state["q3_val"] = ""
    st.session_state["q3_mot"] = None
    st.session_state["q4_val"] = ""
    st.session_state["q4_mot"] = None
    st.session_state["q5_ans"] = None
    st.session_state["q5_mot"] = None
    st.session_state["q6"] = None
    st.session_state["q7_profile"] = None
    st.session_state["q7_plan"] = None
    st.session_state["q8a_dra_val"] = ""
    st.session_state["q8a_cap_val"] = ""
    st.session_state["q8a_mot"] = None
    st.session_state["q8b_ans"] = None
    st.session_state["q8b_mot"] = None
    # ==============================
    st.rerun()

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
    st.image(BASE_DIR / "NAS_Faculty Logo.jpg")

with title_col2:
    st.title("GGY 168 — Introduction to Physical Geography")
    st.header("Normal Exam")
    st.subheader("Section A")

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

valid_pin = st.secrets.get("exam_pin")

if uploaded_files and grader.strip():
    total_scripts = len(uploaded_files)
    current_script = st.session_state["script_index"] + 1
    progress = min(current_script / total_scripts, 1.0)
    st.progress(progress)

    # extract student details from img filename
    image = uploaded_files[st.session_state["script_index"]]
    filename = image.name
    filename = filename.replace(".png","")
    _ ,_ , surname, name, emplid = filename.split("-")
    st.session_state["student_name"] = f"{name} {surname}"

    img, img_url = process_submission(image.getvalue())

    process_solutions()

    tab_1, tab_2 = st.tabs(["Grader", "Memo"])

    with tab_1:
    
        col1, col2 = st.columns(2)

        with col1:
            custom_functions.submission_viewer(img_url)

        with col2:
            with st.expander("Student Details", expanded = False):
                st.markdown(f"""
                - *Name*: **{name}**
                - *Surname*: **{surname}**
                - *Student Number*: **{emplid}**
                """)

            with st.expander("Questions 1 to 4 ", expanded = False):
                st.markdown("**Question 1**")

                q1_col1, q1_col2 = st.columns(2)

                with q1_col1:
                    st.text_input("Shelterbelt Interval",
                                  key = "q1_val")
                with q1_col2:
                    st.selectbox("Units",
                                 ("m","None"),
                                 index = None,
                                 placeholder = "Make a selection...",
                                 key = "q1_unt")

                st.markdown("**Question 2**")

                q2_col1, q2_col2 = st.columns(2)

                with q2_col1:

                    st.text_input("CSA",
                                  key = "q2a_val")

                    st.selectbox("Biggest change in CSA",
                                 ("2024 — 2025","2025 — 2026","Blank"),
                                 index = None,
                                 placeholder = "Make a selection ...",
                                 key = "q2b")

                with q2_col2:

                    st.selectbox("Units",
                                 ("cm²", "None"),
                                 index = None,
                                 placeholder = "Make a selection...",
                                 key = "q2a_unt")

                    st.selectbox("Motivation",
                                 ("Full Credit","Partial Credit","No Credit"),
                                 index = None,
                                 placeholder = "Make a selection...",
                                 key = "q2c")

                st.markdown("**Question 3**")

                q3_col1, q3_col2 = st.columns(2)

                with q3_col1:
                    st.text_input("Answer",
                                  key = "q3_val")

                with q3_col2:
                    st.selectbox("Motivation",
                                 ("Full Credit","Partial Credit","No Credit"),
                                 index = None,
                                 placeholder="Make a selection...",
                                 key = "q3_mot")

                st.markdown("**Question 4**")

                q4_col1, q4_col2 = st.columns(2)

                with q4_col1:
                    st.text_input("Rₑ",
                                  key = "q4_val")

                with q4_col2:
                    st.selectbox("Motivation",
                                 ("Full Credit","Partial Credit","No Credit"),
                                 index = None,
                                 placeholder="Make a selection...",
                                 key = "q4_mot")

            with st.expander("Question 5 to 8", expanded = False):

                st.markdown("**Question 5**")

                q5_col1, q5_col2 = st.columns(2)

                with q5_col1:
                    st.selectbox("Answer",
                                 ("Sabie River","Baviaanskloof River","Blank"),
                                 index = None,
                                 placeholder="Make a selection...",
                                 key = "q5_ans")
                with q5_col2:
                    st.selectbox("Motivation",
                                 ("Full Credit","Partial Credit","No Credit"),
                                 index = None,
                                 placeholder="Make a selection...",
                                 key = "q5_mot")

                st.markdown("**Question 6**")

                st.selectbox("Answer",
                             ("Convex","Uniform","Concave"),
                             index = None,
                             placeholder = "Make a selection...",
                             key = "q6")

                st.markdown("**Question 7**")

                q7_col1, q7_col2 = st.columns(2)

                with q7_col1:
                    st.selectbox("Profile",
                                 ("Convex","Uniform","Concave","Blank"),
                                 index = None,
                                 placeholder = "Make a selection...",
                                 key = "q7_profile")

                with q7_col2:
                    st.selectbox("Plan",
                                 ("Convex","Uniform","Concave","Blank"),
                                 index = None,
                                 placeholder = "Make a selection...",
                                 key = "q7_plan")

                st.markdown("**Question 8**")
                st.markdown("*Question 8 (a)*")

                q8a_col1, q8a_col2, q8a_col3 = st.columns(3)

                with q8a_col1:
                    st.text_input("Drakensberg Foothills",
                                  key = "q8a_dra_val")

                with q8a_col2:
                    st.text_input("Cape Fold Belt",
                                  key = "q8a_cap_val")

                with q8a_col3:
                    st.selectbox("Motivation",
                                 ("Full Credit","Partial Credit","No Credit"),
                                 index=None,
                                 placeholder="Make a selection...",
                                 key = "q8a_mot")

                st.markdown("*Question 8 (b)*")

                q8b_col1, q8b_col2 = st.columns(2)

                with q8b_col1:
                    st.selectbox("Answer",
                                 ("Drakensberg Foothills","Cape Fold Belt","Blank"),
                                 index=None,
                                 placeholder="Make a selection...",
                                 key = "q8b_ans")

                with q8b_col2:
                    st.selectbox("Motivation",
                                 ("Full Credit","Partial Credit","No Credit"),
                                 index=None,
                                 placeholder="Make a selection...",
                                 key = "q8b_mot")

            col2_a, col2_b, col2_c = st.columns(3)

            with col2_a:
                st.button("Grade", on_click=grade_submission)

    with tab_2:

        with st.expander("Question 1", expanded = False):
            q1_sol = st.session_state["question_1"]["solution"]
            interval = round(q1_sol["shelterbelt_interval"],4)
            q1_fc = round(q1_sol["full_credit"], 4)
            q1_pc = round(q1_sol["partial_credit"], 4)
            
            st.markdown(f"""
            - Shelterbelt interval: {interval} m
            - Full credit: ± {q1_fc}
            - Partial credit: ± {q1_pc}
            """)
            

        with st.expander("Question 2", expanded = False):
            q2_sol = st.session_state["question_2"]["solution"]
            q2a = q2_sol["year_3"]["cross_sectional_area"]
            q2a_fc = q2_sol["year_3"]["full_credit"]
            q2a_pc = q2_sol["year_3"]["partial_credit"]
            q2b = q2_sol["part_b"]["ans"]
            q2c = q2_sol["part_c"]["motivation"]

            st.markdown(f"""
            **Question 2a)**
            - Cross sectional area: {q2a} cm²
            - Full credit: ± {q2a_fc}
            - Partial credit: ± {q2a_pc}
            """)

            st.markdown(f"""
            **Question 2b)**
            - Answer: {q2b}
            """)

            st.markdown(f"""
            **Question 2c)**
            {q2c}
            """)
            

        with st.expander("Question 3", expanded = False):
            q3_sol = st.session_state["question_3"]["solution"]
            q3_ans = round(q3_sol["sinuosity"], 4)
            q3_fc = round(q3_sol["full_credit"], 4)
            q3_pc = round(q3_sol["partial_credit"], 4)
            q3_meandering = q3_sol["meandering"]

            st.markdown(f"""
            - Sinuosity: {q3_ans}
            - Full credit: ± {q3_fc}
            - Partial credit: ± {q3_pc}
            """)

            st.markdown(f"""
            {q3_meandering}
            """)

        with st.expander("Question 4", expanded = False):
            q4_sol = st.session_state["question_4"]["solution"]
            q4_re = q4_sol["reynolds_number"]
            q4_fc = q4_sol["full_credit"]
            q4_pc = q4_sol["partial_credit"]
            q4_ans = q4_sol["answer"]

            st.markdown(f"""
            - Reynold's number: {q4_re}
            - Full credit: ± {q4_fc}
            - Partial credit: ± {q4_pc}
            """)

            st.markdown(f"""
            {q4_ans}
            """)

        with st.expander("Question 5", expanded = False):
            q5_sol = st.session_state["question_5"]["solution"]
            q5_sab = round(q5_sol["river_1"]["discharge"], 4)
            q5_sab_fc = round(q5_sol["river_1"]["full_credit"], 4)
            q5_sab_pc = round(q5_sol["river_1"]["partial_credit"], 4)

            q5_bav = round(q5_sol["river_2"]["discharge"], 4)
            q5_bav_fc = round(q5_sol["river_2"]["full_credit"], 4)
            q5_bav_pc = round(q5_sol["river_2"]["partial_credit"], 4)

            q5_ans = q5_sol["answer"]
            q5_mot = q5_sol["motivation"]

            st.markdown(f"""
            **Sabie River**
            - Discharge: {q5_sab} m³/s
            - Full credit: ± {q5_sab_fc}
            - Partial credit: ± {q5_sab_pc}
            """)

            st.markdown(f"""
            **Baviaanskloof River**
            - Discharge: {q5_bav} m³/s
            - Full credit: ± {q5_bav_fc}
            - Partial credit: ± {q5_bav_pc}
            """)

            st.markdown(f"""
            The {q5_ans}. {q5_mot}
            """)

        with st.expander("Question 6", expanded = False):
            q6_sol = st.session_state["question_6"]["solution"]
            q6_ans = q6_sol["slope_unit"]

            st.markdown(f"""
            - Slope unit: {q6_ans} slope
            """)

        with st.expander("Question 7", expanded = False):
            q7_sol = st.session_state["question_7"]["solution"]
            q7_profile = q7_sol["slope_form"]["profile"]
            q7_plan = q7_sol["slope_form"]["plan"]

            st.markdown(f"""
            - Profile: {q7_profile}
            - Plan: {q7_plan}
            """)

        with st.expander("Question 8", expanded = False):
            q8_sol = st.session_state["question_8"]["solution"]

            q8_dra = round(q8_sol["site_1"]["downslope_force"], 4)
            q8_dra_fc = round(q8_sol["site_1"]["full_credit"], 4)
            q8_dra_pc = round(q8_sol["site_1"]["partial_credit"], 4)

            q8_cap = round(q8_sol["site_1"]["downslope_force"], 4)
            q8_cap_fc = round(q8_sol["site_1"]["full_credit"], 4)
            q8_cap_pc = round(q8_sol["site_1"]["partial_credit"], 4)

            q8a_ans = q8_sol["part_a"]["answer"]
            q8a_mot = q8_sol["part_a"]["motivation"]

            q8b_ans = q8_sol["part_b"]["answer"]
            q8b_mot = q8_sol["part_b"]["motivation"]

            st.markdown(f"""
            **Drakensberg Foothills***
            - Downslope force: {q8_dra} N
            - Full credit: {q8_dra_fc}
            - Partial credit: {q8_dra_pc}
            """)

            st.markdown(f"""
            **Cape Fold Mountains***
            - Downslope force: {q8_cap} N
            - Full credit: {q8_cap_fc}
            - Partial credit: {q8_cap_pc}
            """)

            st.markdown(f"""
            The {q8a_ans}. {q8a_mot}
            """)

            st.markdown(f"""
            {q8b_ans}. {q8b_mot}
            """)

                
            
            
