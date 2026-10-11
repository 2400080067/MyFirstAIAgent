import hashlib
import json
import os
from pathlib import Path
from datetime import datetime
from uuid import uuid4
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

from agent_core import GeneratedImage, ask_agent, load_memory


# =========================================================
# PAGE SETTINGS
# =========================================================

st.set_page_config(
    page_title="Reyans AI Assistant",
    page_icon=":material/auto_awesome:",
    layout="wide",
    initial_sidebar_state="auto",
)

USER_DATA_DIR = Path(__file__).resolve().parent / "data" / "users"
REQUIRED_AUTH_FIELDS = (
    "redirect_uri",
    "cookie_secret",
    "client_id",
    "client_secret",
    "server_metadata_url",
)

try:
    auth_settings = st.secrets["auth"]
    auth_is_configured = all(auth_settings.get(field) for field in REQUIRED_AUTH_FIELDS)
except (KeyError, StreamlitSecretNotFoundError):
    auth_is_configured = False

is_authenticated = auth_is_configured and st.user.is_logged_in

if is_authenticated:
    user_subject = st.user.get("sub")
    if not user_subject:
        st.error("Your sign-in provider did not return a stable account identifier.")
        st.stop()

    user_id = hashlib.sha256(str(user_subject).encode("utf-8")).hexdigest()
    if st.session_state.get("authenticated_user_id") != user_id:
        st.session_state.clear()
        st.session_state.authenticated_user_id = user_id

    user_data_dir = USER_DATA_DIR / user_id
    HISTORY_FILE = user_data_dir / "chat_history.json"
    MEMORY_FILE = user_data_dir / "memory.json"
    user_display_name = (
        st.user.get("name")
        or st.user.get("email")
        or "Your account"
    )
else:
    HISTORY_FILE = None
    MEMORY_FILE = None
    user_display_name = "Guest"

CHAT_ROW_HTML = """
<div class="chat-row">
        <button class="chat-title" type="button"></button>
        <button class="chat-options" type="button" aria-label="Chat options" title="Chat options">...</button>
        <div class="chat-menu" role="menu" hidden></div>
</div>
"""

CHAT_ROW_CSS = """
.chat-row {
        display: flex;
        width: 100%;
        min-width: 0;
        height: 40px;
        position: relative;
        font-family: var(--st-font, sans-serif);
}
.chat-title, .chat-options {
        border: 0;
        color: #f4f6f2;
        background: transparent;
        cursor: pointer;
        font: inherit;
}
.chat-title {
        flex: 1;
        min-width: 0;
        overflow: hidden;
        padding: 0 9px;
        border-radius: 4px 0 0 4px;
        text-align: left;
        text-overflow: ellipsis;
        white-space: nowrap;
}
.chat-row.active .chat-title, .chat-row:hover .chat-title {
        background: #24342d;
}
.chat-options {
        width: 34px;
        flex: 0 0 34px;
        border-radius: 0 4px 4px 0;
        font-weight: 700;
        letter-spacing: 1px;
}
.chat-options:hover, .chat-options:focus-visible {
        background: #34483e;
}
.chat-menu {
    position: absolute;
    top: calc(100% + 4px);
    right: 0;
        z-index: 10000;
        width: 208px;
        padding: 5px;
        border: 1px solid #3a4b42;
        border-radius: 7px;
        background: #17231e;
        box-shadow: 0 12px 30px #0005;
}
.chat-menu[hidden] { display: none; }
.chat-menu button {
        display: block;
        width: 100%;
        min-height: 36px;
        padding: 7px 10px;
        border: 0;
        border-radius: 4px;
        color: #f4f6f2;
        background: transparent;
        cursor: pointer;
        font: inherit;
        text-align: left;
}
.chat-menu button:hover, .chat-menu button:focus-visible {
        background: #34483e;
}
.chat-menu button[data-action="delete"] { color: #ff8878; }
"""

