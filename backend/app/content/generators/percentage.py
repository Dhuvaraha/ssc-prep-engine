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
    rounded = round(value, 2)
    return str(int(rounded)) if rounded.is_integer() else str(rounded)


def _pct(value: float) -> str:
    return f"{_fmt(value)}%"


def _question(
    index: int,
    pattern_type: str,
    subtopic: str,
    difficulty: int,
    expected_time_seconds: int,
    question_text: str,
    answer: str,
    distractors: list[str],
    explanation: str,
    fast_method: str,
) -> GeneratedQuestion:
    unique: list[str] = []
    seen = {answer}
    for distractor in distractors:
        if distractor not in seen:
            seen.add(distractor)
            unique.append(distractor)
        if len(unique) == 3:
            break
    if len(unique) != 3:
        raise ValueError(f"Need three unique distractors for {question_text}")

    raw = [answer, *unique]
    shift = index % 4
    options = tuple(raw[shift:] + raw[:shift])
    return GeneratedQuestion(
        pattern_type=pattern_type,
        subtopic=subtopic,
        difficulty=difficulty,
        expected_time_seconds=expected_time_seconds,
        question_text=question_text,
        options=options,  # type: ignore[arg-type]
        correct_option=options.index(answer) + 1,
        explanation=explanation,
        fast_method=fast_method,
    )


