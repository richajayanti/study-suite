from openai import OpenAI
from dotenv import load_dotenv
import os
import streamlit as st
from pypdf import PdfReader
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from io import BytesIO
import json

st.set_page_config(page_title="Cover Letter Generator")
st.title("Cover Letter Generator with Resume Parsing and ATS Optimization")

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def extract_resume_text(uploaded_file):
    """
    Extracts text from an uploaded résumé file.

    Accepts PDF or plain text files. For PDFs, each page is read using PdfReader
    and text is extracted if available. If the file is a .txt, the contents
    are decoded into a UTF-8 string.

    Returns:
        str: Combined raw text extracted from the uploaded file.
    """
    if uploaded_file is None:
        return ""

    # If the uploaded file is a PDF, extract text from each page.
    if uploaded_file.type == "application/pdf":
        reader = PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            # Some pages may return None, so we fall back to an empty string
            text += page.extract_text() or ""
        return text

    # For plain text files
    try:
        return uploaded_file.read().decode("utf-8", errors="ignore")
    except:
        return ""


def parse_resume_to_json(resume_text):
    """
    Converts raw resume text into structured JSON

    Sends the resume text to the OpenAI model and requests output in a strict JSON
    structure containing: skills, experience, achievements, education, and projects.
    If parsing fails, the function returns an empty structured template.

    Args:
        resume_text (str): Raw extracted résumé text.

    Returns:
        dict: A structured representation of résumé content.
    """
    prompt = f"""
    Extract structured résumé information from the text below.
    Return ONLY valid JSON in exactly this structure:

    {{
      "skills": [],
      "experience": [],
      "achievements": [],
      "education": [],
      "projects": []
    }}

    Projects may include personal, academic, research, capstone, or portfolio work.
    If the resume is missing a category, return an empty list for it.

    Resume text:
    {resume_text}
    """

    response = client.chat.completions.create(
        model="gpt-5.1",
        messages=[{"role": "user", "content": prompt}]
    )

    # Attempt to parse JSON. If it fails, return a clean default structure.
    try:
        parsed = json.loads(response.choices[0].message["content"])
    except:
        parsed = {
            "skills": [],
            "experience": [],
            "achievements": [],
            "education": [],
            "projects": []
        }

    return parsed


def generate_cover_letter(contact_person, your_name, role, company_name, resume_data, job_description):
    """
    Generates a personalized cover letter.

    Uses structured resume data (skills, experience, achievements, projects, education)
    and the job description to create a grounded, non-generic cover letter.
    The prompt encourages the model to integrate resume details meaningfully.

    Args:
        contact_person (str): Name of hiring manager or recipient.
        your_name (str): Applicant's name.
        role (str): Job role being applied for.
        company_name (str): Company name.
        resume_data (dict): Structured JSON resume data.
        job_description (str): Raw job description text.

    Returns:
        str: The generated cover letter text.
    """
    prompt = f"""
    Write a polished, professional cover letter.

    To: {contact_person}
    From: {your_name}

    Job Role: {role}
    Company: {company_name}

    Use the following résumé data:

    Skills:
    {resume_data["skills"]}

    Experience:
    {resume_data["experience"]}

    Achievements:
    {resume_data["achievements"]}

    Education:
    {resume_data["education"]}

    Projects:
    {resume_data["projects"]}

    The job description is:
    {job_description}

    Use the resume information to make the letter specific and grounded.
    Avoid generic AI phrasing or filler, and keep the tone professional.
    """

    response = client.chat.completions.create(
        model="gpt-5.1",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message["content"]


def get_ats_score(resume_data, job_description):
    """
    Computes an approximate ATS keyword match score.

    Extracts essential keywords from the job description using the model,
    then checks which of those keywords appear in the résumé content.
    The score is the percentage of matched keywords.

    Args:
        resume_data (dict): Parsed résumé data fields.
        job_description (str): Full job description text.

    Returns:
        tuple: (score_percentage, matched_keywords, missing_keywords)
    """
    # Combine resume content into a searchable text block
    resume_text = (
        " ".join(resume_data["skills"])
        + " "
        + " ".join(resume_data["experience"])
        + " "
        + " ".join(resume_data["projects"])
    ).lower()

    extract_prompt = f"""
    Extract the 10–20 most important keywords or skills from this job description.
    Return them as a Python list of strings only.

    Job description:
    {job_description}
    """

    response = client.chat.completions.create(
        model="gpt-5.1",
        messages=[{"role": "user", "content": extract_prompt}]
    )

    # Model returns a Python list as text, so eval is used cautiously
    try:
        keywords = eval(response.choices[0].message["content"])
    except:
        keywords = []

    matches = [kw for kw in keywords if kw.lower() in resume_text]
    missing = [kw for kw in keywords if kw.lower() not in resume_text]

    score = int((len(matches) / len(keywords)) * 100) if keywords else 0

    return score, matches, missing


def generate_pdf(letter_text):
    """
    Generates a PDF file from the cover letter text.

    Writes the content line-by-line onto a PDF canvas and stores the
    resulting file in a buffer for download through Streamlit.

    Args:
        letter_text (str): Cover letter text to write into the PDF.

    Returns:
        BytesIO: A buffer containing the generated PDF file.
    """
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)

    text_obj = c.beginText(40, 750)
    text_obj.setFont("Times-Roman", 12)

    # Each line is written individually to maintain formatting
    for line in letter_text.split("\n"):
        text_obj.textLine(line)

    c.drawText(text_obj)
    c.save()
    buffer.seek(0)
    return buffer


# Streamlit interface begins
st.subheader("Enter Information")

contact_person = st.text_input("Who is the letter addressed to?")
your_name = st.text_input("Your Name")
role = st.text_input("Job Role")
company_name = st.text_input("Company Name")

uploaded_resume = st.file_uploader("Upload your resume (PDF or text)", type=["pdf", "txt"])
job_description = st.text_area("Paste the job description")


if st.button("Generate Cover Letter"):
    if not all([contact_person, your_name, role, company_name, job_description]):
        st.error("Please fill out all fields and upload a résumé.")
    else:
        with st.spinner("Extracting résumé text..."):
            resume_text = extract_resume_text(uploaded_resume)

        with st.spinner("Parsing résumé into structured data..."):
            resume_data = parse_resume_to_json(resume_text)

        with st.spinner("Generating cover letter..."):
            letter = generate_cover_letter(
                contact_person,
                your_name,
                role,
                company_name,
                resume_data,
                job_description
            )

        with st.spinner("Computing ATS score..."):
            score, matches, missing = get_ats_score(resume_data, job_description)

        st.subheader("Your Cover Letter")
        st.write(letter)

        st.subheader("ATS Keyword Match Score")
        st.metric("Score", f"{score}%")
        st.write("Matched Keywords:", matches)
        st.write("Missing Keywords:", missing)

        pdf_file = generate_pdf(letter)
        st.download_button(
            label="Download as PDF",
            data=pdf_file,
            file_name="cover_letter.pdf",
            mime="application/pdf"
        )
