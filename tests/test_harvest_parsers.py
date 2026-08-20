"""Parsing what the harvesters fetch — the half that needs no network.

`harvest/err.py` and `harvest/selges.py` sat at 0 % between them, 226
statements, because they talk to third parties and the suite deliberately does
not. That exclusion is right for `fetch` and `crawl`; it is not right for the
parsers, which are pure functions over a string and are where every bug these
modules have had actually lived.

`parse_episode` carries three fixed bugs as comments and no test for any of
them:

  * entities were never decoded, so `&#8211;` reached the reader as literal
    characters through 27 000 words of transcript;
  * only `.mp3` was accepted, and the 2015 and 2019 series serve HLS `.m3u8`,
    so two whole archives looked empty;
  * an episode was required to have a transcript, which discarded the
    audio-only series entirely.

A comment recording a fixed bug is not a test. These are.

**Every fixture here is synthetic.** ERR transcripts and Selges keeles are
owner-only by licence — `redistributable = 0` — so no real harvested text goes
in this repository. The Estonian below is invented; only the *shape* of the
markup is copied, which is the thing being parsed.
"""

from __future__ import annotations

import json

import pytest

from eesti.harvest import err, selges


def page(main: dict | None = None, clips: list[dict] | None = None,
         serial: str = "Testsari", siblings: list[str] | None = None) -> str:
    """An ERR episode page with the two structures the parser reads."""
    data = {"serialName": serial, "mainContent": main or {},
            "playerClips": clips or []}
    html = ["<html><head><script>",
            f"window.pageControlData = {json.dumps(data, ensure_ascii=False)};",
            "</script>"]
    if siblings is not None:
        html.append(
            '<script type="application/ld+json">'
            + json.dumps({"@type": "ItemList", "itemListElement":
                          [{"url": u} for u in siblings]})
            + "</script>")
    html.append("</head><body></body></html>")
    return "\n".join(html)


class TestTheThreeBugsThatAreOnlyComments:
    def test_entities_are_decoded(self):
        """`&#8211;` reached the reader as literal characters, through 27 000
        words of transcript, because nothing decoded them."""
        got = err.parse_episode(page({
            "heading": "Proov", "body": "<p>Ma lugesin raamatut &#8211; ja see oli hea.</p>",
        }), "https://r4.err.ee/1/x")
        assert got is not None
        assert "&#8211;" not in got.body and "–" in got.body

    def test_double_encoded_entities_are_decoded_too(self):
        got = err.parse_episode(page({
            "heading": "Proov", "body": "<p>Ta &amp;amp; tema</p>"}),
            "https://r4.err.ee/1/x")
        assert "&amp;" not in got.body and "&" in got.body

    def test_an_hls_stream_counts_as_audio(self):
        """The 2015 and 2019 series serve `.m3u8`. Accepting only MP3 dropped
        both archives, which is why they looked empty."""
        got = err.parse_episode(
            page({"heading": "Proov"},
                 clips=[{"src": "//media.err.ee/lugu.m3u8"}]),
            "https://r4.err.ee/1/x")
        assert got.audio_url == "https://media.err.ee/lugu.m3u8"

    def test_a_plain_mp3_still_counts(self):
        got = err.parse_episode(
            page({"heading": "Proov"}, clips=[{"src": "https://a/b.mp3"}]),
            "https://r4.err.ee/1/x")
        assert got.audio_url == "https://a/b.mp3"

    def test_an_unplayable_clip_is_not_taken_as_audio(self):
        got = err.parse_episode(
            page({"heading": "Proov"}, clips=[{"src": "//a/b.jpg"}]),
            "https://r4.err.ee/1/x")
        assert got.audio_url is None

    def test_an_episode_with_audio_and_no_transcript_survives(self):
        """Requiring text discarded the audio-only series entirely."""
        got = err.parse_episode(
            page({"heading": "Ainult heli", "body": ""},
                 clips=[{"src": "//a/b.m3u8"}]),
            "https://r4.err.ee/1/x")
        assert got is not None and got.body == "" and got.audio_url




