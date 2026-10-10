"""Draft unit dialogues and reading texts with Claude Opus 5.5 (S2; ADR-0009, step 1).

A model may write material; only code may key it (ADR-0004). This script does
the first step and nothing else: it asks Claude Opus 5.5, through the Message
Batches API with one cached system prompt, for drafts that `cli material check`
and `cli material blind` then judge. Nothing it writes is trusted, and nothing
it writes reaches a learner except through `content/material/checked/`.

    python content/material/draft.py prompt               # the system prompt, as sent
    python content/material/draft.py submit [UNIT...]     # a dialoog and a tekst per unit
    python content/material/draft.py collect BATCH        # → drafts/<unit>/<slug>.json, gated
    python content/material/draft.py revise DRAFT...      # failing drafts back, with the findings
    python content/material/draft.py trim DRAFT... --blind OUT  # five questions the blind run kept
    python content/material/draft.py blindlog OUT        # a blind run's drops → log.md

`collect` runs the deterministic gates on every draft it writes and appends
the outcome to `log.md`; a draft the gates refuse is also kept under
`rejected/`, so the log can be checked against what the model wrote.

Needs `ANTHROPIC_API_KEY` (the git-ignored `.env`) and the word list with EKI's
levels (`cli build`, `cli import-levels`).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DRAFTS = HERE / "drafts"
REJECTED = HERE / "rejected"
LOG = HERE / "log.md"
BATCHES = HERE / "batches.jsonl"

MODEL = "claude-opus-5-5"
EFFORT = "high"
#: Room for adaptive thinking at high effort and a draft of about 2K tokens.
MAX_TOKENS = 32000

#: Bumped when the instructions change; every draft names the prompt that made it.
#: `s2-draft-1` was `s2-draft-2` without the reading-task-4 paragraph of a text's
#: brief (`unit_brief(..., version=...)` reproduces either).
DRAFT_PROMPT = "s2-draft-2"
REVISE_PROMPT = "s2-revise-1"

#: Questions a checked file keeps (`qa/opus-sessions.md`, S2); drafts ask for
#: more, because the gates and the blind check drop some.
QUESTIONS = 5
DRAFT_QUESTIONS = 7

#: HARNO's B1 reading task 4 (`harnotasks.phrase_bank`) removes sentence
#: endings into a bank and needs at least `BANK_MINIMUM` in one text. A text is
#: asked for `BANK_ENDINGS`, so a task has a choice of places; it is sent back
#: only below the minimum, because pushing an A1 text past it makes the model
#: bolt on clauses nobody would write (*lill, mis on punane*).
BANK_ENDINGS = 5
BANK_MINIMUM = 4

# ---------------------------------------------------------------------------
# What each unit's material is about. The situation is the course's choice;
# the language is the model's, held to the gates.
# ---------------------------------------------------------------------------

PLAN: dict[str, dict[str, tuple[str, str]]] = {
    "tutvume": {
        "dialoog": ("kursusel", (
            "The first lesson of an Estonian course. The teacher and a new learner "
            "get acquainted: the learner's first name and surname, nationality, "
            "job, and a mobile number written in digits. Build it on EKI's "
            "Tutvumine and Tervitused exchanges.")),
        "tekst": ("uus-oppija", (
            "A newcomer introduces themself in the first person, as on a course's "
            "first page: name, nationality, job, the people around them in the "
            "nominative (Minu naine on arst.), what they do now in the present "
            "tense.")),
    },
    "pere": {
        "dialoog": ("pilt", (
            "Two colleagues look at a family photo on a phone: who is who, their "
            "names, how many brothers, sisters or children someone has (kaks "
            "venda), whose child is whose (Peetri tütar).")),
        "tekst": ("minu-pere", (
            "Someone describes their family: who the members are, their names and "
            "jobs, how many children and siblings, possession through the genitive "
            "(minu ema nimi, Kati mees).")),
    },
    "kohvik": {
        "dialoog": ("kohvikus", (
            "Ordering at a café counter: what the customer would like (the "
            "partitive after soovima, tahtma), what the café does not have today "
            "(negation), the price and paying. Build it on EKI's Kohvikus või "
            "restoranis exchanges.")),
        "tekst": ("lounapaus", (
            "A short text about a lunch break in a small café: what one person "
            "eats and drinks there, what they do not eat or drink and why "
            "(negation with the partitive), what it costs in euros.")),
    },
    "kodu": {
        "dialoog": ("uus-korter", (
            "Two friends talk about one friend's new flat: in which town and on "
            "which street it is, which rooms it has, what is in which room "
            "(the inessive), where they go and where they come from.")),
        "tekst": ("minu-kodu", (
            "Someone describes their home: town and street, the rooms, what is "
            "where, where they go in the morning and where they come back from "
            "in the evening.")),
    },
    "paev": {
        "dialoog": ("millal", (
            "Two people arrange to meet: what each does at what time (kell 8), "
            "when work or school starts and ends, what they have to or want to "
            "do (pean minema, tahan süüa).")),
        "tekst": ("minu-paev", (
            "One working day of one person: the routine with clock times in "
            "digits, hommikul, õhtul, how often things happen (alati, tihti, "
            "harva).")),
    },
    "linn": {
        "dialoog": ("tee-kusimine", (
            "Asking the way in a town centre, as in EKI's Tee küsimine exchanges "
            "(Vabandust, kus on siin ...?): the answer places things with "
            "postpositions (panga kõrval, poe taga) and plurals. No imperatives "
            "yet: say where one goes (Te lähete ...), not Minge!")),
        "tekst": ("minu-linn", (
            "The centre of a small town: what is next to, behind or in front of "
            "what, how many shops or cafés there are (plurals), with conjunctions "
            "such as sest, kui, et.")),
    },
    "meeldib": {
        "dialoog": ("nadalavahetus", (
            "Two friends plan the weekend: what each likes doing (mulle meeldib "
            "+ da-infinitive), what they want or have to do, whether they have "
            "time (mul on aega), and agree on a plan.")),
        "tekst": ("vaba-aeg", (
            "One person's free time: what they like doing and where, what they "
            "do not like, what they need for it (mul on vaja ...).")),
    },
    "eile": {
        "dialoog": ("puhkepaev", (
            "Monday at work: two colleagues tell each other what they did "
            "yesterday or at the weekend, where they went or have been (käisin, "
            "läksin), what the weather was like (oli ilus ilm, sadas vihma).")),
        "tekst": ("reis", (
            "A short account in the simple past of a day trip to another "
            "Estonian town: how the person travelled, the weather, what they "
            "did and saw, when they came home.")),
    },
    "poes": {
        "dialoog": ("turul", (
            "At a market stall or a shop counter, built on EKI's Toidupoes and "
            "Turul exchanges: asking prices (Mis see maksab?), buying a whole "
            "thing (Ma võtan ühe leiva: the total object in the genitive) against "
            "a part of a mass (pool kilo juustu: the partitive), what is not on "
            "sale today (Täna ei ole maasikaid: the partitive subject), Kas veel "
            "midagi? – Ei, see on kõik., Kas kotti on vaja? – Ei, aitäh., paying.")),
        "tekst": ("poeskaik", (
            "In the simple past: what someone bought in a shop (whole things as "
            "total objects in the genitive, ostsin leiva; masses in the "
            "partitive, ostsin piima), and what the shop did not have (poes ei "
            "olnud kala: the partitive subject).")),
    },
}

# ---------------------------------------------------------------------------
# What each topic lets a text use, in the words the model is told
# ---------------------------------------------------------------------------

#: Topics (from `units.UNITS`) → what they add to the allowed forms. A topic
#: that adds no form tag (`kusisonad`, `kellaaeg`) still names its use.
TOPIC_FORMS = {
    "fraasid": "EKI's A1 phrases, word for word (they are exempt from the forms gate)",
    "arvud": "numbers in digits, and numerals in the nominative",
    "asesonad": "personal, demonstrative and question pronouns in any case "
                "(mina/ma, minu/mu, mulle, mul; see, seda; kes, mis, mida)",
    "kusisonad": "question words (kes, mis, kus, kuhu, kust, millal, miks, kuidas, mitu)",
    "olevik": "the present tense, affirmative: elan, elad, elab, elame, elate, elavad",
    "lauseehitus": "simple main clauses",
    "pohivormid": "the singular genitive and partitive (ema, ema; maja, maja; laps, lapse, last)",
    "arvsonad": "numerals with a noun in the partitive (kaks venda, viis eurot)",
    "osastav": "the partitive in its uses (Ma joon kohvi. Palun kaks saia.)",
    "eitus": "negation: ei + the verb (ei taha, ei ole, pole), ei + nud (ei olnud)",
    "gen-stem": "genitive stems",
    "kohakaanded": "the singular local cases: illative (-sse and short), inessive "
                   "(-s), elative (-st), allative (-le), adessive (-l), ablative "
                   "(-lt): Tallinnas, kooli, hommikul, mul",
    "verb-form": "the ma- and da-infinitives (lähen sööma, tahan süüa, pean minema)",
    "kellaaeg": "clock times (kell 8, kell pool kaheksa)",
    "maarsonad": "adverbs of time and frequency (alati, tihti, harva, vahel)",
    "kaassonad": "postpositions and prepositions with the genitive or partitive "
                 "(maja kõrval, poe taga, enne tööd, pärast tööd)",
    "mitmus": "the plural, in any case already allowed (poed, poode, poodides)",
    "sidesonad": "all conjunctions (sest, et, kui, kuid, nii et, siis)",
    "ma-da-inf": "which verbs take the ma- or da-infinitive",
    "mul-on": "mul on, mulle meeldib, mul on vaja",
    "lihtminevik": "the simple past: olin, olid, oli, olime, olite, olid; elasin, elas",
    "kaima-minema": "käima against minema (käisin poes, läksin poodi)",
    "obj-case": "the object's case: total object in the genitive (ostsin leiva), "
                "partial in the partitive (ostsin piima, ei ostnud leiba)",
    "osaalus": "the partitive subject in a negated existential (Poes ei olnud piima.)",
}

#: Topics that add form tags to the gate (`gates.TAG_TOPICS`, `docs/material.md`),
#: in course order: what a unit's brief lists as not allowed yet. The others
#: change how forms are used, not which forms exist.
FORM_TOPICS = ("pohivormid", "eitus", "kohakaanded", "verb-form", "kaassonad",
               "mitmus", "sidesonad", "lihtminevik")

#: What no unit from 2 to 10 allows, said once in the system prompt.
NOT_YET = [
    "the imperative: Tule! Minge! Ära tule! (unit 11)",
    "the conditional: tahaksin, oleks (unit 12)",
    "comparatives and superlatives: suurem, kõige suurem (unit 13)",
    "the perfect and participles: olen käinud, tehtud, elav (unit 14)",
    "ordinal numbers: esimene, teine, kolmas (unit 15)",
    "the ma-forms in -mas, -mast, -mata, -maks and the des-form: käin ujumas, "
    "tulen tööd tegemast, lugedes (unit 16)",
    "the translative -ks, terminative -ni, essive -na, abessive -ta and comitative "
    "-ga: arstiks, kella viieni, õpetajana, piimata, bussiga, sõbraga (unit 18)",
    "the impersonal: räägitakse, tehti (unit 23)",
    "the indirect mood: olevat (unit 25)",
]

# ---------------------------------------------------------------------------
# The system prompt: the stable, cached prefix
# ---------------------------------------------------------------------------

SYSTEM_HEAD = """\
You write short reading material for a free Estonian course for adults whose
first language is Russian: one dialogue or one reading text for one unit of the
course, as JSON.

