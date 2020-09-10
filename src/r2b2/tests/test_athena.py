import pytest

from r2b2.athena import Athena
from r2b2.contest import Contest
from r2b2.contest import ContestType
from r2b2.minerva import Minerva
from r2b2.tests import util as util

default_contest = util.generate_contest(10000)


def test_simple_athena():
    simple_athena = Athena(.1, 2**31 - 1, .1, default_contest)
    assert simple_athena.alpha == .1
    assert simple_athena.beta == 0.0
    assert simple_athena.delta == 2**31 - 1
    assert simple_athena.max_fraction_to_draw == .1
    assert len(simple_athena.rounds) == 0
    assert len(simple_athena.min_winner_ballots) == 0


def test_athena_minerva_paper():
    contest = Contest(100000, {'A': 75000, 'B': 25000}, 1, ['A'], ContestType.MAJORITY)
    athena = Athena(.1, 1, .1, contest)
    minerva = Minerva(.1, .1, contest)
    athena.compute_min_winner_ballots([50])
    minerva.compute_min_winner_ballots([50])

    # From Athena paper
    assert athena.min_winner_ballots == [32]
    assert minerva.min_winner_ballots == [31]


def test_exceptions():
    contest = Contest(100000, {'A': 60000, 'B': 40000}, 1, ['A'], ContestType.MAJORITY)
    athena = Athena(.1, 1, .1, contest)
    with pytest.raises(ValueError):
        athena.compute_min_winner_ballots([])
    with pytest.raises(ValueError):
        athena.compute_min_winner_ballots([0])
    with pytest.raises(ValueError):
        athena.compute_min_winner_ballots([1, 2])
    with pytest.raises(ValueError):
        athena.compute_min_winner_ballots([20, 20])
    with pytest.raises(ValueError):
        athena.compute_min_winner_ballots([20, 19])
    with pytest.raises(ValueError):
        athena.compute_min_winner_ballots([10001])

    athena.compute_min_winner_ballots([20])
    with pytest.raises(ValueError):
        athena.compute_min_winner_ballots([20])
    with pytest.raises(ValueError):
        athena.compute_min_winner_ballots([19])
    with pytest.raises(ValueError):
        athena.compute_min_winner_ballots([10001])
