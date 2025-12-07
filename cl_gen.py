from openai import OpenAI
from dotenv import load_dotenv
import os
import streamlit as st
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from io import BytesIO

# Set up the page and title the Streamlit interface
st.set_page_config(page_title="Cover Letter Generator")
st.title("Cover Letter Generator")

# Load API key from the .env file
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# Function that asks the model to write the cover letter
def generate_cover_letter(contact_person, your_name, role, company_name, personal_experience, job_description):
    # This prompt gives the model some structure and asks it to avoid typical AI-sounding language
    prompt = f"""
    Write a polished, professional cover letter.

    To: {contact_person}
    From: {your_name}

    Job Role: {role}
    Company: {company_name}

    The candidate has experience in: {personal_experience}

    Tailor it to match this job description:
    {job_description}

    Please keep the tone clear and professional. Avoid awkward phrasing, unnecessary filler,
    em dashes, or anything that sounds obviously AI-generated.
    """

    response = client.chat.completions.create(
        model="gpt-5.1",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message["content"]

# function scores 
def get_ats_score(personal_experience, job_description):
    # First we ask the model to pull out the important keywords from the job description
    extract_prompt = f"""
    Pull out the 10 to 20 most important keywords or skills from this job description.
    Please return the results as a Python list of strings without additional explanation.

    Job description:
    {job_description}
    """

    response = client.chat.completions.create(
        model="gpt-5.1",
        messages=[{"role": "user", "content": extract_prompt}]
    )

    # The model sends back something like: ["Python", "API Development", ...]
    # We try to evaluate it into a list; if it fails, we fall back to an empty list.
    try:
        keywords = eval(response.choices[0].message["content"])
    except:
        keywords = []

    exp_lower = personal_experience.lower()

    # Determine what matches and what's missing
    matches = [kw for kw in keywords if kw.lower() in exp_lower]
    missing = [kw for kw in keywords if kw.lower() not in exp_lower]

    # Compute a simple percentage score based on the matches
    if keywords:
        score = int((len(matches) / len(keywords)) * 100)
    else:
        score = 0

    return score, matches, missing, keywords

# function turns generated letter into pdf
def generate_pdf(text):
    # We use a bytes buffer rather than writing straight to disk.
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)

    # Establish a starting text position and font
    text_object = c.beginText(40, 750)
    text_object.setFont("Times-Roman", 12)

    # Add the text line by line
    for line in text.split("\n"):
        text_object.textLine(line)

    c.drawText(text_object)
    c.save()

    buffer.seek(0)
    return buffer

# streamlit UI

st.subheader("Enter Your Information")

contact_person = st.text_input("Who is the letter addressed to?")
your_name = st.text_input("Your Name")
role = st.text_input("Job Role")
company_name = st.text_input("Company Name")
personal_experience = st.text_area("Your relevant experience")
job_description = st.text_area("Paste the job description")

# Button that triggers both the cover letter and ATS scoring
if st.button("Generate Cover Letter"):
    if not all([contact_person, your_name, role, company_name, personal_experience, job_description]):
        st.error("Please make sure all fields are filled out.")
    else:
        with st.spinner("Creating your cover letter..."):
            letter = generate_cover_letter(
                contact_person,
                your_name,
                role,
                company_name,
                personal_experience,
                job_description
            )

        with st.spinner("Analyzing your keyword match..."):
            score, matches, missing, keywords = get_ats_score(
                personal_experience,
                job_description
            )

        st.success("Your cover letter is ready.")

        # Show the letter text
        st.subheader("Your Cover Letter")
        st.write(letter)

        # Show ATS scoring info
        st.subheader("ATS Keyword Match Score")
        st.metric(label="Score", value=f"{score}%")

        st.write("Matched Keywords:")
        st.write(matches if matches else "None found")

        st.write("Missing Keywords:")
        st.write(missing if missing else "None missing")

        # Offer PDF download
        pdf_file = generate_pdf(letter)
        st.download_button(
            label="Download as PDF",
            data=pdf_file,
            file_name="cover_letter.pdf",
            mime="application/pdf"
        )
