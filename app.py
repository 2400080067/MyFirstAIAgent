import streamlit as st
from agent_core import ask_agent

st.set_page_config(
    page_title="My AI Agent",
    page_icon="🤖"
)

st.title("🤖 My AI Agent")
st.write("Chat with my local AI agent using Ollama.")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:

    with st.chat_message(message["role"]):
        st.write(message["content"])

question = st.chat_input("Ask your AI agent something...")

if question:

    st.session_state.messages.append({
        "role": "user",
        "content": question
    })

    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):

        with st.spinner("Thinking..."):

            answer = ask_agent(question)

        st.write(answer)

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer
    })