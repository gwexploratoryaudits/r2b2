import math

import pytest
from click.testing import CliRunner

from r2b2.cli import cli
from r2b2.contest import Contest
from r2b2.contest import ContestType
from r2b2.minerva import Minerva
from r2b2.tests import util as util

default_contest = util.generate_contest(10000)


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
    contest2 = Contest(100000, {'A': 51000, 'B': 49000}, 1, ['A'], ContestType.MAJORITY)
    minerva2 = Minerva(.05, .05, contest2)

    assert minerva1.min_sample_size == 13
    assert minerva2.min_sample_size == 840


def test_kmin_upper_bound():
    contest1 = Contest(100000, {'A': 60000, 'B': 40000}, 1, ['A'], ContestType.MAJORITY)
    minerva1 = Minerva(.1, .1, contest1)
    contest2 = Contest(100000, {'A': 90000, 'B': 10000}, 1, ['A'], ContestType.MAJORITY)
    minerva2 = Minerva(.1, .1, contest2)

    assert minerva1.kmin_search_upper_bound(200) == 116
    assert minerva2.kmin_search_upper_bound(2000) == 1467


def test_minerva_first_round_estimate():

    contest1 = Contest(100000, {'A': 60000, 'B': 40000}, 1, ['A'], ContestType.MAJORITY)
    minerva1 = Minerva(.1, .1, contest1)
    contest2 = Contest(100000, {'A': 51000, 'B': 49000}, 1, ['A'], ContestType.MAJORITY)
    minerva2 = Minerva(.1, .1, contest2)
    contest3 = Contest(10000000, {'A': 5040799, 'B': 10000000-5040799}, 1, ['A'], ContestType.MAJORITY)
    minerva3 = Minerva(.1, 1.0, contest3)

    assert minerva1.next_sample_size() == 179
    assert minerva2.next_sample_size() == 17272
    assert minerva3.next_sample_size() == 103483


def test_minerva_first_round_gaussian_estimate():
    contest4 = Contest(1000000, {'A': 502000, 'B': 498000}, 1, ['A'], ContestType.PLURALITY)
    minerva4 = Minerva(.1, 1.0, contest4)

    assert minerva4.next_sample_size_gaussian() == 429778


def test_minerva_second_round_estimate():
    contest1 = Contest(100000, {'A': 60000, 'B': 40000}, 1, ['A'], ContestType.MAJORITY)
    minerva1 = Minerva(.1, .1, contest1)
    minerva1.compute_min_winner_ballots([100])
    minerva1.sample_winner_ballots.append(54)
    contest2 = Contest(4504975+4617886, {'Trump': 4617886, 'Clinton': 4504975}, 1, ['Trump'], ContestType.PLURALITY)
    minerva2 = Minerva(.1, 1.0, contest2)
    minerva2.compute_min_winner_ballots([45081])
    minerva2.sample_winner_ballots.append(22634)

    assert minerva1.next_sample_size() == 305
    assert minerva2.next_sample_size() == 111257


def test_minerva_georgia_senate_2020():
    ga_senate_race = Contest(2453876 + 2358432, {'A': 2453876, 'B': 2358432}, 1, ['A'], ContestType.PLURALITY)

    ga_senate_audit = Minerva(.1, 1.0, ga_senate_race)
    irrelevant_scale_up = 1.0238785631
    estimates = []
    for sprob in [.7, .8, .9]:
        estimates.append(math.ceil(irrelevant_scale_up * ga_senate_audit.next_sample_size(sprob=sprob)))
    assert estimates == [10486, 13205, 18005]
    ga_senate_audit.rounds.append(9903)
    ga_senate_audit.current_dist_null()
    ga_senate_audit.current_dist_reported()
    assert abs(ga_senate_audit.compute_risk(4950) - 0.527638189598802) < .000001
    ga_senate_audit.find_kmin(True)
    ga_senate_audit.truncate_dist_null()
    ga_senate_audit.truncate_dist_reported()
    ga_senate_audit.rounds.append(24000)
    ga_senate_audit.current_dist_null()
    ga_senate_audit.current_dist_reported()
    assert abs(ga_senate_audit.compute_risk(11900) - 2.663358309286826) < .000001
    ga_senate_audit.find_kmin(True)
    ga_senate_audit.truncate_dist_null()
    ga_senate_audit.truncate_dist_reported()
    ga_senate_audit.rounds.append(45600)
    ga_senate_audit.current_dist_null()
    assert abs(ga_senate_audit.compute_risk(24000)) < .000001

    ga_senate_audit = Minerva(.1, 1.0, ga_senate_race)
    ga_senate_audit.rounds.append(17605)
    ga_senate_audit.current_dist_null()
    ga_senate_audit.current_dist_reported()
    assert abs(ga_senate_audit.compute_risk(8900) - 0.081750333563781) < .000001

    ga_senate_audit = Minerva(.1, 1.0, ga_senate_race)
    ga_senate_audit.rounds.append(17605)
    ga_senate_audit.current_dist_null()
    ga_senate_audit.current_dist_reported()
    assert ga_senate_audit.compute_risk(17605) == 0

    ga_senate_audit = Minerva(.1, 1.0, ga_senate_race)
    ga_senate_audit.rounds.append(17605)
    ga_senate_audit.current_dist_null()
    ga_senate_audit.current_dist_reported()
    assert abs(ga_senate_audit.compute_risk(0) - 1) < .000001


def test_minerva_kmins():
    contest = Contest(100000, {'A': 60000, 'B': 40000}, 1, ['A'], ContestType.MAJORITY)
    minerva = Minerva(.1, .1, contest)
    minerva.compute_min_winner_ballots([100, 200, 400])

    # From existing software
    assert minerva.min_winner_ballots == [58, 113, 221]


def test_interactive_minerva():
    runner = CliRunner()
    user_in = 'minerva\n0.1\n0.1\n100000\n2\nA\n60000\nB\n40000\n1\nA\nMAJORITY\ny\ny\n100\nn\n57\nn\n200\nn\n112\nn\n400\nn\n221\n'
    result = runner.invoke(cli, 'interactive', input=user_in)
    output_file = open('src/r2b2/tests/data/cli_test_expected_out_interactive_minerva.txt', 'r')
    expected_out = output_file.read()
    assert result.output == expected_out
    output_file.close()


def test_compute_risk_minerva():
    runner = CliRunner()
    user_in = 'minerva\n0.1\n0.1\n100000\n2\nA\n60000\nB\n40000\n1\nA\nMAJORITY\ny\ny\n100\ny\n57\nn\n60\n'
    result = runner.invoke(cli, 'interactive', input=user_in)
    output_file = open('src/r2b2/tests/data/cli_test_expected_out_compute_risk_minerva.txt', 'r')
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
