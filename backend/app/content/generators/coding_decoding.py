from __future__ import annotations

from dataclasses import dataclass

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


@dataclass(frozen=True)
class GeneratedQuestion:
    pattern_type: str
    subtopic: str
    difficulty: int
    expected_time_seconds: int
    question_text: str
    options: tuple[str, str, str, str]
    correct_option: int
    explanation: str
    fast_method: str


def _pos(letter: str) -> int:
    return ALPHABET.index(letter) + 1


def _letter(position: int) -> str:
    return ALPHABET[(position - 1) % 26]


def _shift(word: str, amount: int) -> str:
    return "".join(_letter(_pos(ch) + amount) for ch in word)


def _opposite(word: str) -> str:
    return "".join(_letter(27 - _pos(ch)) for ch in word)


def _alternate(word: str, odd_shift: int, even_shift: int) -> str:
    return "".join(
        _letter(_pos(ch) + (odd_shift if index % 2 == 0 else even_shift))
        for index, ch in enumerate(word)
    )


def _position_shift(word: str, sign: int) -> str:
    return "".join(_letter(_pos(ch) + sign * (index + 1)) for index, ch in enumerate(word))


def _swap_pairs(word: str) -> str:
    chars = list(word)
    for index in range(0, len(chars) - 1, 2):
        chars[index], chars[index + 1] = chars[index + 1], chars[index]
    return "".join(chars)


def _vowel_consonant(word: str, vowel_shift: int, consonant_shift: int) -> str:
    return "".join(
        _letter(_pos(ch) + (vowel_shift if ch in "AEIOU" else consonant_shift))
        for ch in word
    )


def _normal_numeric(word: str) -> str:
    return "-".join(str(_pos(ch)) for ch in word)


def _reverse_numeric(word: str) -> str:
    return "-".join(str(27 - _pos(ch)) for ch in word)


def _sum_positions(word: str) -> int:
    return sum(_pos(ch) for ch in word)


def _fallback(answer: str) -> list[str]:
    if answer.isdigit():
        value = int(answer)
        return [str(value + 1), str(max(0, value - 1)), str(value + 5)]
    if "-" in answer and all(part.isdigit() for part in answer.split("-")):
        parts = [int(part) for part in answer.split("-")]
        return [
            "-".join(str(part + 1) for part in parts),
            "-".join(str(max(1, part - 1)) for part in parts),
            "-".join(str(part) for part in reversed(parts)),
        ]
    if answer.isalpha() and answer.isupper():
        return [_shift(answer, 1), _shift(answer, -1), answer[::-1], _swap_pairs(answer)]
    return ["xx", "yy", "zz", "na"]


def _make(
    index: int,
    *,
    pattern: str,
    subtopic: str,
    difficulty: int,
    seconds: int,
    question: str,
    answer: str,
    distractors: list[str],
    explanation: str,
    fast_method: str,
) -> GeneratedQuestion:
    seen = {answer}
    clean: list[str] = []
    for item in [*distractors, *_fallback(answer)]:
        if item not in seen:
            seen.add(item)
            clean.append(item)
        if len(clean) == 3:
            break
    if len(clean) != 3:
        raise ValueError(f"Need three unique distractors: {question}")

    raw = [answer, *clean]
    shift = index % 4
    options = tuple(raw[shift:] + raw[:shift])
    return GeneratedQuestion(
        pattern_type=pattern,
        subtopic=subtopic,
        difficulty=difficulty,
        expected_time_seconds=seconds,
        question_text=question,
        options=options,  # type: ignore[arg-type]
        correct_option=options.index(answer) + 1,
        explanation=explanation,
        fast_method=fast_method,
    )


