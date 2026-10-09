"""`fraasid`: greetings and survival phrases, from EKI's A1 phrase collection.

The phrases and their grouping are EKI's: Sõrmus, Pool, Kallas, Kiisla (2025),
*Kasulikke väljendeid A1-tasemel eesti keele õppijale*, Sõnaveeb (CC BY 4.0).
The collection is in Estonian only; the Russian shown is EKI EVS's where EVS
gives the phrase (`evs.phrase_russian`), and nothing where it does not.

Two rules, each keyed by EKI's own arrangement:

- **olukord** — a communicative function (*Tänamine*) → the phrase EKI files
  under it. The pairs of functions whose phrases serve each other (`APART`)
  never share a choice set: a wish can take leave or congratulate, *Kõike
  head!* can congratulate, *Vabandust?* can ask for a repeat.
- **vastus** — the first line of one of EKI's two-part exchanges → its reply
  (*Aitäh! – Palun!*). A distractor is a reply from the other kind of exchange
  (social or at the counter), never one that could also answer: *Palun!* can say
  "yes, please", *Ei ole midagi.* can answer thanks.

Changes to EKI's text, as CC BY 4.0 asks: alternatives written with a slash keep
their first reading (*Mina olen Maria.*, *sularahas*); *Tervist!*, *Tšau!* and
*Head ööd!* are shown in the list but never asked, because each also serves
another function.
"""

from __future__ import annotations

import random
import sqlite3
from dataclasses import dataclass

from .item import BLANK
from .patterns import PatternDrill

SOURCE_ID = "eki-valjendid"
URL = "https://sonaveeb.ee/learn#v-pills-kasulikke-valjendeid-a1"

BASE_RULES = ("olukord", "vastus")


@dataclass(frozen=True)
class Function:
    id: str
    et: str           # EKI's heading
    ru: str           # the heading glossed for the learner
    phrases: tuple[str, ...]


FUNCTIONS: tuple[Function, ...] = (
    Function("tervitus", "Tervitused", "приветствие",
             ("Tere!", "Tere hommikust!", "Tere päevast!", "Tere õhtust!",
              "Kuidas läheb?")),
    Function("tutvumine", "Tutvumine", "знакомство",
             ("Mina olen Maria.", "Mis su nimi on?", "Kas teie olete Maria?")),
    Function("araminek", "Äraminek", "прощание",
             ("Head aega!", "Nägemist!", "Kõike head!")),
    Function("vabandus", "Vabandused", "извинение", ("Vabandust!",)),
    Function("tanamine", "Tänamine", "благодарность", ("Aitäh!", "Suur aitäh!")),
    Function("onnitlus", "Õnnitlused", "поздравление", ("Palju õnne!",)),
    Function("soov", "Soovid", "пожелание",
             ("Häid pühi!", "Häid jõule!", "Head uut aastat!", "Head reisi!",
              "Head isu!")),
    Function("selgitus", "Selgituse palumine", "просьба переспросить",
             ("Kuidas, palun?", "Palun ütle uuesti.")),
)

#: Functions whose phrases a speaker may use for each other: never in one set.
APART = (frozenset({"araminek", "soov"}), frozenset({"onnitlus", "soov"}),
         frozenset({"onnitlus", "araminek"}), frozenset({"selgitus", "vabandus"}))

#: EKI's two-part exchanges: first line, reply.
EXCHANGES: tuple[tuple[str, str], ...] = (
    ("Kuidas läheb?", "Hästi! Aga sul?"),
    ("Vabandust!", "Ei ole midagi."),
    ("Aitäh!", "Palun!"),
    ("Kas veel midagi?", "Ei, see on kõik."),
    ("Kas kotti on vaja?", "Ei, aitäh."),
    ("Kas maksate kaardiga või sularahas?", "Maksan kaardiga."),
)
_SOCIAL = frozenset({"Kuidas läheb?", "Vabandust!", "Aitäh!"})
#: Replies that could answer a counter question too ("yes, please", "nothing").
_OPEN = frozenset({"Palun!", "Ei ole midagi."})


def _ru(words: sqlite3.Connection | None, phrase: str) -> str:
    if words is None:
        return ""
    from .evs import phrase_russian

    return phrase_russian(words, phrase)


def _why(words, phrase: str, filed: str) -> str:
    meaning = _ru(words, phrase)
    said = f"*{phrase}* — {meaning} (EKI EVS). " if meaning else ""
    return f"{said}В сборнике EKI эта фраза — в разделе «{filed}»."


def _situation(rng: random.Random, words) -> PatternDrill:
    target = rng.choice(FUNCTIONS)
    answer = rng.choice(target.phrases)
    others = [f for f in FUNCTIONS if f.id != target.id
              and frozenset({f.id, target.id}) not in APART]
    rng.shuffle(others)
    picked: list[Function] = []
    for f in others:
        if all(frozenset({f.id, p.id}) not in APART for p in picked):
            picked.append(f)
        if len(picked) == 2:
            break
    choices = [answer] + [rng.choice(f.phrases) for f in picked]
    rng.shuffle(choices)
    return PatternDrill(
        f"{target.et}: {BLANK}", answer, next(c for c in choices if c != answer),
        "", "fraas", "olukord", _why(words, answer, target.et), "fraasid",
        answer_ru=(target.ru,), choices=tuple(choices), source_id=SOURCE_ID,
        translate=False)


def _reply(rng: random.Random, words) -> PatternDrill:
    first, answer = rng.choice(EXCHANGES)
    social = first in _SOCIAL
    pool = [r for f, r in EXCHANGES if (f in _SOCIAL) != social
            and (social or r not in _OPEN)]
    distractor = rng.choice(pool)
    choices = [answer, distractor]
    rng.shuffle(choices)
    meaning = _ru(words, answer)
    why = (f"*{answer}* — {meaning} (EKI EVS). " if meaning else "") + \
        f"Так в сборнике EKI отвечают на *{first}*"
    return PatternDrill(
        f"{first} – {BLANK}", answer, distractor, "", "vastus", "vastus", why,
        "fraasid", choices=tuple(choices), source_id=SOURCE_ID, translate=False)


def drills(count: int = 10, seed: int | None = None,
           rules: tuple[str, ...] | None = None,
           words: sqlite3.Connection | None = None) -> list[PatternDrill]:
    rng = random.Random(seed)
    wanted = [r for r in (rules or BASE_RULES) if r in BASE_RULES]
    makers = {"olukord": _situation, "vastus": _reply}
    out: list[PatternDrill] = []
    tries = 0
    while wanted and len(out) < count and tries < count * 20:
        item = makers[wanted[tries % len(wanted)]](rng, words)
        tries += 1
        # No sentence twice in a set while another is possible.
        if any((item.prompt, item.answer) == (o.prompt, o.answer) for o in out) \
                and tries < count * 10:
            continue
        out.append(item)
    return out
