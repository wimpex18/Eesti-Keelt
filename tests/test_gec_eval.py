"""Grammar eval distinguishes empty edits from bad linguistic edits."""

from eesti.evals import gec


def test_unchanged_target_does_not_count_as_caught():
    assert not gec._flagged({"corrections": [
        {"wrong": "raamatut", "correct": "raamatut"}]}, "raamatut")


def test_clean_controls_report_no_ops_separately(monkeypatch):
    cases = (
        gec.Case("Ma sõin suppi.", None, None, None, "EKI partitive"),
        gec.Case("Ma ei ostnud piletit.", None, None, None, "EKI negation"),
    )

    def answer(_provider, sentence, _model, _evidence):
        pair = ("suppi", "suppi") if "suppi" in sentence else ("piletit", "pileti")
        return {"corrections": [{"wrong": pair[0], "correct": pair[1]}]}

    monkeypatch.setattr(gec, "_ask", answer)
    score = gec.run("local", cases=cases, verbose=False)
    assert score["left_alone"] == "0/2"
    assert score["no_op_flags"] == 1
    assert score["changed_flags"] == 1
