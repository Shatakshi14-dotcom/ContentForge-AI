
import os
from urllib.parse import urlparse, parse_qs

from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
)

from google import genai

# ==========================
# LOAD ENV VARIABLES
# ==========================

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

# ==========================
# EXTRACT VIDEO ID
# ==========================

def get_video_id(url):

    if "youtu.be" in url:
        return url.split("/")[-1].split("?")[0]

    parsed = urlparse(url)

    return parse_qs(parsed.query)["v"][0]


# ==========================
# MAIN
# ==========================

url = input("Paste YouTube URL: ")

try:

    video_id = get_video_id(url)

    print("Video ID:", video_id)

    api = YouTubeTranscriptApi()

    transcript = api.fetch(video_id)

    text = " ".join(
        item.text for item in transcript
    )

    print("Transcript fetched successfully")
    print("Length:", len(text))

    print("\nChoose output type:")
    print("1. Summary")
    print("2. Study Notes")
    print("3. Social Media Content")

    choice = input("Enter choice (1/2/3): ")

    if choice == "1":

        prompt = f"""
        Summarize the following transcript in 5 bullet points.

        Transcript:
        {text}
        """

    elif choice == "2":

        prompt = f"""
        Create detailed study notes.

        Include:
        - Key ideas
        - Important examples
        - Actionable takeaways
        - Final summary

        Transcript:
        {text}
        """

    elif choice == "3":

        prompt = f"""
        From this transcript create:

        - 5 tweet ideas
        - 3 LinkedIn posts
        - 10 content hooks

        Transcript:
        {text}
        """

    else:

        prompt = f"""
        Summarize the following transcript.

        Transcript:
        {text}
        """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    print("\nRESULT:\n")
    print(response.text)

    with open(
        "summary.txt",
        "w",
        encoding="utf-8"
    ) as f:

        f.write(response.text)

    print("\nSummary saved to summary.txt")

except TranscriptsDisabled:

    print("This video has no subtitles available.")

except NoTranscriptFound:

    print("No transcript found for this video.")

except KeyError:

    print("Invalid YouTube URL.")

except Exception as e:

    print("\nUnexpected error:")
    print(e)

