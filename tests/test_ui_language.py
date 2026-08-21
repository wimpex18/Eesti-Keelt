"""Which language each part of the interface is written in.

`CLAUDE.md` states the rule before it states anything else, because getting it
wrong is not cosmetic: the learner is a Russian speaker learning Estonian.

  * **UI labels stay Estonian** — `Kirjutamine`, `Kuulamine`, `Rada`. They are
    the words printed on the exam paper, and a learner who has only ever seen
    "Письмо" has to translate under time pressure on the day.
  * **Grammar terms stay Estonian** — they have to be learned, and a
    translation would have to be unlearned.
  * **Anything explaining, warning or instructing is Russian** — "a caveat
    nobody can read is not a caveat".

Audited 2026-08-21 against the rendered page and it had drifted three ways at
once: explanatory strings still in Estonian (`Ükski osa ei tohi olla null.`,
`Kuula ja kirjuta üles.`), the readiness verdict in Estonian above its own
Russian reasons, and the path state badges in **English** — `REFERENCE`,
`READY`, `LOCKED` — which serves neither language.

The fix keeps the Estonian and puts Russian beside it, so the label still
teaches and the interface is still usable.
"""

from __future__ import annotations

import html
import re
from pathlib import Path

import pytest

PAGE = Path(__file__).resolve().parents[1] / "eesti" / "web" / "index.html"


CYRILLIC = re.compile(r"[\u0400-\u04ff]")
INTERPOLATION = re.compile(r"\$\{[^{}]*\}")
# A run that carries any of these is JavaScript that happened to end in a dot,
# not a sentence shown to anybody.
CODEISH = re.compile(r"[;{}`]|=>|===|!==|\|\||&&|\$\(")


def ui_sentences(page: str):
    """Every run of user-facing text on the page that ends like a sentence.

    Covers the HTML body and the template literals the script renders from,
    by reading text between tags rather than parsing either -- nested template
    literals make backtick matching unreliable, and `>...<` does not care.
    Comments are stripped first so prose *about* the code is not mistaken for
    prose *in* it, and `${...}` is blanked so an interpolated value cannot
    complete a sentence that is not really there.
    """
    src = re.sub(r"<!--.*?-->", "", page, flags=re.S)
    src = re.sub(r"<style.*?</style>", "", src, flags=re.S)
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    src = re.sub(r"^\s*//.*$", "", src, flags=re.M)
    # Entities first. `&#10;` is a line break written with a semicolon in it,
    # and the semicolon made the CODEISH filter below discard the whole
    # attribute as JavaScript -- which is how the writing placeholder stayed
    # Estonian while this check reported the page clean.
    src = html.unescape(src)
    src = INTERPOLATION.sub("\x00", src)

    chunks = re.findall(r">([^<>]{4,400})<", src)
    chunks += [m.group(1) or m.group(2) for m in
               re.finditer(r'"([^"\\\n]{4,300})"|\'([^\'\\\n]{4,300})\'', src)]
    # The attributes a person actually reads or hears. `placeholder` is where
    # the writing screen's instruction lived: it spans two lines via `&#10;`,
    # so neither the text-between-tags pass nor the single-line literal pass
    # above could see it, and the semicolon inside the entity made the CODEISH
    # filter throw the whole string away as JavaScript.
    chunks += [m.group(1) for m in re.finditer(
        r'(?:placeholder|title|aria-label|alt)\s*=\s*"([^"]{4,400})"', src)]
    for chunk in chunks:
        for run in re.split(r"(?<=[.!?])\s+", chunk):
            run = " ".join(run.split())
            if not run.endswith((".", "!", "?")):
                continue
            if "\x00" in run or CODEISH.search(run) or len(run.split()) < 3:
                continue
            yield run


def cyrillic(s: str) -> bool:
    return any("Ѐ" <= ch <= "ӿ" for ch in s)


@pytest.fixture(scope="module")
def page() -> str:
    return PAGE.read_text(encoding="utf-8")


