import json
import math

from click.testing import CliRunner

import pytest
from r2b2.cli import cli
from r2b2.contest import Contest, ContestType
from r2b2.minerva import Minerva
from r2b2.tests import util as util

default_contest = util.generate_contest(10000)
tol = 0.000001


def test_simple_minerva():
    simple_minerva = Minerva(.1, .1, default_contest)
    assert simple_minerva.alpha == .1
    assert simple_minerva.beta == 0.0
    assert simple_minerva.max_fraction_to_draw == .1
    assert len(simple_minerva.rounds) == 0
    assert len(simple_minerva.sub_audits) == 1
    assert simple_minerva.get_risk_level() is None
    simple_minerva.rounds.append(10)
    simple_minerva.stopped = True
    assert simple_minerva.next_sample_size() == 10
    assert simple_minerva.next_sample_size(verbose=True) == (10, 0, 1)


def test_min_sample_size():
    contest1 = Contest(100000, {'A': 60000, 'B': 40000}, 1, ['A'], ContestType.MAJORITY)
    minerva1 = Minerva(.1, .1, contest1)
    contest2 = Contest(100000, {'A': 51000, 'B': 49000}, 1, ['A'], ContestType.MAJORITY)
    minerva2 = Minerva(.05, .05, contest2)

    assert minerva1.sub_audits['A-B'].min_sample_size == 13
    assert minerva2.sub_audits['A-B'].min_sample_size == 840


def test_kmin_upper_bound():
    contest1 = Contest(100000, {'A': 60000, 'B': 40000}, 1, ['A'], ContestType.MAJORITY)
    minerva1 = Minerva(.1, .1, contest1)
    contest2 = Contest(100000, {'A': 90000, 'B': 10000}, 1, ['A'], ContestType.MAJORITY)
    minerva2 = Minerva(.1, .1, contest2)

    assert minerva1.kmin_search_upper_bound(200, minerva1.sub_audits['A-B']) == 116
    assert minerva2.kmin_search_upper_bound(2000, minerva2.sub_audits['A-B']) == 1467


def test_minerva_first_round_estimate():

    contest1 = Contest(100000, {'A': 60000, 'B': 40000}, 1, ['A'], ContestType.MAJORITY)
    minerva1 = Minerva(.1, .1, contest1)
    contest2 = Contest(100000, {'A': 51000, 'B': 49000}, 1, ['A'], ContestType.MAJORITY)
    minerva2 = Minerva(.1, .1, contest2)
    contest3 = Contest(10000000, {'A': 5040799, 'B': 10000000 - 5040799}, 1, ['A'], ContestType.MAJORITY)
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
    minerva1.compute_min_winner_ballots(minerva1.sub_audits['A-B'], [100])
    minerva1.sample_ballots['A'].append(54)
    minerva1.sample_ballots['B'].append(100 - 54)
    contest2 = Contest(4504975 + 4617886, {'Trump': 4617886, 'Clinton': 4504975}, 1, ['Trump'], ContestType.PLURALITY)
    minerva2 = Minerva(.1, 1.0, contest2)
    minerva2.compute_min_winner_ballots(minerva2.sub_audits['Trump-Clinton'], [45081])
    minerva2.sample_ballots['Trump'].append(22634)
    minerva2.sample_ballots['Clinton'].append(45081 - 22634)

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
    ga_senate_audit.execute_round(9903, {'A': 4950, 'B': 9903-4950})
    assert abs(ga_senate_audit.pvalue_schedule[-1] - 0.527638189598802) < .000001
    ga_senate_audit.execute_round(24000, {'A': 11900, 'B': 24000-11900})
    assert abs(ga_senate_audit.pvalue_schedule[-1] - 2.663358309286826) < .000001
    ga_senate_audit.execute_round(45600, {'A': 24000, 'B': 45600-24000})
    assert abs(ga_senate_audit.pvalue_schedule[-1]) < 0.000001

    ga_senate_audit = Minerva(.1, 1.0, ga_senate_race)
    ga_senate_audit.execute_round(17605, {'A': 8900, 'B': 17605-8900})
    assert abs(ga_senate_audit.get_risk_level() - 0.081750333563781) < .000001

    ga_senate_audit = Minerva(.1, 1.0, ga_senate_race)
    ga_senate_audit.execute_round(17605, {'A': 17605, 'B': 0})
    assert ga_senate_audit.get_risk_level() == 0

    ga_senate_audit = Minerva(.1, 1.0, ga_senate_race)
    ga_senate_audit.execute_round(17605, {'A': 0, 'B': 17605})
    assert abs(ga_senate_audit.get_risk_level() - 1) < 0.000001


