import pytest

from nob.utils.join import join


@pytest.mark.parametrize(
    "sequence, kwargs, expected",
    [
        # Empty sequences
        ([], {}, "nothing."),
        ([], {"final_dot": False}, "nothing"),
        ([], {"nothing_when_empty": False}, "."),
        ([], {"nothing_when_empty": False, "final_dot": False}, ""),
        # Single element
        (["John"], {}, "John."),
        (["John"], {"final_dot": False}, "John"),
        ([123], {}, "123."),
        # Two elements
        (["Eric", "Norbert"], {}, "Eric and Norbert."),
        (["Eric", "Norbert"], {"final_and": False}, "Eric, Norbert."),
        (["Eric", "Norbert"], {"blob": " - "}, "Eric and Norbert."),
        (["Eric", "Norbert"], {"blob": " - ", "final_and": False}, "Eric - Norbert."),
        (["Eric", "Norbert"], {"final_and": False, "final_dot": False}, "Eric, Norbert"),
        # Three or more elements
        (["John", "Eric", "Norbert"], {}, "John, Eric and Norbert."),
        (["John", "Eric", "Norbert"], {"blob": ""}, "JohnEric and Norbert."),
        (["John", "Eric", "Norbert"], {"blob": "", "final_and": False}, "JohnEricNorbert."),
        (
            ["John", "Eric", "Norbert"],
            {"blob": "", "final_and": False, "final_dot": False},
            "JohnEricNorbert",
        ),
        (["A", "B", "C", "D"], {"blob": " | "}, "A | B | C and D."),
        (["A", "B", "C", "D"], {"blob": " | ", "final_and": False}, "A | B | C | D."),
        (["A", "B", "C", "D"], {"blob": " | ", "final_and": False, "final_dot": False}, "A | B | C | D"),
        # Testing non-string object conversion
        ([1, 2, 3], {}, "1, 2 and 3."),
    ],
)
def test_join_cases(sequence, kwargs, expected):
    """Test all explicitly provided parameterized cases for utility join."""
    assert join(sequence, **kwargs) == expected


@pytest.mark.parametrize(
    "sequence",
    [
        [],
        ["single"],
        ["pair", "values"],
        ["multiple", "values", "to", "process"],
        [str(i) for i in range(15)],
    ],
)
@pytest.mark.parametrize("blob", [", ", ",", " - ", "-", "_", ":", ".", "!", "a", "abc", "123", ""])
def test_join_like_string_join(sequence: list[str], blob: str):
    """Verify that using join with features turned off perfectly mirrors standard str.join."""
    assert join(sequence, blob=blob, final_and=False, final_dot=False, nothing_when_empty=False) == blob.join(
        sequence
    )
