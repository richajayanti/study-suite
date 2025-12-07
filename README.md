# AI Productivity Toolkit

This repository contains two Streamlit applications designed to automate and simplify common writing and research tasks using OpenAI models and modern NLP tools.

The toolkit includes:

---

## Cover Letter Generator

Upload your resume (PDF or `.txt`) and a tech job description to generate a tailored cover letter based on your experiences.  
The tool parses your resume into relevant sections (skills, experience, education, projects, awards), integrates this information into the writing, and provides ATS keyword analysis with matched/missing keywords.  
The final letter can be downloaded as a PDF.

---

## YouTube Assistant

Paste a YouTube URL to automatically retrieve a video transcript, break it into semantic chunks, embed the chunks, and store them in a FAISS vector index.  
The app uses vector search to identify the most important parts of the video and generates a structured summary along with a customizable MCQ quiz.  
All processing runs locally with a clean Streamlit interface.

---

Both applications run locally and require an OpenAI API key.

---

## Installation

Clone the repository:

```bash
git clone https://github.com/yourusername/yourrepo.git
cd yourrepo
```

Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate   # macOS/Linux
venv\Scripts\activate      # Windows
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file in the project directory and add:

```
OPENAI_API_KEY=your_openai_api_key_here
```

---

## Running the Applications

### Cover Letter Generator
```bash
streamlit run cover_letter_app.py
```

### YouTube Assistant
```bash
streamlit run yt_app.py
```

---

## Project Structure

```
/cover_letter_app.py   - Cover letter generator application
/yt_app.py             - YouTube summarizer and quiz tool
requirements.txt
README.md
.env (not included)
```

---

## Notes

- The YouTube Assistant requires the video to have a publicly available transcript.  
- OpenAI usage costs depend on your API plan; smaller models can be used to keep usage reasonable.  
- Both apps are modular and can be extended with additional features.
