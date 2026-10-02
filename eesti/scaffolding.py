"""Russian reading support for the EKI-based personal-pronoun exercise.

These are editorial translations of the existing exercise frames, not additional
answer keys. Estonian forms remain solely in pronouns.TABLES (EKI Teatmik).
Only exact known frames receive a translation; new frames never inherit one.
"""

PRONOUNS = {
    "mina": ("я", "мне", "у меня", "меня", "обо мне", "со мной", "мой"),
    "sina": ("ты", "тебе", "у тебя", "тебя", "о тебе", "с тобой", "твой"),
    "tema": ("он / она", "ему / ей", "у него / неё", "его / её", "о нём / ней", "с ним / ней", "его / её"),
    "meie": ("мы", "нам", "у нас", "нас", "о нас", "с нами", "наш"),
    "teie": ("вы", "вам", "у вас", "вас", "о вас", "с вами", "ваш"),
    "nemad": ("они", "им", "у них", "их", "о них", "с ними", "их"),
}

FRAMES = {
    "Anna see raamat ____.": (1, "Дай эту книгу {}."),
    "____ on kaks last.": (2, "{} двое детей."),
    "Ma ootan ____.": (3, "Я жду {}."),
    "Me räägime ____.": (4, "Мы говорим {}."),
    "Ma tulen ____.": (5, "Я приду {}."),
    "See on ____ auto.": (6, "Это {} машина."),
}


def pronoun_support(shown: dict) -> dict:
    """Reading support without revealing any Estonian answer form."""
    if shown.get("topic") != "asesonad":
        return {}
    pronoun = PRONOUNS.get(shown.get("lemma"))
    frame = FRAMES.get(shown.get("prompt"))
    if not pronoun or not frame:
        return {}
    index, template = frame
    sentence = template.format(pronoun[index])
    # Possessive gender follows машина in Russian, independently of the speaker.
    if index == 6:
        sentence = sentence.replace("мой машина", "моя машина").replace(
            "твой машина", "твоя машина").replace("наш машина", "наша машина").replace(
            "ваш машина", "ваша машина")
    questions = {1: "кому?", 2: "у кого?", 3: "кого?", 4: "о ком?", 5: "с кем?", 6: "чья?"}
    return {"lemma_ru": pronoun[0], "sentence_ru": sentence[0].upper() + sentence[1:],
            "form_ru": questions[index]}
