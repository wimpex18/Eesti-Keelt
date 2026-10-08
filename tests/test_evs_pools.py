"""Public practice from EKI EVS's example phrases (DEV-54).

The harvested corpus is owner-only (`eesti/licences.py`), so outside the
owner's scope `sources.connect` shows an empty library. EVS is CC BY 4.0: its
example phrases stand in for the corpus there, credited to EKI. Every test here
runs in an explicit guest or owner scope — locally without `PROXY_TOKEN` a
request is the owner's unless the identity says otherwise.
"""

from __future__ import annotations

import shutil
import sqlite3

import pytest
from estnltk.vabamorf.morf import synthesize

from eesti import config, evs, identity
from eesti.item import BLANK, accepts

#: Genuine EVS phrases with EKI's Russian (CC BY 4.0), chosen because their
#: words are in the fixture word list: one or more per corpus-based topic, two
#: with a comma before `et`, and short ones for tiles, dictation and reading aloud.
PHRASES = (
    ("pea", "vanaema silitab lapse pead", "бабушка гладит ребёнка по голове"),
    ("õhtu", "ta korraldas perekondliku õhtu", "он устроил семейное торжество / семейный вечер"),
    ("minut", "kell on kümne minuti pärast seitse", "без десяти [минут] семь [часов]"),
    ("pilet", "ostsin kolm piletit teatrisse", "я купил три билета в театр"),
    ("kohv", "pärast lõunasööki pakuti kohvi", "после обеда был подан кофе"),
    ("lumi", "sügisel tuli lumi varakult maha", "осенью снег выпал рано"),
    ("jõudma", "buss jõuab Tartust Tallinna kolme tunniga",
     "автобус идёт из Тарту в Таллинн три часа"),
    ("raske", "koolis pidasid õpetajad teda raskeks lapseks",
     "в школе учителя считали его трудным ребёнком"),
    ("raamat", "istus uuesti raamatute taha", "он снова засел за книги"),
    ("külm", "sügisel enne külmade saabumist", "осенью до наступления холодов / морозов"),
    ("leidma", "järsku leidsin, et mu kohver oli kadunud",
     "вдруг я обнаружил, что мой чемодан пропал"),
    ("tundma", "tundsin häälest, et see oled sina",
     "я по голосу узнал, что это ты; я узнал / опознал тебя по голосу"),
    ("eksam", "eesti keele eksam", "экзамен по эстонскому языку"),
    ("isa", "kolme lapse isa", "отец троих детей"),
    ("jalgratas", "kolme rattaga jalgratas", "трёхколёсный велосипед"),
)

#: Phrases that are not one spelled-out sentence: an open slot, alternatives,
#: and an idiom. None may reach practice.
EXCLUDED = (
    evs.Example("kohv", "{keda} kohvile kutsuma",
                "приглашать/пригласить {кого} на кофе / на чашку кофе"),
    evs.Example("pilet", "piletid on läbi / välja müüdud", "билеты распроданы"),
    evs.Example("külm", "külm sõda", "холодная война", evs.IDIOM),
)

ESTONIAN = {et for _, et, _ in PHRASES}
CORPUS_TOPICS = ("gen-stem", "osastav", "mitmus", "kohakaanded", "harvad-kaanded")
GUEST = identity.Scope(identity.GUEST, id="evs-pools")
HEADERS = {"x-eesti-scope": "guest", "x-eesti-guest": "evs-pools"}


@pytest.fixture
def evs_words(monkeypatch, tmp_path, fixture_data):
    """The fixture word list with EVS's phrases imported, as `cli import-evs` leaves it."""
    path = tmp_path / "eesti.db"
    shutil.copy(fixture_data["words"], path)
    conn = sqlite3.connect(path)
    evs.store_examples(conn, [evs.Example(*p) for p in PHRASES] + list(EXCLUDED))
    conn.close()
    monkeypatch.setattr(config, "DB_PATH", path)
    return path


