"""An outage must not turn into a clean grammar answer or misleading health."""
import urllib.error

import pytest

from eesti.evals.health import probe
from eesti.providers.grammar import GECUnavailable, TartuNLPGrammar, why_failed


@pytest.mark.parametrize('payload', [{}, {'error': 'busy'}, {'corrections': None},
                                     {'corrections': [{}]}])
def test_incompatible_payload_is_not_no_errors(payload):
    with pytest.raises(ValueError):
        TartuNLPGrammar.validate(payload, v2=True)


def test_probe_reports_each_endpoint_and_real_failure(monkeypatch):
    def post(self, url, text, timeout=None):
        if url.endswith('/v2'):
            raise TimeoutError()
        raise urllib.error.HTTPError(url, 500, 'Internal error', {}, None)
    monkeypatch.setattr(TartuNLPGrammar, '_post', post)
    result = probe()
    assert not result['operational'] and len(result['results']) == 6
    assert {r['failure'] for r in result['results']} == {'TimeoutError', 'HTTPError 500'}
    with pytest.raises(GECUnavailable) as caught:
        TartuNLPGrammar().check('Tere')
    assert 'v2=TimeoutError' in why_failed(caught.value)
    assert 'spans=HTTPError 500' in why_failed(caught.value)


def test_health_means_valid_post_response_not_get_reachability(monkeypatch):
    monkeypatch.setattr(TartuNLPGrammar, '_post', lambda *args: {'corrections': []})
    assert probe()['operational']


@pytest.mark.parametrize('payload', ['{}', '{"corrections": null}', '{"corrections": [{}]}'])
def test_malformed_llm_response_is_not_a_clean_answer(monkeypatch, payload):
    from eesti.providers import grammar, llm

    def reply(*args, **kwargs):
        assert kwargs['attempts'] == 1
        return payload
    monkeypatch.setattr(llm, 'complete', reply)
    with pytest.raises(ValueError):
        grammar.LLMGrammar('workers-ai').check('Ma elan Tallinnas.')