def build_coding_decoding_bank() -> list[GeneratedQuestion]:
    bank: list[GeneratedQuestion] = []
    words = ["LIGHT", "TRAIN", "BRAVE", "HOUSE", "WORLD", "SMILE", "POINT", "CLOUD", "GREEN", "CHAIR"]
    examples = ["CAT", "MIND", "ROAD", "BOOK", "FISH", "QUIZ", "STONE", "APPLE", "ZEBRA", "WATER"]

    # 1. Fixed shifts
    shifts = [1, 2, -1, 3, -2, 1, -3, 2, 1, -2]
    for example, target, amount in zip(examples, words, shifts):
        coded = _shift(example, amount)
        answer = _shift(target, amount)
        bank.append(_make(
            len(bank), pattern="fixed-caesar-shift", subtopic="Fixed letter shift coding",
            difficulty=1 if len(bank) < 4 else 2, seconds=35,
            question=f"In a certain code, {example} is written as {coded}. How is {target} written?",
            answer=answer,
            distractors=[_shift(target, amount + 1), _shift(target, amount - 1), answer[::-1]],
            explanation=f"Every letter moves by {amount:+d}; {target} becomes {answer}.",
            fast_method="Compare source and code letter-by-letter and verify one constant offset.",
        ))

    # 2. Alternating shifts
    odd_even = [(3,-2),(2,-1),(1,-2),(3,-1),(2,-3),(1,-1),(2,-2),(3,-2),(1,-3),(2,-1)]
    for example, target, (odd, even) in zip(words, examples, odd_even):
        coded = _alternate(example, odd, even)
        answer = _alternate(target, odd, even)
        bank.append(_make(
            len(bank), pattern="alternating-shift-code", subtopic="Alternating shift coding",
            difficulty=2 if len(bank) < 13 else 3, seconds=45,
            question=f"{example} is coded as {coded} using odd-position shift {odd:+d} and even-position shift {even:+d}. How is {target} coded?",
            answer=answer,
            distractors=[_alternate(target, odd + 1, even), _alternate(target, odd, even - 1), _shift(target, odd)],
            explanation=f"Apply {odd:+d} to positions 1,3,5... and {even:+d} to positions 2,4,6....",
            fast_method="Separate odd and even positions.",
        ))

    # 3. Opposite alphabet
    for target in words:
        answer = _opposite(target)
        bank.append(_make(
            len(bank), pattern="reverse-alphabet-code", subtopic="Reverse alphabet coding",
            difficulty=1, seconds=40,
            question=f"Using opposite letters A↔Z, B↔Y, ... how is {target} coded?",
            answer=answer,
            distractors=[_shift(answer, 1), _shift(answer, -1), answer[::-1]],
            explanation=f"Replace every letter by its alphabet opposite. {target} becomes {answer}.",
            fast_method="Opposite normal positions sum to 27.",
        ))

    # 4. Alphabet-position numeric codes
    for index, target in enumerate(words):
        reverse_mode = index % 2 == 1
        answer = _reverse_numeric(target) if reverse_mode else _normal_numeric(target)
        bank.append(_make(
            len(bank), pattern="alphabet-position-code", subtopic="Alphabet position numeric code",
            difficulty=1 if index < 4 else 2, seconds=40,
            question=f"Using {'A=26, B=25, ... Z=1' if reverse_mode else 'A=1, B=2, ... Z=26'}, find the code for {target}.",
            answer=answer,
            distractors=[_normal_numeric(target) if reverse_mode else _reverse_numeric(target), answer[::-1]],
            explanation="Convert each letter independently using the stated alphabet numbering.",
            fast_method="Reverse value = 27 − normal position.",
        ))

    # 5. Sum-of-position codes
    offsets = [-1, -1, 0, 2, 3, -2, 1, 0, 4, -3]
    for example, target, offset in zip(examples, words, offsets):
        example_code = _sum_positions(example) + offset
        answer_value = _sum_positions(target) + offset
        answer = str(answer_value)
        bank.append(_make(
            len(bank), pattern="position-sum-code", subtopic="Position sum code",
            difficulty=2 if len(bank) < 44 else 3, seconds=50,
            question=f"{example} is coded as {example_code} using the sum of alphabet positions with a fixed adjustment. What is the code for {target}?",
            answer=answer,
            distractors=[str(answer_value + 1), str(answer_value - 1), str(_sum_positions(target))],
            explanation=f"Letter-position sum for {target} is {_sum_positions(target)}; apply the same adjustment {offset:+d}.",
            fast_method="Find the position sum once, then apply the fixed adjustment.",
        ))

    # 6. Reversal/rearrangement
    modes = ["full","full","middle","full","middle","full","middle","full","middle","full"]
    for example, target, mode in zip(examples, words, modes):
        def encode(word: str) -> str:
            if mode == "full":
                return word[::-1]
            return word if len(word) < 3 else word[0] + word[-2:0:-1] + word[-1]

        coded = encode(example)
        answer = encode(target)
        bank.append(_make(
            len(bank), pattern="word-reversal-code", subtopic="Reversal/rearrangement coding",
            difficulty=1 if mode == "full" else 2, seconds=45,
            question=f"In a code, {example} is written as {coded}. Using the same positional rearrangement, how is {target} written?",
            answer=answer,
            distractors=[target[::-1], _swap_pairs(target), _shift(answer, 1)],
            explanation="The code changes the order of letters, not their alphabet values.",
            fast_method="Check whether the same letters are simply rearranged before testing shifts.",
        ))

    # 7. Position-wise shifts
    signs = [1,1,-1,1,-1,1,-1,1,-1,1]
    for example, target, sign in zip(examples, words, signs):
        coded = _position_shift(example, sign)
        answer = _position_shift(target, sign)
        bank.append(_make(
            len(bank), pattern="alphabet-transform", subtopic="Position-wise alphabet transform",
            difficulty=3, seconds=55,
            question=f"{example} is coded as {coded} by shifting successive positions {'+1,+2,+3,...' if sign > 0 else '−1,−2,−3,...'}. How is {target} coded?",
            answer=answer,
            distractors=[_shift(target, sign), _position_shift(target, -sign), answer[::-1]],
            explanation="Apply the position number itself as the shift amount.",
            fast_method="Write the shift above each letter position.",
        ))

    # 8. Artificial-language sentence coding
    sentence_cases = [
        ("RED SKY BRIGHT","ka mi zo","BLUE SKY CLEAR","tu mi pa","SKY","mi"),
        ("GOOD FOOD TASTY","ra ki po","GOOD BOOK USEFUL","ra se nu","GOOD","ra"),
        ("FAST TRAIN MOVES","di ko la","FAST CAR SHINES","di pe ru","FAST","di"),
        ("GREEN LEAF SOFT","xo ve ni","GREEN GRASS WET","xo pa qu","GREEN","xo"),
        ("SMART CHILD LEARNS","bu fi ke","SMART PHONE COSTLY","bu zo ra","SMART","bu"),
        ("COLD WATER PURE","me si vo","COLD NIGHT DARK","me lu ga","COLD","me"),
        ("HAPPY PEOPLE SMILE","ja no fe","HAPPY DAY SUNNY","ja tu li","HAPPY","ja"),
        ("BIG HOUSE CLEAN","ru ma se","BIG TREE TALL","ru ko vi","BIG","ru"),
        ("NEW PLAN READY","te la ku","NEW JOB OPEN","te fi sa","NEW","te"),
        ("WHITE CLOUD MOVES","qi ro na","WHITE PAPER CLEAN","qi su me","WHITE","qi"),
    ]
    for s1, c1, s2, c2, ask, answer in sentence_cases:
        alternatives = list(dict.fromkeys((c1 + " " + c2).split()))
        bank.append(_make(
            len(bank), pattern="sentence-substitution-code", subtopic="Sentence / substitution code",
            difficulty=2, seconds=60,
            question=f'"{s1}" = "{c1}" and "{s2}" = "{c2}". What is the code for "{ask}"?',
            answer=answer,
            distractors=[code for code in alternatives if code != answer],
            explanation=f'"{ask}" is common to both sentences and "{answer}" is common to both coded forms.',
            fast_method="Common word ↔ common code.",
        ))

    # 9. Vowel/consonant conditional coding
    settings = [(2,-1),(1,-2),(2,-2),(1,-1),(2,-3),(1,-2),(2,-1),(1,-3),(2,-2),(1,-1)]
    for example, target, (vowel_shift, consonant_shift) in zip(examples, words, settings):
        coded = _vowel_consonant(example, vowel_shift, consonant_shift)
        answer = _vowel_consonant(target, vowel_shift, consonant_shift)
        bank.append(_make(
            len(bank), pattern="vowel-consonant-code", subtopic="Vowel/consonant conditional coding",
            difficulty=3, seconds=55,
            question=f"Vowels shift {vowel_shift:+d} and consonants {consonant_shift:+d}. {example} becomes {coded}. How is {target} coded?",
            answer=answer,
            distractors=[_vowel_consonant(target, vowel_shift + 1, consonant_shift), _vowel_consonant(target, vowel_shift, consonant_shift - 1), _shift(target, vowel_shift)],
            explanation="Classify each letter as vowel or consonant, then apply the matching shift.",
            fast_method="Mark V/C before transforming.",
        ))

    # 10. Pairwise/block rearrangement
    for index, (example, target) in enumerate(zip(examples, words)):
        shift_after = index >= 5
        coded = _swap_pairs(example)
        answer = _swap_pairs(target)
        if shift_after:
            coded = _shift(coded, 1)
            answer = _shift(answer, 1)
        bank.append(_make(
            len(bank), pattern="pairwise-rearrangement-code", subtopic="Pairwise / block rearrangement",
            difficulty=2 if not shift_after else 3, seconds=60,
            question=f"Adjacent pairs are swapped{' and then shifted +1' if shift_after else ''}. {example} becomes {coded}. How is {target} coded?",
            answer=answer,
            distractors=[_swap_pairs(target), _shift(target, 1), answer[::-1]],
            explanation="Split the word into adjacent pairs and apply the same pair operation to every block.",
            fast_method="Draw pair separators before rearranging.",
        ))

    if len(bank) != 100:
        raise AssertionError(f"Expected 100 questions, got {len(bank)}")
    return bank
