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

BASE_DIR = Path(__file__).resolve().parent.parent

@st.cache_data(show_spinner="Loading submission...", max_entries=3, scope = "session")
def load_submission(file_bytes: bytes):
    img_bytes = np.frombuffer(image.getvalue(), dtype=np.uint8)
    cv_img = cv.imdecode(img_bytes, cv.IMREAD_COLOR)

    _, disp_img = cv.imencode(".jpg",warped_img, [int(cv.IMWRITE_JPEG_QUALITY), 80])
    b64_str = base64.b64encode(disp_img).decode("utf-8")
    img_url = f"data:image/jpg;base64,{b64_str}"

    return cv_img, img_url

def next_submission():
    st.session_state["script_index"] += 1
    del st.session_state["graded_submission"]
    # ==============================

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
    st.subheader("Section A — Theory")

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
    surname, name, emplid = filename.split("_")
    st.session_state["student"] = f"{name} {surname} ({emplid})"

    img, img_url = load_submission(image.get.getvalue())

    col1, col2 = st.columns(2)

    with col1:
        custom_functions.submission_viewer(img_url)

    with col2:
        with st.expander("Student Details", expanded = False):
            st.markdown(f"""
            - *Name*: **{name}**
            - *Surname*: **{surname}**
            - *Student Number*: **{emplid}**
            - *Alignment Method*: **{method}**
            """)

        with st.expander("Questions 1 to 4 ", expanded = True):
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
                st.text_input("CSA", key = "q2a_val")
                st.selectbox("Biggest change in CSA",
                             ("2024 — 2025","2025 — 2026","Blank"),
                             index = None,
                             placeholder = "Make a selection ...",
                             key = "q2b")

            with q2_col2:
                st.selectbox("Units",
                             ("cm²", "None"),
                             index = None,
                             placeholder = "Make a selection...")
                st.selectbox("Motivation",
                             ("Full Credit","Partial Credit","No Credit"),
                             index = None,
                             placeholder = "Make a selection...")

            st.markdown("**Question 3**")

            q3_col1, q3_col2 = st.columns(2)

            with q3_col1:
                st.text_input("Answer", key = "q3_val")

            with q3_col1:
                st.selectbox("Motivation",
                             ("Full Credit","Partial Credit","No Credit"),
                             index = None,
                             placeholder="Make a selection...",
                             key = "q3_mot")

            st.markdown("**Question 4**")

            q4_col1, q4_col2 = st.columns(2)

            with q4_col1:
                st.text_input("Rₑ", key = "q4_val")

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
                              key = "q8db_val")

            with q8a_col2:
                st.text_input("Cape Fold Belt",
                              key = "q8cfb_val")

            with q8a_col3:
                st.selectbox("Motivation",
                             ("Full Credit","Partial Credit","No Credit"),
                             index=None,
                             placeholder="Make a selection...",
                             key = "q8a_mot")

            st.markdown("*Question 8 (a)*")

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
                             index=None.
                             placeholder="Make a selection...",
                             key = "q8b_mot")

                
            
            