What you write is checked by code, and only what passes reaches a learner. The
checks are strict and mechanical, so write to them. In order:

1. **Vabamorf.** Every word is a standard Estonian form that the Vabamorf
   analyser knows without guessing, spelt as ÕS spells it. Proper names you use
   in the text go in `names` (speakers' names are declared already); everything
   else must be an ordinary dictionary word.
2. **Word level.** Every noun, verb, adjective and adverb is a word on EKI's A1
   list (below), judged by its dictionary form: *raamatu* counts as *raamat*,
   *läksin* as *minema*. Pronouns, numerals, conjunctions, adpositions and
   interjections are not checked here. At most three other words may be used,
   each declared in `off_list` with its dictionary form and a short Russian
   gloss; a declared word must really be used and must not already be on the
   list. Note that common words are missing from the A1 list: *hea*, *halb*,
   *vana*, *soe*, *külm*, *natuke*, *kook*, *arve* are not A1 (so *Head aega!*
   and *Head isu!* need *hea* declared; prefer *Nägemist!*).
3. **Grammar so far.** Every word form comes from grammar the course has
   taught by this unit. The unit's message lists what is allowed; anything not
   listed is not. Code reads each word in its sentence with Vabamorf's
   disambiguator, so write sentences whose forms cannot be read as something
   untaught: *Piima ma ei taha* is read as a short illative; *Ma ei taha piima*
   is not. EKI's A1 phrases (below) are exempt from this check when they appear
   word for word.
4. **Answers.** Each question's `answer` is a span of 1–8 words copied from the
   text exactly as shown, occurring in the whole shown text **exactly once** as
   whole words. For a dialogue the shown text includes each speaker's name
   before each line (`Mari: Tere!`), so a speaker's name is never an answer.
   The question is in Estonian, ends with a question mark, has at least three
   words, and does not contain its answer. Questions obey checks 1–3 too:
   before the genitive is taught (unit 3) ask *Mis on tema perekonnanimi?*,
   not *Mis on Igori perekonnanimi?*; before the local cases (unit 5), not
   *Mis on Olgal?*.
5. **Gaps.** A gap names one word of one line (`at` is the turn or paragraph
   index from 0) by its dictionary form and Vabamorf tag. The word occurs once
   in that line; Vabamorf generates exactly that word for that lemma and tag
   and no other; the tag is taught by this unit. Allowed tags: `sg g`, `sg p`,
   `sg ill`, `sg in`, `sg el`, `sg all`, `sg ad`, `sg abl`, `pl n`, `pl g`,
   `pl p`, `pl in`; for verbs `n`, `d`, `b`, `me`, `te`, `vad` (present),
   `sin`, `s`, `sime`, `site` (simple past), `ma`, `da`. Avoid words with two
   accepted forms (*kahte*/*kaht*, *majja*/*majasse*) and homographs.
6. **No duplicates.** No question or answer twice; no gap twice.

Then a second model answers every question **without the key**, once with the
text and once **without** it, and fills every gap with the word blanked:

- a question it cannot answer from the text, or answers differently, is dropped;
- a question it answers right **without the text** is dropped as guessable, so
  ask about what only this text says: a name, a number, a time, a place, an
  item, a reason given here; never what common sense supplies
  (*Mida juuakse kohvikus?* → *kohvi* is guessable);
- a gap it fills with another word is dropped, so a gap's sentence must allow
  only one word for that lemma and tag.

## How to write

- Natural, everyday Estonian, the way EKI's phrase collections speak: short
  sentences, one idea each, the vocabulary of the unit's situation. A learner
  in their first weeks reads this, so repeat useful words rather than vary them.
- A dialogue has 6–10 turns between 2 people (at most 4), each turn one or two
  short sentences. Give each speaker an `id` (a, b, ...), a `name` and a
  `role_ru` in Russian (for example «администратор», «покупательница»).
- A text has 80–150 words (counted by spaces) in 1–4 paragraphs, written for
  the learner: third person, or first person when the situation asks for it.
- Use names that Vabamorf knows, such as Mari, Kati, Kadri, Kertu, Marta, Aino,
  Maria, Olga, Svetlana, Juhan, Peeter, Tiit, Mart, Mihkel, Rein, Tõnu,
  Martin, Igor, Ivan, Sergei, Andrei, and Estonian towns (Tallinn, Tartu,
  Pärnu, Narva). Declare every name the text uses that is not a speaker's.
- Write numbers, prices, times and phone numbers in digits where you can:
  digits pass every check.
- Nothing about real businesses, real prices or real people; nothing that
  could be false about the world.
- Write `questions` in the order the text answers them, about different parts
  of the text, each with a short, exact answer. Prefer questions whose answer
  is a noun phrase, a number or a short clause.
- Write `gaps` on the unit's own new forms where the unit has them.
- `title` is Estonian, short, and obeys the checks; `harno` is the HARNO topic
  you are given; leave `names` empty when the text uses no other names.

## EKI's A1 phrases (exempt from the grammar check, word for word)

{phrases}

## EKI's phrasing for situations (Sõrmus, Pool, Kallas, Kiisla 2025)

The A1 and A2 collections *Kasulikke väljendeid* (EKI, Sõnaveeb, CC BY 4.0)
say these things this way. Build dialogues on them where the unit's grammar
allows every form; only the lines in the list above are exempt.

{situations}

## Grammar no unit you write for allows yet

{not_yet}

## EKI's A1 word list ({count} words, dictionary forms)

{words}
"""

#: EKI's situation exchanges, from the A1 and A2 collections on Sõnaveeb
#: (`https://sonaveeb.ee/learn`, read 10 Oct 2026). Alternatives written with a
#: slash are EKI's.
SITUATIONS = {
    "Tutvumine (A1 1.2)": [
        "Mina olen Maria/Martin.", "Olen Maria/Martin.",
        "Mis su nimi on? – Maria/Martin.", "Kas teie olete Maria/Martin?",
    ],
    "Tervitused (A1 1.1)": [
        "Kuidas läheb? – Hästi. / Väga hästi. / Normaalselt. / Pole viga. / "
        "Halvasti. / Nii ja naa.",
    ],
    "Selgituse palumine (A1 1.8, A2 1.9)": [
        "Kuidas, palun?", "Mida?", "Palun ütle uuesti.",
        "Vabandust, ma ei saanud aru. Palun ütle/öelge veel kord.",
        "Mida see sõna tähendab?", "Kuidas seda eesti keeles öelda?",
    ],
    "Bussis (A1 2.2)": [
        "Kas see koht on vaba? – Jaa, palun.", "Kas see koht on vaba? – Kahjuks kinni.",
    ],
    "Kohvikus või restoranis (A1 2.3, A2 2.6)": [
        "Palun mulle supp/praad/kook.",
        "Üks kohv palun. – Kas must või piimaga? – Piimaga.",
        "Must kohv / piimaga kohv palun! – Kas siin või kaasa? – Siin. / Kaasa.",
        "Palun menüüd.", "Palun arvet.",
        "Kas olete valmis tellima? – Me mõtleme veel natuke.",
        "Mis päevapraad teil täna on?",
        "Kas päevapraadi/päevasuppi veel saab? – Supp on kahjuks otsas, aga "
        "päevapraadi veel on.",
        "Päevapraad/päevasupp palun! – Midagi juua? – Ma võtan vett.",
        "Kas maksate kaardiga või sularahas/sulas? – Maksan kaardiga.",
    ],
    "Riidepoes (A1 2.4)": [
        "Kas ma saan aidata? – Ma soovin osta pluusi/mütsi/jopet.",
        "Mis number see pluus on? – Number nelikümmend.",
        "Kui palju see müts maksab? – Viisteist eurot.",
    ],
    "Toidupoes (A1 2.5, A2 2.10)": [
        "Palun see tort / viis lihapirukat.", "Palun pool kilo juustu/vorsti.",
        "Mis see maksab? Mis need maksavad?", "Palju see maksab? Palju need maksavad?",
        "Vabandage, kus teil ketšup on? – Ma näitan teile.",
        "Vabandage, kus teil küpsised on? – Näete, seal.",
        "Kas teil on kliendikaart?",
        "Kas maksate kaardiga või sularahas/sulas? – Maksan kaardiga.",
    ],
    "Turul (A1 2.6, A2 2.11)": [
        "Mis on kilohind?", "Kui palju see juust maksab?",
        "Mis see kala maksab? / Mis selle kala hind on?",
        "Kui palju maasikad maksavad?",
        "Palun pool kilo / kolmsada grammi vorsti/juustu.",
        "Palun kaks kilo maasikaid/kurke/tomateid.", "Ma võtan ühe kapsa.",
        "Kas need on Eesti tomatid/maasikad?",
        "Kas veel midagi? – Ei, see on kõik.", "Kas kotti on vaja? – Ei, aitäh.",
        "Kas kaardiga saab maksta? – Kahjuks mitte. Ainult sularahas.",
    ],
    "Tee küsimine (A2 1.10)": [
        "Vabandust, kus on siin apteek/tualett?",
        "Vabandust, kas siin lähedal on apteek? – Kahjuks ma ei tea.",
        "Vabandust, kus on lähim apteek? – Kohe üle tee.",
        "Mis buss läheb bussijaama? – Number kolm.",
        "Minge siit otse edasi 500 meetrit.", "Pöörake paremale/vasakule.",
    ],
    "Arsti juures (A1 2.1)": [
        "Mul on palavik/köha/nohu.", "Mul valutab pea/kurk/kõrv/kõht/selg/hammas.",
    ],
}


def _a1_words(words) -> list[str]:
    rows = words.execute(
        "SELECT word FROM official_levels WHERE level = 'A1' ORDER BY word").fetchall()
    return [w for (w,) in rows]


def system_prompt(words) -> str:
    """The cached prefix: the rules, EKI's phrases, EKI's A1 list. Byte-stable."""
    from eesti.phrases import EXCHANGES, FUNCTIONS

    phrases = [p for f in FUNCTIONS for p in f.phrases]
    phrases += [f"{a} – {b}" for a, b in EXCHANGES]
    situations = "\n".join(
        f"- {name}: " + " | ".join(lines) for name, lines in SITUATIONS.items())
    a1 = _a1_words(words)
    return SYSTEM_HEAD.format(
        phrases="\n".join(f"- {p}" for p in dict.fromkeys(phrases)),
        situations=situations,
        not_yet="\n".join(f"- {n}" for n in NOT_YET),
        count=len(a1),
        words=", ".join(a1),
    )


def unit_brief(unit_id: str, kind: str, version: str = DRAFT_PROMPT) -> str:
    """The user message for one draft: the unit, its grammar, the situation."""
    from eesti.material.gates import introduced
    from eesti.units import UNITS, by_id, home, words_for

    unit = by_id(unit_id)
    slug, situation = PLAN[unit_id][kind]
    taught = introduced(unit_id)
    order = [t for u in UNITS if u.n <= unit.n for t in u.topics]
    allowed = [f"- {TOPIC_FORMS[t]}" for t in order if t in TOPIC_FORMS]
    new = [f"- {TOPIC_FORMS[t]}" for t in unit.topics if t in TOPIC_FORMS]
    not_yet = [f"{TOPIC_FORMS[t]} (unit {home(t).n})" for t in FORM_TOPICS
               if t not in taught]
    words = ", ".join(words_for(unit)) or "(none listed; use the situation's words)"
    what = ("a dialogue (`kind`: `dialoog`) of 6–10 turns" if kind == "dialoog"
            else "a reading text (`kind`: `tekst`) of 80–150 words")
    bank = "" if kind == "dialoog" or version == "s2-draft-1" else f"""
At least {BANK_ENDINGS} of the text's sentences end in a clause after a comma that
opens with one of: {", ".join(openers(unit_id))}, and runs 2–9 words to the end
of the sentence with no other comma (Ma olen õpetaja, aga minu mees on arst.);
each such ending occurs once in the text. HARNO's B1 reading task 4 removes
these endings into a bank for the learner to put back.
"""
    return f"""\
Write {what} for unit {unit.n}, *{unit.et}*.

- `unit`: `{unit.id}`; `slug`: `{slug}`; `harno`: `{unit.harno[0]}`
- The unit's goal (Russian): {unit.goal_ru}
- Situation: {situation}
- The unit's word set (use the A1 words among them): {words}

Allowed forms, beyond the nominative singular, uninflected words, numbers in
digits and the conjunctions *ja*, *aga*, *või*:
{chr(10).join(allowed)}

New in this unit, so use them where they fit naturally:
{chr(10).join(new) or "- (nothing new in form; practise what is listed)"}

Not allowed yet, besides the list in your instructions:
{chr(10).join(f"- {n}" for n in not_yet) or "- (nothing else)"}
{bank}
Write {DRAFT_QUESTIONS} questions (the checks drop some; {QUESTIONS} are kept) and
2–4 gaps on this unit's forms where its forms allow one.
"""


def openers(unit_id: str) -> list[str]:
    """The words a removable ending may open with, by what the unit has taught.

    *ja* is left out: a comma before *ja* is rarely right in Estonian.
    """
    from eesti.harnotasks import OPENERS
    from eesti.material.gates import BASIC_CONJUNCTIONS, introduced

    conjunctions = "sidesonad" in introduced(unit_id)
    return [w for w, topic in OPENERS.items() if w != "ja" and (
        w in BASIC_CONJUNCTIONS or topic != "sidesonad" or conjunctions)]


def bank_endings(material) -> list[str]:
    """The sentence endings exam reading task 4 could remove from a text, each
    once in it (`harnotasks._removable`, `phrase_bank`)."""
    from eesti.harnotasks import _removable
    from eesti.morph import split_sentences

    sentences = [s for p in material.paragraphs for s in split_sentences(p)]
    body = " ".join(sentences)
    out = []
    for s in sentences:
        found = _removable(s)
        if found:
            ending = s[found[0]:found[1]]
            if body.count(ending) == 1 and ending.casefold() not in {e.casefold() for e in out}:
                out.append(ending)
    return out


def to_fix(material, report) -> list[str]:
    """What a draft must change before the blind check, or nothing.

    Must: a gate's failure, fewer than `QUESTIONS` questions left, a digit in an
    answer, too few endings for reading task 4. When anything must change, the
    gates' drops are listed too, so the rewrite fixes them on the way; drops
    alone, with enough questions left, are what drafting seven was for.
    """
    must = [str(f) for f in report.failures]
    if report.passed and len(report.questions) < QUESTIONS:
        must.append(f"[questions] only {len(report.questions)} questions pass the gates; "
                    f"{QUESTIONS} are needed, so write new ones in place of the dropped")
    for q in report.questions:
        if any(ch.isdigit() for ch in q.answer):
            # `comprehension.normalise` keeps letters only: *6 eurot* would
            # match *5 eurot*, and *12* matches nothing.
            must.append(f"[answers] question {q.id}: *{q.answer}* has digits, which code "
                        "does not compare; write that number in words in the text "
                        "and in the answer, or ask about something else")
    if material.kind == "tekst":
        endings = bank_endings(material)
        if len(endings) < BANK_MINIMUM:
            words = ", ".join(openers(material.unit))
            found = "; ".join(f"*{e}*" for e in endings) or "none"
            must.append(
                f"[reading 4] {len(endings)} sentences end in a removable clause "
                f"({found}); {BANK_ENDINGS} are needed. A removable clause follows a "
                f"comma, opens with one of: {words}, runs 2–9 words to the end of the "
                "sentence with no other comma, and occurs once in the text")
    return must + [str(f) for f in report.dropped] if must else []


def revise_brief(draft: dict, findings: list[str], notes: list[str] = ()) -> str:
    editor = "" if not notes else (
        "\nNotes from the session that runs these checks (a reader, not code; "
        "follow them where they agree with the checks):\n"
        + "\n".join(f"- {n}" for n in notes) + "\n")
    return f"""\
The checks refused this draft. Rewrite it so that it passes: keep the unit,
slug, kind and situation, change only what you must, and keep the dialogue or
text natural and coherent. Every finding below is from code; do not argue with
it. Where a word is beyond the unit's grammar or level, rephrase around it
rather than declaring it, unless declaring it is the only natural way.

Code compares answers on letters only and ignores digits, so an answer never
contains a digit: where a question asks for a number, price or time, the text
writes it in words (kaks eurot, kell kuus) and the answer copies those words.
A dropped question's id may be reused for its replacement.

Findings:
{chr(10).join(f"- {f}" for f in findings)}
{editor}
The draft:
{json.dumps(draft, ensure_ascii=False, indent=2)}

Return the whole corrected draft, with {DRAFT_QUESTIONS} questions and 2–4 gaps.
"""


# ---------------------------------------------------------------------------
# The Batches API
# ---------------------------------------------------------------------------

def output_schema() -> dict:
    """The draft's JSON Schema without the fields the pipeline owns.

    `authoring` and `schema_version` are written here, `checks` by the
    pipeline. Constraints structured outputs cannot enforce are moved into
    descriptions by the SDK's own transform; the gates enforce them anyway.
    """
    from anthropic import transform_schema

    from eesti.material.schema import json_schema

    schema = json_schema()
    for key in ("authoring", "schema_version"):
        schema["properties"].pop(key, None)
    schema["required"] = [k for k in schema.get("required", [])
                          if k in schema["properties"]]
    schema.get("$defs", {}).pop("Authoring", None)
    return transform_schema(schema)


def _request(custom_id: str, system: str, user: str) -> dict:
    return {
        "custom_id": custom_id,
        "params": {
            "model": MODEL,
            "max_tokens": MAX_TOKENS,
            "system": [{"type": "text", "text": system,
                        "cache_control": {"type": "ephemeral"}}],
            "messages": [{"role": "user", "content": user}],
            "thinking": {"type": "adaptive"},
            "output_config": {"effort": EFFORT,
                              "format": {"type": "json_schema",
                                         "schema": output_schema()}},
        },
    }


def _record(entry: dict) -> None:
    entry = {"on": datetime.now(timezone.utc).isoformat(timespec="seconds"), **entry}
    with BATCHES.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _words():
    from eesti import config
    from eesti.cli._helpers import words_db

    words = words_db(config.DB_PATH)
    if words is None:
        sys.exit(1)
    return words


def _client():
    import anthropic

    from eesti import env

    env.load()
    return anthropic.Anthropic()


def _submit(requests: list[dict], kind: str, prompts: dict[str, str],
            dry: bool, notes: dict[str, list[str]] | None = None) -> str | None:
    """Send one batch and record it: each request's prompt version, and the
    reader's notes a revision carried."""
    if dry:
        print(json.dumps(requests[0], ensure_ascii=False, indent=2)[:4000])
        print(f"... {len(requests)} requests (dry run, nothing sent)")
        return None
    batch = _client().messages.batches.create(requests=requests)
    _record({"batch": batch.id, "kind": kind, "prompts": prompts,
             **({"notes": notes} if notes else {})})
    print(f"batch {batch.id}: {len(requests)} requests")
    return batch.id


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_prompt(args) -> int:
    """The system prompt, or one request's brief as a given prompt version sent it."""
    if args.unit:
        print(unit_brief(args.unit, args.kind, args.version))
    else:
        print(system_prompt(_words()))
    return 0


def cmd_submit(args) -> int:
    words = _words()
    system = system_prompt(words)
    units = args.units or list(PLAN)
    kinds = args.kinds or ["dialoog", "tekst"]
    requests = [_request(f"{u}--{k}--0", system, unit_brief(u, k))
                for u in units for k in kinds]
    _submit(requests, "draft", {r["custom_id"]: DRAFT_PROMPT for r in requests},
            args.dry_run)
    return 0


def cmd_revise(args) -> int:
    from eesti.material import gates

    words = _words()
    system = system_prompt(words)
    requests, prompts, notes = [], {}, {}
    for name in args.drafts:
        path = Path(name)
        raw = path.read_text(encoding="utf-8")
        doc = json.loads(raw)
        material, report, schema = gates.check_text(raw, words)
        findings = [str(f) for f in schema] if report is None else to_fix(material, report)
        if args.blind:
            findings += blind_drops(args.blind, path)
            if report is not None and findings and not to_fix(material, report):
                findings += [str(f) for f in report.dropped]
        if not findings:
            print(f"{path}: nothing to fix")
            continue
        before = doc.get("authoring", {}).get("prompt_version", DRAFT_PROMPT)
        cid = f"{doc['unit']}--{doc['kind']}--{before.count('+') + 1}"
        body = {k: v for k, v in doc.items() if k not in ("authoring", "schema_version", "checks")}
        mine = [n.split(":", 1)[1].strip() for n in args.note or []
                if n.split(":", 1)[0] == f"{doc['unit']}/{doc['slug']}"]
        requests.append(_request(cid, system, revise_brief(body, findings, mine)))
        prompts[cid] = f"{before}+{REVISE_PROMPT}"
        if mine:
            notes[cid] = mine
    if not requests:
        return 0
    _submit(requests, "revise", prompts, args.dry_run, notes)
    return 0


def _draft_text(message) -> str | None:
    if getattr(message, "stop_reason", None) in ("refusal", "max_tokens"):
        return None
    text = "".join(getattr(b, "text", "") for b in message.content
                   if getattr(b, "type", "") == "text")
    return text or None


def _log(lines: list[str]) -> None:
    new = not LOG.exists()
    with LOG.open("a", encoding="utf-8") as f:
        if new:
            f.write("# Material drafts: what the gates and the blind check refused\n\n"
                    "Written by `draft.py collect` and by hand after each "
                    "`cli material blind` run (`README.md`).\n")
        f.write("\n".join(lines) + "\n")


def cmd_collect(args) -> int:
    from eesti.material import gates
    from eesti.material.schema import Material, dump

    words = _words()
    client = _client()
    batch = client.messages.batches.retrieve(args.batch)
    if batch.processing_status != "ended":
        print(f"batch {args.batch}: {batch.processing_status}; collect it later")
        return 2
    entry = next((json.loads(line) for line in BATCHES.read_text(encoding="utf-8").splitlines()
                  if json.loads(line)["batch"] == args.batch), {})
    prompts = entry.get("prompts", {})
    lines = [f"\n## Batch `{args.batch}` ({entry.get('kind', '?')}, "
             f"{datetime.now(timezone.utc).date()})\n"]
    again = 0
    for result in client.messages.batches.results(args.batch):
        unit, kind, rnd = result.custom_id.split("--")
        slug = PLAN[unit][kind][0]
        where = f"`{unit}/{slug}` round {rnd}"
        rejected = REJECTED / unit / f"{slug}.r{rnd}.json"
        if result.result.type != "succeeded":
            lines.append(f"- {where}: request {result.result.type}")
            again += 1
            continue
        message = result.result.message
        text = _draft_text(message)
        usage = message.usage
        cost = (f"{usage.input_tokens} in, {usage.cache_read_input_tokens or 0} cached, "
                f"{usage.output_tokens} out")
        if text is None:
            lines.append(f"- {where}: no draft ({message.stop_reason}) [{cost}]")
            again += 1
            continue
        doc = json.loads(text)
        prompt = prompts.get(result.custom_id, DRAFT_PROMPT)
        doc.update({"unit": unit, "slug": slug, "kind": kind,
                    "authoring": {"engine": MODEL, "prompt_version": prompt[:40]}})
        try:
            material = Material.model_validate(doc)
        except ValueError as exc:
            rejected.parent.mkdir(parents=True, exist_ok=True)
            rejected.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n",
                                encoding="utf-8")
            first = [e.get("msg", "") for e in getattr(exc, "errors", lambda: [])()][:3]
            lines.append(f"- {where}: the schema refused it ({'; '.join(first)}) [{cost}]")
            again += 1
            continue
        path = DRAFTS / unit / f"{slug}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(dump(material), encoding="utf-8")
        report = gates.check(material, words)
        fix = to_fix(material, report)
        state = ("passes the gates" if report.passed else "refused by the gates")
        lines.append(f"- {where} `{material.sha8()}` ({prompt}): {state}, "
                     f"{len(report.questions)} questions and {len(report.gaps)} gaps "
                     f"kept [{cost}]")
        lines += [f"  - {f}" for f in fix]
        if fix:
            again += 1
            rejected.parent.mkdir(parents=True, exist_ok=True)
            rejected.write_text(dump(material), encoding="utf-8")
        print(f"{where}: {state}; {len(fix)} to fix")
    _log(lines)
    print(f"{again} of the batch's drafts need another round")
    return 0


