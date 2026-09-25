"""What every generated exercise has in common.

The UI, the review scheduler and the CLI need the same things from every
generator: show it, grade it, name what is asked, reveal the solution, and link
the rule. This is the one definition.

Grading is deterministic everywhere — no model, no network.
"""

from __future__ import annotations

from dataclasses import asdict

BLANK = "____"



def accepts(answer: str, given: str) -> bool:
    """Trim, casefold, compare. An answer with parallel forms (`minule ~ mulle`,
    as EKI prints them) accepts any one of them."""
    said = given.strip().casefold()
    if said == answer.strip().casefold():
        return True
    return any(said == variant.strip().casefold() for variant in answer.split(" ~ "))

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
        return accepts(self.answer, given)

    @property
    def hint(self) -> str:
        """What the learner is told before answering. An empty `lemma` means the word is
        the answer (question words), so it is not printed.
        """
        return f"{self.lemma}, {self.label}" if self.lemma else self.label

    @property
    def solution(self) -> str:
        """The completed sentence, capitalised if the blank opens it."""
        answer = self.answer
        if self.prompt.startswith(BLANK):
            answer = answer[:1].upper() + answer[1:]
        return self.prompt.replace(BLANK, answer)

    @property
    def reference(self) -> dict | None:
        """The EKK section for this item's topic, or None where no section covers it."""
        from .curriculum import by_id
        from .grammar import describe

        # The error tag's entry first (written for a mistake), then the topic id's: most
        # topics have no tag, and the nine tags must match the Notion log.
        tag = by_id(self.topic).tag
        found = describe(tag) if tag else None
        if found and found.get("known"):
            return found
        by_topic = describe(self.topic)
        return by_topic if by_topic.get("known") else found

    def to_dict(self) -> dict:
        # `label` alongside `hint`, so the page can style the word and the requested form
        # separately.
        return asdict(self) | {
            "hint": self.hint,
            "label": self.label,
            "reference": self.reference,
        }
