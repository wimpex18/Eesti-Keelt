"""A secret belongs where the code that reads it runs, and nowhere else.

The Worker and the Cloud Run container read different variables; a key in the
wrong half is silently absent and the feature falls back (e.g. an LLM key stored
as a Worker secret leaves the grammar check offline and the Notion chain
inert). These tests read the deploy workflow, the Worker source and the scripts.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "deploy.yml"
WORKER = ROOT / "deploy" / "worker.ts"

#: Read by the Python app, therefore Cloud Run environment variables. The
#: Worker must never be given these.
CONTAINER_ONLY = ("OPENROUTER_API_KEY", "NVIDIA_API_KEY", "HF_TOKEN")

#: Read by the Worker, therefore Worker secrets. The VAPID pair signs and
#: encrypts reminders in `sendPush`; the Python app never reads it.
WORKER_SECRETS = ("CLOUD_RUN_URL", "PROXY_TOKEN", "STATE_TOKEN",
                  "VAPID_PUBLIC_KEY", "VAPID_PRIVATE_KEY")


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


def test_the_private_push_key_never_reaches_the_python_app():
    """It is a Worker secret. Read on Cloud Run it would do nothing, and a
    reminder would silently never be sent."""
    import subprocess

    found = subprocess.run(
        ["git", "grep", "-l", "VAPID_PRIVATE_KEY", "--", "eesti/"],
        cwd=ROOT, capture_output=True, text=True).stdout.split()
    # `cli push-keys` writes it into `.env`; nothing else in the app may read it.
    assert found in ([], ["eesti/cli/ops.py"]), found


@pytest.mark.parametrize("name", CONTAINER_ONLY)
def test_the_worker_source_never_reads_them(name, worker):
    """If the Worker ever legitimately needs one, this test should be changed
    deliberately rather than the secret quietly re-added to the workflow."""
    assert name not in worker


def test_there_is_a_script_for_setting_them_where_they_belong():
    script = ROOT / "deploy" / "set-llm-key.sh"
    assert script.exists()
    body = script.read_text(encoding="utf-8")
    # Read without echo and passed on stdin: not in shell history, not in the process
    # table, never printed.
    assert "read -rs" in body


class TestTheDeploymentCanSayWhetherTheKeyLanded:
    """A running deployment can be asked whether an explaining key is configured
    (`/api/engines`), since a missing key is otherwise invisible from outside.
    """

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
        monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "test-key")
        monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "test-account")
        got = client.get("/api/engines").json()
        assert got["can_explain"] is True

    def test_only_an_llm_is_credited_with_explaining(self, client):
        """Vabamorf and TartuNLP cannot explain in Russian, so they do not count as
        explaining engines.
        """
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
    """The scripts verify their own work: `set-llm-key.sh` reads the variable name back
    off the service.
    """

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
    """The image stamps its build time (and commit when passed), and health reports it,
    since the Worker and the app deploy by different routes.
    """

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
    """The smoke run compares the image build stamp with main's head commit, because a
    run fired by `deploy` usually sees the previous image; staleness warns rather
    than fails.
    """

    WORKFLOW = ROOT / ".github" / "workflows" / "smoke.yml"

    @classmethod
    def _step(cls) -> dict:
        import yaml

        doc = yaml.safe_load(cls.WORKFLOW.read_text(encoding="utf-8"))
        return doc["jobs"]["check"]["steps"][0]

    @classmethod
    def _script(cls) -> str:
        """The step's shell without its comments, so assertions match code, not prose."""
        return "\n".join(line for line in cls._step()["run"].splitlines()
                         if not line.lstrip().startswith("#"))

    def test_the_triggering_commit_reaches_the_script(self):
        """The triggering commit's timestamp reaches the script."""
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
        assert "image is current" in self._script()


class TestEveryDeployGetsChecked:
    """Every merge gets checked: smoke also runs on a daily schedule (off the hour), not
    only after `deploy`, which is filtered to Worker paths.
    """

    WORKFLOW = ROOT / ".github" / "workflows" / "smoke.yml"

    @classmethod
    def _doc(cls) -> dict:
        import yaml

        return yaml.safe_load(cls.WORKFLOW.read_text(encoding="utf-8"))

    @classmethod
    def _triggers(cls) -> dict:
        doc = cls._doc()
        # `on:` parses as the boolean True in YAML 1.1.
        return doc.get("on", doc.get(True))

    @classmethod
    def _script(cls) -> str:
        step = next(s for s in cls._doc()["jobs"]["check"]["steps"]
                    if "Check the deployment" in s["name"])
        return "\n".join(line for line in step["run"].splitlines()
                          if not line.lstrip().startswith("#"))

    def test_it_runs_on_a_schedule(self):
        """The only trigger that covers a merge touching neither the Worker
        paths nor anything else `deploy` watches — which is most of them."""
        assert "schedule" in self._triggers()

    def test_the_schedule_avoids_the_hour_mark(self):
        """Everybody's daily job is at :00, and the runner queue shows it."""
        for entry in self._triggers()["schedule"]:
            minute = entry["cron"].split()[0]
            assert minute not in ("0", "30"), entry["cron"]

    def test_the_deploy_trigger_survives(self):
        """It is still the fastest signal on the merges it covers. Deleting it
        would 'fix' the staleness warning by removing the run."""
        assert self._triggers()["workflow_run"]["workflows"] == ["deploy"]

    def test_it_does_not_fire_on_every_push(self):
        """`push: main` fires within a minute of every merge, always before
        Cloud Build finishes — so every run would warn STALE and the warning
        would become the thing people scroll past."""
        assert "push" not in self._triggers()


