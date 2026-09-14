# The app on Google Cloud Run. A container, not a Worker: drills are generated
# with Vabamorf, a compiled C++ Python extension (docs/deploy.md).

# ---------------------------------------------------------------------------
# Builder: produce the derived databases, then throw the toolchain away.
# ---------------------------------------------------------------------------
# Python 3.14.7, pinned to the patch: the image, CI, the eval and local `.venv`
# run the same interpreter.
FROM python:3.14.7-slim AS builder

WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY eesti/ ./eesti/

# Derived from the public CC-BY-SA word list; nothing owner-only is baked in.
RUN python -m eesti.cli fetch-data \
 && python -m eesti.cli build \
 && python -m eesti.cli export \
 && rm -rf data/raw

# EKK's rection table comes from EKI and may refuse a datacenter IP: a failure
# costs the `rektsioon` topic, not the image.
RUN python -m eesti.cli rections || \
    echo "WARNING: EKK rection table unavailable at build time; \
run 'python -m eesti.cli rections' later to enable the rektsioon topic."

# EKI's CC BY 4.0 dictionaries, committed gzipped in `deploy/eki/` (see its
# README). Reference data goes into `data/eesti.db` in the image — never into a
# learner database, which a state restore replaces. Each import ends in `||` so
# a missing or unreadable file costs one feature; `/api/health` `reference`
# counts and the smoke workflow report what is missing.
COPY deploy/eki/ ./deploy/eki/
RUN python -m eesti.cli import-levels deploy/eki/A1A2B1.txt || \
    echo "NOTE: EKI level vocabulary not in the build context; \
words keep their estimated CEFR levels. See docs/sources.md."
RUN python -m eesti.cli import-psv deploy/eki/psv_EKI_CCBY40.xml.gz || \
    echo "NOTE: EKI learner dictionary not in the build context; \
word cards show Sonaveeb's native-level definition. See docs/sources.md."
RUN python -m eesti.cli import-evs deploy/eki/evs_EKI_CCBY40.xml.gz || \
    echo "NOTE: EKI Estonian-Russian dictionary not in the build context; \
word cards show Sonaveeb's Russian only. See docs/sources.md."
RUN python -m eesti.cli import-vsl deploy/eki/vsl_EKI_CCBY40.xml.gz || \
    echo "NOTE: EKI foreign-words lexicon not in the build context. See docs/sources.md."
RUN python -m eesti.cli import-har deploy/eki/har_EKI_CCBY40.xml.gz || \
    echo "NOTE: EKI education terms not in the build context. See docs/sources.md."
RUN python -m eesti.cli import-ekss deploy/eki/ekss_EKI_CCBY40.xml.gz || \
    echo "NOTE: EKI explanatory dictionary not in the build context. See docs/sources.md."

# ---------------------------------------------------------------------------
# Runtime
# ---------------------------------------------------------------------------
FROM python:3.14.7-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY eesti/ ./eesti/
COPY --from=builder /build/data/ ./data/
# The hand-written glossary is tracked, not built, so copy it explicitly.
COPY data/seed_glossary.tsv ./data/seed_glossary.tsv

# Build stamp for /api/health (`built`, `revision`), written right after the
# code is copied so it changes whenever `eesti/` does. Pass the commit with
# `--build-arg BUILD_REV="$COMMIT_SHA"`.
ARG BUILD_REV=""
RUN printf '{"built":"%s","revision":"%s"}\n' \
      "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$BUILD_REV" > /app/BUILD_INFO

# The harvested corpus is owner-only and not baked in; it is pushed at runtime
# (docs/deploy.md). Without it the reading library is empty.
VOLUME ["/app/data/content"]
ENV EESTI_CONTENT_DB=/app/data/content/content.db

EXPOSE 8080
# Cloud Run injects $PORT; `exec` makes uvicorn PID 1 so it receives SIGTERM.
CMD ["sh", "-c", "exec python -m uvicorn eesti.app:app --host 0.0.0.0 --port ${PORT:-8080}"]