def blind_drops(outputs: list[str] | None, path: Path) -> list[str]:
    """What saved `cli material blind` runs dropped from this draft, as printed."""
    out = []
    for name in outputs or []:
        for line in Path(name).read_text(encoding="utf-8").splitlines():
            head, _, rest = line.partition(": drop ")
            if rest and Path(head).resolve() == path.resolve():
                out.append(rest)
    return out


def cmd_trim(args) -> int:
    """Keep the first `QUESTIONS` questions the gates and the blind runs kept,
    and the gaps they kept, so a checked file has five questions."""
    import re

    from eesti.material import gates
    from eesti.material.schema import Material, dump

    words = _words()
    for name in args.drafts:
        path = Path(name)
        material = Material.model_validate_json(path.read_text(encoding="utf-8"))
        report = gates.check(material, words)
        gone = {m.group(1) for d in blind_drops(args.blind, path)
                for m in [re.match(r"\[blind\] (?:question|gap) (\w+):", d)] if m}
        mine = [d.split(":", 1)[1].strip() for d in args.drop or []
                if d.split(":", 1)[0] == f"{material.unit}/{material.slug}"]
        if mine:
            gone |= set(mine)
            asked = {q.id: q.question for q in material.questions}
            named = ", ".join(f"{i} *{asked.get(i, '?')}*" for i in mine)
            _log([f"\n- `{material.unit}/{material.slug}`: left out by the reader: "
                  f"{named} ({args.why})"])
        questions = [q for q in report.questions if q.id not in gone][:args.keep]
        trimmed = material.model_copy(update={
            "questions": questions,
            "gaps": [g for g in report.gaps if g.id not in gone]})
        path.write_text(dump(trimmed), encoding="utf-8")
        print(f"{path}: {len(trimmed.questions)} questions, {len(trimmed.gaps)} gaps")
    return 0


