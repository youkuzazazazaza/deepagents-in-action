from langchain.agents import create_agent

agent = create_agent(model=model, tools=[echo])
result = agent.invoke({"messages": [("user", f"调用 echo，原样返回 {TEXT}")]})
for message in result["messages"]:
    print(message.type, getattr(message, "name", None) or "", str(message.content)[:120])
    if isinstance(message, AIMessage):
        for call in message.tool_calls:
            print("  请求工具:", call["name"], "参数:", call["args"], "调用 ID:", call["id"])
    if isinstance(message, ToolMessage):
        print("  对应调用 ID:", message.tool_call_id, "执行状态:", message.status)