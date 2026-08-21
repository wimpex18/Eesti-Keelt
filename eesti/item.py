"""What every generated exercise has in common.

Four generators now produce practice items — object-case templates, corpus
clozes, conjugation frames and the closed-class patterns — and the UI, the
review scheduler and the CLI all want the same five things from any of them:
show it, grade it, name what is being asked, reveal the solution, and link the
rule.

Each generator kept its own copy of those five, which is exactly the code that
drifts: one grader trimmed whitespace and another did not, one carried the
handbook reference and another dropped it. This is the one definition.

Grading is **deterministic everywhere** — no model, no network. A drill whose
correctness depends on a service is a drill that is wrong when the service is
down, and this project already assumes services are down.
"""

from __future__ import annotations

from dataclasses import asdict

BLANK = "____"


class GradedItem:
    """Mixin for exercise dataclasses.

    Expects the fields `prompt`, `answer`, `distractor`, `lemma`, `topic` and a
    `label` property naming the form being asked for.
    """

    prompt: str
    answer: str
    distractor: str
    lemma: str
    topic: str

    @property
    def label(self) -> str:  # pragma: no cover - each item defines its own
        raise NotImplementedError

    def check(self, given: str) -> bool:
        """Deterministic grading: trim, casefold, compare."""
        return given.strip().casefold() == self.answer.casefold()

    @property
    def hint(self) -> str:
        """What the learner is told before answering.

        An empty `lemma` means the word itself is the answer — question words —
        and naming it would print the solution above the prompt.
        """
        return f"{self.lemma}, {self.label}" if self.lemma else self.label

    @property
    def solution(self) -> str:
        """The completed sentence, capitalised if the blank opens it.

        A sentence-initial blank is common in the imperative and question-word
        frames, and a lowercase sentence start reads as a bug rather than as an
        answer.
        """
        answer = self.answer
        if self.prompt.startswith(BLANK):
            answer = answer[:1].upper() + answer[1:]
        return self.prompt.replace(BLANK, answer)

    @property
    def reference(self) -> dict | None:
        """The EKK section for this item's topic, so rule and exercise ship together.

        None where the topic has no tagged rule — a paradigm is not a rule with
        a section, and a confidently wrong link is worse than no link.
        """
        from .curriculum import by_id
        from .grammar import describe

        # The error tag first -- its entry is written for somebody who got the
        # thing wrong. Failing that, the topic's own id: 18 of the 23 drillable
        # topics carry no tag, because tags are the fixed nine the Notion log
        # validates against and that set must not grow to accommodate a link.
        tag = by_id(self.topic).tag
        found = describe(tag) if tag else None
        if found and found.get("known"):
            return found
        by_topic = describe(self.topic)
        return by_topic if by_topic.get("known") else found

    def to_dict(self) -> dict:
        # `label` alongside `hint`, because the page needs the two halves apart.
        # `hint` glues lemma and label into one string, and a screen that renders
        # them at one weight, beside a gloss and a level, is four different kinds
        # of information in a single grey run-on.
        return asdict(self) | {
            "hint": self.hint,
            "label": self.label,
            "reference": self.reference,
        }
