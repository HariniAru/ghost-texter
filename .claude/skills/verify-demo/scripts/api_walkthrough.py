"""Walk the draft lifecycle over HTTP against a confirmed synthetic demo server.

Started by run-demo.sh, which supplies GHOST_DEMO_URL and GHOST_DEMO_TOKEN.
Every request that changes state happens after guard() confirms a demo server.
Simulated sends only. Standard library only.
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

URL = os.environ["GHOST_DEMO_URL"].rstrip("/")
TOKEN = os.environ["GHOST_DEMO_TOKEN"]
# Direct connection only, so a proxy can never redirect these requests elsewhere.
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


class Failed(Exception):
    pass


def call(method, path, body=None):
    request = urllib.request.Request(
        URL + path,
        method=method,
        data=None if body is None else json.dumps(body).encode(),
        headers={
            "Authorization": "Bearer " + TOKEN,
            "Content-Type": "application/json",
            # Matches what a browser sends, so the origin check is exercised.
            "Origin": URL,
        },
    )
    try:
        with OPENER.open(request, timeout=30) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as exc:
        return exc.code, None


def expect(label, condition):
    if not condition:
        raise Failed(label)
    print("ok   " + label)


def guard():
    """Stop unless this is provably a synthetic server with sending off."""
    if urllib.parse.urlsplit(URL).hostname != "127.0.0.1":
        raise Failed("server is not on loopback")
    code, status = call("GET", "/api/status")
    if code != 200:
        raise Failed(f"status check returned {code}; token not accepted")
    if status["mode"] != "demo":
        raise Failed("server is not in demo mode")
    if status["llm"] or status["send_enabled"]:
        raise Failed("model or sending is enabled")
    recipients = status["recipients"]
    if not recipients or not all(r.endswith("@example.test") for r in recipients):
        raise Failed("recipients are not all synthetic")
    return recipients


def walkthrough(recipients):
    recipient = recipients[0]

    code, inbox = call("GET", "/api/inbox")
    expect("inbox lists unread conversations", code == 200 and inbox)

    query = urllib.parse.urlencode({"recipient": recipient})
    code, detail = call("GET", "/api/conversation?" + query)
    expect(
        "conversation returns context and a labeled excerpt",
        code == 200 and detail["context"] and detail["summary_kind"] == "excerpt",
    )

    code, first = call("POST", "/api/drafts", {"recipient": recipient})
    expect("draft starts pending at version 1", code == 200 and first["version"] == 1)

    code, same = call("POST", "/api/drafts", {"recipient": recipient})
    expect("same snapshot reuses the pending draft", code == 200 and same["id"] == first["id"])

    code, edited = call(
        "PATCH", f"/api/drafts/{first['id']}", {"version": 1, "text": "synthetic edit one"}
    )
    expect("saving an edit increments the version", code == 200 and edited["version"] == 2)

    code, _ = call("PATCH", f"/api/drafts/{first['id']}", {"version": 1, "text": "out of date"})
    expect("edit with an old version is refused", code == 409)

    code, _ = call("POST", f"/api/drafts/{first['id']}/approve", {"version": 1})
    expect("approval of an old version is refused", code == 409)

    code, rows = call("GET", "/api/drafts")
    saved = next((row for row in rows if row["id"] == first["id"]), None) if code == 200 else None
    expect(
        "saved edit can be reopened",
        saved is not None and saved["text"] == "synthetic edit one" and saved["status"] == "pending",
    )

    code, rejected = call("POST", f"/api/drafts/{first['id']}/reject", {"version": 2})
    expect("rejecting resolves the draft", code == 200 and rejected["status"] == "rejected")

    code, _ = call("POST", f"/api/drafts/{first['id']}/approve", {"version": 2})
    expect("a rejected draft cannot be approved", code == 409)

    code, second = call("POST", "/api/drafts", {"recipient": recipient})
    expect(
        "a new draft can follow a rejection",
        code == 200 and second["id"] != first["id"] and second["version"] == 1,
    )

    code, edited = call(
        "PATCH", f"/api/drafts/{second['id']}", {"version": 1, "text": "synthetic edit two"}
    )
    expect("second draft saves its edit", code == 200 and edited["version"] == 2)

    code, sent = call("POST", f"/api/drafts/{second['id']}/approve", {"version": 2})
    expect(
        "confirming records a simulated send of the exact saved text",
        code == 200
        and sent["status"] == "sent"
        and sent["text"] == "synthetic edit two"
        and "Simulated" in sent["receipt"],
    )

    code, _ = call("POST", f"/api/drafts/{second['id']}/approve", {"version": 2})
    expect("a duplicate approval is refused", code == 409)


def main():
    try:
        recipients = guard()
        if "--check-only" in sys.argv:
            return 0
        walkthrough(recipients)
    except Failed as exc:
        print("FAIL " + str(exc), file=sys.stderr)
        return 1
    except (urllib.error.URLError, TimeoutError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL could not complete the walkthrough: {type(exc).__name__}", file=sys.stderr)
        return 1
    print("PASS API walkthrough complete. All sends were simulated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
