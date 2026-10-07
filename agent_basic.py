from ollama import chat

response = chat(
    model="llama3.2",
    messages=[
        {
            "role": "user",
            "content": "What is an AI agent? Explain in simple words."
        }
    ]
)

print(response.message.content)