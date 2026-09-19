"""Which language each part of the interface is written in (rule in `AGENTS.md`).

  * **UI labels stay Estonian** — `Kirjutamine`, `Kuulamine`, `Rada`: the exam's
    own words.
  * **Grammar terms stay Estonian** — they must be learned.
  * **Anything explaining, warning or instructing is Russian** — a caveat nobody
    can read is not a caveat.
"""

from __future__ import annotations

import ast
import html
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

from pagesrc import markup, markup_and_script, scripts



CYRILLIC = re.compile(r"[\u0400-\u04ff]")
INTERPOLATION = re.compile(r"\$\{[^{}]*\}")
# A run that carries any of these is JavaScript that happened to end in a dot,
# not a sentence shown to anybody.
CODEISH = re.compile(r"[;{}`]|=>|===|!==|\|\||&&|\$\(")


def ui_sentences(page: str):
    """Every run of user-facing text on the page that ends like a sentence.

    Reads text between tags (not a parser; nested template literals defeat
    backtick matching). Comments are stripped and `${...}` blanked first.
    """
    src = re.sub(r"<!--.*?-->", "", page, flags=re.S)
    src = re.sub(r"<style.*?</style>", "", src, flags=re.S)
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    src = re.sub(r"^\s*//.*$", "", src, flags=re.M)
    # Decode entities first: `&#10;` contains a semicolon that the CODEISH filter
    # would otherwise treat as JavaScript.
    src = html.unescape(src)
    src = INTERPOLATION.sub("\x00", src)

    chunks = re.findall(r">([^<>]{4,400})<", src)
    chunks += [m.group(1) or m.group(2) for m in
               re.finditer(r'"([^"\\\n]{4,300})"|\'([^\'\\\n]{4,300})\'', src)]
    # Attributes a person reads or hears, including multi-line `placeholder`s written
    # with `&#10;`.
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
    return markup_and_script()


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


#: Estonian explanations that must stay removed, checked on the page and in API
#: responses.
ESTONIAN_EXPLANATIONS = [
    "Ükski osa ei tohi olla null.",
    "Kuula ja kirjuta üles.",
    "Vasta valjusti ja kuula end üle.",
    "Töövihikuid pole veel imporditud.",
    "Ametlikku materjali pole veel imporditud.",
    # The page said this with parentheses, so the version listed here for
    # months matched nothing. Corrected to what the code actually had.
    "Mikrofon vajab HTTPS-i (või localhost'i).",
    # Served by `api/speech.py` into `#dictState`.
    "Tekstikogu on tühi",
]


