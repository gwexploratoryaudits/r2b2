import math

import pytest
from click.testing import CliRunner

import r2b2.tests.util as util
from r2b2.cli import cli
from r2b2.contest import Contest
from r2b2.contest import ContestType
from r2b2.minerva import Minerva

default_contest = util.generate_contest(100000)


def test_simple_minerva():
    simple_minerva = Minerva(.1, .1, default_contest)
    assert simple_minerva.alpha == .1
    assert simple_minerva.beta == 0.0
    assert simple_minerva.max_fraction_to_draw == .1
    assert len(simple_minerva.rounds) == 0
    assert len(simple_minerva.min_winner_ballots) == 0


def test_min_sample_size():
    contest1 = Contest(100000, {'A': 60000, 'B': 40000}, 1, ['A'], ContestType.MAJORITY)
    minerva1 = Minerva(.1, .1, contest1)
    contest2 = Contest(100000, {'A': 100000, 'B': 0}, 1, ['A'], ContestType.MAJORITY)
    minerva2 = Minerva(.05, .2, contest2)
    contest3 = Contest(100000, {'A': 51000, 'B': 49000}, 1, ['A'], ContestType.MAJORITY)
    minerva3 = Minerva(.05, .05, contest3)

    # Numbers x below satisfy: (p1 / p0)^x > 1 / alpha yet (p1 / p0)^(x-1) <= 1 / alpha.
    assert minerva1.min_sample_size == 13
    assert minerva2.min_sample_size == 5
    assert minerva3.min_sample_size == 152


def test_minerva_kmins():
    contest = Contest(100000, {'A': 60000, 'B': 40000}, 1, ['A'], ContestType.MAJORITY)
    minerva = Minerva(.1, .1, contest)
    minerva.compute_min_winner_ballots([100, 200, 400])

    # From existing software
    assert minerva.min_winner_ballots == [58, 113, 221]


def test_interactive_minerva():
    runner = CliRunner()
    user_in = 'minerva\n0.1\n0.1\n100000\n2\nA\n60000\nB\n40000\n1\nA\nMAJORITY\ny\ny\n100\n57\nn\n200\n112\nn\n400\n221\n'
    result = runner.invoke(cli, 'interactive', input=user_in)
    output_file = open('src/r2b2/tests/data/cli_test_expected_out_interactive_minerva.txt', 'r')
    expected_out = output_file.read()
    assert result.output == expected_out
    output_file.close()


def test_bulk_minerva():
    # Ballot-by-ballot Minerva should yield identical stopping rules to BRAVO.
    contest = Contest(100000, {'A': 60000, 'B': 40000}, 1, ['A'], ContestType.MAJORITY)
    minerva = Minerva(.1, .01, contest)
    minerva.compute_all_min_winner_ballots()
    # p0 not hardcoded as .5 for scalability with odd total contest ballots.
    p0 = (minerva.contest.contest_ballots // 2) / minerva.contest.contest_ballots
    log_winner_multiplier = math.log(minerva.contest.winner_prop / p0)
    log_loser_multiplier = math.log((1 - minerva.contest.winner_prop) / p0)
    log_rhs = math.log(1 / minerva.alpha)

    for i in range(len(minerva.rounds)):
        n = minerva.rounds[i]
        kmin = minerva.min_winner_ballots[i]
        # Assert this kmin satisfies ratio, but a kmin one less does not.
        assert kmin * log_winner_multiplier + (n - kmin) * log_loser_multiplier > log_rhs
        assert (kmin - 1) * log_winner_multiplier + (n - kmin + 1) * log_loser_multiplier <= log_rhs


def test_sentinel():
    contest = Contest(100000, {'A': 60000, 'B': 40000}, 1, ['A'], ContestType.MAJORITY)
    minerva = Minerva(.1, .1, contest)
    minerva.compute_min_winner_ballots([13, 14, 15])
    assert minerva.min_winner_ballots == [13, None, 14]


def test_exceptions():
    contest = Contest(100000, {'A': 60000, 'B': 40000}, 1, ['A'], ContestType.MAJORITY)
    minerva = Minerva(.1, .1, contest)
    with pytest.raises(ValueError):
        minerva.compute_min_winner_ballots([])
    with pytest.raises(ValueError):
        minerva.compute_min_winner_ballots([0])
    with pytest.raises(ValueError):
        minerva.compute_min_winner_ballots([1, 2])
    with pytest.raises(ValueError):
        minerva.compute_min_winner_ballots([20, 20])
    with pytest.raises(ValueError):
        minerva.compute_min_winner_ballots([20, 19])
    with pytest.raises(ValueError):
        minerva.compute_min_winner_ballots([10001])

    minerva.compute_min_winner_ballots([20])
    with pytest.raises(ValueError):
        minerva.compute_min_winner_ballots([20])
    with pytest.raises(ValueError):
        minerva.compute_min_winner_ballots([19])
    with pytest.raises(ValueError):
        minerva.compute_min_winner_ballots([10001])
