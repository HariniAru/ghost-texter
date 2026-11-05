# Sources and baseline decisions

## Local projects inspected

- `../chase-travel-chatbot`: FastAPI settings, backend dependency organization, React/TypeScript package structure, and docs layout.
- `../genai-case-review`: Python/LangGraph dependency conventions and backend module layout.

These informed conventions. No sibling secrets or domain datasets were copied. Sibling projects were not changed.

## Official upstream references checked during implementation

- [LangGraph interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts): persistent human review, interrupt payloads, and resume behavior. Dispatch stays outside replayable graph nodes.
- [Mac Messages MCP](https://github.com/carterlasalle/mac_messages_mcp): stdio launcher, direct-conversation tools, macOS permissions, and limitations.
- [Mac Messages MCP tool implementation](https://github.com/carterlasalle/mac_messages_mcp/blob/main/mac_messages_mcp/server.py): tool_get_recent_messages and tool_send_message arguments.
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk): stdio client and session initialization.

The exact connector installed on this Mac has not been exercised against private data. See SETUP.md and PROJECT_PLAN.md for live validation steps.

AI activation references: [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs) and [GPT-4.1 mini](https://developers.openai.com/api/docs/models/gpt-4.1-mini). The existing model choice was retained.
