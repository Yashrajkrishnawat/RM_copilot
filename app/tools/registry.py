from dataclasses import dataclass
from typing import Callable

from pydantic import BaseModel, ValidationError


@dataclass
class Tool:
    name: str
    description: str
    args_model: type[BaseModel]
    fn: Callable
    requires_approval: bool = False

    def spec(self):
        schema = self.args_model.model_json_schema()
        schema.pop("title", None)
        return {
            "type": "function",
            "function": {"name": self.name, "description": self.description, "parameters": schema},
        }

    def run(self, raw_args: dict):
        try:
            args = self.args_model(**raw_args)
        except ValidationError as e:
            return {"error": "invalid_arguments", "details": e.errors(include_url=False)}
        try:
            return self.fn(**args.model_dump())
        except Exception as e:
            return {"error": "tool_failed", "details": str(e)}


REGISTRY: dict[str, Tool] = {}


def tool(name, description, args_model, requires_approval=False):
    def wrap(fn):
        REGISTRY[name] = Tool(name, description, args_model, fn, requires_approval)
        return fn
    return wrap


def specs_for(names):
    return [REGISTRY[n].spec() for n in names if n in REGISTRY]