class TestTheExamsOwnWordsSurvive:
    """Translating these away would cost the learner the exam vocabulary."""

    @pytest.mark.parametrize("word", [
        "Rada", "Lugemine", "Kuulamine", "Rääkimine", "Kirjutamine",
        "Sõnavara", "Õppimine", "Kordamine", "Eksam",
    ])
    def test_the_estonian_label_is_still_there(self, page, word):
        assert f">{word}<" in page or f">{word}<span" in page, (
            f"{word} is the word on the exam paper and must stay on screen")

    @pytest.mark.parametrize("word", [
        "Rada", "Lugemine", "Kuulamine", "Rääkimine", "Kirjutamine", "Sõnavara",
    ])
    def test_it_carries_a_russian_gloss(self, page, word):
        """`RU` is the one place the glosses live, so a tab added later gets one
        by being in the map rather than by somebody remembering this file."""
        block = page[page.index("const RU = {"):]
        block = block[:block.index("};")]
        assert f'"{word}"' in block, f"{word} has no entry in RU"


class TestNothingUserFacingIsEnglish:
    def test_the_path_state_badges_are_not_english(self, page):
        """They read `REFERENCE`, `READY`, `LOCKED` — neither the language
        being learned nor the one being read."""
        block = page[page.index("const RU = {"):]
        block = block[:block.index("};")]
        for state in ("reference", "ready", "locked"):
            m = re.search(rf'"{state}":\s*"([^"]+)"', block)
            assert m, f"no gloss for the {state!r} state"
            assert cyrillic(m.group(1)), f"{state} renders as {m.group(1)!r}"

    def test_the_badge_renders_through_the_map(self, page):
        assert "RU[t.state]" in page, (
            "the state badge must render through RU or it prints the raw "
            "English key")


class TestExplanationsAreRussian:
    """The category the rule is strictest about."""

    @pytest.mark.parametrize("gone", [
        "Ükski osa ei tohi olla null.",
        "Kuula ja kirjuta üles.",
        "Vasta valjusti ja kuula end üle.",
        "Töövihikuid pole veel imporditud.",
        "Ametlikku materjali pole veel imporditud.",
        # The page said this with parentheses, so the version listed here for
        # months matched nothing. Corrected to what the code actually had.
        "Mikrofon vajab HTTPS-i (või localhost'i).",
    ])
    def test_the_estonian_version_is_gone(self, page, gone):
        assert gone not in page, f"still explaining in Estonian: {gone!r}"

    def test_the_no_part_may_be_zero_warning_is_readable(self, page):
        """The one that decides whether a learner fails the exam for ignoring a
        section. It sat in Estonian for months."""
        assert "Ни одна часть не должна быть нулём." in page

    def test_the_readiness_verdict_is_russian(self):
        """It rendered `A2 · ei ole veel` directly above a paragraph of Russian
        reasons explaining why."""
        from eesti import readiness

        source = Path(readiness.__file__).read_text(encoding="utf-8")
        block = source[source.index("if not grammar:"):]
        block = block[:block.index("return Readiness(")]
        verdicts = re.findall(r'verdict = "([^"]+)"', block)
        assert len(verdicts) == 4
        for v in verdicts:
            assert cyrillic(v), f"verdict {v!r} is not readable by this learner"


class TestEverySentenceOnThePageIsReadable:
    """The rule above, derived instead of listed.

    `TestExplanationsAreRussian` names six strings that must be gone. It has
    passed since it was written, and one of the six was never actually in the
    page: the code said `Mikrofon vajab HTTPS-i (või localhost'i).` with
    parentheses and the test looked for the version without them. The assert
    was `not in page`, so a string the code did not contain passed trivially
    while the Estonian sentence it was meant to remove sat on the speaking
    screen untouched. A hand-maintained list of forbidden strings cannot fail
    that way loudly -- it fails silently, which is worse.

    What can be derived is the shape of an explanation. **Labels do not end in
    a full stop.** `Kontrolli`, `Kuula ette`, `Rada` are labels and stay
    Estonian; anything that runs to a sentence is explaining, warning or
    instructing, and by the rule that is Russian. So: every sentence-shaped run
    of user-facing text on the page must contain Cyrillic.

    Run against the page as it stood before the translation work, this flags 22
    strings -- including *both* microphone variants.

    **What it cannot see**, stated so the green tick is not read as more than
    it is: a run built around an interpolation. `` `, ebaõnnestus ${n}.` `` is
    one word once the `${...}` is blanked, far below any threshold that does
    not also flag every label. Two strings escaped that way and were found by
    reading the diff, not by this test. Distinguishing a short Estonian
    fragment from a short Estonian *label* needs judgement, and a word list
    that encoded that judgement would be the hand-maintained list this replaced.
    """

    def test_no_sentence_is_written_in_a_language_the_learner_cannot_read(self, page):
        estonian = sorted({s for s in ui_sentences(page) if not cyrillic(s)})
        assert not estonian, (
            "sentences explain, and an explanation nobody can read is not an "
            "explanation:\n  " + "\n  ".join(estonian))

    def test_the_check_is_actually_looking_at_something(self, page):
        """A rule that matches nothing would pass for ever. It is the same
        failure as the assert above, one level up."""
        assert len(list(ui_sentences(page))) > 25


