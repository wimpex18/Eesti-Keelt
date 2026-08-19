"""A secret belongs where the code that reads it runs, and nowhere else.

The deployment has two halves, and each reads a different set of environment
variables. Putting one in the wrong half is silent: nothing errors, the value
simply is not there, and the feature degrades into its fallback.

That happened. `OPENROUTER_API_KEY` is read by `eesti/providers/llm.py`, which
runs in the container on Cloud Run. The deploy workflow stored it as a *Worker*
secret, where nothing reads it — so the grammar checker sat permanently in
offline mode (object-case candidates and typos, no corrections), which also
meant no correction ever carried a fix, no "log it" button ever rendered, and
nothing ever reached the Notion log. A whole chain, inert, because a credential
was one hop away from the process that needed it.

It is also the worse half of the trade: all the exposure of holding a key, none
of the benefit.

These tests read the deploy workflow and the Worker source, and hold the line.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "deploy.yml"
WORKER = ROOT / "deploy" / "worker.ts"

#: Read by the Python app, therefore Cloud Run environment variables. The
#: Worker must never be given these.
CONTAINER_ONLY = ("OPENROUTER_API_KEY", "GROQ_API_KEY", "ANTHROPIC_API_KEY")

#: Read by the Worker, therefore Worker secrets.
WORKER_SECRETS = ("CLOUD_RUN_URL", "PROXY_TOKEN", "STATE_TOKEN")


@pytest.fixture(scope="module")
def workflow() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def worker() -> str:
    return WORKER.read_text(encoding="utf-8")


@pytest.mark.parametrize("name", CONTAINER_ONLY)
def test_container_keys_are_not_pushed_to_the_worker(name, workflow):
    assert f'put {name}' not in workflow, (
        f"{name} is read by the Python app on Cloud Run. Stored as a Worker "
        f"secret it does nothing, and the feature that needs it degrades "
        f"silently. Use deploy/set-llm-key.sh."
    )


@pytest.mark.parametrize("name", WORKER_SECRETS)
def test_the_workers_own_secrets_are_still_pushed(name, workflow):
    """The opposite mistake would break the deployment outright, but loudly."""
    assert f'put {name}' in workflow


@pytest.mark.parametrize("name", CONTAINER_ONLY)
def test_the_worker_source_never_reads_them(name, worker):
    """If the Worker ever legitimately needs one, this test should be changed
    deliberately rather than the secret quietly re-added to the workflow."""
    assert name not in worker


def test_there_is_a_script_for_setting_them_where_they_belong():
    script = ROOT / "deploy" / "set-llm-key.sh"
    assert script.exists()
    body = script.read_text(encoding="utf-8")
    # Read without echo and passed on stdin: not in shell history, not in the
    # process table, never printed.
    assert "read -rs" in body
