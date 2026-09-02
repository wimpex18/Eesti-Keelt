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


class TestTheDeploymentCanSayWhetherTheKeyLanded:
    """`test_the_workflow_does_not_push_the_llm_key_to_the_worker` above stops
    the mistake being made again. This is the other half: a way to ask a
    *running* deployment whether the key is where the code that reads it runs.

    Without it the failure is invisible from outside — health is green, the
    checker serves offline mode, and because only an explained correction
    offers a "log it" button, the Notion chain is inert too."""

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient

        from eesti import app as app_module

        return TestClient(app_module.app)

    def test_it_reports_every_engine_in_the_chain(self, client):
        from eesti.providers.grammar import build_chain

        got = client.get("/api/engines").json()
        assert [e["name"] for e in got["engines"]] == [p.name for p in build_chain()]

    def test_it_costs_no_quota(self, client, monkeypatch):
        """Configuration only. If this ever called a provider it could not be
        in the smoke test, which runs on every deploy."""
        import urllib.request

        def forbidden(*a, **k):  # pragma: no cover - the point is it is unused
            raise AssertionError("/api/engines made a network call")

        monkeypatch.setattr(urllib.request, "urlopen", forbidden)
        assert client.get("/api/engines").status_code == 200

    def test_it_cannot_explain_with_no_llm_key(self, client, monkeypatch):
        """The exact production state that looked healthy: offline mode."""
        from eesti.providers.llm import PROVIDERS

        for p in PROVIDERS.values():
            monkeypatch.delenv(p.key_env, raising=False)
        assert client.get("/api/engines").json()["can_explain"] is False

    def test_it_can_explain_once_the_key_is_on_this_process(self, client,
                                                            monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        got = client.get("/api/engines").json()
        assert got["can_explain"] is True

    def test_only_an_llm_is_credited_with_explaining(self, client):
        """Vabamorf reports evidence without judgement, and TartuNLP answers in
        Estonian with no language parameter — neither can teach a Russian
        speaker why the case was wrong."""
        got = client.get("/api/engines").json()
        for e in got["engines"]:
            assert e["explains"] == e["name"].startswith("llm:")

    def test_the_smoke_test_asks(self):
        workflow = (ROOT / ".github" / "workflows" / "smoke.yml").read_text()
        assert "/api/engines" in workflow
        assert ".can_explain" in workflow


class TestTheDeepCheckIsOptIn:
    """The configuration check cannot tell a working key from a revoked one.
    Sending one real sentence can — but it spends a request of a 50/day free
    tier, so it belongs on a manual switch, not on every deploy."""

    WORKFLOW = ROOT / ".github" / "workflows" / "smoke.yml"

    @pytest.fixture(scope="class")
    @classmethod
    def workflow(cls) -> str:
        return cls.WORKFLOW.read_text(encoding="utf-8")

    def test_it_does_not_run_automatically(self, workflow):
        import yaml

        parsed = yaml.safe_load(workflow)
        # `on:` parses as the boolean True in YAML 1.1.
        triggers = parsed.get("on", parsed.get(True))
        assert triggers["workflow_dispatch"]["inputs"]["deep"]["default"] is False

    def test_it_is_guarded_by_the_switch(self, workflow):
        assert 'if [ "$DEEP" = "true" ]' in workflow

    def test_it_probes_the_documented_weakness(self, workflow):
        """If one sentence is going to cost a request, it should be the one
        this whole app is pointed at: a completed object that must be genitive
        `raamatu`, not partitive `raamatut`."""
        assert "raamatut" in workflow

    def test_only_an_llm_engine_counts_as_a_pass(self, workflow):
        """`vabamorf-offline` answering is exactly the failure being checked
        for — an answer, with no explanation behind it."""
        assert "llm:*)" in workflow


class TestTheScriptsCheckTheirOwnWork:
    """`set-llm-key.sh` printed "Done" and told the operator to go and look.
    A run of it left the service without the variable, and the only symptom
    was corrections arriving without explanations — so nobody looked, and the
    grammar checker sat in offline mode until the deployment was asked
    directly."""

    SET = ROOT / "deploy" / "set-llm-key.sh"
    CHECK = ROOT / "deploy" / "check-service.sh"

    def test_setting_the_key_verifies_it_landed(self):
        body = self.SET.read_text(encoding="utf-8")
        assert "spec.template.spec.containers[0].env.name" in body
        assert "exit 1" in body.split("Verifying")[1]

    def test_it_warns_when_traffic_is_on_an_older_revision(self):
        """A variable set on the newest revision does nothing while an older
        one serves — configured, verified, and still not in effect."""
        body = self.SET.read_text(encoding="utf-8")
        assert "update-traffic" in body

    def test_neither_script_ever_reads_a_value(self):
        """Names are enough to answer "is it set", and a value printed into a
        Cloud Shell scrollback is a value leaked."""
        for path in (self.SET, self.CHECK):
            body = path.read_text(encoding="utf-8")
            assert "env.value" not in body, f"{path.name} fetches a value"

    def test_the_read_only_script_changes_nothing(self):
        body = self.CHECK.read_text(encoding="utf-8")
        for mutating in ("services update", "services delete", "services replace"):
            assert mutating not in body.replace("update-traffic", ""), mutating


class TestTheDeploymentSaysWhichBuildItIs:
    """A Python change was merged, the Worker redeployed green, and the new
    endpoint was still absent from production. Nothing could distinguish
    "the container build has not run yet" from "the build failed" from "there
    is no trigger" — the Worker and the app deploy by different routes, so a
    green deploy workflow says nothing about the app.

    The image stamps itself; health reports the stamp."""

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient

        from eesti import app as app_module

        return TestClient(app_module.app)

    def test_health_carries_the_stamp(self, client):
        got = client.get("/api/health").json()
        assert "built" in got and "revision" in got

    def test_a_source_checkout_says_so_rather_than_guessing(self, client):
        """There is no image and no build here. `null` is the honest answer;
        inventing a date would make the field useless for its one purpose."""
        assert client.get("/api/health").json()["built"] is None

    def test_the_stamp_is_written_after_the_code_is_copied(self):
        """Written before, the layer cache would freeze it and the stamp would
        outlive the code it describes — worse than not having one."""
        body = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        runtime = body.split("# Runtime")[1]
        assert runtime.index("COPY eesti/") < runtime.index("BUILD_INFO")

    def test_the_commit_is_optional(self):
        """A Cloud Build trigger configured against a plain Dockerfile passes
        no build args. The timestamp alone answers the question that prompted
        this, so requiring the commit would mean shipping nothing."""
        body = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        assert 'ARG BUILD_REV=""' in body

    def test_the_smoke_test_reports_it(self):
        workflow = (ROOT / ".github" / "workflows" / "smoke.yml").read_text()
        assert ".built" in workflow


class TestTheSmokeRunSaysWhenItIsLookingAtTheOldImage:
    """Reporting the stamp was half the job; nothing compared it to anything.

    `smoke` fires on `deploy` completing, and `deploy` deploys the *Worker*.
    The app is a separate container built by a Cloud Build trigger on `main`,
    which nothing in this repository can observe — so the smoke run that fires
    on a merge is looking at the previous image. Not usually: structurally,
    every time.

    Measured on the merge of PR #30. Merge at 20:11:20Z; the smoke run fired at
    20:12:11Z and reported an image built 14:39:50Z, five and a half hours old,
    with every check under it green; the new image landed at 20:14:20Z, two
    minutes *after* the run that was meant to be checking it. That merge
    carried the Python 3.13 runtime move, whose one open risk was whether the
    image builds at all — and a green tick about the wrong deployment reads
    exactly like a green tick about the right one.
    """

    WORKFLOW = ROOT / ".github" / "workflows" / "smoke.yml"

    @classmethod
    def _step(cls) -> dict:
        import yaml

        doc = yaml.safe_load(cls.WORKFLOW.read_text(encoding="utf-8"))
        return doc["jobs"]["check"]["steps"][0]

    @classmethod
    def _script(cls) -> str:
        """The step's shell without its comments.

        Every assertion here searches the `run:` for a construct that the
        comment above that construct also names. Two guards written the same
        way last week passed on the prose while the code they guarded was
        deleted, so the prose is stripped before looking.
        """
        return "\n".join(line for line in cls._step()["run"].splitlines()
                         if not line.lstrip().startswith("#"))

    def test_the_triggering_commit_reaches_the_script(self):
        """`github.event.workflow_run.head_commit.timestamp` is the only half
        the run was missing — it already had the build stamp."""
        env = self._step()["env"]
        assert "TRIGGER_COMMIT_AT" in env
        assert "workflow_run.head_commit.timestamp" in env["TRIGGER_COMMIT_AT"]

    def test_the_two_are_actually_compared(self):
        code = self._script()
        assert "TRIGGER_COMMIT_AT" in code, "the value arrives and is never read"
        assert "-lt" in code and "date -u -d" in code

    def test_a_stale_image_warns_rather_than_fails(self):
        """A stale image inside the Cloud Build window is the normal, correct
        state. A check that failed on every merge is a check people learn to
        scroll past, and then it is worth less than nothing."""
        code = self._script()
        stale = code[code.index("STALE IMAGE") - 400:code.index("STALE IMAGE") + 400]
        assert "::warning::" in stale
        assert "fail=1" not in stale

    def test_it_still_fires_on_the_deploy_it_cannot_see(self):
        """The whole fix is about that trigger's blind spot. Removing the
        trigger would 'fix' the warning by removing the run."""
        import yaml

        doc = yaml.safe_load(self.WORKFLOW.read_text(encoding="utf-8"))
        # `on:` parses as the boolean True in YAML 1.1.
        triggers = doc.get("on", doc.get(True))
        assert triggers["workflow_run"]["workflows"] == ["deploy"]

    def test_a_manual_run_has_nothing_to_compare_against(self):
        """`workflow_run.head_commit` is empty on a dispatch, and there is no
        checkout here to ask git. Saying nothing beats comparing against an
        empty string and reporting every manual run as stale."""
        code = self._script()
        assert '[ -n "$TRIGGER_COMMIT_AT" ]' in code

    def test_the_good_case_is_said_out_loud(self):
        """Silence on success means the reader cannot tell 'checked, and the
        image is current' from 'never checked'. That distinction is the entire
        subject of this class."""
        assert "post-merge" in self._script()


class TestASplitDeploymentIsNotAFlake:
    """Production answered the same question two ways within a minute:
    `/api/engines` reported an LLM configured while `/api/check` fell through
    to offline mode. Not a contradiction — two revisions serving, only one
    carrying the key, and each request landing wherever it landed.

    Asked once, that reads as a flake and gets re-run until it passes. Asked
    five times, disagreement between instances is itself the finding, and it
    is an error rather than a warning: an app that works or does not depending
    on which instance answers is not a supported state, unlike having no key
    at all."""

    WORKFLOW = ROOT / ".github" / "workflows" / "smoke.yml"

    @pytest.fixture(scope="class")
    @classmethod
    def workflow(cls) -> str:
        return cls.WORKFLOW.read_text(encoding="utf-8")

    def test_it_asks_more_than_once(self, workflow):
        block = workflow.split("Asked five times")[1][:900]
        assert "for _ in 1 2 3 4 5" in block

    def test_disagreement_fails_the_run(self, workflow):
        block = workflow.split('elif [ "$kinds" -gt 1 ]')[1][:600]
        assert "::error::" in block
        assert "fail=1" in block

    def test_it_names_the_fix(self, workflow):
        """A split is fixed by moving traffic, not by setting the key again."""
        block = workflow.split('elif [ "$kinds" -gt 1 ]')[1][:600]
        assert "update-traffic" in block

    def test_the_counting_survives_set_e(self, workflow):
        """The step runs under `bash -e`. `[ x -gt 0 ] && n=$((n+1))` returns
        non-zero when the test fails, which ends the step — so the counters
        are `if` blocks."""
        block = workflow.split("kinds=0")[1][:400]
        assert "&&" not in block.split("fi")[0]
        assert block.lstrip().startswith("if [")


class TestTheSummaryFieldCannotBeConfusedForAPerEngineOne:
    """The check read the response body with `grep -q '"explains":true'`. Each
    engine carries a field of that name too, and it is true for every `llm:`
    provider whether or not that provider is available — so the grep matched a
    per-engine field on an unavailable provider and reported the chain healthy
    while production was in offline mode.

    Worse than a missed check: it contradicted the deep check in the same run,
    and I spent a round diagnosing a traffic split that did not exist.

    Two fixes, both needed. The summary field has its own name, and the
    workflow reads JSON with jq rather than by matching text."""

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient

        from eesti import app as app_module

        return TestClient(app_module.app)

    def test_the_summary_field_has_a_name_of_its_own(self, client, monkeypatch):
        from eesti.providers.llm import PROVIDERS

        for p in PROVIDERS.values():
            monkeypatch.delenv(p.key_env, raising=False)
        got = client.get("/api/engines").json()
        assert "explains" not in got, (
            "a top-level field sharing a name with a per-item field is a trap "
            "for every line-oriented reader"
        )
        assert got["can_explain"] is False

    def test_the_body_still_contains_the_string_that_fooled_the_grep(self, client,
                                                                     monkeypatch):
        """Not incidental — it is why the rename was the fix rather than a
        tidier regex. Any check matching text against this body can still be
        misled; only reading the named field cannot."""
        from eesti.providers.llm import PROVIDERS

        for p in PROVIDERS.values():
            monkeypatch.delenv(p.key_env, raising=False)
        body = client.get("/api/engines").text
        assert '"explains":true' in body
        assert '"can_explain":false' in body

    def test_the_workflow_parses_json_instead_of_matching_text(self):
        workflow = (ROOT / ".github" / "workflows" / "smoke.yml").read_text()
        block = workflow.split("Asked five times")[1][:800]
        assert "jq -r" in block
        assert "grep" not in block


class TestTheKeyListIsNotHandMaintained:
    """`check-service.sh` reported NOTION_TOKEN missing and said what its
    absence costs; `set-llm-key.sh` then refused to set it, because it carried
    its own hardcoded list of four names. Two lists of the same thing become
    two different lists — the same failure as the hand-written tab list, one
    layer down."""

    SET = ROOT / "deploy" / "set-llm-key.sh"

    def test_the_script_reads_the_apps_own_list(self):
        body = self.SET.read_text(encoding="utf-8")
        assert "KNOWN_KEYS" in body, "the allowed names must come from env.py"

    def test_no_hardcoded_alternation_of_key_names(self):
        body = self.SET.read_text(encoding="utf-8")
        assert "OPENROUTER_API_KEY|GROQ_API_KEY" not in body

    def test_every_key_the_app_reads_can_be_set(self):
        """Including the ones that are not LLM keys. The script's name is
        narrower than its job, which is a naming wart, not a limit."""
        import re
        import subprocess

        from eesti.env import KNOWN_KEYS

        body = self.SET.read_text(encoding="utf-8")
        # Run the same extraction the script runs, against the same file.
        script = re.search(r"sed -n '(/\^KNOWN_KEYS[^']*)'", body)
        assert script, "the extraction command changed shape"
        got = subprocess.run(
            ["sh", "-c",
             f"sed -n '{script.group(1)}' {ROOT / 'eesti' / 'env.py'} "
             r"""| sed -n 's/^ *"\([A-Z0-9_]*\)".*/\1/p'"""],
            capture_output=True, text=True, check=True).stdout.split()
        assert set(got) == set(KNOWN_KEYS), (
            f"the script would accept {sorted(got)}, the app reads "
            f"{sorted(KNOWN_KEYS)}"
        )
