from ollama import chat

question = input("You: ")

response = chat(
    model="llama3.2",
    messages=[
        {
            "role": "user",
            "content": question
        }
    ]
)

print("AI:", response.message.content)