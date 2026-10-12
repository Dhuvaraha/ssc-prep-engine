from fractions import Fraction as F
import json
from pathlib import Path

from app.content.syllogism import evaluate


def test_original_pilot_arithmetic_and_constraint_checks():
    items = json.loads((Path(__file__).parents[1]/'data/original_reasoning_depth_pilot.json').read_text())["items"]
    assert len({item["id"] for item in items}) == len(items)
    assert all(len(set(item["options"])) == 4 and len(item["wrong_options"]) == 3 for item in items)
    loss = (1-F(140,100)*F(90,100)*F(80,100)*F(95,100))*100
    assert loss == F(424,100)
    switch_time = (1-F(1,6)-24*(F(1,30)-F(1,90)))/F(1,45)
    assert switch_time == F(27,2) and 0 < switch_time < 24
    speed = 72/(F(24,18)+F(24,24)+F(24,36)+F(10,60))
    assert round(float(speed),2) == 22.74
    assert 1**3+3**3+5**3-3*1*3*5 == 9*(9**2-3*23) == 108
    assert (25**2-(12-5)**2) - (25**2-(12+5)**2) == 240
    premises = [("some", "archivists", "cyclists"), ("no", "cyclists", "readers")]
    conclusions = [("some_not", "archivists", "readers"), ("no", "archivists", "readers"),
                   ("some", "cyclists", "archivists")]
    assert [evaluate(premises, c)["must_follow"] for c in conclusions] == [True, False, True]
    encoded = ''.join(chr((ord(c)-65+shift)%26+65) for c,shift in zip('RISK'[::-1],[1,2,1,2]))
    assert encoded == "LUJT"
    assert ((F(45+42,2)/F(36+54+30,3))-1)*100 == F(875,100)
    assert [item["correct_option"] for item in items] == [1,2,3,2,3,3,2,1]


def test_reference_feasibility_rule_rejects_impossible_real_sums():
    # A key-looking numeric answer must not override a contradictory stem.
    total, square_sum = 18, 36
    assert 3*square_sum < total*total
