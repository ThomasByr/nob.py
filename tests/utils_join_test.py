from random import choices, randint
from string import ascii_letters

from pytest import fixture

from nob.utils.join import join


@fixture()
def iterable():
    m, n = 3, 4  # because I don't want to hardcode a list of random shit
    return ["".join(choices(ascii_letters, k=randint(m, n))) for _ in range(randint(m, n))]


def test_join_edge_cases():
    assert join([]) == "nothing."
    assert join(["John"]) == "John."
    assert join(["John"], final_dot=False) == "John"
    assert join(["Eric", "Norbert"]) == "Eric and Norbert."
    assert join(["Eric", "Norbert"], final_and=False) == "Eric, Norbert."


def test_join_like_join(iterable: list[str]):
    blobs = (", ", ",", " - ", "-", "_", ":", ".", "!", "a", "abc", "123")
    for blob in blobs:
        assert join(iterable, blob, False, False) == blob.join(iterable)


def test_join_final_and():
    sequence = "John", "Eric", "Norbert"
    assert join(sequence) == "John, Eric and Norbert."
    assert join(sequence, "") == "JohnEric and Norbert."
    assert join(sequence, "", False) == "JohnEricNorbert."
    assert join(sequence, "", False, False) == "JohnEricNorbert"
