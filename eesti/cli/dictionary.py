"""Sõnastik's model-drafted glosses (`eesti/dictionary_glosses.py`).

    cli dictionary words [--limit N]       # the bounded word set still to draft
    cli dictionary glosses [--limit N]     # Opus 5.5 drafts English and Ukrainian,
                                           # code gates, Haiku 5.5 translates back
                                           # blind, code keeps what names the word
    cli dictionary glosses --draft-batch ID           # resume after the drafting batch
    cli dictionary glosses --check-batch ID --drafts FILE   # resume after the check
    cli dictionary import [PATH]           # content/dictionary/glosses.jsonl → the
                                           # words database, every line re-checked

Needs `ANTHROPIC_API_KEY` (the git-ignored `.env`) and the word list with EKI's
levels and EVS (`cli build`, `cli import-levels`, `cli import-evs`).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ._helpers import words_db


def _words(args):
    from .. import config

    return words_db(getattr(args, "words_db", None) or config.DB_PATH)


def _root(args) -> Path:
    from ..dictionary_glosses import ROOT

    return Path(args.root) if getattr(args, "root", None) else ROOT


def cmd_dictionary_words(args: argparse.Namespace) -> int:
    """List the words a run would draft for."""
    from ..dictionary_glosses import candidates

    words = _words(args)
    if words is None:
        return 1
    found = candidates(words, _root(args), args.limit)
    for w in found:
        print(f"{w.lemma}\t{w.pos}\t{'; '.join(w.russian)}")
    print(f"{len(found)} words to draft")
    return 0


def _client():
    import anthropic

    return anthropic.Anthropic(max_retries=2)


def _check(client, root: Path, drafts, wait: float) -> int:
    """Submit the blind back-translation, wait, judge, write."""
    from ..dictionary_glosses import CHECKER, back_requests, log_batch
    from ..material.blind import wait as wait_for

    requests, groups = back_requests(drafts)
    if not requests:
        print("nothing to check")
        return 0
    batch = client.messages.batches.create(requests=requests).id
    log_batch(root, batch=batch, kind="check", model=CHECKER, items=len(drafts),
              requests=len(requests))
    print(f"back-translation batch {batch}: {len(drafts)} glosses in {len(requests)} requests")
    if not wait_for(client, batch, limit=wait):
        print(f"not finished; resume with --check-batch {batch} --drafts <the drafts file>")
        return 2
    return _judge(client, root, batch, groups)


def _judge(client, root: Path, batch: str, groups) -> int:
    from ..dictionary_glosses import CHECKER, append, collect, cost, judge, log_batch

    texts, usage = collect(client, batch)
    kept, refused = judge(texts, groups, batch)
    append(root / "glosses.jsonl", kept)
    append(root / "rejected.jsonl", refused)
    spent = cost(CHECKER, usage)
    log_batch(root, batch=batch, kind="check-result", model=CHECKER, kept=len(kept),
              refused=len(refused), usage=usage, dollars=spent)
    print(f"kept {len(kept)}, refused {len(refused)} after the back-translation; ${spent}")
    return 0


def cmd_dictionary_glosses(args: argparse.Namespace) -> int:
    """Draft, gate, back-translate and judge, waiting for each batch."""
    from ..dictionary_glosses import (MODEL, _done, append, back_requests, candidates, collect,
                                      cost, draft_requests, gate_drafts, load_drafts, log_batch,
                                      save_drafts)
    from ..material.blind import wait as wait_for

    root = _root(args)
    client = _client()
    if args.check_batch:
        if not args.drafts:
            print("--check-batch needs --drafts, the file the drafting step wrote")
            return 1
        _, groups = back_requests(load_drafts(Path(args.drafts)))
        return _judge(client, root, args.check_batch, groups)

    words = _words(args)
    if words is None:
        return 1
    found = candidates(words, root, args.limit)
    requests, groups = draft_requests(found)
    if args.draft_batch:
        batch = args.draft_batch
    else:
        if not requests:
            print("every word of the set has a kept or refused draft")
            return 0
        batch = client.messages.batches.create(requests=requests).id
        log_batch(root, batch=batch, kind="draft", model=MODEL, words=len(found),
                  requests=len(requests))
        print(f"drafting batch {batch}: {len(found)} words in {len(requests)} requests")
    if not wait_for(client, batch, limit=args.wait):
        print(f"not finished; resume with --draft-batch {batch} (same --limit)")
        return 2
    texts, usage = collect(client, batch)
    drafts, refused = gate_drafts(texts, groups, batch, _done(root))
    append(root / "rejected.jsonl", refused)
    spent = cost(MODEL, usage)
    log_batch(root, batch=batch, kind="draft-result", model=MODEL, gated=len(drafts),
              refused=len(refused), usage=usage, dollars=spent)
    path = save_drafts(root, drafts, batch)
    print(f"{len(drafts)} drafts passed the gates, {len(refused)} refused; ${spent}; {path}")
    return _check(client, root, drafts, args.wait)


def cmd_dictionary_import(args: argparse.Namespace) -> int:
    """Import the checked glosses into the words database, re-checking each."""
    from ..dictionary import import_glosses

    words = _words(args)
    if words is None:
        return 1
    stats = import_glosses(words, Path(args.path) if args.path else None)
    print(f"{stats['stored']} glosses imported, {stats['refused']} refused")
    return 1 if stats["refused"] else 0


def cmd_dictionary(args: argparse.Namespace) -> int:
    return args.dictionary_func(args)


def register(sub) -> None:
    """Register this group's commands beside their handlers."""
    p = sub.add_parser("dictionary", help="Sõnastik: model-drafted English and Ukrainian "
                       "glosses, checked by a blind back-translation")
    p.set_defaults(func=cmd_dictionary)
    actions = p.add_subparsers(dest="dictionary_command", required=True)

    a = actions.add_parser("words", help="the bounded word set still to draft")
    a.add_argument("--limit", type=int, default=None)
    a.add_argument("--root", default=None, help="defaults to content/dictionary")
    a.add_argument("--words-db", default=None)
    a.set_defaults(dictionary_func=cmd_dictionary_words)

    a = actions.add_parser("glosses", help="draft (Opus 5.5), gate, back-translate "
                           "(Haiku 5.5) and keep what names the word again")
    a.add_argument("--limit", type=int, default=None)
    a.add_argument("--draft-batch", default=None, help="collect this drafting batch")
    a.add_argument("--check-batch", default=None, help="judge this back-translation batch")
    a.add_argument("--drafts", default=None, help="the drafts file a --check-batch judges")
    a.add_argument("--wait", type=float, default=6 * 3600,
                   help="seconds to wait for each batch (default 6 h)")
    a.add_argument("--root", default=None, help="defaults to content/dictionary")
    a.add_argument("--words-db", default=None)
    a.set_defaults(dictionary_func=cmd_dictionary_glosses)

    a = actions.add_parser("import", help="content/dictionary/glosses.jsonl into the words database")
    a.add_argument("path", nargs="?", default=None)
    a.add_argument("--words-db", default=None)
    a.set_defaults(dictionary_func=cmd_dictionary_import)