class TestTheJsonBlobItIsAllPulledFrom:
    def test_a_page_with_no_blob_yields_nothing(self):
        assert err._page_data("<html><body>nothing here</body></html>") == {}

    def test_malformed_json_is_not_an_exception(self):
        """A third party changing its markup must degrade, not crash a harvest
        that is already 170 pages in."""
        assert err._page_data(
            "<script>window.pageControlData = {not json};\n</script>") == {}

    def test_the_blob_is_trimmed_at_its_own_closing_brace(self):
        """The regex can overrun into later script on the page, so the payload
        is cut at the first balanced brace rather than at the first `}`."""
        html = page({"heading": "Proov", "body": "<p>Tekst</p>"})
        html += "\n<script>window.other = {\"a\": 1};</script>"
        assert err._page_data(html).get("serialName") == "Testsari"

    def test_nested_braces_survive_the_trim(self):
        assert err._balanced('{"a": {"b": {"c": 1}}} trailing') == \
            '{"a": {"b": {"c": 1}}}'


class TestWalkingTheSeriesWithoutABrowser:
    """ERR's archive listing is client-side, so the crawl walks episode-to-
    episode through each page's ItemList instead."""

    def test_sibling_episodes_are_found(self):
        html = page(siblings=["https://r4.err.ee/755936/mingi-slug",
                              "https://r4.err.ee/764574/teine-slug"])
        assert err._sibling_urls(html) == [
            "https://r4.err.ee/755936/mingi-slug",
            "https://r4.err.ee/764574/teine-slug"]

    def test_a_link_that_is_not_an_episode_is_ignored(self):
        html = page(siblings=["https://r4.err.ee/755936/ok",
                              "https://news.err.ee/12345/uudis"])
        assert err._sibling_urls(html) == ["https://r4.err.ee/755936/ok"]

    def test_no_itemlist_is_not_an_error(self):
        assert err._sibling_urls(page()) == []

    def test_malformed_ldjson_is_skipped(self):
        html = page().replace("</head>",
                              '<script type="application/ld+json">{oops</script></head>')
        assert err._sibling_urls(html) == []

    def test_the_series_name_gates_the_crawl(self):
        """Pages whose series differs are fetched once but never expanded, so
        the walk stays inside the archive it started in."""
        assert err._series_name(page(serial="Keelekõdi")) == "Keelekõdi"
        assert err._series_name("<html></html>") == ""


class TestMeasuringHowEstonianAThingIs:
    """The measurement that demoted the radio archives: they came out at 12 %
    Estonian, being Russian grammar lessons with Estonian examples in them."""

    def make(self, body):
        return err.Episode(url="u", title="t", body=body, audio_url=None,
                           published=None, summary="")

    def test_estonian_prose_scores_high(self):
        assert self.make("Ma lugesin eile raamatut ja see oli hea.").estonian_share > 0.9

    def test_a_russian_lesson_scores_low(self):
        got = self.make("Сегодня мы изучаем эстонский падеж osastav.")
        assert got.estonian_share < 0.5

    def test_an_empty_body_is_zero_not_a_crash(self):
        assert self.make("").estonian_share == 0.0

    def test_word_count_is_words(self):
        assert self.make("üks kaks kolm").word_count == 3


class TestSelgesKeeles:
    def make(self, body):
        return selges.Post(url="u", title="t", body=body, published="2018-01-01")

    def test_it_is_measured_the_same_way(self):
        assert self.make("Eesti keel on ilus keel.").estonian_share > 0.9

    def test_a_post_becomes_an_item_with_a_band_and_no_cefr_claim(self):
        """`level` stays None on purpose: nobody credible has rated these, and
        deriving CEFR from vocabulary rated 342 of 349 simplified items as B2."""
        items = selges.to_items([self.make("Eesti keel on ilus keel."),
                                 self.make("Ma elan Tallinnas ja töötan kodus."),
                                 self.make("Täna on ilus ilm ja päike paistab.")])
        assert len(items) == 3
        assert all(i.level is None for i in items)
        assert all(i.band in ("kergem", "keskmine", "raskem") for i in items)

    def test_the_item_carries_what_the_reader_needs(self):
        item = selges.to_items([self.make("Eesti keel on ilus keel.")])[0]
        assert item.source_id == "selges-keeles" and item.skill == "lugemine"
        assert item.meta["words"] == 5 and item.meta["published"] == "2018-01-01"

    def test_markup_is_cleaned_through_the_shared_cleaner(self):
        """Four harvesters each had a private tag regex and gave three
        different answers on one line of input. There is one cleaner now."""
        assert selges._clean("<p>Ma lugesin  raamatut .</p>") == "Ma lugesin raamatut."
