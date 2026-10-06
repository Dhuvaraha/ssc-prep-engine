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
    return str(int(rounded)) if float(rounded).is_integer() else str(rounded)


def _money(value: float) -> str:
    return f"₹{_fmt(value)}"


def _pct(value: float) -> str:
    return f"{_fmt(value)}%"


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


def build_profit_loss_discount_bank() -> list[GeneratedQuestion]:
    bank: list[GeneratedQuestion] = []

    direct = [
        (800,920),(1250,1100),(600,690),(1500,1350),(2400,2760),
        (3200,2880),(1750,2100),(960,840),(4500,5400),(2250,2025),
    ]
    for cp, sp in direct:
        rate = round(abs(sp-cp)/cp*100, 2)
        kind = "profit" if sp > cp else "loss"
        opposite = "loss" if kind == "profit" else "profit"
        answer = f"{_pct(rate)} {kind}"
        bank.append(_make(
            len(bank), pattern="direct-profit-loss", subtopic="Direct profit/loss",
            difficulty=1 if len(bank) < 4 else 2, seconds=35,
            question=f"An article costs {_money(cp)} and is sold for {_money(sp)}. Find the profit or loss percentage.",
            answer=answer,
            distractors=[f"{_pct(rate+5)} {kind}", f"{_pct(max(1,rate-5))} {kind}", f"{_pct(rate)} {opposite}"],
            explanation=f"Difference = {_money(abs(sp-cp))}; divide by CP {_money(cp)} and multiply by 100.",
            fast_method="Profit/loss percentage is always based on cost price.",
        ))

    recover = [
        ("cp",1200,20,"profit"),("cp",1700,15,"loss"),("sp",1600,25,"profit"),("sp",2500,12,"loss"),("cp",2160,20,"profit"),
        ("sp",3600,12.5,"profit"),("cp",1840,8,"loss"),("sp",4800,15,"profit"),("cp",2700,10,"loss"),("sp",2250,20,"loss"),
    ]
    for mode, value, rate, kind in recover:
        factor = 1 + rate/100 if kind == "profit" else 1 - rate/100
        if mode == "cp":
            answer_value = round(value/factor, 2)
            question = f"An article is sold for {_money(value)} at a {_pct(rate)} {kind}. Find its cost price."
            explanation = f"CP = SP ÷ {_fmt(factor)} = {_money(answer_value)}."
        else:
            answer_value = round(value*factor, 2)
            question = f"An article costs {_money(value)} and is sold at a {_pct(rate)} {kind}. Find the selling price."
            explanation = f"SP = CP × {_fmt(factor)} = {_money(answer_value)}."
        bank.append(_make(
            len(bank), pattern="recover-cp-sp", subtopic="Recover CP or SP", difficulty=2, seconds=45,
            question=question, answer=_money(answer_value),
            distractors=[_money(answer_value+100), _money(max(1,answer_value-100)), _money(answer_value*1.1)],
            explanation=explanation,
            fast_method="Use SP = CP × (1 ± rate/100).",
        ))

    marked = [
        ("sp",1500,20),("sp",2400,15),("mp",1360,20),("mp",1700,15),("sp",3200,12.5),
        ("mp",2360,20),("sp",1800,30),("mp",2250,25),("sp",4250,18),("mp",3280,20),
    ]
    for mode, value, discount in marked:
        if mode == "sp":
            result = round(value*(1-discount/100), 2)
            question = f"Marked price is {_money(value)} and discount is {_pct(discount)}. Find selling price."
            explanation = f"SP = MP × {_fmt(1-discount/100)} = {_money(result)}."
        else:
            result = round(value/(1-discount/100), 2)
            question = f"An article sells for {_money(value)} after a {_pct(discount)} discount. Find marked price."
            explanation = f"MP = SP ÷ {_fmt(1-discount/100)} = {_money(result)}."
        bank.append(_make(
            len(bank), pattern="marked-price-discount", subtopic="Marked price and discount", difficulty=2, seconds=45,
            question=question, answer=_money(result),
            distractors=[_money(result+100), _money(max(1,result-100)), _money(result*1.1)],
            explanation=explanation,
            fast_method="Discount is calculated on marked price.",
        ))

    successive = [
        (2000,20,10),(1500,15,20),(3200,10,15),(2500,30,10),(1800,15,8),
        (2200,25,12),(3600,20,15),(2800,10,20),(4200,18,10),(1600,12,12),
    ]
    for mp, d1, d2 in successive:
        sp = round(mp*(1-d1/100)*(1-d2/100), 2)
        bank.append(_make(
            len(bank), pattern="successive-discounts", subtopic="Successive discounts", difficulty=3, seconds=55,
            question=f"An article marked {_money(mp)} gets successive discounts of {_pct(d1)} and {_pct(d2)}. Find final selling price.",
            answer=_money(sp),
            distractors=[_money(sp+100), _money(max(1,sp-100)), _money(mp*(1-(d1+d2)/100))],
            explanation=f"SP = MP × {_fmt(1-d1/100)} × {_fmt(1-d2/100)} = {_money(sp)}.",
            fast_method="Multiply discount factors; do not add discounts.",
        ))

    markup = [(20,10),(30,10),(40,20),(25,20),(50,30),(60,25),(35,15),(20,20),(45,25),(30,20)]
    for m, d in markup:
        factor = (1+m/100)*(1-d/100)
        rate = round(abs(factor-1)*100, 2)
        if rate == 0:
            answer = "No profit, no loss"
            distractors = ["5% profit","5% loss","10% profit"]
        else:
            kind = "profit" if factor > 1 else "loss"
            opposite = "loss" if kind == "profit" else "profit"
            answer = f"{_pct(rate)} {kind}"
            distractors = [f"{_pct(rate+5)} {kind}", f"{_pct(max(1,rate-5))} {kind}", f"{_pct(rate)} {opposite}"]
        bank.append(_make(
            len(bank), pattern="markup-discount-profit", subtopic="Markup, discount and profit", difficulty=3, seconds=60,
            question=f"An article is marked {_pct(m)} above CP and sold after a {_pct(d)} discount. Find final profit/loss percentage.",
            answer=answer, distractors=distractors,
            explanation=f"Let CP=100. MP={100+m}; SP={_fmt((100+m)*(1-d/100))}. Compare SP with 100.",
            fast_method="SP/CP = (1+markup)(1−discount).",
        ))

    targets = [(360,25,10),(1680,25,16),(800,20,20),(1250,15,8),(2400,25,20),(1500,12,10),(3200,18,25),(900,30,10),(2750,20,12),(1800,25,25)]
    for cp, profit, discount in targets:
        sp = cp*(1+profit/100)
        mp = round(sp/(1-discount/100), 2)
        bank.append(_make(
            len(bank), pattern="target-marked-price", subtopic="Required marked price", difficulty=3, seconds=60,
            question=f"CP is {_money(cp)}. To earn {_pct(profit)} profit after {_pct(discount)} discount, what should MP be?",
            answer=_money(mp),
            distractors=[_money(mp+100), _money(max(1,mp-100)), _money(sp)],
            explanation=f"Target SP={_money(sp)}; divide by {_fmt(1-discount/100)} to get MP={_money(mp)}.",
            fast_method="MP = CP × profit factor ÷ discount-retention factor.",
        ))

    false_weights = [(900,1.0),(800,1.0),(750,1.0),(875,1.0),(900,.95),(800,.96),(900,1.10),(850,1.05),(960,1.0),(750,.90)]
    for grams, receive_factor in false_weights:
        factor = 1000*receive_factor/grams
        rate = round(abs(factor-1)*100, 2)
        kind = "profit" if factor >= 1 else "loss"
        answer = f"{_pct(rate)} {kind}"
        bank.append(_make(
            len(bank), pattern="false-weight", subtopic="Dishonest dealer / false weight", difficulty=3, seconds=70,
            question=f"A dealer receives {_fmt(receive_factor*100)}% of the normal 1-kg price but delivers only {grams} g. Find profit/loss percentage.",
            answer=answer,
            distractors=[f"{_pct(rate+5)} {kind}", f"{_pct(max(1,rate-5))} {kind}", f"{_pct(rate)} {'loss' if kind == 'profit' else 'profit'}"],
            explanation="Compare money received for the claimed kilogram with the true cost of the grams actually delivered.",
            fast_method="Use actual quantity delivered as the cost base.",
        ))

    extra = [
        (1500,(20,10),20,20),(3000,(15,15),250,20),(2000,(10,5),100,25),(2400,(25,10),150,15),(1800,(20,5),80,20),
        (3200,(12.5,10),200,18),(2500,(15,10),120,25),(4000,(20,20),300,15),(1600,(10,10),50,20),(5000,(25,5),400,12),
    ]
    for listed, discounts, extra_cost, profit in extra:
        purchase = listed
        for discount in discounts:
            purchase *= 1-discount/100
        effective_cp = round(purchase+extra_cost, 2)
        sp = round(effective_cp*(1+profit/100), 2)
        bank.append(_make(
            len(bank), pattern="extra-costs", subtopic="Extra cost and final profit", difficulty=3, seconds=65,
            question=f"Listed price {_money(listed)}, purchase discounts {_pct(discounts[0])} and {_pct(discounts[1])}, extra cost {_money(extra_cost)}, target profit {_pct(profit)}. Find SP.",
            answer=_money(sp),
            distractors=[_money(sp+100), _money(max(1,sp-100)), _money(purchase*(1+profit/100))],
            explanation=f"Discounted purchase={_money(purchase)}; effective CP={_money(effective_cp)}; SP={_money(sp)}.",
            fast_method="Add seller-borne expenses before applying profit.",
        ))

    equal_sp = [(1000,20,20),(1200,25,25),(1500,10,10),(2000,15,15),(2400,30,30),(1800,20,10),(2500,25,15),(3000,10,20),(1600,12.5,20),(2200,30,10)]
    for sp, gain, loss in equal_sp:
        cp1 = sp/(1+gain/100)
        cp2 = sp/(1-loss/100)
        total_cp = cp1+cp2
        total_sp = 2*sp
        rate = round(abs(total_sp-total_cp)/total_cp*100, 2)
        kind = "profit" if total_sp >= total_cp else "loss"
        answer = f"{_pct(rate)} {kind}"
        bank.append(_make(
            len(bank), pattern="equal-sp-overall", subtopic="Equal SP / overall result", difficulty=3, seconds=70,
            question=f"Two articles sell for {_money(sp)} each; first at {_pct(gain)} gain, second at {_pct(loss)} loss. Find overall result.",
            answer=answer,
            distractors=[f"{_pct(rate+2)} {kind}", f"{_pct(max(.5,rate-2))} {kind}", f"{_pct(rate)} {'loss' if kind == 'profit' else 'profit'}"],
            explanation="Recover both cost prices from the common selling price, add them, then compare with total SP.",
            fast_method="Equal x% gain/loss at equal SP gives x²/100% loss only when the two percentages are equal.",
        ))

    changes = [(20,20,30),(30,10,20),(25,20,10),(40,20,25),(50,30,20),(20,10,5),(35,15,25),(60,25,20),(45,25,15),(30,20,5)]
    for markup_rate, old_discount, new_discount in changes:
        new_factor = (1+markup_rate/100)*(1-new_discount/100)
        rate = round(abs(new_factor-1)*100, 2)
        if rate == 0:
            answer = "No profit, no loss"
            distractors = ["5% profit","5% loss","10% profit"]
        else:
            kind = "profit" if new_factor > 1 else "loss"
            answer = f"{_pct(rate)} {kind}"
            distractors = [f"{_pct(rate+5)} {kind}", f"{_pct(max(1,rate-5))} {kind}", f"{_pct(rate)} {'loss' if kind == 'profit' else 'profit'}"]
        bank.append(_make(
            len(bank), pattern="change-in-selling-price", subtopic="Change in sale price/profit", difficulty=3, seconds=65,
            question=f"An article is marked {_pct(markup_rate)} above CP. If discount changes from {_pct(old_discount)} to {_pct(new_discount)}, find the new profit/loss percentage.",
            answer=answer, distractors=distractors,
            explanation=f"Let CP=100. MP={100+markup_rate}; new SP={_fmt((100+markup_rate)*(1-new_discount/100))}.",
            fast_method="Change only the requested stage in the CP→MP→SP chain.",
        ))

    if len(bank) != 100:
        raise AssertionError(f"Expected 100 questions, got {len(bank)}")
    return bank