CHAT_ROW_JS = """
export default function (component) {
    const { data, parentElement, setTriggerValue } = component
    const row = parentElement.querySelector(".chat-row")
    const titleButton = parentElement.querySelector(".chat-title")
    const optionsButton = parentElement.querySelector(".chat-options")
    const menu = parentElement.querySelector(".chat-menu")
    if (!row || !titleButton || !optionsButton || !menu) return

    row.classList.toggle("active", Boolean(data.active))
    titleButton.textContent = `${data.pinned ? "* " : ""}${data.title}`
    titleButton.onclick = () => setTriggerValue("select", true)

    const entries = [
        ["Share chat", "share"],
        ["Rename chat", "rename"],
        [data.pinned ? "Unpin chat" : "Pin chat", data.pinned ? "unpin" : "pin"],
        [data.archived ? "Restore to recents" : "Archive chat", data.archived ? "restore" : "archive"],
        ["Delete chat", "delete"],
    ]

    menu.replaceChildren()
    for (const [label, action] of entries) {
        const item = document.createElement("button")
        item.type = "button"
        item.role = "menuitem"
        item.textContent = label
        item.dataset.action = action
        item.onclick = (event) => {
            event.stopPropagation()
            menu.hidden = true
            setTriggerValue("action", action)
        }
        menu.appendChild(item)
    }

    const closeMenu = () => { menu.hidden = true }
    const openMenu = () => {
        menu.hidden = false
    }

    row.oncontextmenu = (event) => {
        event.preventDefault()
        openMenu()
    }
    optionsButton.onclick = (event) => {
        event.stopPropagation()
        if (menu.hidden) {
            openMenu()
        } else {
            closeMenu()
        }
    }
    parentElement.addEventListener("keydown", (event) => {
        if (event.key === "Escape") closeMenu()
    })
}
"""

CHAT_ROW = st.components.v2.component(
        "reyans.chat_row_context_menu",
        html=CHAT_ROW_HTML,
        css=CHAT_ROW_CSS,
        js=CHAT_ROW_JS,
)

PENDING_QUESTION_KEY = "pending_question_bridge"
PENDING_QUESTION_HTML = """
<div aria-hidden="true"></div>
"""
PENDING_QUESTION_JS = """
export default function (component) {
    const { data, setStateValue } = component
    const storageKey = "reyans.pending-question.v1"
    let question = ""

    if (data.command === "save" && data.question) {
        question = data.question
        sessionStorage.setItem(storageKey, JSON.stringify({
            question,
            expiresAt: Date.now() + 30 * 60 * 1000,
        }))
    } else if (data.command === "clear") {
        sessionStorage.removeItem(storageKey)
    } else {
        try {
            const saved = JSON.parse(sessionStorage.getItem(storageKey) || "null")
            if (saved && saved.expiresAt > Date.now()) {
                question = saved.question
            } else {
                sessionStorage.removeItem(storageKey)
            }
        } catch {
            sessionStorage.removeItem(storageKey)
        }
    }

    if ((data.currentQuestion || "") !== question) {
        setStateValue("pending_question", question)
    }
}
"""
PENDING_QUESTION_BRIDGE = st.components.v2.component(
        "reyans.pending_question_bridge",
        html=PENDING_QUESTION_HTML,
        js=PENDING_QUESTION_JS,
)

