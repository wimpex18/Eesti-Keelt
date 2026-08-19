"""ERR *Lihtsad uudised* — the only live source in the project.

Everything else read here is frozen: the radio courses ended in 2019, Selges
keeles is a fixed set of 349 posts. Both are good and both will say exactly the
same thing in spring 2027. This one publishes weekly, in deliberately
simplified Estonian, about things that happened this month — which is what a
reading exam is made of.

Three things the harvest has to get right, and each was a real defect in the
page rather than a hypothetical:

- ERR serves HTML entities, so `&uuml;` has to become `ü` or the text is not
  Estonian at all
- every issue opens with the same English sentence explaining the series —
  useful to a visitor, noise in a corpus
- the share widget leaks its SVG attributes into paragraph text, which would
  otherwise put `aria-label` into a reading exercise
"""

from __future__ import annotations

import pytest

from eesti.harvest.lihtsad import (MIN_WORDS, _usable, issue_urls, parse_issue,
                                   to_items)

PAGE = """
<html><body>
<script type="application/ld+json">
{"@type":"NewsArticle","headline":"Lihtsad uudised 17. juulil",
 "datePublished":"2026-07-17T12:25:00+0300"}
</script>
<p>0" class="share-svg-text" aria-label="Marked as liked {{ctrl.likes}}"</p>
<p>"Lihtsad uudised," meaning easy or simple news, is for anyone who wants to
   improve their Estonian.</p>
<p>Eesti rahvaarv langes esimest korda &uuml;heksa aasta jooksul.</p>
<p>Statistikaameti andmetest selgub, et 2024. aastal registreeriti 9690
   s&uuml;ndi ja 15 756 surma. Loomulik iive oli 6066 inimesega miinuses.</p>
<p>Kaitsev&auml;gi rajab Narva baasi, kus hakkab teenima umbes kolmsada
   kaitsev&auml;elast ning kuhu ehitatakse uued kasarmud ja &otilde;ppev&auml;ljak.</p>
<p>Rahvuslikus l&otilde;ikes kasvas eestlaste arv kolme tuhande inimese v&otilde;rra,
   samal ajal kui venelaste arv langes enam kui viie tuhande inimese v&otilde;rra.
   Statistik &uuml;tles, et sisser&auml;nde m&otilde;ju on olnud viimastel aastatel
   v&auml;iksem kui varem ja loomulik iive j&auml;&auml;b endiselt negatiivseks.</p>
<p>Это перевод, который не нужен.</p>
</body></html>
"""


@pytest.fixture
def issue():
    return parse_issue(PAGE, "https://news.err.ee/1/")


class TestParagraphFilters:
    def test_the_english_introduction_is_dropped(self):
        assert not _usable('"Lihtsad uudised," meaning easy or simple news, is '
                           "for anyone who wants to improve their Estonian.")

    def test_leaked_markup_is_dropped(self):
        """`aria-label` in a reading exercise is worse than a shorter text."""
        assert not _usable('0" class="share-svg-text" aria-label="Marked"')

    def test_a_russian_paragraph_is_dropped(self):
        """A translation block is not Estonian reading material."""
        assert not _usable("Это перевод, который здесь совершенно не нужен")

    def test_real_estonian_prose_survives(self):
        assert _usable("Eesti rahvaarv langes esimest korda üheksa aasta jooksul.")


class TestParsing:
    def test_entities_become_letters(self, issue):
        """`&uuml;` is not a letter, and a corpus full of them is not Estonian."""
        assert "üheksa" in issue.body
        assert "&uuml;" not in issue.body

    def test_the_headline_and_date_come_from_ld_json(self, issue):
        assert issue.title == "Lihtsad uudised 17. juulil"
        assert issue.published.startswith("2026-07-17")

    def test_the_noise_paragraphs_are_gone(self, issue):
        assert "aria-label" not in issue.body
        assert "meaning easy or simple" not in issue.body
        assert "перевод" not in issue.body

    def test_a_stub_is_not_an_issue(self):
        """A redirect or teaser page must not enter the corpus as a reading."""
        assert parse_issue("<html><p>Lühike.</p></html>", "u") is None

    def test_the_floor_is_a_real_bar(self):
        assert MIN_WORDS >= 50


class TestItems:
    def test_no_level_is_claimed(self, issue):
        """The series is written for learners and is plainly simpler than the
        newsroom's usual output — but "simplified" is not a CEFR level, and this
        app does not invent one."""
        assert to_items([issue])[0].level is None

    def test_it_is_filed_as_reading_without_audio(self, issue):
        """The page says "listen and read", and the player is loaded by
        JavaScript: there is no .mp3 or .m3u8 in the HTML a plain request gets.
        Claiming audio would be a link that never plays."""
        item = to_items([issue])[0]
        assert item.skill == "lugemine"
        assert item.audio_url is None
        assert item.meta["audio"] is False

    def test_it_is_marked_as_the_live_feed(self, issue):
        assert to_items([issue])[0].meta["live_feed"] is True


class TestAgainstTheLiveFeed:
    @pytest.fixture(scope="class")
    @classmethod
    def urls(cls):
        try:
            return issue_urls()
        except Exception as exc:  # noqa: BLE001 - a third party being down
            pytest.skip(f"ERR unreachable: {exc}")

    def test_the_feed_still_lists_issues(self, urls):
        assert len(urls) > 5

    def test_they_are_article_urls(self, urls):
        assert all(u.startswith("https://news.err.ee/") for u in urls)
