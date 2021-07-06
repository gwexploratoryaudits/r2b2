import pytest
from r2b2.contest import Contest, ContestType


def test_simple_contest():
    """Tests creation of a simple Contest object."""
    simplecontest = Contest(100, {'a': 60, 'b': 40}, 1, ['a'], ContestType.PLURALITY)
    assert simplecontest.contest_ballots == 100
    assert simplecontest.num_candidates == 2
    assert simplecontest.num_winners == 1
    assert simplecontest.contest_type == ContestType.PLURALITY
    assert simplecontest.tally['a'] == 60
    assert simplecontest.tally['b'] == 40
    for cand in simplecontest.candidates:
        assert cand in simplecontest.tally.keys()
    assert simplecontest.reported_winners[0] == 'a'
    assert len(simplecontest.sub_contests) == 1


def test_sorting_tally():
    """Tests creation of a contest will sort the candidate tally before storing."""
    contest1 = Contest(100, {'a': 10, 'b': 40, 'c': 50}, 1, ['c'], ContestType.PLURALITY)
    assert contest1.candidates[0] == 'c'
    assert contest1.candidates[1] == 'b'
    assert contest1.candidates[2] == 'a'
    contest2 = Contest(100, {'a': 40, 'b': 10, 'c': 30}, 2, ['c', 'a'], ContestType.PLURALITY)
    assert contest2.candidates[0] == 'a'
    assert contest2.candidates[1] == 'c'
    assert contest2.candidates[2] == 'b'
    assert contest2.reported_winners[0] == 'a'
    assert contest2.reported_winners[1] == 'c'


def test_pairwise_sub_contests():
    contest = Contest(100, {'a': 50, 'b': 20, 'c': 10, 'd': 10, 'e': 5}, 1, ['a'], ContestType.PLURALITY)
    assert len(contest.sub_contests) == 4
    for i in range(4):
        assert contest.sub_contests[i].reported_winner == 'a'
        assert contest.sub_contests[i].reported_loser in ['b', 'c', 'd', 'e']
        assert contest.sub_contests[i].reported_winner_ballots == 50
        assert contest.sub_contests[i].reported_loser_ballots == contest.tally[contest.sub_contests[i].reported_loser]


def test_repr():
    """Tests __repr__ function."""
    simplecontest1 = Contest(100, {'a': 60, 'b': 40}, 1, ['a'], ContestType.PLURALITY)
    simplecontest2 = Contest(100, {'a': 60, 'b': 40}, 1, ['a'], ContestType.PLURALITY)
    assert repr(simplecontest1) == repr(simplecontest2)
    diffcontest1 = Contest(100, {'a': 60, 'b': 40}, 1, ['a'], ContestType.MAJORITY)
    assert repr(simplecontest1) != diffcontest1


def test_str():
    """Tests __str__ function."""
    simplecontest1 = Contest(100, {'a': 60, 'b': 40}, 1, ['a'], ContestType.PLURALITY)
    contest1_str = 'Contest\n-------\nContest Ballots: 100\n'
    contest1_str += 'Reported Tallies:\n     {:<15} {}\n     {:<15} {}\n'.format('a', 60, 'b', 40)
    contest1_str += 'Reported Winners: [\'a\']\n'
    contest1_str += 'Contest Type: ContestType.PLURALITY\n\n'
    assert str(simplecontest1) == contest1_str


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