def build_percentage_bank() -> list[GeneratedQuestion]:
    bank: list[GeneratedQuestion] = []

    direct_cases = [
        (25, 360), (12.5, 640), (35, 480), (18, 750), (62.5, 320),
        (7.5, 840), (44, 1250), (16.6666667, 540), (2.5, 2400), (72, 625),
    ]
    for p, value in direct_cases:
        answer = round(p * value / 100, 2)
        shown = "16⅔" if abs(p - 16.6666667) < 0.01 else _fmt(p)
        bank.append(_question(
            len(bank), "percent-of-number", "Percent of a number",
            1 if len(bank) < 3 else 2, 30,
            f"What is {shown}% of {value}?", _fmt(answer),
            [_fmt(answer * 0.8), _fmt(answer * 1.2), _fmt(answer + 15), _fmt(answer / 2)],
            f"{shown}% means {shown}/100 of the quantity. The result is {_fmt(answer)}.",
            "Convert the percentage to a familiar fraction or multiplier first.",
        ))

    reverse_cases = [
        (20, 84, 420), (12.5, 75, 600), (35, 210, 600), (7.5, 54, 720),
        (62.5, 250, 400), (18, 99, 550), (45, 324, 720), (2.5, 45, 1800),
        (16.6666667, 120, 720), (72, 504, 700),
    ]
    for p, part, whole in reverse_cases:
        shown = "16⅔" if abs(p - 16.6666667) < 0.01 else _fmt(p)
        bank.append(_question(
            len(bank), "reverse-percentage", "Recover the whole", 2, 45,
            f"{shown}% of a number is {part}. What is the number?", _fmt(whole),
            [_fmt(whole * 0.8), _fmt(whole * 1.2), _fmt(whole + 100), _fmt(whole - 100)],
            f"({shown}/100) × N = {part}. Therefore N = {_fmt(whole)}.",
            "Scale the known percentage-part back to 100 units.",
        ))

    change_cases = [
        (80, 100, 25, "increase"), (250, 220, 12, "decrease"),
        (480, 600, 25, "increase"), (750, 630, 16, "decrease"),
        (1250, 1500, 20, "increase"), (960, 1080, 12.5, "increase"),
        (640, 560, 12.5, "decrease"), (400, 470, 17.5, "increase"),
        (1500, 1275, 15, "decrease"), (360, 441, 22.5, "increase"),
    ]
    for old, new, rate, direction in change_cases:
        answer = f"{_pct(rate)} {direction}"
        opposite = "decrease" if direction == "increase" else "increase"
        bank.append(_question(
            len(bank), "percentage-change", "Percentage increase/decrease", 2, 40,
            f"A value changes from {old} to {new}. What is the percentage {direction}?", answer,
            [f"{_pct(max(1, rate - 5))} {direction}", f"{_pct(rate + 5)} {direction}", f"{_pct(rate)} {opposite}"],
            f"Change = {abs(new-old)}. Divide by the original {old} and multiply by 100 to get {_pct(rate)} {direction}.",
            "Percentage change always uses the original value as the normal base.",
        ))

    successive_cases = [
        ((20, 25), 50, "increase"), ((25, -20), 0, "no change"),
        ((-20, -10), 28, "decrease"), ((10, 20), 32, "increase"),
        ((-25, 20), 10, "decrease"), ((30, -15), 10.5, "increase"),
        ((12.5, 20), 35, "increase"), ((-10, -10, -10), 27.1, "decrease"),
        ((5, 15), 20.75, "increase"), ((40, -25), 5, "increase"),
    ]
    for changes, rate, direction in successive_cases:
        parts = ", then ".join(
            f"{abs(change)}% {'increase' if change >= 0 else 'decrease'}"
            for change in changes
        )
        answer = "No change" if direction == "no change" else f"{_pct(rate)} {direction}"
        factor = 1.0
        for change in changes:
            factor *= 1 + change / 100
        distractors = (
            ["5% increase", "5% decrease", "10% increase"]
            if direction == "no change"
            else [f"{_pct(max(0.5, rate-5))} {direction}", f"{_pct(rate+5)} {direction}",
                  f"{_pct(rate)} {'decrease' if direction == 'increase' else 'increase'}"]
        )
        bank.append(_question(
            len(bank), "successive-change", "Successive percentage changes", 3, 55,
            f"A quantity undergoes a {parts}. What is the net percentage change?", answer,
            distractors,
            f"Multiply the change factors. Their product is {_fmt(factor)}, giving {answer.lower()}.",
            "Use multipliers; successive percentage changes do not normally add.",
        ))

    reversal_cases = [
        ("more", 25, 20, "less"), ("less", 20, 25, "more"),
        ("more", 50, 33.33, "less"), ("less", 40, 66.67, "more"),
        ("more", 10, 9.09, "less"), ("more", 20, 16.67, "less"),
        ("less", 60, 150, "more"), ("more", 12.5, 11.11, "less"),
        ("more", 33.33, 25, "less"), ("less", 25, 33.33, "more"),
    ]
    for relation, x, reverse_rate, reverse_word in reversal_cases:
        answer = f"{_pct(reverse_rate)} {reverse_word}"
        bank.append(_question(
            len(bank), "more-less-reversal", "More/less reverse comparison", 3, 50,
            f"A is {_pct(x)} {relation} than B. B is approximately what percent {reverse_word} than A?",
            answer,
            [f"{_pct(x)} {reverse_word}", f"{_pct(max(1, reverse_rate-7))} {reverse_word}",
             f"{_pct(reverse_rate+7)} {reverse_word}", f"{_pct(reverse_rate)} {'more' if reverse_word == 'less' else 'less'}"],
            "Use a base of 100 for the reference quantity, then recompute the reverse comparison using the new denominator.",
            "More→reverse less = x/(100+x); less→reverse more = x/(100-x).",
        ))

    expenditure_cases = [
        ("increases", 25, 0, 20, "decrease"), ("increases", 20, 0, 16.67, "decrease"),
        ("increases", 50, 0, 33.33, "decrease"), ("decreases", 20, 0, 25, "increase"),
        ("decreases", 25, 0, 33.33, "increase"), ("increases", 10, 0, 9.09, "decrease"),
        ("increases", 60, 0, 37.5, "decrease"), ("decreases", 10, 0, 11.11, "increase"),
        ("increases", 28, 22, 4.69, "decrease"), ("increases", 25, 10, 12, "decrease"),
    ]
    for price_direction, price_rate, allowed_expense, rate, quantity_direction in expenditure_cases:
        price_factor = 1 + price_rate/100 if price_direction == "increases" else 1 - price_rate/100
        expense_factor = 1 + allowed_expense/100
        if allowed_expense:
            text = (
                f"The price of a commodity {price_direction} by {_pct(price_rate)}. "
                f"If expenditure may increase by only {_pct(allowed_expense)}, by what percent "
                f"should consumption {quantity_direction}?"
            )
        else:
            text = (
                f"The price of a commodity {price_direction} by {_pct(price_rate)}. "
                "By what percent should consumption change so that expenditure remains the same?"
            )
        answer = f"{_pct(rate)} {quantity_direction}"
        bank.append(_question(
            len(bank), "constant-expenditure", "Price-consumption-expenditure", 3, 60,
            text, answer,
            [f"{_pct(max(1, rate-4))} {quantity_direction}", f"{_pct(rate+4)} {quantity_direction}",
             f"{_pct(rate)} {'increase' if quantity_direction == 'decrease' else 'decrease'}"],
            f"Consumption factor = expenditure factor ÷ price factor = {_fmt(expense_factor)} ÷ {_fmt(price_factor)}.",
            "Use expenditure = price × consumption.",
        ))

    savings_cases = [
        (8,5,20,30,3.33,"increase"), (5,4,20,10,60,"increase"),
        (7,5,10,20,15,"decrease"), (4,3,25,20,40,"increase"),
        (3,2,10,5,20,"increase"), (5,4,10,5,30,"increase"),
        (9,7,15,10,32.5,"increase"), (5,3,-10,-5,17.5,"decrease"),
        (6,5,25,20,50,"increase"), (10,7,12,20,6.67,"decrease"),
    ]
    for income, expense, income_change, expense_change, rate, direction in savings_cases:
        old_saving = income - expense
        new_income = income * (1 + income_change/100)
        new_expense = expense * (1 + expense_change/100)
        new_saving = new_income - new_expense
        answer = f"{_pct(rate)} {direction}"
        bank.append(_question(
            len(bank), "income-expenditure-savings", "Income, expenditure and savings", 3, 70,
            f"Income and expenditure are in the ratio {income}:{expense}. Income changes by "
            f"{income_change:+g}% and expenditure by {expense_change:+g}%. What is the percentage change in savings?",
            answer,
            [f"{_pct(max(1, rate-10))} {direction}", f"{_pct(rate+10)} {direction}",
             f"{_pct(rate)} {'decrease' if direction == 'increase' else 'increase'}"],
            f"Old saving={old_saving}. New income={_fmt(new_income)}, new expenditure={_fmt(new_expense)}, "
            f"new saving={_fmt(new_saving)}. Hence savings show {answer}.",
            "Use ratio units; savings = income − expenditure before and after.",
        ))

    marks_cases = [
        ("A student scores 62.5% of 800 marks. How many marks are scored?", "500", ["480","520","625"],
         "62.5%=5/8; 800×5/8=500.", "62.5%=5/8."),
        ("The pass mark is 40% of a 750-mark exam. What is the pass mark?", "300", ["280","320","375"],
         "40% of 750=300.", "40%=2/5."),
        ("A candidate scores 35% and fails by 30 marks. If the pass percentage is 40%, what are the total marks?", "600", ["500","650","750"],
         "The 5 percentage-point gap equals 30 marks, so total=600.", "Percentage-point gap × total = marks gap."),
        ("A candidate scores 54% and passes by 24 marks. If the pass percentage is 50%, what are the total marks?", "600", ["480","500","720"],
         "The 4 percentage-point excess equals 24 marks, so total=600.", "Use the percentage-point gap."),
        ("One candidate gets 48% and fails by 12 marks; another gets 55% and passes by 30 marks. What are the total marks?", "600", ["500","700","800"],
         "The score gap is 7% and marks gap is 42, so total=600.", "Combine fail/pass mark gaps."),
        ("If the pass percentage is 36% in a 500-mark exam, the pass mark is?", "180", ["160","190","200"],
         "36% of 500=180.", "36%=30%+6%."),
        ("A student scores 420 marks out of 600. What percentage is that?", "70%", ["65%","72%","75%"],
         "420/600×100=70%.", "Part/whole×100."),
        ("A candidate needs 45% to pass. She gets 198 marks and fails by 27. What are the total marks?", "500", ["450","550","600"],
         "Pass marks=225; 225 is 45% of 500.", "Recover pass marks first."),
        ("The pass mark is 42% of 800. What is it?", "336", ["320","344","360"],
         "42% of 800=336.", "42%=40%+2%."),
        ("A student scores 68% of 750. Marks scored?", "510", ["500","520","540"],
         "68% of 750=510.", "Use 70%−2%."),
    ]
    for text, answer, distractors, explanation, shortcut in marks_cases:
        bank.append(_question(
            len(bank), "marks-pass-percentage", "Marks and pass percentage", 2, 60,
            text, answer, distractors, explanation, shortcut,
        ))

    growth_cases = [
        ("A population of 10,000 grows by 10% each year for 2 years. Final population?", "12100", ["12000","11000","12200"], "10000×1.1²=12100."),
        ("A population is 13,230 after two consecutive annual increases of 5%. What was it two years ago?", "12000", ["11800","12500","12600"], "13230/1.05²=12000."),
        ("A machine worth ₹20,000 depreciates by 10% each year for 2 years. Value after 2 years?", "₹16200", ["₹16000","₹18000","₹16400"], "20000×0.9²=16200."),
        ("A quantity of 25,000 rises by 20% and then falls by 10%. Final value?", "27000", ["26500","27500","30000"], "25000×1.2×0.9=27000."),
        ("After a 30% increase followed by a 15% decrease, a population is 11,050. Original population?", "10000", ["9500","10500","11000"], "Original×1.30×0.85=11050."),
        ("An army is reduced by 10% in each of 3 successive stages. If it starts at 1,000,000, final strength?", "729000", ["700000","730000","810000"], "1000000×0.9³=729000."),
        ("A town of 8,000 grows by 5% annually for 3 years. Population after 3 years?", "9261", ["9200","9400","8820"], "8000×1.05³=9261."),
        ("A value falls by 20% and then rises by 25%. If it started at 15,000, final value?", "15000", ["14400","15600","18000"], "15000×0.8×1.25=15000."),
        ("A population of 16,000 rises by 12.5% and then 20%. Final population?", "21600", ["20800","22000","22400"], "16000×1.125×1.2=21600."),
        ("Production is 5,000 units, then changes by +10%, +10%, and -20%. Final production?", "4840", ["4800","4900","5000"], "5000×1.1×1.1×0.8=4840."),
    ]
    for text, answer, distractors, explanation in growth_cases:
        bank.append(_question(
            len(bank), "population-growth-decay", "Population/growth/depreciation", 3, 55,
            text, answer, distractors, explanation, "Use repeated percentage multipliers.",
        ))

    product_cases = [
        ("A rectangle's length increases by 20% and breadth by 25%. Percentage change in area?", "50% increase", ["45% increase","50% decrease","55% increase"], "1.2×1.25=1.5."),
        ("A cuboid's length increases by 10%, breadth by 20%, and height decreases by 25%. Percentage change in volume?", "1% decrease", ["1% increase","5% decrease","10% decrease"], "1.1×1.2×0.75=0.99."),
        ("The side of a square increases by 10%. Percentage increase in area?", "21% increase", ["10% increase","20% increase","22% increase"], "1.1²=1.21."),
        ("The radius of a circle decreases by 20%. Percentage decrease in area?", "36% decrease", ["20% decrease","40% decrease","44% decrease"], "0.8²=0.64."),
        ("A cylinder's radius increases by 10% and height by 20%. Percentage increase in volume?", "45.2% increase", ["32% increase","42% increase","44% increase"], "1.1²×1.2=1.452."),
        ("Price rises by 15% while quantity bought falls by 10%. Percentage change in expenditure?", "3.5% increase", ["5% increase","3.5% decrease","1.5% increase"], "1.15×0.90=1.035."),
        ("A machine's hourly output rises by 25% but operating time falls by 20%. Percentage change in total output?", "No change", ["5% increase","5% decrease","10% increase"], "1.25×0.8=1."),
        ("A rectangle's length decreases by 10% and breadth increases by 20%. Percentage change in area?", "8% increase", ["10% increase","8% decrease","2% increase"], "0.9×1.2=1.08."),
        ("The edge of a cube increases by 20%. Percentage increase in volume?", "72.8% increase", ["60% increase","44% increase","80% increase"], "1.2³=1.728."),
        ("A rectangle's length increases by 25% and breadth decreases by 20%. Percentage change in area?", "No change", ["5% increase","5% decrease","10% decrease"], "1.25×0.8=1."),
    ]
    for text, answer, distractors, explanation in product_cases:
        bank.append(_question(
            len(bank), "product-change", "Percentage change in a product", 3, 65,
            text, answer, distractors, explanation, "Multiply all changing factors.",
        ))

    if len(bank) != 100:
        raise AssertionError(f"Expected 100 percentage questions, got {len(bank)}")
    return bank