st.markdown(
    """
    <style>
    .stApp {
        background-color: #f8f9f6;
        background-image: linear-gradient(#17231e08 1px, transparent 1px), linear-gradient(90deg, #17231e08 1px, transparent 1px);
        background-size: 32px 32px;
        background-position: center top;
    }

    .main .block-container {
        max-width: 1080px;
        padding: 2rem 3.5rem 7rem;
    }

    [data-testid="stSidebar"] {
        border-right: 1px solid #31564a;
    }

    [data-testid="stSidebar"] .block-container {
        padding: 1.6rem 1.15rem 1.5rem;
    }

    .brand-lockup {
        display: flex;
        align-items: center;
        gap: 0.8rem;
        margin: 0.15rem 0 1.8rem;
    }

    .brand-mark {
        display: grid;
        place-items: center;
        width: 42px;
        height: 42px;
        border-radius: 5px 13px 5px 13px;
        background: #c9ed7b;
        color: #183a31;
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.35rem;
        font-weight: 700;
    }

    .brand-name {
        color: #f5f8f3;
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.08rem;
        font-weight: 700;
        line-height: 1.15;
    }

    .brand-caption, .sidebar-label {
        color: #adc2b6;
        font-size: 0.68rem;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }

    .sidebar-label {
        margin: 1.45rem 0 0.55rem;
    }

    .workspace-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        padding: 0.25rem 0 1.3rem;
        border-bottom: 1px solid #cfd8d0;
        margin-bottom: 2rem;
    }

    .workspace-kicker {
        color: #53645a;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.14em;
        text-transform: uppercase;
    }

    .model-chip {
        padding: 0.45rem 0.7rem;
        border: 1px solid #17231e;
        border-radius: 4px;
        background: #17231e;
        color: #f4f6f2;
        font-size: 0.72rem;
        font-weight: 600;
        white-space: nowrap;
    }

    .model-dot {
        display: inline-block;
        width: 7px;
        height: 7px;
        margin-right: 0.4rem;
        border-radius: 50%;
        background: #c9ed7b;
        vertical-align: 1px;
    }

    .welcome-eyebrow {
        margin: 0 0 0.6rem;
        color: #a63d2e;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
    }

    .welcome-note {
        max-width: 610px;
        color: #526159;
        font-size: 1.02rem;
        line-height: 1.65;
    }

    .suggestion-label {
        margin: 2rem 0 0.7rem;
        color: #526159;
        font-size: 0.75rem;
        font-weight: 600;
    }

    [data-testid="stChatMessage"] {
        padding-top: 1.15rem;
        padding-bottom: 1.15rem;
    }

    [data-testid="stChatInput"] {
        border-color: #bfc9c1;
        border-radius: 5px 13px 5px 13px;
        background: #ffffff;
        box-shadow: 0 12px 36px rgba(23, 35, 30, 0.1);
    }

    [data-testid="stChatInput"] textarea {
        font-size: 0.98rem;
    }

    [data-testid="stSidebar"] [data-testid="stButton"] button {
        min-height: 2.6rem;
        border-radius: 4px;
        text-align: left;
    }

    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] {
        line-height: 1.72;
    }

    [data-testid="stChatMessage"] strong {
        color: #a63d2e;
    }

    @media (max-width: 720px) {
        .main .block-container {
            padding: 1.3rem 1.1rem 6rem;
        }

        .workspace-header {
            margin-bottom: 1.4rem;
        }

        .model-chip {
            font-size: 0.65rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# USER CHAT HISTORY
# =========================================================

def load_chat_history():

    if not os.path.exists(HISTORY_FILE):
        return []

    try:

        with open(HISTORY_FILE, "r", encoding="utf-8") as file:
            return json.load(file)

    except (json.JSONDecodeError, OSError):

        return []


def save_chat_history(history):

    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(HISTORY_FILE, "w", encoding="utf-8") as file:

        json.dump(
            history,
            file,
            indent=4,
            ensure_ascii=False
        )


def export_chat_markdown(chat):

    return "\n\n".join(
        f"## {message['role'].title()}\n\n{message['content']}"
        for message in chat.get("messages", [])
    )


def get_gemini_api_key():
    try:
        return st.secrets.get("GEMINI_API_KEY")
    except StreamlitSecretNotFoundError:
        return None


def save_generated_image(image):
    extension = {
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/webp": "webp",
    }[image.mime_type]
    images_dir = MEMORY_FILE.parent / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}.{extension}"
    (images_dir / filename).write_bytes(image.image_bytes)
    return filename


def render_chat_message(message):
    st.markdown(message["content"])
    image_filename = message.get("image_file")
    if not image_filename:
        return

    image_path = MEMORY_FILE.parent / "images" / Path(image_filename).name
    if image_path.is_file():
        st.image(str(image_path))
    else:
        st.warning("This generated image is no longer available.")


@st.dialog("Share chat")
def share_chat_dialog(chat_index):

    chat = st.session_state.chat_history[chat_index]
    title = chat.get("title", "chat")
    filename = "".join(
        character.lower() if character.isalnum() else "-"
        for character in title
    ).strip("-") or "chat"

    st.caption("Download a Markdown copy of this conversation.")
    st.download_button(
        "Download conversation",
        data=export_chat_markdown(chat),
        file_name=f"{filename[:60]}.md",
        mime="text/markdown",
        icon=":material/download:",
        width="stretch",
    )


@st.dialog("Rename chat")
def rename_chat_dialog(chat_index):

    chat = st.session_state.chat_history[chat_index]
    with st.form(f"rename_chat_form_{chat_index}"):
        renamed_title = st.text_input(
            "Chat name",
            value=chat.get("title", "New chat"),
            key=f"rename_chat_input_{chat_index}",
        )
        if st.form_submit_button(
            "Save name",
            icon=":material/check:",
            type="primary",
            width="stretch",
        ):
            if renamed_title.strip():
                chat["title"] = renamed_title.strip()
                save_chat_history(st.session_state.chat_history)
                st.rerun()
            else:
                st.warning("Enter a name for this chat.")


@st.dialog("Delete chat")
def delete_chat_dialog(chat_index):

    title = st.session_state.chat_history[chat_index].get("title", "New chat")
    st.write(f"Permanently delete **{title}**? This cannot be undone.")
    delete_col, cancel_col = st.columns(2)

    if delete_col.button(
        "Delete permanently",
        key=f"confirm_delete_chat_{chat_index}",
        icon=":material/delete:",
        type="primary",
        width="stretch",
    ):
        del st.session_state.chat_history[chat_index]

        if st.session_state.current_chat == chat_index:
            st.session_state.current_chat = None
            st.session_state.messages = []
        elif (
            st.session_state.current_chat is not None
            and st.session_state.current_chat > chat_index
        ):
            st.session_state.current_chat -= 1

        save_chat_history(st.session_state.chat_history)
        st.rerun()

    if cancel_col.button("Cancel", width="stretch"):
        st.rerun()


def render_chat_item(chat_index, chat):

    title = chat.get("title", "New chat")
    result = CHAT_ROW(
        key=f"chat_row_{chat_index}",
        data={
            "title": title,
            "active": st.session_state.current_chat == chat_index,
            "pinned": chat.get("pinned", False),
            "archived": chat.get("archived", False),
        },
        on_select_change=lambda: None,
        on_action_change=lambda: None,
    )
    if result.select:
        st.session_state.current_chat = chat_index
        st.session_state.messages = chat.get("messages", [])
        st.rerun()

    action = result.action

    if action == "share":
        share_chat_dialog(chat_index)
    elif action == "rename":
        rename_chat_dialog(chat_index)
    elif action == "pin":
        chat["pinned"] = True
        save_chat_history(st.session_state.chat_history)
        st.rerun()
    elif action == "unpin":
        chat.pop("pinned", None)
        save_chat_history(st.session_state.chat_history)
        st.rerun()
    elif action == "archive":
        chat["archived"] = True
        save_chat_history(st.session_state.chat_history)
        st.rerun()
    elif action == "restore":
        chat.pop("archived", None)
        save_chat_history(st.session_state.chat_history)
        st.rerun()
    elif action == "delete":
        delete_chat_dialog(chat_index)


if not is_authenticated:
    st.markdown(
        """
        <div class="workspace-header">
            <div class="workspace-kicker">Personal AI workspace</div>
            <div class="model-chip"><span class="model-dot"></span>LLAMA 3.2 / LOCAL</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="welcome-eyebrow">Ask first. Sign in for your answer.</div>',
        unsafe_allow_html=True,
    )
    st.title("What would you like to know?")
    st.markdown(
        '<div class="welcome-note">Ask about anything, including coding-platform problems in the programming language you choose. Sign in to get an answer and save your conversation privately.</div>',
        unsafe_allow_html=True,
    )

    guest_question = st.chat_input(
        "Ask Reyans a question...",
        key="guest_chat_input",
    )
    pending_state = st.session_state.get(PENDING_QUESTION_KEY, {})
    existing_pending_question = pending_state.get("pending_question", "")
    guest_bridge = PENDING_QUESTION_BRIDGE(
        key=PENDING_QUESTION_KEY,
        data={
            "command": "save" if guest_question else "read",
            "question": guest_question or "",
            "currentQuestion": existing_pending_question,
        },
        on_pending_question_change=lambda: None,
    )
    pending_question = guest_question or guest_bridge.pending_question

    if pending_question:
        with st.chat_message("user", avatar=":material/person:"):
            st.markdown(pending_question)

        if auth_is_configured:
            st.info("Your question is ready. Sign in to get Reyans's answer.")
            if st.button(
                "Sign in to get answer",
                icon=":material/login:",
                type="primary",
            ):
                st.login()
        else:
            st.warning(
                "Sign-in is not configured yet. The site owner must finish "
                "Google OIDC setup before Reyans can answer."
            )
            st.markdown("See [AUTH_SETUP.md](AUTH_SETUP.md) for setup steps.")
    elif not auth_is_configured:
        st.caption(
            "You can enter a question now. Secure sign-in must be configured "
            "before an answer can be generated."
        )

    st.stop()


