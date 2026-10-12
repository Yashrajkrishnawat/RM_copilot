from openai import OpenAI

from app.config import settings

class LLMClient:
    def __init__(self):
        self.client = OpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key)

    def chat(self, messages, tools = None):
        if settings.llm_disable_thinking and messages and messages[0]["role"] == "system":
            messages = [{**messages[0], "content": messages[0]["content"] + "\n/no_think"}, * messages[1:]]

        kwargs = {
            "model" : settings.llm_model,
            "messages": messages,
            "temperature": settings.llm_temperature,
            "extra_body":{"options": {"num_ctx": settings.llm_num_ctx}},
        }

        if tools:
            kwargs["tools"] = tools

        return self.client.chat.completions.create(**kwargs).choices[0].message