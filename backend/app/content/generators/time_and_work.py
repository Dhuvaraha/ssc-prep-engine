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


def _gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return abs(a) or 1


def _fraction(num: int, den: int) -> str:
    divisor = _gcd(num, den)
    num //= divisor
    den //= divisor
    return str(num) if den == 1 else f"{num}/{den}"


def _alternate_time(a_days: int, b_days: int, starts: str) -> float:
    remaining = 1.0
    elapsed = 0
    while remaining > 1e-12:
        worker = starts if elapsed % 2 == 0 else ("B" if starts == "A" else "A")
        rate = 1 / (a_days if worker == "A" else b_days)
        if remaining <= rate + 1e-12:
            return round(elapsed + remaining / rate, 2)
        remaining -= rate
        elapsed += 1
    return float(elapsed)


def build_time_and_work_bank() -> list[GeneratedQuestion]:
    bank: list[GeneratedQuestion] = []

    direct = [(10,15),(12,18),(8,24),(20,30),(6,12),(16,48),(15,25),(14,21),(9,18),(24,40)]
    for a, b in direct:
        answer = round(a*b/(a+b), 2)
        bank.append(_make(
            len(bank), pattern="direct-combined-work", subtopic="Direct combined work",
            difficulty=1 if len(bank) < 3 else 2, seconds=45,
            question=f"A can finish a job in {a} days and B in {b} days. In how many days can they finish it together?",
            answer=f"{_fmt(answer)} days",
            distractors=[f"{_fmt(answer+2)} days", f"{_fmt(max(1,answer-2))} days", f"{_fmt((a+b)/2)} days", f"{_fmt(answer+5)} days"],
            explanation=f"Add the rates 1/{a} and 1/{b}; invert the result to get {_fmt(answer)} days.",
            fast_method="For two workers, together time = xy/(x+y).",
        ))

    fraction_pool = ["1/36","1/30","1/24","1/18","1/15","1/12","1/10","1/9","1/8","1/6","1/5","1/4","1/3","2/5","1/2","3/5","2/3","3/4"]
    remaining_cases = [(9,12,5),(10,15,3),(12,18,4),(8,24,4),(20,30,5),(15,25,6),(14,21,4),(16,48,6),(18,24,5),(24,40,8)]
    for a, b, days in remaining_cases:
        den = a*b
        done_num = days*(a+b)
        divisor = _gcd(done_num, den)
        done_num //= divisor
        done_den = den//divisor
        answer = _fraction(done_den-done_num, done_den)
        done = _fraction(done_num, done_den)
        bank.append(_make(
            len(bank), pattern="remaining-work", subtopic="Remaining work", difficulty=2, seconds=50,
            question=f"A can do a work in {a} days and B in {b} days. They work together for {days} days. What fraction remains?",
            answer=answer, distractors=[done, *fraction_pool],
            explanation=f"They complete {done}; remaining work = 1 - {done} = {answer}.",
            fast_method="Combined rate × elapsed time gives work completed.",
        ))

    find_one = [(6,10),(8,12),(15,20),(10,15),(12,18),(4,12),(9,18),(5,20),(7.5,15),(18,30)]
    for together, b in find_one:
        a = round(1/(1/together-1/b), 2)
        bank.append(_make(
            len(bank), pattern="find-individual-rate", subtopic="Find individual worker", difficulty=2, seconds=55,
            question=f"A and B together finish in {_fmt(together)} days. B alone takes {b} days. How long does A alone take?",
            answer=f"{_fmt(a)} days",
            distractors=[f"{_fmt(a+5)} days", f"{_fmt(max(1,a-5))} days", f"{_fmt(b-together)} days", f"{_fmt(a+10)} days"],
            explanation=f"A's rate = 1/{_fmt(together)} - 1/{b}; inverting gives {_fmt(a)} days.",
            fast_method="Subtract rates, not times.",
        ))

    ratios = [(3,2,18),(5,4,20),(4,3,24),(2,1,14),(7,5,21),(3,1,30),(5,2,25),(4,1,16),(6,5,18),(9,6,27)]
    for ea, eb, a_time in ratios:
        b_time = round(a_time*ea/eb, 2)
        bank.append(_make(
            len(bank), pattern="efficiency-time-ratio", subtopic="Efficiency vs time", difficulty=2, seconds=45,
            question=f"Efficiency A:B is {ea}:{eb}. If A takes {a_time} days, how many days does B take?",
            answer=f"{_fmt(b_time)} days",
            distractors=[f"{_fmt(a_time*eb/ea)} days", f"{_fmt(b_time+3)} days", f"{_fmt(max(1,b_time-3))} days", f"{_fmt(b_time+6)} days"],
            explanation=f"Time is inverse to efficiency, so B takes {_fmt(b_time)} days.",
            fast_method="Efficiency m:n means time n:m.",
        ))

    mixed = [(8,45,8,18,5,8),(6,30,10,24,4,5),(12,20,8,30,6,4),(10,24,6,20,5,3),(9,40,12,30,6,6),(5,36,8,24,4,4),(16,15,10,24,8,5),(7,42,14,21,7,7),(6,48,12,24,3,6),(15,18,9,30,10,3)]
    for men, md, women, wd, target_men, target_women in mixed:
        man_rate = 1/(men*md)
        woman_rate = 1/(women*wd)
        answer = round(1/(target_men*man_rate + target_women*woman_rate), 2)
        bank.append(_make(
            len(bank), pattern="mixed-workforce", subtopic="Men/Women workforce", difficulty=3, seconds=75,
            question=f"{men} men finish in {md} days and {women} women in {wd} days. How long will {target_men} men and {target_women} women take?",
            answer=f"{_fmt(answer)} days",
            distractors=[f"{_fmt(answer+2)} days", f"{_fmt(max(1,answer-2))} days", f"{_fmt(answer+5)} days", f"{_fmt(answer+8)} days"],
            explanation="Find one man's and one woman's rate separately, then add the target group's rates.",
            fast_method="Derive per-person efficiency before mixing worker types.",
        ))

    worker_days = [(7,12,2,8),(8,15,1,10),(12,20,1.5,18),(15,16,2,12),(9,24,1,18),(20,18,0.5,12),(14,21,2,14),(25,12,1,15),(18,20,1.5,15),(10,30,2,20)]
    for workers, days, work_factor, new_days in worker_days:
        answer = round(workers*days*work_factor/new_days, 2)
        work_text = "the same work" if work_factor == 1 else f"{_fmt(work_factor)} times the work"
        bank.append(_make(
            len(bank), pattern="worker-days", subtopic="Worker-days proportion", difficulty=2, seconds=55,
            question=f"{workers} equal workers finish a job in {days} days. How many workers are needed for {work_text} in {new_days} days?",
            answer=f"{_fmt(answer)} workers",
            distractors=[f"{_fmt(max(1,answer-2))} workers", f"{_fmt(answer+2)} workers", f"{workers} workers", f"{_fmt(answer+5)} workers"],
            explanation=f"Workers × days is proportional to work, giving {_fmt(answer)} workers.",
            fast_method="Use M1D1/W1 = M2D2/W2.",
        ))

    alternates = [(12,18,"A"),(10,15,"B"),(8,12,"A"),(20,30,"B"),(16,24,"A"),(9,18,"B"),(14,21,"A"),(6,12,"B"),(15,25,"A"),(24,40,"B")]
    for a, b, starts in alternates:
        answer = _alternate_time(a,b,starts)
        joint = round(a*b/(a+b), 2)
        bank.append(_make(
            len(bank), pattern="alternate-days", subtopic="Alternate-day work", difficulty=3, seconds=70,
            question=f"A takes {a} days and B {b} days. They work on alternate days starting with {starts}. When is the work completed?",
            answer=f"{_fmt(answer)} days",
            distractors=[f"{_fmt(answer+1)} days", f"{_fmt(max(1,answer-1))} days", f"{_fmt(joint)} days", f"{_fmt(answer+2)} days"],
            explanation=f"Count full 2-day cycles, then the final partial day. Total = {_fmt(answer)} days.",
            fast_method="Cycle first; final partial day second.",
        ))

    stages = [(10,15,4),(12,18,3),(8,24,2),(20,30,5),(15,25,6),(14,21,4),(16,48,6),(18,24,5),(24,40,8),(9,12,3)]
    for a, b, solo_days in stages:
        remaining = 1-solo_days/a
        extra = round(remaining/(1/a+1/b), 2)
        total = round(solo_days+extra, 2)
        bank.append(_make(
            len(bank), pattern="staged-join-leave", subtopic="Join/leave staged work", difficulty=3, seconds=70,
            question=f"A takes {a} days and B {b} days. A works alone for {solo_days} days, then B joins. Total time?",
            answer=f"{_fmt(total)} days",
            distractors=[f"{_fmt(extra)} days", f"{_fmt(total+2)} days", f"{_fmt(max(1,total-2))} days", f"{_fmt(a*b/(a+b))} days"],
            explanation=f"Finish stage 1 first, then use the joint rate on the remainder. Total = {_fmt(total)} days.",
            fast_method="Split the timeline into stages.",
        ))

    wages = [(3,2,10,10,5000),(5,3,8,8,6400),(4,3,12,8,7600),(2,1,15,10,4000),(7,5,6,9,8400),(3,1,20,15,7200),(5,2,9,12,6800),(4,1,10,16,5000),(6,5,7,7,7700),(9,6,5,8,9000)]
    for ea, eb, da, db, total in wages:
        ca, cb = ea*da, eb*db
        share = round(total*ca/(ca+cb), 2)
        bank.append(_make(
            len(bank), pattern="work-and-wages", subtopic="Work and wages", difficulty=3, seconds=55,
            question=f"Efficiency A:B is {ea}:{eb}. A works {da} days and B {db} days. From ₹{total}, what is A's share?",
            answer=f"₹{_fmt(share)}",
            distractors=[f"₹{_fmt(total-share)}", f"₹{_fmt(share+500)}", f"₹{_fmt(max(0,share-500))}", f"₹{_fmt(total/2)}"],
            explanation=f"Contribution ratio = {ca}:{cb}; A receives ₹{_fmt(share)}.",
            fast_method="Wages follow efficiency × time.",
        ))

    partial = [(20,4,25,5),(25,5,20,4),(40,8,30,6),(15,3,25,5),(12.5,2,20,4),(30,6,20,5),(50,10,25,5),(10,2,15,3),(35,7,40,8),(18,3,24,4)]
    for pa, da, pb, db in partial:
        rate = (pa/100)/da + (pb/100)/db
        answer = round(1/rate, 2)
        bank.append(_make(
            len(bank), pattern="fractional-work-rate", subtopic="Fraction/percentage work rate", difficulty=3, seconds=65,
            question=f"A completes {_fmt(pa)}% in {da} days and B {_fmt(pb)}% in {db} days. Working together, how many days for the whole job?",
            answer=f"{_fmt(answer)} days",
            distractors=[f"{_fmt(answer+2)} days", f"{_fmt(max(1,answer-2))} days", f"{_fmt(answer+5)} days", f"{_fmt(answer+8)} days"],
            explanation=f"Convert both statements into daily rates and add them. Time = {_fmt(answer)} days.",
            fast_method="Partial percentage ÷ days = daily percentage rate.",
        ))

    if len(bank) != 100:
        raise AssertionError(f"Expected 100 questions, got {len(bank)}")
    return bank
