import pytest

from app.content.syllogism import evaluate


def test_two_existential_groups_cannot_be_joined():
    result = evaluate([("some", "cartons", "papers"), ("some", "cartons", "utensils")],
                      ("some", "papers", "utensils"))
    assert result["consistent"] and result["possible"]
    assert not result["must_follow"]
    assert result["counterexample"] is not None


@pytest.mark.parametrize("premises,conclusion,follows", [
    ([("all", "A", "B"), ("all", "B", "C")], ("all", "A", "C"), True),
    ([("all", "A", "B")], ("all", "B", "A"), False),
    ([("some", "A", "B"), ("all", "B", "C")], ("some", "A", "C"), True),
    ([("some", "A", "B")], ("some", "B", "A"), True),
    ([("no", "A", "B")], ("no", "B", "A"), True),
    ([("some_not", "A", "B")], ("some_not", "B", "A"), False),
    ([("all", "A", "B"), ("no", "B", "C")], ("no", "A", "C"), True),
])
def test_categorical_rules(premises, conclusion, follows):
    assert evaluate(premises, conclusion)["must_follow"] is follows


def test_existence_is_explicit_and_inconsistent_premises_do_not_pass():
    assert not evaluate([("all", "A", "B")], ("some", "B", "A"))["must_follow"]
    assert evaluate([("all", "A", "B")], ("some", "B", "A"), nonempty=("A",))["must_follow"]
    result = evaluate([("no", "A", "B"), ("some", "A", "B")], ("all", "A", "B"))
    assert not result["consistent"] and not result["must_follow"]


def test_iterators_preserve_premises_and_existence_assumptions():
    assert evaluate(iter([("all", "A", "B"), ("all", "B", "C")]),
                    ("some", "A", "C"), nonempty=iter(["A"]))["must_follow"]
