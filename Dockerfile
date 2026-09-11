# The app on Cloudflare Containers.
#
# Why a container and not a Worker: `cloze`, `conjugation`, `patterns` and
# `verbs` all call Vabamorf at request time, and Vabamorf is a compiled C++
# Python extension. Workers run JavaScript and WASM, so an earlier plan in this
# repo — export everything to D1 and serve from a Worker — described an app that
# only looked things up. This one *generates*, so it needs a real Python process.

# ---------------------------------------------------------------------------
# Builder: produce the derived databases, then throw the toolchain away.
# ---------------------------------------------------------------------------
# 3.13, and only after CI ran the whole suite on it. estnltk publishes wheels
# for 3.11 through 3.14, but a wheel existing is not the same as Vabamorf's
# compiled extension and everything above it behaving -- so `tests.yml` runs a
# 3.11 and a 3.13 leg, and the 3.13 leg passes the morphology gate against
# TalTech's native gold forms, not merely the unit tests. 3.11 stays in that
# matrix because it is what this image shipped until now.
FROM python:3.13-slim AS builder

WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY eesti/ ./eesti/

# Derived from the public CC-BY-SA wordlist, so this is reproducible from
# scratch and nothing owner-only is baked into an image.
RUN python -m eesti.cli fetch-data \
 && python -m eesti.cli build \
 && python -m eesti.cli export \
 && rm -rf data/raw

# EKK's rection table is fetched separately and is allowed to fail.
#
# It is the one build step that depends on a third party being willing to talk
# to a datacenter IP, and EKI already returned 403 to a GitHub Actions runner
# on this exact URL. Chained with `&&` it would take the whole image down with
# it — so a build machine having a bad afternoon would cost the entire deploy.
#
# The cost of it failing is one topic: `rektsioon` reports "run `cli rections`
# once" and the other twenty generators are untouched. That is the right trade
# against an unbuildable image, and it is the same rule the rest of the app
# follows — own the core, let every third party be optional.
RUN python -m eesti.cli rections || \
    echo "WARNING: EKK rection table unavailable at build time; \
run 'python -m eesti.cli rections' later to enable the rektsioon topic."

# EKI's two downloads, if the person building the image has them.
#
# Neither is fetched, here or anywhere: EKI serve both behind a form asking who
# you are and what the material will be used in, and answering that is worth
# doing rather than stepping around. The learner downloads them once and drops
# them in `deploy/eki/`; this copies whatever is there.
#
# The directory always exists and always holds its README, so the COPY cannot
# fail on an empty build context -- a conditional COPY is not a thing Docker
# has, and an image that will not build because somebody has not filled in a
# form at EKI would be the wrong trade.
#
# Both write into `data/eesti.db`, which is baked into this image. That is the
# whole reason the build does it at all: the two imports are reference data,
# identical for everybody, and `vocab.db` -- where the learner definitions used
# to live -- travels in the state snapshot, which a restore replaces wholesale.
# Kept there they would survive until the first Cloud Run cold start.
#
# Without the files each command says what is missing and returns 1, so the
# `||` is doing real work: the image builds, the word list keeps its estimated
# levels, and the word card keeps Sõnaveeb's native-level wording.
COPY deploy/eki/ ./deploy/eki/
RUN python -m eesti.cli import-levels deploy/eki/A1A2B1.txt || \
    echo "NOTE: EKI level vocabulary not in the build context; \
words keep their estimated CEFR levels. See deploy/eki/README.md."
RUN python -m eesti.cli import-psv deploy/eki/psv_EKI_CCBY40.xml || \
    echo "NOTE: EKI learner dictionary not in the build context; \
word cards show Sonaveeb's native-level definition. See deploy/eki/README.md."

# ---------------------------------------------------------------------------
# Runtime
# ---------------------------------------------------------------------------
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY eesti/ ./eesti/
COPY --from=builder /build/data/ ./data/

# When this image was built, and from what.
#
# Written here, immediately after the code is copied, so the layer cache
# invalidates exactly when `eesti/` changes -- a stamp that survives a code
# change would be worse than none.
#
# It exists because of a question nothing could answer: a Python change was
# merged, the Worker redeployed, and the new endpoint was still missing from
# production. There was no way to tell whether the container build had not run
# yet, had failed, or had never been wired up at all. `built` answers that
# without any deploy-side configuration.
#
# `revision` is the exact commit, and needs the builder to pass it:
#   docker build --build-arg BUILD_REV="$COMMIT_SHA" .
# Unset it and the timestamp still answers the question that matters.
ARG BUILD_REV=""
RUN printf '{"built":"%s","revision":"%s"}\n' \
      "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$BUILD_REV" > /app/BUILD_INFO

# Harvested reading material is NOT baked in. Two reasons: re-running the ERR
# and Selges keeles harvest on every image build would hammer someone else's
# server for no reason, and that material is owner-only by licence, so it has no
# business inside a distributable image. Supply it at runtime — see
# docs/deploy.md — and without it the reading library is simply empty.
VOLUME ["/app/data/content"]
ENV EESTI_CONTENT_DB=/app/data/content/content.db

# Verified by building and running this image, not by reading it: the app
# starts, /api/health reports 160 316 words, Vabamorf generates a conditional
# drill in-container, an answer is recorded, and a snapshot survives destroying
# the container and creating a new one. Image is ~1.08 GB.

EXPOSE 8080
# `$PORT` rather than a literal: Cloud Run injects the port it expects the
# container to listen on, and a service configured with anything but 8080 would
# otherwise fail its health check with a container that is running perfectly.
# `exec` so uvicorn is PID 1 and gets Cloud Run's shutdown signal directly.
CMD ["sh", "-c", "exec python -m uvicorn eesti.app:app --host 0.0.0.0 --port ${PORT:-8080}"]