def test_minerva_kmins():
    contest = Contest(100000, {'A': 60000, 'B': 40000}, 1, ['A'], ContestType.MAJORITY)
    minerva = Minerva(.1, .1, contest)
    minerva.compute_min_winner_ballots(minerva.sub_audits['A-B'], [100, 200, 400])

    # From existing software
    assert minerva.sub_audits['A-B'].min_winner_ballots == [58, 113, 221]


def test_execute_round_minerva():
    contest = Contest(100000, {'A': 60000, 'B': 40000}, 1, ['A'], ContestType.MAJORITY)
    minerva = Minerva(.1, .1, contest)
    assert not minerva.execute_round(100, {'A': 57, 'B': 43})
    assert not minerva.stopped
    assert minerva.sample_ballots['A'] == [57]
    assert minerva.sample_ballots['B'] == [43]
    assert not minerva.sub_audits['A-B'].stopped
    assert minerva.rounds == [100]
    assert not minerva.execute_round(200, {'A': 112, 'B': 88})
    assert not minerva.stopped
    assert minerva.sample_ballots['A'] == [57, 112]
    assert minerva.sample_ballots['B'] == [43, 88]
    assert not minerva.sub_audits['A-B'].stopped
    assert minerva.rounds == [100, 200]
    assert minerva.execute_round(400, {'A': 221, 'B': 179})
    assert minerva.stopped
    assert minerva.sample_ballots['A'] == [57, 112, 221]
    assert minerva.sample_ballots['B'] == [43, 88, 179]
    assert minerva.sub_audits['A-B'].stopped
    assert minerva.rounds == [100, 200, 400]
    assert minerva.get_risk_level() < 0.1


def test_interactive_minerva():
    runner = CliRunner()
    user_in = \
        'minerva\n0.1\n0.1\n100000\n2\nA\n60000\nB\n40000\n1\nA\nMAJORITY\ny\ny\nn\n100\n57\n43\nn\nn\n200\n112\n88\nn\nn\n400\n221\n179\n'
    result = runner.invoke(cli, 'interactive', input=user_in)
    output_file = open('src/r2b2/tests/data/cli_test_expected_out_interactive_minerva.txt', 'r')
    expected_out = output_file.read()
    assert result.output == expected_out
    output_file.close()


# FIXME: Replace with different test?
# This option no longer exists in cli
# def test_compute_risk_minerva():
#     runner = CliRunner()
#     user_in = 'minerva\n0.1\n0.1\n100000\n2\nA\n60000\nB\n40000\n1\nA\nMAJORITY\ny\ny\n100\ny\n57\nn\n60\n'
#     result = runner.invoke(cli, 'interactive', input=user_in)
#     output_file = open('src/r2b2/tests/data/cli_test_expected_out_compute_risk_minerva.txt', 'r')
#     expected_out = output_file.read()
#     assert result.output == expected_out
#     output_file.close()


def test_next_sample_size_minerva():
    runner = CliRunner()
    user_in = 'minerva\n0.1\n0.1\n100000\n2\nA\n60000\nB\n40000\n1\nA\nMAJORITY\ny\ny\ny\n.7\nn\n100\n60\n40\n'
    result = runner.invoke(cli, 'interactive', input=user_in)
    output_file = open('src/r2b2/tests/data/cli_test_expected_out_next_sample_size_minerva.txt', 'r')
    expected_out = output_file.read()
    assert result.output == expected_out
    output_file.close()


def test_multiple_candidate_minerva():
    test_file = 'src/r2b2/tests/data/full_multi_cand.json'
    with open(test_file, 'r') as tf:
        data = json.load(tf)
        test = 'testx'
        # Get contest from test
        contest_data = data[test]['election']['contests']['contest_1']
        contest = Contest(contest_data['contest_ballots'], contest_data['tally'], contest_data['num_winners'],
                          contest_data['reported_winners'], ContestType[contest_data['contest_type']])
        audit = Minerva(data[test]['alpha'], 1.0, contest)

        for r in data[test]['rounds']:
            sample_raw = data[test]['rounds'][r]['pvalue']['observations']
            sample_size = sum(sample_raw)
            sample = {}
            for i, c in enumerate(contest.candidates):
                sample[c] = sample_raw[i]
            audit.execute_round(sample_size, sample)
            assert abs(data[test]['rounds'][r]['pvalue']['expected']['pvalue'] - audit.pvalue_schedule[-1]) < tol
            for pair in data[test]['rounds'][r]['pvalue']['expected']['pairwise']:
                assert abs(data[test]['rounds'][r]['pvalue']['expected']['pairwise'][pair] -
                           audit.sub_audits[pair].pvalue_schedule[-1]) < tol


