import pytest

from r2b2.contest import Contest
from r2b2.contest import ContestType


def test_simple_contest():
    """Tests creation of a simple Contest object."""
    simplecontest = Contest(100, {
        'a': 60,
        'b': 40
    }, 1, ['a'], ContestType.PLURALITY)
    assert simplecontest.contest_ballots == 100
    assert simplecontest.num_candidates == 2
    assert simplecontest.num_winners == 1
    assert simplecontest.contest_type == ContestType.PLURALITY
    assert simplecontest.tally['a'] == 60
    assert simplecontest.tally['b'] == 40
    for cand in simplecontest.candidates:
        assert cand in simplecontest.tally.keys()
    assert simplecontest.reported_winners[0] == 'a'
    assert simplecontest.winner_prop == 0.6


def test_initialization_errors():
    """Tests exceptions raised correctly by __init__()."""
    tally = {'a': 20, 'b': 30, 'c': 40}
    win = ['c']
    ctype = ContestType.PLURALITY
    # contest_ballots TypeError
    with pytest.raises(TypeError):
        Contest('abc', tally, 1, win, ctype)
    with pytest.raises(TypeError):
        Contest(20.5, tally, 1, win, ctype)
    with pytest.raises(TypeError):
        Contest(True, tally, 1, win, ctype)
    # contest_ballots ValueError
    with pytest.raises(ValueError):
        Contest(0, tally, 1, win, ctype)
    # tally TypeError
    with pytest.raises(TypeError):
        Contest(100, 20, 1, win, ctype)
    with pytest.raises(TypeError):
        Contest(100, [20, 30, 40], 1, win, ctype)
    with pytest.raises(TypeError):
        Contest(100, {'a': 2.5, 'b': 3.5}, 1, win, ctype)
    with pytest.raises(TypeError):
        Contest(100, {1: 2, 3: 4}, 1, win, ctype)
    # tally ValueError
    with pytest.raises(ValueError):
        Contest(100, {'a': 100, 'c': 100}, 1, win, ctype)
    with pytest.raises(ValueError):
        Contest(100, {'a': 0, 'c': 0}, 1, win, ctype)
    # num_winners TypeError
    with pytest.raises(TypeError):
        Contest(100, tally, 2.5, win, ctype)
    with pytest.raises(TypeError):
        Contest(100, tally, False, win, ctype)
    with pytest.raises(TypeError):
        Contest(100, tally, 'c', win, ctype)
    # num_winners ValueError
    with pytest.raises(ValueError):
        Contest(100, tally, 4, win, ctype)
    with pytest.raises(ValueError):
        Contest(100, tally, 0, win, ctype)
    # reported_winners TypeError
    with pytest.raises(TypeError):
        Contest(100, tally, 1, 1, ctype)
    with pytest.raises(TypeError):
        Contest(100, tally, 1, 'a', ctype)
    with pytest.raises(TypeError):
        Contest(100, tally, 1, False, ctype)
    with pytest.raises(TypeError):
        Contest(100, tally, 1, [1], ctype)
    # reported_winners ValueError
    with pytest.raises(ValueError):
        Contest(100, tally, 1, ['a', 'b'], ctype)
    with pytest.raises(ValueError):
        Contest(100, tally, 2, [], ctype)
    with pytest.raises(ValueError):
        Contest(100, tally, 1, ['x'], ctype)
    # contest_type TypeError
    with pytest.raises(TypeError):
        Contest(100, tally, 1, win, 1)
    with pytest.raises(TypeError):
        Contest(100, tally, 1, win, 'PLURALITY')
    with pytest.raises(TypeError):
        Contest(100, tally, 1, win, None)
