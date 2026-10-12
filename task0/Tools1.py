from Scripts.bottle import response
from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from langchain_core.utils.pydantic import create_model


@tool
def echo(text: str) -> str:
    return f"原样返回echo: {text}"

model = create_model(ScriptedChatModel(responses=[
    AIMessage(content="", tool_calls=[{
        "name": "echo", "args": {"text": TEXT}, "id": "template-echo",
    }]),
    AIMessage(content="工具调用流程结束；请检查实际 ToolMessage。"),
]
))