class TestAScheduledRunKnowsWhatToCompareAgainst:
    """On a schedule there is no triggering commit, so the run asks the GitHub API for
    main's head.
    """

    @classmethod
    def _step(cls) -> dict:
        import yaml

        doc = yaml.safe_load(
            (ROOT / ".github" / "workflows" / "smoke.yml").read_text(encoding="utf-8"))
        return next(s for s in doc["jobs"]["check"]["steps"]
                    if "Check the deployment" in s["name"])

    @classmethod
    def _script(cls) -> str:
        return "\n".join(line for line in cls._step()["run"].splitlines()
                          if not line.lstrip().startswith("#"))

    def test_the_token_and_repo_reach_the_step(self):
        env = self._step()["env"]
        assert "GH_TOKEN" in env and "REPO" in env

    def test_it_asks_the_api_for_mains_head(self):
        code = self._script()
        assert "commits/main" in code
        assert "commit.committer.date" in code

    def test_a_failed_lookup_warns_rather_than_failing(self):
        """Somebody else's bad minute is not this app's outage — the rule
        `net.py` and the eval workflow already follow."""
        code = self._script()
        chunk = code[code.index("commits/main") - 200:code.index("commits/main") + 700]
        assert "::warning::" in chunk
        assert "fail=1" not in chunk

    def test_a_stale_image_is_diagnosed_by_when_the_run_fired(self):
        """Diagnose staleness by elapsed time since main's head: minutes means the build is
        still running; a day means it failed or never ran.
        """
        code = self._script()
        assert "FAILED or never ran" in code
        assert "Cloud Build had not \\\nfinished yet" in code or "not \\" in code

    def test_the_diagnosis_is_made_by_the_clock_not_the_trigger(self):
        """Decided by the clock, not by what triggered the run."""
        code = self._script()
        assert "BUILD_WINDOW" in code and "date -u +%s" in code
        assert '"$WHEN" = "scheduled"' not in code


class TestASplitDeploymentIsNotAFlake:
    """Ask the deep check several times: instances disagreeing (a traffic split) is an
    error, not a flake.
    """

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
        """The split's fix is moving traffic, and the message says so."""
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
    """The summary field is `can_explain` (distinct from the per-engine `explains`),
    and the workflow reads JSON with `jq`, not grep.
    """

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

    def test_the_workflow_parses_json_instead_of_matching_text(self):
        workflow = (ROOT / ".github" / "workflows" / "smoke.yml").read_text()
        block = workflow.split("Asked five times")[1][:800]
        assert "jq -r" in block
        assert "grep" not in block


class TestTheKeyListIsNotHandMaintained:
    """The key list comes from the app (`env.KNOWN_KEYS`), not a second hand-written
    list in a script.
    """

    SET = ROOT / "deploy" / "set-llm-key.sh"

    def test_the_script_reads_the_apps_own_list(self):
        body = self.SET.read_text(encoding="utf-8")
        assert "KNOWN_KEYS" in body, "the allowed names must come from env.py"

    def test_no_hardcoded_alternation_of_key_names(self):
        body = self.SET.read_text(encoding="utf-8")
        assert "OPENROUTER_API_KEY|NVIDIA_API_KEY" not in body

    def test_every_key_the_app_reads_can_be_set(self):
        """Including the ones that are not LLM keys. The script's name is
        narrower than its job, which is a naming wart, not a limit."""
        import re
        import shlex
        import subprocess

        from eesti.env import KNOWN_KEYS

        body = self.SET.read_text(encoding="utf-8")
        # Run the same extraction the script runs, against the same file.
        script = re.search(r"sed -n '(/\^KNOWN_KEYS[^']*)'", body)
        assert script, "the extraction command changed shape"
        got = subprocess.run(
            ["sh", "-c",
             f"sed -n '{script.group(1)}' {shlex.quote(str(ROOT / 'eesti' / 'env.py'))} "
             r"""| sed -n 's/^ *"\([A-Z0-9_]*\)".*/\1/p'"""],
            capture_output=True, text=True, check=True).stdout.split()
        assert set(got) == set(KNOWN_KEYS), (
            f"the script would accept {sorted(got)}, the app reads "
            f"{sorted(KNOWN_KEYS)}"
        )


class TestTheLiveDictionaryIsChecked:
    """`EKILEX_API_KEY` set on Cloud Run is not the same as Ekilex answering the
    card: the key can sit on a revision without traffic, or beside an image
    older than the code that reads it. Only asking the card tells."""

    @staticmethod
    def _script() -> str:
        import yaml

        doc = yaml.safe_load((ROOT / ".github" / "workflows" / "smoke.yml").read_text(encoding="utf-8"))
        step = next(s for s in doc["jobs"]["check"]["steps"] if "Check the deployment" in s["name"])
        return "\n".join(l for l in step["run"].splitlines() if not l.lstrip().startswith("#"))

    def test_the_card_is_asked_which_dictionary_answered(self):
        code = self._script()
        assert "/api/enrich/" in code and ".definition_source" in code and ".russian_source" in code
        assert "ekilex)" in code and "sonapi)" in code

    def test_a_missing_key_warns_rather_than_fails(self):
        code = self._script()
        chunk = code[code.index("/api/enrich/"):code.index("esac", code.index("/api/enrich/"))]
        assert "::warning::" in chunk and "fail=1" not in chunk

    def test_the_word_it_asks_is_not_answered_by_the_seed(self):
        """A seeded word's Russian would not say which dictionary answered;
        the check reads `definition_source`, and the word is not seeded anyway."""
        from eesti import meaning

        assert "poiss" not in meaning._seed()

    def test_check_service_names_the_key_and_its_cost(self):
        script = (ROOT / "deploy" / "check-service.sh").read_text(encoding="utf-8")
        assert "EKILEX_API_KEY|" in script
