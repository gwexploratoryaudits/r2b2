import math

import pytest
from click.testing import CliRunner

from r2b2.athena import Athena
from r2b2.cli import cli
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
    assert len(simple_athena.sub_audits['a-b'].min_winner_ballots) == 0
    assert simple_athena.get_risk_level() is None


def test_athena_minerva_paper():
    contest = Contest(100000, {'A': 75000, 'B': 25000}, 1, ['A'], ContestType.MAJORITY)
    athena = Athena(.1, 1, .1, contest)
    minerva = Minerva(.1, .1, contest)
    athena.compute_min_winner_ballots(athena.sub_audits['A-B'], [50])
    minerva.compute_min_winner_ballots(minerva.sub_audits['A-B'], [50])

    # From Athena paper
    assert athena.sub_audits['A-B'].min_winner_ballots == [32]
    assert minerva.sub_audits['A-B'].min_winner_ballots == [31]


def test_athena_execute_round():
    contest = Contest(100000, {'A': 75000, 'B': 25000}, 1, ['A'], ContestType.MAJORITY)
    athena = Athena(.1, 1, .1, contest)
    assert not athena.execute_round(50, {'A': 31, 'B': 19})
    assert not athena.stopped
    assert athena.sample_ballots['A'] == [31]
    assert athena.sample_ballots['B'] == [19]
    assert not athena.sub_audits['A-B'].stopped
    assert athena.rounds == [50]
    assert athena.execute_round(100, {'A': 70, 'B': 30})
    assert athena.stopped
    assert athena.sample_ballots['A'] == [31, 70]
    assert athena.sample_ballots['B'] == [19, 30]
    assert athena.sub_audits['A-B'].stopped
    assert athena.rounds == [50, 100]
    assert athena.get_risk_level() < 0.1


def test_interactive_athena():
    runner = CliRunner()
    user_in = 'athena\n0.1\n0.1\n100000\n2\nA\n75000\nB\n25000\n1\nA\nMAJORITY\ny\n1\ny\nn\n50\n31\n19\nn\nn\n100\n70\n30\n'
    result = runner.invoke(cli, 'interactive', input=user_in)
    output_file = open('src/r2b2/tests/data/cli_test_expected_out_interactive_athena.txt', 'r')
    expected_out = output_file.read()
    assert result.output == expected_out
    output_file.close()


def test_bulk_athena():
    # Same as Minerva (that is, delta = infinity)

    # Ballot-by-ballot Minerva should yield identical stopping rules to BRAVO.
    contest = Contest(100000, {'A': 60000, 'B': 40000}, 1, ['A'], ContestType.MAJORITY)
    athena = Athena(.1, 2**31 - 1, .01, contest)
    athena.compute_all_min_winner_ballots(athena.sub_audits['A-B'])
    # p0 not hardcoded as .5 for scalability with odd total contest ballots.
    p0 = (athena.contest.contest_ballots // 2) / athena.contest.contest_ballots
    log_winner_multiplier = math.log(athena.sub_audits['A-B'].sub_contest.winner_prop / p0)
    log_loser_multiplier = math.log((1 - athena.sub_audits['A-B'].sub_contest.winner_prop) / p0)
    log_rhs = math.log(1 / athena.alpha)

    for i in range(len(athena.rounds)):
        n = athena.rounds[i]
        kmin = athena.sub_audits['A-B'].min_winner_ballots[i]
        # Assert this kmin satisfies ratio, but a kmin one less does not.
        assert kmin * log_winner_multiplier + (n - kmin) * log_loser_multiplier > log_rhs
        assert (kmin - 1) * log_winner_multiplier + (n - kmin + 1) * log_loser_multiplier <= log_rhs


def test_athena_next_sample_size():
    # TODO: Create tests for ahtena next sample size
    simple_athena = Athena(0.1, 1, 0.1, default_contest)
    simple_athena.next_sample_size()
    pass


def test_exceptions():
    contest = Contest(100000, {'A': 60000, 'B': 40000}, 1, ['A'], ContestType.MAJORITY)
    with pytest.raises(ValueError):
        Athena(.1, 0, .1, contest)
    athena = Athena(.1, 1, .1, contest)
    with pytest.raises(Exception):
        athena.stopping_condition_pairwise('A-B')
    athena.rounds.append(10)
    with pytest.raises(ValueError):
        athena.stopping_condition_pairwise('X')
    athena.rounds = []
    with pytest.raises(ValueError):
        athena.compute_min_winner_ballots(athena.sub_audits['A-B'], [])
    with pytest.raises(ValueError):
        athena.compute_min_winner_ballots(athena.sub_audits['A-B'], [0])
    with pytest.raises(ValueError):
        athena.compute_min_winner_ballots(athena.sub_audits['A-B'], [1, 2])
    with pytest.raises(ValueError):
        athena.compute_min_winner_ballots(athena.sub_audits['A-B'], [20, 20])
    with pytest.raises(ValueError):
        athena.compute_min_winner_ballots(athena.sub_audits['A-B'], [20, 19])
    with pytest.raises(ValueError):
        athena.compute_min_winner_ballots(athena.sub_audits['A-B'], [10001])

    athena.compute_min_winner_ballots(athena.sub_audits['A-B'], [20])
    with pytest.raises(ValueError):
        athena.compute_min_winner_ballots(athena.sub_audits['A-B'], [20])
    with pytest.raises(ValueError):
        athena.compute_min_winner_ballots(athena.sub_audits['A-B'], [19])
    with pytest.raises(ValueError):
        athena.compute_min_winner_ballots(athena.sub_audits['A-B'], [10001])

    contest2 = Contest(100, {'A': 60, 'B': 30}, 1, ['A'], ContestType.MAJORITY)
    athena2 = Athena(0.1, 1, 1.0, contest2)
    with pytest.raises(ValueError):
        athena2.compute_min_winner_ballots(athena2.sub_audits['A-B'], [91])
    athena2.rounds.append(10)
    with pytest.raises(Exception):
        athena2.compute_all_min_winner_ballots(athena2.sub_audits['A-B'])
    athena2.rounds = []
    with pytest.raises(ValueError):
        athena2.compute_all_min_winner_ballots(athena2.sub_audits['A-B'], 0)
    with pytest.raises(ValueError):
        athena2.compute_all_min_winner_ballots(athena2.sub_audits['A-B'], 200)
    with pytest.raises(ValueError):
        athena2.compute_all_min_winner_ballots(athena2.sub_audits['A-B'], 0)
