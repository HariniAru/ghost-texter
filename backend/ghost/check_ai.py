"""Test AI summaries and paused drafts with synthetic data only; no Messages access."""

import sys

from langgraph.checkpoint.memory import InMemorySaver

from ghost.config import Settings
from ghost.workflow import AIConfigurationError, build_graph, summarize

CONTEXT = (
    "[2026-10-18 10:00:00] Alex: want to grab coffee tomorrow?\n"
    "[2026-10-17 09:00:00] You: hey! how has your week been?"
)


def check(settings):
    settings = settings.model_copy(update={"llm": True})
    summary = summarize(CONTEXT, settings)
    graph = build_graph(InMemorySaver(), settings)
    result = graph.invoke(
        {
            "context": CONTEXT,
            "style": "Warm, casual, short. Do not invent availability or agree to plans.",
            "examples": ["hey! what time were you thinking?", "sounds fun :) let me check"],
        },
        {"configurable": {"thread_id": "synthetic-ai-check"}},
    )
    if not result.get("__interrupt__"):
        raise RuntimeError("Draft did not pause for approval")
    return summary["summary"], result["text"]


def main():
    try:
        summary, draft = check(Settings())
    except AIConfigurationError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except Exception:
        print(
            "AI check failed. Check the configured model provider and model access (or run ollama serve for local mode). "
            "No messages were accessed or sent.",
            file=sys.stderr,
        )
        return 2
    print("Synthetic conversation only; no Messages access.\n")
    print("Summary:\n" + summary + "\n\nProposed reply:\n" + draft)
    print("\nPASS: draft paused for approval. Nothing was sent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