pending_state = st.session_state.get(PENDING_QUESTION_KEY, {})
pending_question = pending_state.get("pending_question", "")
pending_bridge = PENDING_QUESTION_BRIDGE(
    key=PENDING_QUESTION_KEY,
    data={
        "command": "read",
        "question": "",
        "currentQuestion": pending_question,
    },
    on_pending_question_change=lambda: None,
)
pending_question = pending_question or pending_bridge.pending_question or ""
if pending_question == st.session_state.get("pending_question_consumed"):
    pending_question = ""

# Guard against stale browser-persisted pending questions being replayed after the
# user already entered a fresh message.
if "pending_question_replay_guard" not in st.session_state:
    st.session_state.pending_question_replay_guard = ""
if "pending_question_consumed" not in st.session_state:
    st.session_state.pending_question_consumed = ""


def clear_pending_question_bridge():
    """Clear any stale browser-persisted pending question after a fresh prompt."""
    st.session_state.pending_question_replay_guard = ""
    st.session_state.pending_question_consumed = ""
    PENDING_QUESTION_BRIDGE(
        key="pending_question_cleanup",
        data={
            "command": "clear",
            "question": "",
            "currentQuestion": "",
        },
        on_pending_question_change=lambda: None,
    )


# =========================================================
# LOAD CHAT HISTORY
# =========================================================