class TestTheMaterialIsNeverGlossed:
    def test_grammar_topic_names_stay_estonian(self):
        """`osastav` must be learned; glossing it in the path would mean
        unlearning it later."""
        from eesti.curriculum import TOPICS

        for topic in TOPICS:
            assert not cyrillic(topic.et), f"{topic.id} has a Russian et name"

    def test_the_wordlist_is_not_translated_in_place(self, page):
        """Sõnavara lists Estonian words; the translation belongs on the card,
        not instead of the word."""
        assert "vocRow" in page
        block = page[page.index("function vocRow("):]
        block = block[:block.index("\n}")]
        assert "esc(it.word)" in block, "the Estonian word must be the row label"


# Estonian is written in the Latin alphabet. A naive letter-for-letter map is
# enough to generate what a transliteration of an Estonian term *would* look
# like, which is all this needs -- it is looking for a spelling that should
# never occur, not parsing Russian.
_TO_CYRILLIC = str.maketrans({
    "a": "а", "b": "б", "d": "д", "e": "е", "f": "ф", "g": "г", "h": "х",
    "i": "и", "j": "й", "k": "к", "l": "л", "m": "м", "n": "н", "o": "о",
    "p": "п", "r": "р", "s": "с", "t": "т", "u": "у", "v": "в",
    "õ": "о", "ä": "а", "ö": "о", "ü": "ю", "š": "ш", "ž": "ж",
})

# The modules that carry Russian explanation prose.
_PROSE = ("grammar.py", "cloze.py", "patterns.py", "drills.py", "curriculum.py",
          "forms.py", "readiness.py")


def prose_files() -> list[Path]:
    """The prose modules, resolved and asserted to exist."""
    root = Path(__file__).resolve().parents[1] / "eesti"
    return [root / name for name in _PROSE if (root / name).exists()]


def estonian_terms() -> set[str]:
    """Every Estonian grammar term the app teaches, from the two lists that
    already hold them. Derived, so a term added later is checked by existing."""
    from eesti import grammar
    from eesti.curriculum import TOPICS

    terms = {t.et for t in TOPICS}
    terms |= {r.et_term for r in grammar.REFERENCES.values()}
    words = set()
    for term in terms:
        words |= {w.strip("*«»,.:;()").lower() for w in term.split()}
    # Short words transliterate into noise; the terms that matter are long.
    return {w for w in words if len(w) >= 6 and w.isalpha()}


class TestAGrammarTermIsNeverTransliterated:
    """`omastav` appeared as **омастав** in nine explanation strings.

    That is neither language. The rule says the Estonian term stays Estonian
    *because it has to be learned*, and a learner who meets `основа омастава`
    has been taught a spelling that appears in no textbook, no dictionary and
    no exam paper -- they cannot look it up and cannot recognise it when EKK
    writes `omastav`. It is strictly worse than either translating the term or
    leaving it alone.

    The tell was that the codebase already had the right Russian rendering:
    `ru_term="основа генитива"` on the `gen-stem` reference, sitting three
    lines above prose that invented a second one. The same job written twice
    became two behaviours -- so this checks the terms rather than the strings.
    """

    def test_no_estonian_term_appears_in_cyrillic_letters(self):
        found = []
        for path in prose_files():
            name = path.name
            source = path.read_text(encoding="utf-8").lower()
            for term in estonian_terms():
                # The stem, so declined Russian endings ("омастава") still hit.
                stem = term.translate(_TO_CYRILLIC)[:-1]
                if len(stem) >= 5 and stem in source:
                    found.append(f"{name}: {term} written as {stem}…")
        assert not found, (
            "an Estonian grammar term spelled in Cyrillic can be looked up "
            "nowhere:\n  " + "\n  ".join(sorted(set(found))))

    def test_there_is_something_to_check(self):
        """The guard against a rule that silently matches nothing.

        Written first as `len(estonian_terms()) >= 10`, which checked the
        half that was never in doubt: the path was wrong, every file was
        skipped, and the check above passed on the nine transliterations it
        was written to catch. Assert on both sides of the search.
        """
        assert len(estonian_terms()) >= 10
        assert len(prose_files()) == len(_PROSE)