def test_bulk_minerva():
    # Ballot-by-ballot Minerva should yield identical stopping rules to BRAVO.
    contest = Contest(100000, {'A': 60000, 'B': 40000}, 1, ['A'], ContestType.MAJORITY)
    minerva = Minerva(.1, .01, contest)
    minerva.compute_all_min_winner_ballots(minerva.sub_audits['A-B'])
    # p0 not hardcoded as .5 for scalability with odd total contest ballots.
    p0 = (minerva.contest.contest_ballots // 2) / minerva.contest.contest_ballots
    log_winner_multiplier = math.log(minerva.sub_audits['A-B'].sub_contest.winner_prop / p0)
    log_loser_multiplier = math.log((1 - minerva.sub_audits['A-B'].sub_contest.winner_prop) / p0)
    log_rhs = math.log(1 / minerva.alpha)

    for i in range(len(minerva.rounds)):
        n = minerva.rounds[i]
        kmin = minerva.sub_audits['A-B'].min_winner_ballots[i]
        # Assert this kmin satisfies ratio, but a kmin one less does not.
        assert kmin * log_winner_multiplier + (n - kmin) * log_loser_multiplier > log_rhs
        assert (kmin - 1) * log_winner_multiplier + (n - kmin + 1) * log_loser_multiplier <= log_rhs


def test_sentinel():
    contest = Contest(100000, {'A': 60000, 'B': 40000}, 1, ['A'], ContestType.MAJORITY)
    minerva = Minerva(.1, .1, contest)
    minerva.compute_min_winner_ballots(minerva.sub_audits['A-B'], [13, 14, 15])
    assert minerva.sub_audits['A-B'].min_winner_ballots == [13, None, 14]


def test_exceptions():
    contest = Contest(100000, {'A': 60000, 'B': 40000}, 1, ['A'], ContestType.MAJORITY)
    minerva = Minerva(.1, .1, contest)
    with pytest.raises(ValueError):
        minerva.compute_min_winner_ballots(minerva.sub_audits['A-B'], [])
    with pytest.raises(ValueError):
        minerva.compute_min_winner_ballots(minerva.sub_audits['A-B'], [0])
    with pytest.raises(ValueError):
        minerva.compute_min_winner_ballots(minerva.sub_audits['A-B'], [1, 2])
    with pytest.raises(ValueError):
        minerva.compute_min_winner_ballots(minerva.sub_audits['A-B'], [20, 20])
    with pytest.raises(ValueError):
        minerva.compute_min_winner_ballots(minerva.sub_audits['A-B'], [20, 19])
    with pytest.raises(ValueError):
        minerva.compute_min_winner_ballots(minerva.sub_audits['A-B'], [10001])

    minerva.compute_min_winner_ballots(minerva.sub_audits['A-B'], [20])
    with pytest.raises(ValueError):
        minerva.compute_min_winner_ballots(minerva.sub_audits['A-B'], [20])
    with pytest.raises(ValueError):
        minerva.compute_min_winner_ballots(minerva.sub_audits['A-B'], [19])
    with pytest.raises(ValueError):
        minerva.compute_min_winner_ballots(minerva.sub_audits['A-B'], [10001])

    contest2 = Contest(100, {'A': 60, 'B': 30}, 1, ['A'], ContestType.MAJORITY)
    minerva2 = Minerva(.1, 1.0, contest2)
    with pytest.raises(ValueError):
        minerva2.compute_min_winner_ballots(minerva2.sub_audits['A-B'], [91])
    minerva2.rounds = [10]
    with pytest.raises(Exception):
        minerva2.compute_all_min_winner_ballots(minerva2.sub_audits['A-B'])
    minerva2.rounds = []
    with pytest.raises(Exception):
        minerva.compute_all_min_winner_ballots(minerva2.sub_audits['A-B'], 200)

    minerva = Minerva(.1, .1, contest)
    with pytest.raises(Exception):
        minerva.stopping_condition_pairwise('A-B')
    minerva.rounds.append(10)
    with pytest.raises(ValueError):
        minerva.stopping_condition_pairwise('x')
