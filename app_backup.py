import streamlit as st
from ollama import chat

st.set_page_config(
    page_title="My AI Agent",
    page_icon="🤖"
)

st.title("🤖 My AI Agent")
st.write("Chat with my local AI agent using Ollama.")

# Store chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous messages
for message in st.session_state.messages:

    with st.chat_message(message["role"]):
        st.write(message["content"])

# Chat input
question = st.chat_input("Ask your AI agent something...")

if question:

    # Show user's message
    st.session_state.messages.append({
        "role": "user",
        "content": question
    })

    with st.chat_message("user"):
        st.write(question)

    # Get AI response
    with st.chat_message("assistant"):

        with st.spinner("Thinking..."):

            response = chat(
                model="llama3.2",
                messages=[
                    {
                        "role": message["role"],
                        "content": message["content"]
                    }
                    for message in st.session_state.messages
                ]
            )

            answer = response.message.content

        st.write(answer)

    # Save AI response
    st.session_state.messages.append({
        "role": "assistant",
        "content": answer
    })