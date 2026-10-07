import json
import re
from datetime import datetime
from ollama import chat
from ddgs import DDGS

# -----------------------------
# Memory
# -----------------------------

def load_memory():

    try:

        with open("memory.json", "r") as file:
            return json.load(file)

    except FileNotFoundError:

        return []


def retrieve_memory(question):

    memories = load_memory()

    question_lower = question.lower()

    for memory in memories:

        key = memory["key"].lower()

        if key in question_lower:

            return memory["value"]

    return None


# -----------------------------
# Calculator
# -----------------------------

def calculator(a, b, operation):

    try:

        a = float(a)
        b = float(b)

        if operation == "add":
            return a + b

        elif operation == "subtract":
            return a - b

        elif operation == "multiply":
            return a * b

        elif operation == "divide":

            if b == 0:
                return "Cannot divide by zero"

            return a / b

        else:
            return "Unknown operation"

    except (ValueError, TypeError):

        return "Invalid numbers"

# -----------------------------
# Time Tool
# -----------------------------

def get_time():
    return datetime.now().strftime("%H:%M:%S")

# -----------------------------
# Web Search Tool
# -----------------------------

def web_search(query):

    try:

        results = []

        with DDGS() as ddgs:

            search_results = ddgs.text(
                query,
                max_results=5
            )

            for result in search_results:

                results.append(
                    f"Title: {result['title']}\n"
                    f"URL: {result['href']}\n"
                    f"Description: {result['body']}"
                )

        if not results:
            return "No search results found."

        return "\n\n".join(results)

    except Exception as e:

        return f"Web search failed: {e}"

# -----------------------------
# Intent Detection
# -----------------------------

def detect_intent(question):

    response = chat(
        model="llama3.2",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an intent classifier for an AI agent. "
                    "Decide whether the user needs current or online "
                    "information from the internet.\n\n"
                    "Return ONLY one of these two words:\n"
                    "WEB_SEARCH\n"
                    "NORMAL\n\n"
                    "Choose WEB_SEARCH when the user asks to search, "
                    "find, look up, check online, browse the internet, "
                    "get latest/current information, news, live information, "
                    "or information that may have changed recently.\n"
                    "Choose NORMAL for general questions, calculations, "
                    "memory questions, greetings, explanations, or casual conversation."
                )
            },
            {
                "role": "user",
                "content": question
            }
        ]
    )

    intent = response.message.content.strip().upper()

    if "WEB_SEARCH" in intent:
        return "WEB_SEARCH"

    return "NORMAL"

# -----------------------------
# Ask Agent
# -----------------------------

def ask_agent(question):

    # -----------------------------
    # Check memory first
    # -----------------------------

    memory = retrieve_memory(question)

    if memory:

        if "name" in question.lower():

            return f"Your name is {memory}."

        return f"I remember: {memory}."


    # -----------------------------
    # Prepare question
    # -----------------------------

    question_lower = question.lower()


    # -----------------------------
    # Check current time
    # -----------------------------

    if "time" in question_lower:

        current_time = get_time()

        return f"The current time is {current_time}."


    # -----------------------------
    # Check calculation
    # -----------------------------

    numbers = re.findall(
        r"\d+(?:\.\d+)?",
        question
    )

    if len(numbers) >= 2:

        a = float(numbers[0])
        b = float(numbers[1])

        if "*" in question or "multiply" in question_lower:

            result = calculator(
                a,
                b,
                "multiply"
            )

            return f"The result of {a:g} * {b:g} is {result:g}."

        elif "+" in question or "add" in question_lower:

            result = calculator(
                a,
                b,
                "add"
            )

            return f"The result of {a:g} + {b:g} is {result:g}."

        elif "-" in question or "subtract" in question_lower:

            result = calculator(
                a,
                b,
                "subtract"
            )

            return f"The result of {a:g} - {b:g} is {result:g}."

        elif "/" in question or "divide" in question_lower:

            result = calculator(
                a,
                b,
                "divide"
            )

            if result == "Cannot divide by zero":

                return (
                    "The calculation failed because "
                    "division by zero is not allowed."
                )

            return f"The result of {a:g} / {b:g} is {result:g}."


    # -----------------------------
    # AI Intent Detection
    # -----------------------------

    intent = detect_intent(question)


    # -----------------------------
    # Web Search
    # -----------------------------

    if intent == "WEB_SEARCH":

        search_result = web_search(question)

        # Check whether web search failed
        if search_result.startswith("Web search failed"):
            return (
                "I couldn't complete the web search right now. "
                "Please try again."
            )

        # Check whether no results were found
        if search_result == "No search results found.":
            return (
                "I couldn't find any useful search results "
                "for your question."
            )

        response = chat(
            model="llama3.2",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an AI assistant. "
                        "Use the web search results provided below "
                        "to answer the user's question clearly. "
                        "Do not invent information that is not present "
                        "in the search results."
                    )
                },
                {
                    "role": "user",
                    "content": (
                        f"User question: {question}\n\n"
                        f"Web search results:\n"
                        f"{search_result}\n\n"
                        "Give a clear and useful answer."
                    )
                }
            ]
        )

        return response.message.content


    # -----------------------------
    # Normal AI Response
    # -----------------------------

    response = chat(
        model="llama3.2",
        messages=[
            {
                "role": "user",
                "content": question
            }
        ]
    )

    return response.message.content