def _items(topic, count=10, seed=1, scope=GUEST):
    from eesti.practice import items_for

    with identity.use(scope):
        return items_for(topic, count=count, seed=seed)


class TestThePool:
    def test_only_spelled_out_example_phrases(self, evs_words):
        conn = sqlite3.connect(evs_words)
        got = {p.estonian for p in evs.phrases(conn)}
        assert got == ESTONIAN
        assert all(p.russian for p in evs.phrases(conn))

    def test_words_and_levels_narrow_it(self, evs_words):
        conn = sqlite3.connect(evs_words)
        short = {p.estonian for p in evs.phrases(conn, max_words=4)}
        assert short == {et for et in ESTONIAN if len(et.split()) <= 4}
        # A level keeps the phrases EKI gives for headwords at that level.
        level = dict(conn.execute("SELECT word, proficiency FROM words"))
        a1 = evs.phrases(conn, levels=("A1",))
        assert a1 and {level.get(p.lemma) for p in a1} == {"A1"}
        assert len(a1) < len(ESTONIAN)

    def test_a_database_that_never_imported_answers_empty(self, tmp_path):
        assert evs.phrases(sqlite3.connect(tmp_path / "none.db")) == []


class TestGuestPractice:
    def test_every_topic_with_a_generator_has_items(self, evs_words):
        """Wherever the owner gets items, so does a guest. (`tuletus` needs derived
        words the fixture list does not have, in every scope.)"""
        from eesti.curriculum import TOPICS

        def empty(scope):
            return [t.id for t in TOPICS
                    if t.generator and not _items(t.id, count=5, scope=scope)]

        assert empty(GUEST) == empty(identity.OWNER_SCOPE) == ["tuletus"]

    @pytest.mark.parametrize("topic", CORPUS_TOPICS)
    def test_corpus_topics_come_from_evs(self, evs_words, topic):
        items = _items(topic)
        assert items
        for item in items:
            assert item.source_id == evs.SOURCE_ID
            # The completed phrase is EKI's, and Vabamorf builds the answer back.
            first = item.answer.split(" ~ ")[0]
            assert item.prompt.replace(BLANK, first) in ESTONIAN
            assert first in synthesize(item.lemma, item.case)

    def test_gen_stem_no_longer_dead_ends(self, client, evs_words):
        got = client.post("/api/practice", json={"topic": "gen-stem", "count": 5},
                          headers=HEADERS).json()
        assert got["items"] and got["detail"] is None
        for item in got["items"]:
            assert item["attribution"] == evs.ATTRIBUTION
        item = got["items"][0]
        verdict = client.post("/api/practice/answer", headers=HEADERS, json={
            "topic": "gen-stem", "prompt": item["prompt"], "answer": item["answer"],
            "given": item["answer"].split(" ~ ")[0], "token": item["token"]}).json()
        assert verdict["correct"]

    def test_commas_come_from_evs(self, evs_words):
        items = _items("kirjavahemargid")
        assert items
        assert {i.answer for i in items} <= ESTONIAN
        assert all(i.source_id == evs.SOURCE_ID for i in items)

    def test_without_the_import_a_corpus_topic_still_says_why(self, client):
        got = client.post("/api/practice", json={"topic": "gen-stem", "count": 5},
                          headers=HEADERS).json()
        assert got["items"] == [] and "корпус" in got["detail"]


#: The fixture's phrases whose order the Russian fixes: a noun last, and before
#: it only nominative and genitive attributes, which cannot follow it.
FIXED = {"eesti keele eksam", "kolme lapse isa"}


