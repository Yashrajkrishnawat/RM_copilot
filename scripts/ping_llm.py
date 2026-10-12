from openai import OpenAI

client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
MODEL = "qwen3:4b"

resp = client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "user", "content": "Say hello in one line. /no_think"}],
)
print("1. Chat:", resp.choices[0].message.content)

tools = [{
    "type": "function",
    "function": {
        "name": "calc_eligibility",
        "description": "Calculate home loan eligibility for a customer",
        "parameters": {
            "type": "object",
            "properties": {
                "monthly_income": {"type": "number", "description": "Net monthly income in INR"},
                "property_value": {"type": "number", "description": "Property value in INR"},
            },
            "required": ["monthly_income", "property_value"],
        },
    },
}]

resp = client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "user", "content": "Customer earns 65000 per month, property worth 28 lakh. How much loan can he get? /no_think"}],
    tools=tools,
    temperature=0.1,
)
msg = resp.choices[0].message
if msg.tool_calls:
    for c in msg.tool_calls:
        print("2. Tool call:", c.function.name, c.function.arguments)
else:
    print("2. No tool call. Model said:", msg.content)