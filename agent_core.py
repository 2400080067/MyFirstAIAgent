import base64
import binascii
from dataclasses import dataclass
import json
import re
import os
from datetime import datetime

try:
    from ollama import chat
except ImportError:  # pragma: no cover - dependency may be absent until install
    chat = None

try:
    from ddgs import DDGS
except ImportError:  # pragma: no cover - dependency may be absent until install
    DDGS = None

try:
    from google import genai
except ImportError:  # pragma: no cover - dependency may be absent until install
    genai = None


def get_gemini_client():
    if genai is None:
        raise RuntimeError(
            "The package 'google-genai' is not installed. "
            "Run: pip install google-genai"
        )

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Add it to your environment "
            "before using the Gemini features."
        )

    return genai.Client(api_key=api_key)


gemini_client = None

IMAGE_GENERATION_MODEL = "gemini-nano-banana-2.1"


@dataclass
class GeneratedImage:
    prompt: str
    image_bytes: bytes
    mime_type: str


CODING_ASSISTANT_PROMPT = (
    "For coding-platform problems such as LeetCode, HackerRank, or Codeforces, "
    "support the programming language the user requests without limiting the "
    "user to a fixed language list. Check the current request and conversation "
    "history for both the problem statement and target language. If either is "
    "missing, ask for the missing information before giving a solution; never "
    "silently choose a language. When both are available, provide an idiomatic, "
    "platform-compatible solution in that language, explain the approach and "
    "correctness briefly, state time and space complexity, and account for "
    "constraints and edge cases. Do not claim that code was executed or tested."
)

PERSONALITY_PROMPT = (
    "You are Reyans, a friendly, helpful, and polished personal AI assistant. "
    "Answer clearly and warmly, keep responses concise but useful, and be a bit "
    "professional without sounding robotic. Use memory naturally when relevant, "
    "help with everyday tasks, explain ideas simply, and stay honest when you do "
    "not know something. "
    f"{CODING_ASSISTANT_PROMPT}"
)

# -----------------------------
# Memory
# -----------------------------

def load_memory(memory_file="memory.json"):

    try:

        with open(memory_file, "r", encoding="utf-8") as file:
            return json.load(file)

    except (FileNotFoundError, json.JSONDecodeError, OSError):

        return []


def retrieve_memory(question, memory_file="memory.json"):

    memories = load_memory(memory_file)

    question_lower = question.lower()

    for memory in memories:

        key = memory["key"].lower()

        if key in question_lower:

            return memory["value"]

    return None


def is_image_generation_request(question):
    if re.match(r"\s*(?:how|what|why|explain|describe)\b", question, re.IGNORECASE):
        return False

    if re.search(
        r"\b(?:draw|paint|illustrate)\b",
        question,
        re.IGNORECASE,
    ):
        return True

    has_generation_action = re.search(
        r"\b(?:generate|create|make|draw|paint|render|design|illustrate)\b",
        question,
        re.IGNORECASE,
    )
    has_image_subject = re.search(
        r"\b(?:image|picture|photo|illustration|artwork|wallpaper|logo|graphic)\b",
        question,
        re.IGNORECASE,
    )
    return bool(has_generation_action and has_image_subject)


def generate_image(prompt, api_key=None):
    if genai is None:
        raise RuntimeError(
            "Image generation requires the 'google-genai' package. "
            "Run: pip install google-genai"
        )

    api_key = api_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Image generation needs a Gemini API key. Set GEMINI_API_KEY "
            "in your environment or Streamlit secrets."
        )

    try:
        with genai.Client(api_key=api_key) as client:
            interaction = client.interactions.create(
                model=IMAGE_GENERATION_MODEL,
                input=prompt,
            )
    except Exception as exc:
        raise RuntimeError(f"Gemini image generation request failed: {exc}") from exc

    output_image = getattr(interaction, "output_image", None)
    encoded_data = getattr(output_image, "data", None)
    if not encoded_data:
        raise RuntimeError(
            "Gemini returned no image. Try a different prompt or check "
            "whether image generation is available for your API key."
        )

    try:
        image_bytes = base64.b64decode(encoded_data, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise RuntimeError("Gemini returned invalid image data.") from exc

    mime_type = getattr(output_image, "mime_type", None) or "image/png"
    if mime_type not in {"image/png", "image/jpeg", "image/webp"}:
        raise RuntimeError(f"Gemini returned an unsupported image type: {mime_type}")

    return GeneratedImage(
        prompt=prompt,
        image_bytes=image_bytes,
        mime_type=mime_type,
    )


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

def gemini_calculator(a, b, operation):

    return calculator(a, b, operation)

gemini_tools = [
    {
        "function_declarations": [
            {
                "name": "gemini_calculator",
                "description": "Performs addition, subtraction, multiplication, or division.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "a": {
                            "type": "number",
                            "description": "First number"
                        },
                        "b": {
                            "type": "number",
                            "description": "Second number"
                        },
                        "operation": {
                            "type": "string",
                            "description": "Operation: add, subtract, multiply, or divide"
                        }
                    },
                    "required": [
                        "a",
                        "b",
                        "operation"
                    ]
                }
            },
            {
                "name": "get_time",
                "description": "Returns the current local time.",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "web_search",
                "description": "Searches the internet and returns current or online information.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query to use on the internet"
                        }
                    },
                    "required": [
                        "query"
                    ]
                }
            }
        ]
    }
]