class TestExplanationsAreRussian:
    """The category the rule is strictest about."""

    @pytest.mark.parametrize("gone", ESTONIAN_EXPLANATIONS)
    def test_the_estonian_version_is_gone(self, page, gone):
        assert gone not in page, f"still explaining in Estonian: {gone!r}"

    @pytest.mark.parametrize("gone", ESTONIAN_EXPLANATIONS)
    def test_the_api_does_not_explain_in_estonian_either(self, gone):
        """The same rule over the API layer, whose explanations reach the same elements."""
        from pathlib import Path
        api = Path(__file__).resolve().parents[1] / "eesti" / "api"
        for mod in sorted(api.glob("*.py")):
            text = mod.read_text(encoding="utf-8")
            assert gone not in text, (
                f"{mod.name} still explains in Estonian: {gone!r}")

    def test_the_no_part_may_be_zero_warning_is_readable(self, page):
        """The one that decides whether a learner fails the exam for ignoring a
        section."""
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
    """Sentence-shaped user-facing text must contain Cyrillic.

    Labels do not end in a full stop (`Kontrolli`, `Rada`), so anything that runs to
    a sentence is explaining and must be Russian. Limitation: a short run built
    around an interpolation (`, ebaõnnestus ${n}.`) is below the threshold and is
    not seen.
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


# Generate what a letter-for-letter Cyrillic transliteration of an Estonian term
# would look like, to search for spellings that must never occur.
_TO_CYRILLIC = str.maketrans({
    "a": "а", "b": "б", "d": "д", "e": "е", "f": "ф", "g": "г", "h": "х",
    "i": "и", "j": "й", "k": "к", "l": "л", "m": "м", "n": "н", "o": "о",
    "p": "п", "r": "р", "s": "с", "t": "т", "u": "у", "v": "в",
    "õ": "о", "ä": "а", "ö": "о", "ü": "ю", "š": "ш", "ž": "ж",
})

#: Modules with Cyrillic in them are prose and are scanned (found, not listed).
#: Only string literals are checked — comments and the `REPAIRS` table must be
#: able to quote the misspelling.
def _literals(path: Path) -> str:
    tree = ast.parse(path.read_text(encoding="utf-8"))

    # The repair table is search-and-replace data, not prose. Its strings have
    # to be collected and subtracted: `ast.walk` flattens the tree, so skipping
    # the assignment node still visits every constant inside it.
    exempt = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
                getattr(t, "id", "") == "REPAIRS" for t in node.targets):
            exempt |= {n.value for n in ast.walk(node)
                       if isinstance(n, ast.Constant)
                       and isinstance(n.value, str)}

    return "\n".join(
        n.value for n in ast.walk(tree)
        if isinstance(n, ast.Constant) and isinstance(n.value, str)
        and n.value not in exempt
    ).lower()


def _prose_modules() -> list[Path]:
    root = Path(__file__).resolve().parents[1] / "eesti"
    return sorted(
        p for p in root.glob("*.py")
        if CYRILLIC.search(p.read_text(encoding="utf-8"))
    )


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
    """Estonian grammar terms never appear transliterated into Cyrillic (`омастав`).

    A transliteration exists in no textbook or exam, so the learner can neither look
    it up nor recognise it. Use the Estonian term or a real Russian rendering
    (`основа генитива`).
    """

    def test_no_estonian_term_appears_in_cyrillic_letters(self):
        found = []
        for path in _prose_modules():
            name = path.name
            source = _literals(path)
            for term in estonian_terms():
                # The stem, so declined Russian endings ("омастава") still hit.
                stem = term.translate(_TO_CYRILLIC)[:-1]
                if len(stem) >= 5 and stem in source:
                    found.append(f"{name}: {term} written as {stem}…")
        assert not found, (
            "an Estonian grammar term spelled in Cyrillic can be looked up "
            "nowhere:\n  " + "\n  ".join(sorted(set(found))))

    def test_there_is_something_to_check(self):
        """Guard that the search finds both the terms and the files it scans."""
        assert len(estonian_terms()) >= 10
        assert len(_prose_modules()) >= 8

def glossed_button_labels(page: str) -> dict[str, str]:
    """Each button that carries a Russian gloss, and its Estonian label."""
    out = {}
    for m in re.finditer(
            r'<button[^>]*\bid="([^"]+)"[^>]*>([^<]*)<span class="ru"[^>]*>', page):
        label = " ".join(m.group(2).split())
        if label:
            out[m.group(1)] = label
    return out


class TestAGlossSurvivesTheButtonBeingUsed:
    """No raw `textContent =` on glossed buttons: it deletes the Russian gloss span.
    `setLabel` restores it.
    """

    def test_no_restore_assignment_wipes_a_gloss(self, page):
        labels = glossed_button_labels(page)
        assert labels, "no glossed buttons found -- the check would be vacuous"
        script = page[page.index("<script>"):]
        offenders = [
            f"{bid} (restores {label!r})"
            for bid, label in labels.items()
            if re.search(rf'\.textContent\s*=\s*["\u0060]{re.escape(label)}["\u0060]',
                         script)
        ]
        assert not offenders, (
            "these set .textContent back to the Estonian label, which drops "
            f"the gloss span with it -- use setLabel(): {offenders}")

    def test_the_helper_puts_the_gloss_back(self, page):
        block = page[page.index("function setLabel("):]
        block = block[:block.index("\n}")]
        assert "querySelector(\".ru\")" in block
        assert "append(ru)" in block, (
            "setLabel must re-attach the gloss after replacing the text")

    def test_every_labelled_button_carries_one(self, page):
        """Every primary button carries a Russian gloss."""
        bare = re.findall(r'<button(?![^>]*\baria-)[^>]*\bid="([^"]+)"[^>]*>'
                          r'([A-ZÕÄÖÜ][^<]{2,40})</button>', page)
        assert not bare, f"button with an Estonian label and no gloss: {bare}"


# ── Which voice reads each label ─────────────────────────────────────────────
#
# The page is `lang="ru"`, so a screen reader speaks everything in a Russian voice
# unless an element says otherwise. An Estonian label (`Kontrolli`) is marked
# `lang="et"` on the element that holds it; its Russian gloss (`.ru`) is marked
# `lang="ru"` again. Checked over the authored page and over every HTML fragment
# a module writes, by parsing: which elements are labels, and which text is
# Estonian, is read from the markup, not listed here.

#: Elements whose text names a control or a section.
LABEL_TAGS = {"button", "summary", "label", "option", "legend", "a",
              "h1", "h2", "h3", "h4", "h5", "h6"}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "source", "track", "wbr"}
LATIN = re.compile(r"[A-Za-zÀ-ÿŠŽšžÕÄÖÜõäöü]")
#: Words no voice mispronounces by language: levels (`A1–B1`), acronyms
#: (`EKK`, `CC BY 4.0`), numbers and host names.
NEUTRAL_WORD = re.compile(
    r"^(?:[A-Z0-9][A-Z0-9.+×–-]*|\d[\d.,×%/–-]*|[a-z0-9-]+(?:\.[a-z0-9-]+)+)$")
#: Where a module's `${...}` stood.
HOLE = "\x00"


class _Node:
    def __init__(self, tag, attrs, parent):
        self.tag, self.attrs, self.parent = tag, dict(attrs), parent
        self.children = []

    def classes(self):
        return (self.attrs.get("class") or "").split()


class _Tree(HTMLParser):
    """A forgiving tree: an unmatched end tag is ignored, an unclosed element runs
    to the end of its fragment."""

    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.root = _Node("#root", {}, None)
        self.stack = [self.root]
        self.feed(source)
        self.close()

    def handle_starttag(self, tag, attrs):
        node = _Node(tag, attrs, self.stack[-1])
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(_Node(tag, attrs, self.stack[-1]))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        if self.stack[-1].tag not in ("script", "style"):
            self.stack[-1].children.append(data)


def _elements(node):
    for child in node.children:
        if isinstance(child, _Node):
            yield child
            yield from _elements(child)


def _texts(node):
    for child in node.children:
        if isinstance(child, str):
            yield child, node
        else:
            yield from _texts(child)


def _lang(node, default):
    """The language a node's text is read in: the nearest `lang`, else the
    document's. A module's fragment does not know where it lands (`None`), so it
    has to say."""
    while node is not None:
        if "lang" in node.attrs:
            return node.attrs["lang"]
        node = node.parent
    return default


def _nearest(node, test):
    while node is not None and node.tag != "#root":
        if test(node):
            return node
        node = node.parent
    return None


def _is_label(node):
    return node.tag in LABEL_TAGS or "tag" in node.classes()


def _in_gloss(node):
    return _nearest(node, lambda n: "ru" in n.classes()) is not None


def _neutral(text):
    words = re.findall(r"[^\s·—→←↗✓✗■()«»:,;!?+]+", text.replace(HOLE, " "))
    return all(NEUTRAL_WORD.match(w) for w in words)


def _js_literals(src: str) -> list[str]:
    """Every string and template literal in a module, each `${...}` replaced by
    `HOLE`. A small tokenizer, so comments, regex literals (`/[&<>"]/g`) and
    templates nested inside `${...}` are not mistaken for markup."""
    out, n = [], len(src)

    def string(i, quote):
        buf = []
        while src[i] != quote:
            if src[i] == "\\":
                buf.append({"n": "\n", "t": "\t"}.get(src[i + 1], src[i + 1]))
                i += 2
                continue
            buf.append(src[i])
            i += 1
        out.append("".join(buf))
        return i + 1

    def template(i):
        buf = []
        while src[i] != "`":
            if src[i] == "\\":
                buf.append(src[i + 1])
                i += 2
            elif src.startswith("${", i):
                i = code(i + 2, inside=True)
                buf.append(HOLE)
            else:
                buf.append(src[i])
                i += 1
        out.append("".join(buf))
        return i + 1

    def code(i, inside=False):
        depth, prev, word = 0, "", ""
        while i < n:
            c = src[i]
            if c.isspace():
                i += 1
            elif src.startswith("//", i):
                j = src.find("\n", i)
                i = n if j < 0 else j
            elif src.startswith("/*", i):
                i = src.index("*/", i) + 2
            elif c in "'\"":
                i, prev, word = string(i + 1, c), "a", ""
            elif c == "`":
                i, prev, word = template(i + 1), "a", ""
            elif c == "/" and (prev == "" or prev in "(,=:[!&|?{};+-*%<>~^"
                               or word in ("return", "typeof", "case")):
                j, klass = i + 1, False
                while src[j] != "/" or klass:
                    if src[j] == "\\":
                        j += 1
                    elif src[j] == "[":
                        klass = True
                    elif src[j] == "]":
                        klass = False
                    j += 1
                i, prev, word = j + 1, "a", ""
            else:
                if c == "{":
                    depth += 1
                elif c == "}":
                    if inside and depth == 0:
                        return i + 1
                    depth -= 1
                if c.isalnum() or c in "_$":
                    word = word + c if prev == "a" else c
                    prev = "a"
                else:
                    prev, word = c, ""
                i += 1
        return i

    code(0)
    return out


def _sources():
    """(where, parsed tree, the language unmarked text is read in)."""
    yield "index.html", _Tree(markup()), "ru"
    for path in scripts():
        for k, lit in enumerate(_js_literals(path.read_text(encoding="utf-8"))):
            if re.search(r"<[a-z]", lit):
                yield f"{path.name} #{k}", _Tree(lit), None


@pytest.fixture(scope="module")
def trees():
    return list(_sources())


def _show(text):
    return " ".join(text.replace(HOLE, "…").split())[:60]


class TestEachLabelIsReadInItsLanguage:
    def test_every_gloss_is_marked_russian(self, trees):
        """Inside an Estonian label, an unmarked gloss would inherit `et`."""
        bare = [f"{where}: <{el.tag} class=ru>"
                for where, tree, _ in trees for el in _elements(tree.root)
                if "ru" in el.classes() and el.attrs.get("lang") != "ru"]
        assert not bare, 'a Russian gloss without lang="ru":\n  ' + "\n  ".join(bare)

    def test_what_a_gloss_explains_is_marked_estonian(self, trees):
        """The element holding a gloss holds the Estonian word it glosses."""
        wrong = []
        for where, tree, default in trees:
            for el in _elements(tree.root):
                if "ru" in el.classes() and not _in_gloss(el.parent) \
                        and _lang(el.parent, default) != "et":
                    own = "".join(t for t in el.parent.children if isinstance(t, str))
                    wrong.append(f"{where}: <{el.parent.tag}> {_show(own)!r}")
        assert not wrong, ("a glossed label read in a Russian voice -- put "
                           'lang="et" on the element holding it:\n  ' + "\n  ".join(wrong))

    def test_every_estonian_label_is_marked_estonian(self, trees):
        """Latin text in a button, summary, form label, option, link, heading or
        tag is an Estonian label, unless it is a code no voice mispronounces."""
        wrong = []
        for where, tree, default in trees:
            for text, parent in _texts(tree.root):
                if not LATIN.search(text) or CYRILLIC.search(text) or _neutral(text):
                    continue
                if _nearest(parent, _is_label) and not _in_gloss(parent) \
                        and _lang(parent, default) != "et":
                    wrong.append(f"{where}: <{parent.tag}> {_show(text)!r}")
        assert not wrong, ("an Estonian label read in a Russian voice:\n  "
                           + "\n  ".join(sorted(set(wrong))))

    def test_nothing_russian_is_marked_estonian(self, trees):
        """The other direction: marking a container `et` must not take the Russian
        inside it along."""
        wrong = [f"{where}: <{parent.tag}> {_show(text)!r}"
                 for where, tree, default in trees
                 for text, parent in _texts(tree.root)
                 if CYRILLIC.search(text) and not LATIN.search(text)
                 and _lang(parent, default) == "et"]
        assert not wrong, ('Russian text read in an Estonian voice -- give it '
                           'lang="ru":\n  ' + "\n  ".join(wrong))

    def test_the_checks_see_the_page_and_the_modules(self, trees):
        """Each check above would pass on nothing at all."""
        glosses = sum("ru" in el.classes()
                      for _, tree, _ in trees for el in _elements(tree.root))
        labels = sum(
            1 for _, tree, default in trees for text, parent in _texts(tree.root)
            if LATIN.search(text) and not CYRILLIC.search(text) and not _neutral(text)
            and _nearest(parent, _is_label) and _lang(parent, default) == "et")
        files = {where.split()[0] for where, _, _ in trees}
        assert glosses >= 70, glosses
        assert labels >= 80, labels
        assert len(files) >= 10, files

