"""Bounded local voice profiles and conservative, read-only example extraction."""

import re

from pydantic import BaseModel, Field, field_validator

from ghost.messaging import MESSAGE_ROW, normalize_transcript


class Pair(BaseModel):
    incoming: str = Field(min_length=1, max_length=2000)
    response: str = Field(min_length=1, max_length=2000)

    @field_validator("incoming", "response")
    @classmethod
    def not_blank(cls, value):
        if not value.strip():
            raise ValueError("Example text cannot be blank")
        return value


class Voice(BaseModel):
    style: str = Field(default="", max_length=2000)
    examples: list[str] = Field(default_factory=list, max_length=30)
    pairs: list[Pair] = Field(default_factory=list, max_length=20)

    @field_validator("examples")
    @classmethod
    def bounded_examples(cls, value):
        if any(not e.strip() or len(e) > 4000 for e in value):
            raise ValueError("Examples must contain 1–4000 characters")
        return value


class Profile(Voice):
    style: str = Field(min_length=1, max_length=2000)
    recipients: dict[str, Voice] = Field(default_factory=dict, max_length=50)


def resolve_profile(data, recipient):
    profile = Profile.model_validate(data)
    specific = profile.recipients.get(recipient)
    style = profile.style
    if specific and specific.style.strip():
        style += "\nRecipient-specific preferences: " + specific.style
    source = specific if specific and (specific.examples or specific.pairs) else profile
    # Deterministic fixed budget, shared across standalone and paired examples.
    budget, examples, pairs = 8000, [], []
    for pair in source.pairs:
        size = len(pair.incoming) + len(pair.response)
        if size <= budget:
            pairs.append(pair.model_dump())
            budget -= size
    for example in source.examples:
        if len(example) <= budget:
            examples.append(example)
            budget -= len(example)
    return {"style": style, "examples": examples, "pairs": pairs}


def suggest_pairs(context, demo=False):
    context = normalize_transcript(context)
    rows = MESSAGE_ROW.findall(context)
    if rows:
        rows.reverse()  # MCP is newest first. Ignore wrappers and multiline ambiguity.
    elif demo:
        rows = context.splitlines()
    else:
        return []
    pending, result = None, []
    for row in rows:
        parsed = re.fullmatch(
            r"(?:\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\] )?"
            r"([^:\[\]\n]+?)(?: \[[^\]\n]+\])*: (.*)",
            row,
        )
        if not parsed:
            pending = None
            continue
        sender, text = parsed.groups()
        text = text.strip()
        if not text or len(text) > 2000 or text.startswith("["):
            pending = None
            continue
        if sender == "You":
            if pending:
                pair = {"incoming": pending, "response": text}
                if pair not in result:
                    result.append(pair)
            pending = None
        else:
            pending = text  # Conservative adjacent pair; don't guess message ownership.
    return result[-20:]
