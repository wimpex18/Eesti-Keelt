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
FROM python:3.11-slim AS builder

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

# ---------------------------------------------------------------------------
# Runtime
# ---------------------------------------------------------------------------
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY eesti/ ./eesti/
COPY --from=builder /build/data/ ./data/

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
CMD ["python", "-m", "uvicorn", "eesti.app:app", "--host", "0.0.0.0", "--port", "8080"]
