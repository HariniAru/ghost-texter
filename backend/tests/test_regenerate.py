import json

import pytest
from fastapi.testclient import TestClient
from ghost import workflow
from ghost.config import Settings
from ghost.main import create_app
from ghost.messaging import DemoMessenger
from langgraph.checkpoint.memory import MemorySaver

ALEX = "alex@example.test"


def answer(schema, *texts):
    """What the model returns: one reply for a first draft, a list of replies for a redraft."""
    return schema(text=texts[0]) if "text" in schema.model_fields else schema(texts=list(texts))


@pytest.fixture
def drafting(tmp_path, monkeypatch):
    """A fake model that records what it was told to avoid and returns scripted replies."""
    seen, replies, temperatures = [], [], []

    class FakeModel:
        def with_structured_output(self, schema):
            self.schema = schema
            return self

        def invoke(self, messages):
            seen.append(json.loads(messages[-1][1])["earlier_drafts_to_avoid"])
            return (
                answer(self.schema, *replies.pop(0))
                if isinstance(replies[0], tuple)
                else answer(self.schema, replies.pop(0))
            )

    def create_model(_settings, temperature=0):
        temperatures.append(temperature)
        return FakeModel()

    monkeypatch.setattr(workflow, "create_model", create_model)
    messenger = DemoMessenger()
    settings = Settings(data_dir=tmp_path, api_token="t", llm=True, _env_file=None)
    with TestClient(create_app(settings, messenger)) as client:
        client.headers["Authorization"] = "Bearer t"
        client.temperatures = temperatures
        yield client, messenger, seen, replies


def redraft(client, row=None):
    """What Draft a reply does: discard the current draft, then ask for a new one."""
    if row:
        client.post(f"/api/drafts/{row['id']}/reject", json={"version": row["version"]})
    return client.post("/api/drafts", json={"recipient": ALEX})


def test_each_new_draft_avoids_the_ones_already_discarded(drafting):
    client, _, seen, replies = drafting
    replies += ["sure, 10 works", "can we do 11?", "yes! see you there"]
    first = redraft(client).json()
    second = redraft(client, first).json()
    third = redraft(client, second).json()
    assert [first["text"], second["text"], third["text"]] == [
        "sure, 10 works",
        "can we do 11?",
        "yes! see you there",
    ]
    assert seen == [[], ["sure, 10 works"], ["can we do 11?", "sure, 10 works"]]


def test_new_messages_or_a_sent_reply_start_the_list_again(drafting):
    client, messenger, seen, replies = drafting
    replies += ["sure, 10 works", "can we do 11?", "ok!"]
    first = redraft(client).json()
    client.post(f"/api/drafts/{first['id']}/reject", json={"version": 1})
    messenger.history[ALEX] += "\nAlex: actually, Friday?"
    second = redraft(client).json()
    assert seen[-1] == []
    client.post(f"/api/drafts/{second['id']}/approve", json={"version": 1})
    redraft(client)
    assert seen[-1] == []


def test_a_new_draft_varies_the_wording_and_skips_a_repeat(drafting):
    client, _, seen, replies = drafting
    replies += ["sure, 10 works", "Sure,  10 works", "can we do 11?"]
    first = redraft(client).json()
    second = redraft(client, first).json()
    assert second["text"] == "can we do 11?"
    assert len(seen) == 3
    # The first draft is steady; later ones are asked to vary.
    assert client.temperatures[0] == 0 and client.temperatures[1] > 0


def test_a_model_that_keeps_repeating_is_refused_after_a_few_tries(drafting):
    client, _, seen, replies = drafting
    replies += ["sure, 10 works"] * 5
    first = redraft(client).json()
    response = redraft(client, first)
    assert response.status_code == 502
    assert response.json()["detail"] == "Failed to generate a response draft. Try again."
    assert len(seen) == 1 + workflow.REDRAFT_TRIES
    assert [r["status"] for r in client.get("/api/drafts").json()] == ["rejected"]


def test_the_retry_is_a_loop_in_the_langgraph_workflow(tmp_path):
    graph = workflow.build_graph(MemorySaver(), Settings(data_dir=tmp_path, _env_file=None))
    edges = {(e.source, e.target) for e in graph.get_graph().edges}
    assert {("draft", "draft"), ("draft", "review"), ("draft", "give_up")} <= edges


def test_sample_drafts_never_loop_even_when_repeated(tmp_path):
    settings = Settings(data_dir=tmp_path, api_token="t", llm=False, _env_file=None)
    with TestClient(create_app(settings, DemoMessenger())) as client:
        client.headers["Authorization"] = "Bearer t"
        first = redraft(client).json()
        second = redraft(client, first)
        assert second.status_code == 200
        assert second.json()["text"] == first["text"]


def test_a_redraft_asks_for_several_replies_and_uses_the_first_new_one(drafting):
    client, _, seen, replies = drafting
    # A one-word voice keeps reaching for its examples, so the model lists several options.
    # The redraft's single reply repeats, so the retry asks for a list and takes the first new one.
    replies += ["ok", "ok", ("ok", "hi", "bye")]
    first = redraft(client).json()
    second = redraft(client, first).json()
    assert second["text"] == "hi"
    assert len(seen) == 3


def test_a_redraft_that_is_not_a_repeat_costs_one_single_reply(drafting):
    client, _, seen, replies = drafting
    replies += ["sure, 10 works", "can we do 11?"]
    first = redraft(client).json()
    assert redraft(client, first).json()["text"] == "can we do 11?"
    assert len(seen) == 2


def test_every_listed_reply_repeating_goes_round_the_loop_with_more_variation(drafting):
    client, _, seen, replies = drafting
    replies += ["ok", "ok", ("ok", "OK"), ("bye", "ok")]
    first = redraft(client).json()
    second = redraft(client, first).json()
    assert second["text"] == "bye"
    assert len(seen) == 4
    assert client.temperatures == [
        0,
        workflow.REDRAFT_TEMPERATURE,
        workflow.RETRY_TEMPERATURE,
        workflow.RETRY_TEMPERATURE,
    ]
