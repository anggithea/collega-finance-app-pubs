from config.settings import client

def get_chat_response(messages, model="llama-3.3-70b-versatile"):
    response = client.chat.completions.create(
        messages=messages,
        model=model,
    )
    return response.choices[0].message.content