# -----------------------------
# Web Search Tool
# -----------------------------

def web_search(query):

    try:

        if DDGS is None:
            return "Web search failed: ddgs is not installed. Run: pip install ddgs"

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

    if chat is None:
        return "NORMAL"

    try:
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
    except Exception:
        return "NORMAL"

    intent = response.message.content.strip().upper()

    if "WEB_SEARCH" in intent:
        return "WEB_SEARCH"

    return "NORMAL"

# -----------------------------
# Ask Agent
# -----------------------------

def ask_agent(
    question,
    conversation_history=None,
    memory_file="memory.json",
    gemini_api_key=None,
):

    conversation_history = conversation_history or []

    if is_image_generation_request(question):
        try:
            return generate_image(question, api_key=gemini_api_key)
        except RuntimeError as exc:
            return f"I couldn't generate the image. {exc}"

    # -----------------------------
    # Check memory first
    # -----------------------------

    memory = retrieve_memory(question, memory_file)

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

        if chat is None:
            return "The local Ollama model is not available. Install the 'ollama' package and start the Ollama service."

        try:
            response = chat(
                model="llama3.2",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"{PERSONALITY_PROMPT} "
                            "Use the web search results provided below "
                            "to answer the user's question clearly. "
                            "Do not invent information that is not present "
                            "in the search results."
                        )
                    },
                    *conversation_history,
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
        except Exception as exc:
            return f"I couldn't reach the local Ollama model: {exc}"


    # -----------------------------
    # Normal AI Response
    # -----------------------------

    if chat is None:
        return "The local Ollama model is not available. Install the 'ollama' package and start the Ollama service."

    try:
        response = chat(
            model="llama3.2",
            messages=[
                {
                    "role": "system",
                    "content": PERSONALITY_PROMPT
                },
                *conversation_history,
                {
                    "role": "user",
                    "content": question
                }
            ]
        )
        return response.message.content
    except Exception as exc:
        return f"I couldn't reach the local Ollama model: {exc}"

gemini_chat_history = []

def ask_gemini(question):
    question_lower = question.lower()

    gemini_chat_history.append({
        "role": "user",
        "content": question
    })

    link_words = [
        "give me links",
        "give me some links",
        "provide links",
        "provide me links",
        "useful links",
        "resources",
        "websites",
        "links to learn",
        "links for",
        "link to"
    ]

    wants_links = any(
        word in question_lower
        for word in link_words
    )

    if wants_links:

        search_query = question

        if len(gemini_chat_history) > 1:
            previous_message = gemini_chat_history[-2]["content"]

            search_query = previous_message + " " + question

        search_result = web_search(search_query)

        return search_result

    try:
        global gemini_client
        if gemini_client is None:
            gemini_client = get_gemini_client()

        prompt = (
            f"{PERSONALITY_PROMPT}\n\n"
            f"User question:\n{question}"
        )

        gemini_chat_history.append({
            "role": "user",
            "content": question
        })

        gemini_contents = ""

        for message in gemini_chat_history:
            if message["role"] == "user":
                gemini_contents += f"User: {message['content']}\n"
            else:
                gemini_contents += f"Assistant: {message['content']}\n"

        response = gemini_client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=gemini_contents,
            config={
                "tools": gemini_tools
            }
        )

    except RuntimeError as exc:
        return str(exc)
    except Exception as exc:
        return f"Gemini request failed: {exc}"

    # Check if Gemini wants to use a tool
    function_calls = getattr(response, "function_calls", None) or []
    if function_calls:

        call = response.function_calls[0]

        if call.name == "gemini_calculator":

            arguments = getattr(call, "args", {}) or {}

            result = gemini_calculator(
                arguments["a"],
                arguments["b"],
                arguments["operation"]
            )

            return f"The result is {result}."
        if call.name == "get_time":
            result = get_time()

            return f"The current time is {result}."
        if call.name == "web_search":
            arguments = getattr(call, "args", {}) or {}

            result = web_search(
                arguments["query"]
            )

            summary_response = gemini_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=f"""
        Summarize the following web search results for the user.

        User question:
        {question}

        Web search results:
        {result}

        Give a clear and simple answer.
        Mention the important information from the search results.
        Do not invent information that is not present in the results.
        """
            )

            return getattr(summary_response, "text", str(summary_response))

    answer = getattr(response, "text", "")

    gemini_chat_history.append({
        "role": "model",
        "content": answer
    })

    return answer