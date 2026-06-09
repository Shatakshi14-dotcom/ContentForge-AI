from flask import session, redirect
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)
from flask import Flask, render_template, request, send_file
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound
)

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

from dotenv import load_dotenv
from pypdf import PdfReader
from docx import Document
from newspaper import Article
from urllib.parse import urlparse, parse_qs
import sqlite3
import pytesseract
from PIL import Image
import google.generativeai as genai
import os
from flask import redirect
chat_history = []
app = Flask(
    __name__,
    template_folder="../frontend/templates",
    static_folder="../frontend/static"
)


UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

load_dotenv()
app.secret_key = "contentforge_super_secret_key"

genai.configure(
    api_key=os.getenv("GEMINI_API_KEY")
)

model = genai.GenerativeModel("gemini-2.5-flash")

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

latest_output = ""


def get_video_id(url):

    if "youtu.be" in url:
        return url.split("/")[-1].split("?")[0]

    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    if "v" in query:
        return query["v"][0]

    return None


@app.route("/")
def home():

    global latest_output

    if "user_id" not in session:
        return redirect("/login")

    return render_template(
        "index.html",
        summary=latest_output,
        username=session.get("username"),
        chat_history=chat_history
    )


@app.route("/summarize", methods=["POST"])
def summarize():

    global latest_output

    url = request.form.get("url")
    pdf_file = request.files.get("pdf_file")
    raw_text = request.form.get("raw_text")
    question = request.form.get("question")
    mode = request.form.get("mode", "summary")

    try:

        # ========= RAW TEXT =========

        if raw_text and raw_text.strip() != "":

            text = raw_text

        # ========= PDF / DOCX =========

        elif pdf_file and pdf_file.filename != "":

            filepath = os.path.join(
                app.config["UPLOAD_FOLDER"],
                pdf_file.filename
            )

            pdf_file.save(filepath)

            text = ""

            # PDF
            if filepath.endswith(".pdf"):

                reader = PdfReader(filepath)

                for page in reader.pages:

                    extracted = page.extract_text()

                    if extracted:
                        text += extracted

            # DOCX
            elif filepath.endswith(".docx"):

                document = Document(filepath)

                for paragraph in document.paragraphs:

                    text += paragraph.text + "\n"

        # ========= BLOG URL =========

        elif url and "youtube.com" not in url and "youtu.be" not in url:

            article = Article(url)

            article.download()
            article.parse()

            text = article.text

        # ========= YOUTUBE =========

        else:

            video_id = get_video_id(url)

            if not video_id:
                raise Exception("Invalid YouTube URL")

            api = YouTubeTranscriptApi()

            transcript = api.fetch(video_id)

            text = " ".join(
                item.text for item in transcript
            )

        # ========= CONTENT MODES =========
        if question and question.strip() != "":

         prompt = f"""
    Answer the following question ONLY using the provided content.

    Content:
    {text}

    Question:
    {question}
    """
        elif mode == "summary":

            prompt = f"""
            Summarize this content in 5 bullet points.

            Content:
            {text}
            """

        elif mode == "notes":

            prompt = f"""
            Create detailed study notes.

            Include:
            - Main concepts
            - Examples
            - Key takeaways
            - Final summary

            Content:
            {text}
            """

        elif mode == "tweets":

            prompt = f"""
            Create:
            - 5 tweet ideas
            - 10 viral hooks

            Content:
            {text}
            """

        elif mode == "linkedin":

            prompt = f"""
            Create 3 professional LinkedIn posts.

            Content:
            {text}
            """

        elif mode == "blog":

            prompt = f"""
            Write a detailed blog article.

            Include:
            - Title
            - Introduction
            - Headings
            - Conclusion

            Content:
            {text}
            """

        else:

            prompt = f"""
            Summarize this content.

            Content:
            {text}
            """

        response = model.generate_content(prompt)

        summary = response.text
        chat_history.append({
    "user": question if question else mode,
    "ai": summary
})

        latest_output = summary

        conn = sqlite3.connect("contentforge.db")
        cursor = conn.cursor()

        cursor.execute(
       "INSERT INTO history(mode, output) VALUES (?, ?)",
       (mode, summary)
)

        conn.commit()
        conn.close()

    except TranscriptsDisabled:

        summary = "Subtitles are disabled for this video."

    except NoTranscriptFound:

        summary = "No transcript found."

    except Exception as e:

        summary = f"Error: {e}"

    return render_template(
        "index.html",
        summary=summary
    )


@app.route("/download_pdf")
def download_pdf():

    global latest_output

    pdf = SimpleDocTemplate("output.pdf")

    styles = getSampleStyleSheet()

    story = []

    paragraphs = latest_output.split("\n")

    for line in paragraphs:

        story.append(
            Paragraph(line, styles["BodyText"])
        )

        story.append(
            Spacer(1, 12)
        )

    pdf.build(story)

    return send_file(
        "output.pdf",
        as_attachment=True
    )
@app.route("/history")
def history():

    search = request.args.get("search", "")

    conn = sqlite3.connect("contentforge.db")

    cursor = conn.cursor()

    if search:

        cursor.execute(
            """
            SELECT * FROM history
            WHERE mode LIKE ? OR output LIKE ?
            ORDER BY id DESC
            """,
            (f"%{search}%", f"%{search}%")
        )

    else:

        cursor.execute(
            "SELECT * FROM history ORDER BY id DESC"
        )

    records = cursor.fetchall()

    conn.close()

    return render_template(
        "history.html",
        history=records,
        search=search
    )

    cursor.execute(
        "SELECT * FROM history ORDER BY id DESC"
    )

    records = cursor.fetchall()

    conn.close()

    return render_template(
        "history.html",
        history=records
    )
@app.route("/delete/<int:id>")
def delete_history(id):

    conn = sqlite3.connect("contentforge.db")

    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM history WHERE id=?",
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect("/history")
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        hashed_password = generate_password_hash(password)

        conn = sqlite3.connect("contentforge.db")
        cursor = conn.cursor()

        try:

            cursor.execute(
                """
                INSERT INTO users(username, password)
                VALUES (?, ?)
                """,
                (username, hashed_password)
            )

            conn.commit()

            return redirect("/login")

        except:

            return "Username already exists."

        finally:

            conn.close()

    return render_template("register.html")
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("contentforge.db")
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM users
            WHERE username = ?
            """,
            (username,)
        )

        user = cursor.fetchone()

        conn.close()

        if user and check_password_hash(
            user[2],
            password
        ):

            session["user_id"] = user[0]
            session["username"] = user[1]

            return redirect("/")

        return "Invalid username or password."

    return render_template("login.html")
@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")
if __name__ == "__main__":
    app.run(debug=True)