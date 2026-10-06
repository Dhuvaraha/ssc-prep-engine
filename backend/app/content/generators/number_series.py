from __future__ import annotations

from dataclasses import dataclass


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


def _fmt(value: float) -> str:
    rounded = round(value, 5)
    return str(int(rounded)) if float(rounded).is_integer() else str(rounded)


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
    for item in distractors:
        if item not in seen:
            seen.add(item)
            clean.append(item)
        if len(clean) == 3:
            break
    if len(clean) != 3:
        raise ValueError(f"Need three unique distractors for: {question}")

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


def _series(values: list[float]) -> str:
    return ", ".join(_fmt(value) for value in values)


def build_number_series_bank() -> list[GeneratedQuestion]:
    bank: list[GeneratedQuestion] = []

    constant_cases = [
        (5,4),(18,7),(72,-9),(2.5,1.5),(100,-12),
        (31,6),(420,-35),(-8,5),(125,25),(3.2,-0.8),
    ]
    for start, step in constant_cases:
        visible = [start + i*step for i in range(5)]
        answer = start + 5*step
        bank.append(_make(
            len(bank), pattern="constant-difference", subtopic="Constant difference",
            difficulty=1, seconds=30,
            question=f"{_series(visible)}, ?",
            answer=_fmt(answer),
            distractors=[_fmt(answer+step), _fmt(answer-step), _fmt(answer+2)],
            explanation=f"Every term changes by {_fmt(step)}; the next term is {_fmt(answer)}.",
            fast_method="Subtract adjacent terms first.",
        ))

    progressive_cases = [
        (3,[2,4,6,8,10],"consecutive even-number differences"),
        (10,[3,6,9,12,15],"multiples of 3"),
        (4,[1,3,5,7,9],"consecutive odd-number differences"),
        (7,[1,4,9,16,25],"successive square differences"),
        (20,[2,5,8,11,14],"differences increasing by 3"),
        (100,[-5,-10,-15,-20,-25],"negative multiples of 5"),
        (2,[2,4,8,16,32],"doubling differences"),
        (50,[-2,-4,-8,-16,-32],"negative doubling differences"),
        (11,[4,9,16,25,36],"square differences"),
        (6,[5,8,11,14,17],"differences increasing by 3"),
    ]
    for start, differences, description in progressive_cases:
        visible = [float(start)]
        for difference in differences[:4]:
            visible.append(visible[-1] + difference)
        answer = visible[-1] + differences[4]
        bank.append(_make(
            len(bank), pattern="progressive-difference", subtopic="Progressive / second differences",
            difficulty=2, seconds=45,
            question=f"{_series(visible)}, ?",
            answer=_fmt(answer),
            distractors=[_fmt(answer+differences[4]), _fmt(answer-differences[4]), _fmt(answer+3)],
            explanation=f"The first differences follow {description}; the next term is {_fmt(answer)}.",
            fast_method="Write the differences below the series.",
        ))

    multiplier_cases = [
        (3,2),(5,3),(256,.5),(729,1/3),(-2,-2),
        (4,1.5),(625,.2),(7,4),(81,-1/3),(2.5,2),
    ]
    for start, ratio in multiplier_cases:
        visible = [float(start)]
        for _ in range(4):
            visible.append(visible[-1]*ratio)
        answer = visible[-1]*ratio
        bank.append(_make(
            len(bank), pattern="multiplication-division", subtopic="Multiplication or division",
            difficulty=2, seconds=35,
            question=f"{_series(visible)}, ?",
            answer=_fmt(answer),
            distractors=[_fmt(answer+2), _fmt(answer-2), _fmt(visible[-1]+ratio)],
            explanation=f"Each term is multiplied by {_fmt(ratio)}; next = {_fmt(answer)}.",
            fast_method="Rapid growth or decay should trigger a ratio check.",
        ))

    mixed_cases = [
        (1,[(3,2)]*5,"×3 + 2"),
        (4,[(2,1)]*5,"×2 + 1"),
        (7,[(2,-3)]*5,"×2 − 3"),
        (2,[(2,1),(3,2),(4,3),(5,4),(6,5)],"×2+1, ×3+2, ×4+3, ..."),
        (3,[(2,-1),(3,-2),(4,-3),(5,-4),(6,-5)],"×2−1, ×3−2, ×4−3, ..."),
        (10,[(2,5)]*5,"×2 + 5"),
        (5,[(4,-1)]*5,"×4 − 1"),
        (2,[(3,1),(3,2),(3,3),(3,4),(3,5)],"×3 then +1,+2,+3,+4,+5"),
        (50,[(2,-10),(2,-20),(2,-30),(2,-40),(2,-50)],"×2 then −10,−20,−30,−40,−50"),
        (1,[(5,1)]*5,"×5 + 1"),
    ]
    for start, operations, description in mixed_cases:
        visible = [float(start)]
        for multiplier, offset in operations[:4]:
            visible.append(visible[-1]*multiplier+offset)
        multiplier, offset = operations[4]
        answer = visible[-1]*multiplier+offset
        bank.append(_make(
            len(bank), pattern="mixed-multiply-add", subtopic="Multiply then add/subtract",
            difficulty=3, seconds=50,
            question=f"{_series(visible)}, ?",
            answer=_fmt(answer),
            distractors=[_fmt(answer+offset or answer+1), _fmt(answer-multiplier), _fmt(visible[-1]*multiplier)],
            explanation=f"The rule is {description}; applying the next step gives {_fmt(answer)}.",
            fast_method="For near-constant ratios, test ×m ± a small constant.",
        ))

    power_cases = [
        ([1,4,9,16,25],36,"consecutive squares"),
        ([8,27,64,125,216],343,"consecutive cubes"),
        ([2,4,8,16,32],64,"powers of 2"),
        ([3,9,27,81,243],729,"powers of 3"),
        ([3,6,11,18,27],38,"n²+2"),
        ([7,15,31,63,127],255,"2ⁿ−1"),
        ([2,9,28,65,126],217,"n³+1"),
        ([0,3,8,15,24],35,"n²−1"),
        ([5,12,21,32,45],60,"n²+4"),
        ([4,10,20,34,52],74,"n²+n+2"),
    ]
    for visible, answer, description in power_cases:
        bank.append(_make(
            len(bank), pattern="square-cube-power", subtopic="Squares, cubes and powers",
            difficulty=2, seconds=40,
            question=f"{_series(visible)}, ?",
            answer=_fmt(answer),
            distractors=[_fmt(answer+2), _fmt(answer-2), _fmt(answer+8)],
            explanation=f"The series follows {description}; next = {_fmt(answer)}.",
            fast_method="Recognise squares, cubes and small offsets around powers.",
        ))

    special_cases = [
        ([2,3,5,7,11],13,"successive primes"),
        ([1,1,2,3,5],8,"Fibonacci"),
        ([1,3,6,10,15],21,"triangular numbers"),
        ([1,2,6,24,120],720,"factorials"),
        ([5,7,11,13,17],19,"successive primes from 5"),
        ([2,4,6,10,16],26,"sum of previous two"),
        ([3,6,12,24,48],96,"doubling"),
        ([2,6,12,20,30],42,"n(n+1)"),
        ([4,9,16,25,36],49,"consecutive squares from 2²"),
        ([6,10,15,21,28],36,"increments +4,+5,+6,+7,+8"),
    ]
    for visible, answer, description in special_cases:
        bank.append(_make(
            len(bank), pattern="special-number-sequence", subtopic="Prime / Fibonacci / triangular / factorial",
            difficulty=2, seconds=45,
            question=f"{_series(visible)}, ?",
            answer=_fmt(answer),
            distractors=[_fmt(answer+2), _fmt(answer-2), _fmt(answer+6)],
            explanation=f"The pattern is {description}; next = {_fmt(answer)}.",
            fast_method="Look for familiar special-number anchors before inventing a custom rule.",
        ))

    interleaved_cases = [
        ([3,6,9,12],[10,20,30,40]),
        ([2,4,8,16],[5,10,15,20]),
        ([1,4,9,16],[2,8,18,32]),
        ([7,12,17,22],[100,90,80,70]),
        ([3,5,8,12],[8,27,64,125]),
        ([20,18,16,14],[1,2,4,8]),
        ([5,10,20,40],[81,27,9,3]),
        ([2,5,10,17],[4,9,16,25]),
        ([11,22,33,44],[2,6,18,54]),
        ([100,80,60,40],[3,6,12,24]),
    ]
    for odd, even in interleaved_cases:
        visible: list[float] = []
        for idx in range(3):
            visible.extend([odd[idx], even[idx]])
        visible.append(odd[3])
        answer = even[3]
        bank.append(_make(
            len(bank), pattern="alternating-interleaved", subtopic="Alternating / interleaved series",
            difficulty=3, seconds=55,
            question=f"{_series(visible)}, ?",
            answer=_fmt(answer),
            distractors=[_fmt(answer+5), _fmt(answer-5), _fmt(answer+10)],
            explanation=f"Odd and even positions form separate clean series; the next even term is {_fmt(answer)}.",
            fast_method="Split odd and even positions whenever a single rule looks unnatural.",
        ))

    fraction_cases = [
        ([3,1.5,.75,.375,.1875],.09375,"divide by 2"),
        ([.5,1,1.5,2,2.5],3,"add 0.5"),
        ([8,4,2,1,.5],.25,"divide by 2"),
        ([.2,.6,1.8,5.4,16.2],48.6,"multiply by 3"),
        ([5,2.5,1.25,.625,.3125],.15625,"divide by 2"),
        ([1.2,2.4,4.8,9.6,19.2],38.4,"multiply by 2"),
        ([10,5,2.5,1.25,.625],.3125,"divide by 2"),
        ([.25,.75,1.25,1.75,2.25],2.75,"add 0.5"),
        ([6,-3,1.5,-.75,.375],-.1875,"multiply by -0.5"),
        ([1,1.25,1.5,1.75,2],2.25,"add 0.25"),
    ]
    for visible, answer, description in fraction_cases:
        bank.append(_make(
            len(bank), pattern="fraction-decimal-ratio", subtopic="Fraction / decimal series",
            difficulty=2, seconds=55,
            question=f"{_series(visible)}, ?",
            answer=_fmt(answer),
            distractors=[_fmt(answer+.25), _fmt(answer-.25), _fmt(answer*2)],
            explanation=f"The rule is {description}; next = {_fmt(answer)}.",
            fast_method="Use a consistent representation and check step or ratio.",
        ))

    cyclic_cases = [
        (20,[("+",5),("-",3),("+",7),("-",5),("+",9)],"+5, −3, +7, −5, +9"),
        (4,[("*",2),("+",3),("*",2),("+",3),("*",2)],"×2, +3 repeating"),
        (100,[("/",2),("-",5),("/",2),("-",5),("/",2)],"÷2, −5 repeating"),
        (3,[("+",4),("*",2),("+",4),("*",2),("+",4)],"+4, ×2 repeating"),
        (50,[("-",10),("/",2),("-",10),("/",2),("-",10)],"−10, ÷2 repeating"),
        (2,[("*",3),("-",1),("*",3),("-",1),("*",3)],"×3, −1 repeating"),
        (81,[("/",3),("+",6),("/",3),("+",6),("/",3)],"÷3, +6 repeating"),
        (10,[("+",1),("+",4),("+",1),("+",4),("+",1)],"+1, +4 repeating"),
        (5,[("*",2),("-",2),("*",2),("-",2),("*",2)],"×2, −2 repeating"),
        (30,[("-",5),("*",2),("-",5),("*",2),("-",5)],"−5, ×2 repeating"),
    ]
    for start, operations, description in cyclic_cases:
        visible = [float(start)]
        for operator, value in operations[:4]:
            current = visible[-1]
            visible.append(
                current+value if operator == "+"
                else current-value if operator == "-"
                else current*value if operator == "*"
                else current/value
            )
        operator, value = operations[4]
        current = visible[-1]
        answer = (
            current+value if operator == "+"
            else current-value if operator == "-"
            else current*value if operator == "*"
            else current/value
        )
        bank.append(_make(
            len(bank), pattern="alternating-operations", subtopic="Alternating / cyclic operations",
            difficulty=3, seconds=60,
            question=f"{_series(visible)}, ?",
            answer=_fmt(answer),
            distractors=[_fmt(answer+value), _fmt(answer-value), _fmt(current)],
            explanation=f"The operation cycle is {description}; next = {_fmt(answer)}.",
            fast_method="Label the gaps and look for a repeating operator cycle.",
        ))

    wrong_cases = [
        ([5,9,13,17,21,25],3,18,"+4"),
        ([2,6,18,54,162,486],4,160,"×3"),
        ([1,4,9,16,25,36],2,8,"consecutive squares"),
        ([3,6,11,18,27,38],4,28,"+3,+5,+7,+9,+11"),
        ([1,1,2,3,5,8],5,9,"Fibonacci"),
        ([100,50,25,12.5,6.25,3.125],3,13,"÷2"),
        ([7,12,17,22,27,32],1,13,"+5"),
        ([2,5,10,17,26,37],4,25,"n²+1"),
        ([4,11,25,53,109,221],2,24,"×2+3"),
        ([8,27,64,125,216,343],4,215,"consecutive cubes"),
    ]
    for correct, index, wrong, rule in wrong_cases:
        shown = list(correct)
        shown[index] = wrong
        answer = _fmt(wrong)
        neighbours = [
            _fmt(correct[index]),
            _fmt(shown[max(0,index-1)]),
            _fmt(shown[min(len(shown)-1,index+1)]),
        ]
        bank.append(_make(
            len(bank), pattern="wrong-number-detection", subtopic="Wrong-number detection",
            difficulty=3, seconds=65,
            question=f"Which number is wrong in the series: {_series(shown)}?",
            answer=answer,
            distractors=neighbours,
            explanation=f"The intended rule is {rule}. The expected value at that position is {_fmt(correct[index])}, so {answer} is wrong.",
            fast_method="Generate the expected clean series and locate the mismatch.",
        ))

    if len(bank) != 100:
        raise AssertionError(f"Expected 100 questions, got {len(bank)}")
    return bank
