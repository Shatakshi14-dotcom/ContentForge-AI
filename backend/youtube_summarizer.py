from urllib.parse import urlparse, parse_qs

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
)

from google import genai

# ==========================
# GEMINI
# ==========================

client = genai.Client(
    api_key="GEMINI_API_KEY"
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
        [item.text for item in transcript]
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
    Create detailed study notes from this transcript.

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
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    print("\nSUMMARY:\n")
    print(response.text)
    with open("summary.txt", "w", encoding="utf-8") as f:
     f.write(response.text)

    print("\nSummary saved to summary.txt")
except TranscriptsDisabled:
    print("This video has no subtitles available.")

except NoTranscriptFound:
    print("No transcript found for this video.")

except TranscriptsDisabled:
    print(
        "\nERROR: Subtitles are disabled for this video."
    )

except NoTranscriptFound:
    print(
        "\nERROR: No transcript available."
    )

except KeyError:
    print(
        "\nERROR: Invalid YouTube URL."
    )

except Exception as e:
    print("\nUNEXPECTED ERROR:")
    print(e)
    