import streamlit as st

home_page = st.Page(
    "pages/home.py",
    title = "Dashboard",
    default = True
)

sec_a_1 = st.Page(
    "pages/section-a.py",
    title = "Section A"
)

sec_a_2 = st.Page(
    "pages/section-a-cont.py",
    title = "Section A (cont.)"
)

sec_b = st.Page(
    "pages/section-b.py",
    title = "Section B"
)

pages = st.navigation({
    "Home"            : [home_page],
    "Sections"      : [sec_a_1, sec_a_2, sec_b]
})

st.set_page_config(page_title="GGY Normal Exam", layout="wide")
pages.run()