if "chat_history" not in st.session_state:

    st.session_state.chat_history = load_chat_history()


if "current_chat" not in st.session_state:

    st.session_state.current_chat = None


if "messages" not in st.session_state:

    st.session_state.messages = []


# =========================================================
# SIDEBAR
# =========================================================

tool_question = None

with st.sidebar:

    st.markdown(
        """
        <div class="brand-lockup">
            <div class="brand-mark">R</div>
            <div>
                <div class="brand-name">Reyans</div>
                <div class="brand-caption">Personal AI agent</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    new_col, clear_col = st.columns(2)

    if new_col.button(
        "New chat",
        icon=":material/edit_square:",
        type="primary",
        width="stretch",
    ):

        st.session_state.current_chat = None
        st.session_state.messages = []

        st.rerun()

    if clear_col.button(
        "Clear all",
        icon=":material/delete_sweep:",
        width="stretch",
    ):

        st.session_state.chat_history = []
        st.session_state.current_chat = None
        st.session_state.messages = []
        save_chat_history(st.session_state.chat_history)

        st.rerun()

    st.markdown('<div class="sidebar-label">Your conversations</div>', unsafe_allow_html=True)

    recent_chats = [
        (index, chat)
        for index, chat in enumerate(st.session_state.chat_history)
        if not chat.get("archived", False)
    ]
    recent_chats.sort(key=lambda item: not item[1].get("pinned", False))

    if not recent_chats:
        st.caption("Your conversations will appear here.")

    for chat_index, chat in recent_chats:
        render_chat_item(chat_index, chat)

    archived_chats = [
        (index, chat)
        for index, chat in enumerate(st.session_state.chat_history)
        if chat.get("archived", False)
    ]
    with st.expander(f"Archived ({len(archived_chats)})"):
        for chat_index, chat in archived_chats:
            render_chat_item(chat_index, chat)

    st.markdown('<div class="sidebar-label">Quick actions</div>', unsafe_allow_html=True)

    if st.button(
        "Web search",
        key="tool_web_search",
        icon=":material/travel_explore:",
        width="stretch",
    ):
        tool_question = "Search the web for the latest updates on renewable energy."

    if st.button(
        "Calculate",
        key="tool_calculate",
        icon=":material/calculate:",
        width="stretch",
    ):
        tool_question = "Calculate 148 multiplied by 36."

    if st.button(
        "Local time",
        key="tool_local_time",
        icon=":material/schedule:",
        width="stretch",
    ):
        tool_question = "What time is it?"

    saved_memories = load_memory(MEMORY_FILE)
    with st.expander(
        f"Saved memories ({len(saved_memories)})",
        icon=":material/bookmark:",
    ):
        if saved_memories:
            for memory in saved_memories:
                st.write(f"**{memory['key']}**: {memory['value']}")
        else:
            st.caption("No saved details yet.")

    st.space("large")
    st.caption(f"Signed in as {user_display_name}")
    if st.button(
        "Log out",
        icon=":material/logout:",
        width="stretch",
    ):
        st.session_state.clear()
        st.logout()
        st.stop()


# =========================================================
# MAIN PAGE
# =========================================================

st.markdown(
    """
    <div class="workspace-header">
        <div class="workspace-kicker">Personal AI workspace</div>
        <div class="model-chip"><span class="model-dot"></span>LLAMA 3.2 / LOCAL</div>
    </div>
    """,
    unsafe_allow_html=True,
)

if st.session_state.messages:
    active_title = "New conversation"
    if st.session_state.current_chat is not None:
        active_title = st.session_state.chat_history[
            st.session_state.current_chat
        ].get("title", active_title)
    st.subheader(active_title)
else:
    current_hour = datetime.now().hour
    if 5 <= current_hour < 12:
        greeting = "Good morning"
    elif current_hour < 17:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"
    st.markdown('<div class="welcome-eyebrow">A thoughtful assistant, ready when you are</div>', unsafe_allow_html=True)
    st.title(greeting)
    st.markdown(
        '<div class="welcome-note">Ask a question, explore an idea, solve a coding-platform problem in your chosen language, or ask Reyans to generate an image. Reyans can also search the web, work through calculations, and remember details you save.</div>',
        unsafe_allow_html=True,
    )


# =========================================================
# DISPLAY CURRENT CHAT
# =========================================================

for message in st.session_state.messages:

    avatar = ":material/auto_awesome:" if message["role"] == "assistant" else ":material/person:"
    with st.chat_message(message["role"], avatar=avatar):
        render_chat_message(message)


starter_question = None

if not st.session_state.messages:
    st.markdown('<div class="suggestion-label">Start with a direction</div>', unsafe_allow_html=True)
    suggestion_columns = st.columns(4)

    if suggestion_columns[0].button(
        "Explore an idea",
        icon=":material/lightbulb:",
        width="stretch",
    ):
        starter_question = "Explain a difficult idea in simple terms."

    if suggestion_columns[1].button(
        "Solve a calculation",
        icon=":material/calculate:",
        width="stretch",
    ):
        starter_question = "Calculate 148 multiplied by 36 and show the steps."

    if suggestion_columns[2].button(
        "Search the web",
        icon=":material/travel_explore:",
        width="stretch",
    ):
        starter_question = "Search the web for the latest updates on renewable energy."

    if suggestion_columns[3].button(
        "Solve a coding problem",
        icon=":material/code:",
        width="stretch",
    ):
        starter_question = "Help me solve a coding-platform problem."


# =========================================================
# CHAT INPUT
# =========================================================

question = st.chat_input(
    "Message Reyans...",
    key="chat_input",
)

if question:
    st.session_state.pending_question_replay_guard = question
    st.session_state.pending_question_consumed = question
    # Clear the browser-persisted pending question as soon as a new prompt is
    # submitted so the old value isn't replayed on the next turn.
    PENDING_QUESTION_BRIDGE(
        key="pending_question_cleanup",
        data={
            "command": "clear",
            "question": "",
            "currentQuestion": "",
        },
        on_pending_question_change=lambda: None,
    )

if pending_question and question is None and pending_question == st.session_state.pending_question_replay_guard:
    pending_question = ""

question = question or starter_question or tool_question or pending_question


# =========================================================
# PROCESS QUESTION
# =========================================================

if question:

    # -----------------------------------------------------
    # Add user message
    # -----------------------------------------------------

    st.session_state.messages.append({

        "role": "user",

        "content": question

    })


    # -----------------------------------------------------
    # Display user question
    # -----------------------------------------------------

    with st.chat_message("user", avatar=":material/person:"):

        st.markdown(question)


    # -----------------------------------------------------
    # Get AI answer
    # -----------------------------------------------------

    with st.chat_message("assistant", avatar=":material/auto_awesome:"):

        with st.spinner("Reyans is thinking..."):

            answer = ask_agent(
                question,
                st.session_state.messages[:-1],
                memory_file=MEMORY_FILE,
                gemini_api_key=get_gemini_api_key(),
            )

        image_filename = None
        if isinstance(answer, GeneratedImage):
            answer_content = f"Generated image: {answer.prompt}"
            st.image(answer.image_bytes, caption=answer.prompt)
            try:
                image_filename = save_generated_image(answer)
            except OSError as exc:
                st.warning(
                    "The image was generated but could not be saved to this "
                    f"account's chat history: {exc}"
                )
        else:
            answer_content = answer
            st.markdown(answer_content)


    # -----------------------------------------------------
    # Add AI answer
    # -----------------------------------------------------

    st.session_state.messages.append({

        "role": "assistant",

        "content": answer_content

    })
    if image_filename:
        st.session_state.messages[-1]["image_file"] = image_filename


    # =====================================================
    # SAVE CHAT HISTORY
    # =====================================================

    if st.session_state.current_chat is None:

        new_chat = {

            "title": question,

            "messages": st.session_state.messages

        }

        st.session_state.chat_history.append(new_chat)

        st.session_state.current_chat = (
            len(st.session_state.chat_history) - 1
        )

    else:

        st.session_state.chat_history[
            st.session_state.current_chat
        ]["messages"] = st.session_state.messages


    save_chat_history(
        st.session_state.chat_history
    )

    if pending_question and question == pending_question:
        st.session_state.pending_question_consumed = pending_question
        clear_pending_question_bridge()