import os
import json
from dotenv import load_dotenv
import streamlit as st
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import FAISS
from langchain.embeddings import OpenAIEmbeddings
from langchain.chat_models import ChatOpenAI
from langchain.schema.output_parser import StrOutputParser
from langchain.prompts import ChatPromptTemplate

load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

st.set_page_config(page_title="YouTube AI Summarizer & Quiz Generator")
st.title("YouTube Summarizer and Quiz Generator")
st.write("Paste a YouTube URL below to summarize the video and generate a quiz.")


def extract_video_id(url: str):
    """Extracts the video ID from full YouTube URLs or youtu.be short links."""
    parsed = urlparse(url)

    # transcript api requires only the video id (part after youtube/ or v=)
    if parsed.hostname in ["www.youtube.com", "youtube.com"]:
        return parse_qs(parsed.query).get("v", [None])[0]

    if parsed.hostname == "youtu.be":
        return parsed.path.lstrip("/")

    return None


def fetch_transcript(video_id: str) -> str:
    """Fetches combined transcript text from a YouTube video."""
    transcript = YouTubeTranscriptApi.get_transcript(video_id)
    return " ".join([t["text"] for t in transcript])


def chunk_text(text: str):
    """Splits transcript into overlapping chunks suitable for embeddings."""
    # uses langchain's recursivecharactertextsplitter to create chunks of 1000 chars
    # and 150 char overlap to make embeddings work better
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    return splitter.split_text(text)


def build_faiss_index(chunks):
    """Builds a FAISS vector store from text chunks using OpenAI embeddings."""
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    # faiss allows semantic search, the system retrieves only relevant parts of transcript
    return FAISS.from_texts(chunks, embedding=embeddings)


def retrieve_relevant_chunks(query: str, store: FAISS, k: int = 5):
    """Finds top-k transcript chunks semantically related to the query."""
    # converts query into embedding, faiss compares it against stored embeddings, return best match chunks
    return store.similarity_search(query, k=k)


def summarize_chunks(chunks: list) -> str:
    """Summarizes transcript segments using GPT."""
    model = ChatOpenAI(model="gpt-5.1") 
    
    prompt = ChatPromptTemplate.from_template("""
    Summarize the following YouTube transcript content clearly for a college student studying for finals.
    Focus on the main ideas, structure, and key takeaways:

    {content}
    """)

    # joins selected chunks together
    chain = prompt | model | StrOutputParser()
    combined = "\n\n".join(chunks)

    return chain.invoke({"content": combined})


def generate_quiz_from_chunks(chunks: list, num_questions: int = 5):
    """
    Generates a structured multiple-choice quiz from transcript chunks.

    Returns strict JSON with:
      - question text
      - four choices
      - correct answer label
    """
    model = ChatOpenAI(model="gpt-5.1")

    # uses to chat to output json, parses json into python dict.
    prompt = ChatPromptTemplate.from_template("""
    Create a quiz based on the following transcript content.
    Generate {num_questions} multiple-choice questions with:
    - A clear question
    - Four answer choices (A, B, C, D)
    - Correct answer labeled with the letter only

    Format the result as JSON:

    {{
      "questions": [
        {{
          "question": "string",
          "choices": ["A text", "B text", "C text", "D text"],
          "answer": "A"
        }}
      ]
    }}

    Transcript:
    {content}
    """)

    chain = prompt | model | StrOutputParser()
    combined = "\n\n".join(chunks)

    raw = chain.invoke({"content": combined, "num_questions": num_questions})

    try:
        return json.loads(raw)
    except:
        return {"questions": []}

# drivers for quiz/summarizing video
def summarize_video_pipeline(video_id: str):
    """Full video summarization workflow."""
    transcript = fetch_transcript(video_id)
    chunks = chunk_text(transcript)
    store = build_faiss_index(chunks)

    retrieved = retrieve_relevant_chunks("summary of full video", store, k=5)
    retrieved_texts = [d.page_content for d in retrieved]

    return summarize_chunks(retrieved_texts)


def quiz_pipeline(video_id: str, num_questions: int = 5):
    """Full quiz generation workflow."""
    transcript = fetch_transcript(video_id)
    chunks = chunk_text(transcript)
    store = build_faiss_index(chunks)

    retrieved = retrieve_relevant_chunks("quiz from full content", store, k=5)
    retrieved_texts = [d.page_content for d in retrieved]

    return generate_quiz_from_chunks(retrieved_texts, num_questions)


# streamlit ui

youtube_url = st.text_input("YouTube Video URL")

if st.button("Summarize Video"):
    if not youtube_url:
        st.error("Please enter a YouTube URL.")
    else:
        video_id = extract_video_id(youtube_url)

        if not video_id:
            st.error("Invalid YouTube URL.")
        else:
            try:
                with st.spinner("Generating summary..."):
                    summary = summarize_video_pipeline(video_id)

                st.subheader("Summary")
                st.write(summary)

            except Exception as e:
                st.error(f"Error: {str(e)}")
                st.info("This video may not have a transcript.")


st.write("---")

num_q = st.number_input("Number of quiz questions", min_value=3, max_value=15, value=5)

if st.button("Generate Quiz"):
    if not youtube_url:
        st.error("Please enter a YouTube URL.")
    else:
        video_id = extract_video_id(youtube_url)

        if not video_id:
            st.error("Invalid YouTube URL.")
        else:
            try:
                with st.spinner("Generating quiz..."):
                    quiz = quiz_pipeline(video_id, num_q)

                st.subheader("Quiz")

                for i, q in enumerate(quiz["questions"], start=1):
                    st.markdown(f"**{i}. {q['question']}**")
                    st.write(f"A. {q['choices'][0]}")
                    st.write(f"B. {q['choices'][1]}")
                    st.write(f"C. {q['choices'][2]}")
                    st.write(f"D. {q['choices'][3]}")
                    st.markdown(f"**Answer: {q['answer']}**")
                    st.write("")

            except Exception as e:
                st.error(f"Error: {str(e)}")
                st.info("Some videos do not support AI quiz generation due to transcript issues.")