def cmd_blindlog(args) -> int:
    """Copy what a `cli material blind` run said about each draft into `log.md`."""
    import re

    text = Path(args.output).read_text(encoding="utf-8")
    batch = re.search(r"^batch (\S+):", text, re.M)
    lines = [f"\n## Blind check `{batch.group(1) if batch else '?'}` ({args.what}, "
             f"{datetime.now(timezone.utc).date()})\n"]
    for line in text.splitlines():
        found = re.match(r"^(\S+\.json): (drop|FAIL after the blind check|checked →) ?(.*)$", line)
        if not found:
            continue
        path, verb, rest = found.groups()
        where = "/".join(Path(path).with_suffix("").parts[-2:])
        if verb == "checked →":
            # The written path may be a scratch directory; the id is the record.
            ident = re.search(r"\((mat:[^)]+)\)", rest)
            verb, rest = "passed as", f"`{ident.group(1)}`" if ident else ""
        lines.append(f"- `{where}`: {verb} {rest}".rstrip())
    _log(lines)
    print(f"{len(lines) - 1} lines logged")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="command", required=True)
    a = sub.add_parser("prompt", help="print the system prompt, or a unit's brief")
    a.add_argument("unit", nargs="?", choices=list(PLAN))
    a.add_argument("--kind", choices=("dialoog", "tekst"), default="dialoog")
    a.add_argument("--version", default=DRAFT_PROMPT)
    a.set_defaults(func=cmd_prompt)
    a = sub.add_parser("submit", help="one batch: a dialoog and a tekst per unit")
    a.add_argument("units", nargs="*", help="unit ids (default: units 2–10)")
    a.add_argument("--kinds", nargs="*", choices=("dialoog", "tekst"))
    a.add_argument("--dry-run", action="store_true")
    a.set_defaults(func=cmd_submit)
    a = sub.add_parser("collect", help="write a batch's drafts and gate them")
    a.add_argument("batch")
    a.set_defaults(func=cmd_collect)
    a = sub.add_parser("revise", help="send failing drafts back with their findings")
    a.add_argument("drafts", nargs="+")
    a.add_argument("--blind", action="append", metavar="OUTPUT",
                   help="a saved `cli material blind` run whose drops count as findings")
    a.add_argument("--note", action="append", metavar="UNIT/SLUG: TEXT",
                   help="a reader's note for one draft, recorded with the batch")
    a.add_argument("--dry-run", action="store_true")
    a.set_defaults(func=cmd_revise)
    a = sub.add_parser("trim", help="keep the first five questions the gates and blind runs kept")
    a.add_argument("drafts", nargs="+")
    a.add_argument("--keep", type=int, default=QUESTIONS)
    a.add_argument("--blind", action="append", metavar="OUTPUT",
                   help="a saved `cli material blind` run whose drops are left out")
    a.add_argument("--drop", action="append", metavar="UNIT/SLUG:ID",
                   help="an item the reader leaves out; logged with --why")
    a.add_argument("--why", default="", help="why the reader left those items out")
    a.set_defaults(func=cmd_trim)
    a = sub.add_parser("blindlog", help="log a `cli material blind` run's drops")
    a.add_argument("output", help="the run's saved output")
    a.add_argument("--what", default="scratch run, all questions",
                   help="which run this was, for the log's heading")
    a.set_defaults(func=cmd_blindlog)
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