class TestPhraseTiles:
    def test_word_order_is_built_from_evs_tiles(self, evs_words):
        items = _items("sonajark")
        # Each left out has another correct order: `ostsin kolm piletit
        # teatrisse` has a verb, `sügisel enne külmade saabumist` an adverb, and
        # `kolme rattaga jalgratas` is also `jalgratas kolme rattaga`.
        assert {i.answer for i in items} == FIXED
        for item in items:
            words = item.answer.split()
            assert item.source_id == evs.SOURCE_ID and item.rule == "evs-order"
            assert sorted(item.tiles) == sorted(words) and list(item.tiles) != words
            assert item.ru and item.choices == ()
            # The tiles in EKI's order are the answer; another order is not.
            assert accepts(item.answer, " ".join(words))
            assert not accepts(item.answer, " ".join(item.tiles))
            assert 3 <= len(words) <= 7

    @pytest.mark.parametrize("phrase, fixed", [
        # Genitive chains and a determiner with one adjective: EKK SÜ 98, 104.
        ("kolme lapse isa", True),
        ("laulja populaarsuse saladus", True),
        ("minu kunagine klassiõde", True),
        # EKK SÜ 104's free orders: an adjective beside a genitive, a cardinal
        # beside an ordinal; and two descriptive adjectives.
        ("dollari ametlik kurss", False),
        ("viis viimast lehekülge", False),
        ("kenad sirged jalad", False),
        # An attribute in another case can follow its head (EKK SÜ 102).
        ("kolme rattaga jalgratas", False),
        # Not an attribute before a head: coordination, address, a label.
        ("palk pluss preemia", False),
        ("sa vana nõid", False),
        ("buss number kuus", False),
        # A clause: verb-second is usual, not obligatory (EKK SÜ 92).
        ("ostsin kolm piletit teatrisse", False),
    ])
    def test_only_an_order_ekk_fixes_is_built(self, phrase, fixed):
        """Every phrase here is EVS's. A tile item whose other order is also
        Estonian would mark the learner wrong for correct Estonian."""
        from eesti.wordorder import phrase_tiles

        built = phrase_tiles([evs.Example("x", phrase, "—")], count=1, seed=1)
        assert bool(built) is fixed

    def test_the_server_grades_the_built_phrase(self, client, evs_words):
        got = client.post("/api/practice", json={"topic": "sonajark", "count": 3},
                          headers=HEADERS).json()
        item = got["items"][0]
        assert item["tiles"] and item["attribution"] == evs.ATTRIBUTION
        verdict = client.post("/api/practice/answer", headers=HEADERS, json={
            "topic": "sonajark", "prompt": item["prompt"], "answer": item["answer"],
            "given": item["answer"], "token": item["token"]}).json()
        assert verdict["correct"]


class TestOwnerScope:
    def test_the_private_corpus_comes_first(self, evs_words):
        sources = [i.source_id for i in _items("gen-stem", scope=identity.OWNER_SCOPE)]
        assert "selges-keeles" in sources
        assert sources == sorted(sources, key=lambda s: s != "selges-keeles")


class TestListeningAndSpeaking:
    def test_dictation_reads_evs_phrases(self, client, evs_words):
        got = client.get("/api/dictation/next?count=3&seed=1", headers=HEADERS).json()
        assert got["passages"] and not got["starter"]
        assert all(p["source"] == evs.SOURCE_ID and p["text"] in ESTONIAN
                   for p in got["passages"])
        assert "EKI" in got["note"]
        p = got["passages"][0]
        verdict = client.post("/api/dictation/answer", headers=HEADERS,
                              json={"token": p["token"], "typed": p["text"]}).json()
        assert verdict["correct"]

    def test_read_aloud_offers_evs_phrases(self, client, evs_words):
        got = client.get("/api/speaking/readaloud?kind=lause&n=4&seed=1",
                         headers=HEADERS).json()
        assert got["items"]
        assert all(i["source"] == evs.SOURCE_ID and i["text"] in ESTONIAN
                   for i in got["items"])

    @pytest.mark.parametrize("part", ["lugemine", "kuulamine"])
    def test_mock_reading_and_listening_are_not_empty(self, client, evs_words, part):
        got = client.get(f"/api/mock/A2/{part}?seed=1", headers=HEADERS).json()
        assert got["tasks"] and "detail" not in got
        assert "EKI" in got["note"]
