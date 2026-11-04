from flask import Flask, render_template, request
import ollama
import sqlite3
import os
from dotenv import load_dotenv
from tavily import TavilyClient

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Tavily API
api_key = os.getenv("TAVILY_API_KEY")
tavily = TavilyClient(api_key=api_key)


# ---------------- DATABASE ---------------- #

def create_database():
    os.makedirs("database", exist_ok=True)

    conn = sqlite3.connect("database/tutorbot.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chats(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT,
            answer TEXT
        )
    """)

    conn.commit()
    conn.close()


# ---------------- WEB SEARCH ---------------- #

def search_web(question):
    result = tavily.search(
        query=question,
        max_results=3
    )
    return result


# ---------------- DETECT LIVE QUESTIONS ---------------- #

def is_current_question(question):

    keywords = [
        "today",
        "latest",
        "current",
        "news",
        "weather",
        "ipl",
        "score",
        "live",
        "cm",
        "chief minister",
        "prime minister",
        "president",
        "bitcoin",
        "stock",
        "price",
        "2026",
        "2027"
    ]

    question = question.lower()

    return any(word in question for word in keywords)


# ---------------- HOME ---------------- #

@app.route("/")
def home():
    return render_template("index.html")


# ---------------- CHAT ---------------- #

@app.route("/chat", methods=["GET", "POST"])
def chat():

    question = ""
    answer = ""

    if request.method == "POST":

        question = request.form.get("question", "").strip()

        if question:

            try:

                # Current affairs → Search Internet
                if is_current_question(question):

                    web = search_web(question)

                    if web.get("results"):

                        context = web["results"][0]["content"]

                        prompt = f"""
You are an intelligent AI assistant.

Using the latest information below, answer the user's question clearly.

Latest Information:
{context}

User Question:
{question}
"""

                        response = ollama.chat(
                            model="llama3.2",
                            messages=[
                                {
                                    "role": "user",
                                    "content": prompt
                                }
                            ]
                        )

                        answer = response["message"]["content"]

                    else:
                        answer = "Sorry, I couldn't find any recent information."

                # Normal Questions → Ollama
                else:

                    response = ollama.chat(
                        model="llama3.2",
                        messages=[
                            {
                                "role": "user",
                                "content": question
                            }
                        ]
                    )

                    answer = response["message"]["content"]

                # Save to database
                conn = sqlite3.connect("database/tutorbot.db")
                cursor = conn.cursor()

                cursor.execute(
                    "INSERT INTO chats(question,answer) VALUES(?,?)",
                    (question, answer)
                )

                conn.commit()
                conn.close()

            except Exception as e:
                answer = "Error: " + str(e)

    return render_template(
        "chat.html",
        question=question,
        answer=answer
    )


# ---------------- RUN ---------------- #

if __name__ == "__main__":
    create_database()
    app.run(debug=True)