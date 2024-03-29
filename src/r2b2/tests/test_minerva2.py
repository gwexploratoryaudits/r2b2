import pytest

from r2b2.contest import Contest
from r2b2.contest import ContestType
from r2b2.minerva2 import Minerva2
from r2b2.tests import util as util

default_contest = util.generate_contest(10000)
tol = 0.000001


def test_minerva2_kmins():
    contest = Contest(100000, {'A': 60000, 'B': 40000}, 1, ['A'], ContestType.MAJORITY)
    minerva2 = Minerva2(.1, .1, contest)
    minerva2.compute_min_winner_ballots(minerva2.sub_audits['A-B'], 100)

    # From existing software
    assert minerva2.sub_audits['A-B'].min_winner_ballots == [58]


def test_simple_minerva2():
    simple_minerva2 = Minerva2(.1, .1, default_contest)
    assert simple_minerva2.alpha == .1
    assert simple_minerva2.beta == 0.0
    assert simple_minerva2.max_fraction_to_draw == .1
    assert len(simple_minerva2.rounds) == 0
    assert len(simple_minerva2.sub_audits) == 1
    assert simple_minerva2.get_risk_level() is None
    simple_minerva2.rounds.append(10)
    simple_minerva2.stopped = True
    assert simple_minerva2.next_sample_size() == 10
    assert simple_minerva2.next_sample_size(verbose=True) == (10, 0, 1)


def test_min_sample_size():
    contest1 = Contest(100000, {'A': 60000, 'B': 40000}, 1, ['A'], ContestType.MAJORITY)
    minerva1 = Minerva2(.1, .1, contest1)
    contest2 = Contest(100000, {'A': 51000, 'B': 49000}, 1, ['A'], ContestType.MAJORITY)
    minerva2 = Minerva2(.05, .05, contest2)

    assert minerva1.sub_audits['A-B'].min_sample_size == 13
    assert minerva2.sub_audits['A-B'].min_sample_size == 840


def test_kmin_upper_bound():
    contest1 = Contest(100000, {'A': 60000, 'B': 40000}, 1, ['A'], ContestType.MAJORITY)
    minerva1 = Minerva2(.1, .1, contest1)
    contest2 = Contest(100000, {'A': 90000, 'B': 10000}, 1, ['A'], ContestType.MAJORITY)
    minerva2 = Minerva2(.1, .1, contest2)

    assert minerva1.kmin_search_upper_bound(200, minerva1.sub_audits['A-B']) == 116
    assert minerva2.kmin_search_upper_bound(2000, minerva2.sub_audits['A-B']) == 1467


def test_minerva2_first_round_estimate():

    contest1 = Contest(100000, {'A': 60000, 'B': 40000}, 1, ['A'], ContestType.MAJORITY)
    minerva1 = Minerva2(.1, .1, contest1)
    contest2 = Contest(100000, {'A': 51000, 'B': 49000}, 1, ['A'], ContestType.MAJORITY)
    minerva2 = Minerva2(.1, .1, contest2)
    contest3 = Contest(10000000, {'A': 5040799, 'B': 10000000 - 5040799}, 1, ['A'], ContestType.MAJORITY)
    minerva3 = Minerva2(.1, 1.0, contest3)

    assert minerva1.next_sample_size() == 179
    assert minerva2.next_sample_size() == 17272
    assert minerva3.next_sample_size() == 103483


def test_minerva2_second_round_estimate():
    contest1 = Contest(100000, {'A': 60000, 'B': 40000}, 1, ['A'], ContestType.MAJORITY)
    minerva1 = Minerva2(.1, .1, contest1)
    minerva1.compute_min_winner_ballots(minerva1.sub_audits['A-B'], 100)
    minerva1.sample_ballots['A'].append(54)
    minerva1.sample_ballots['B'].append(100 - 54)
    contest2 = Contest(4504975 + 4617886, {'Trump': 4617886, 'Clinton': 4504975}, 1, ['Trump'], ContestType.PLURALITY)
    minerva2 = Minerva2(.1, 1.0, contest2)
    minerva2.compute_min_winner_ballots(minerva2.sub_audits['Trump-Clinton'], 45081)
    minerva2.sample_ballots['Trump'].append(22634)
    minerva2.sample_ballots['Clinton'].append(45081 - 22634)

    bound_on_binary_search_error = 15
    s1 = minerva1.next_sample_size()
    s2 = minerva2.next_sample_size()
    assert s1 >= 306 \
        and s1 <= 306 + bound_on_binary_search_error
    assert s2 >= 111257 \
        and s2 <= 111257 + bound_on_binary_search_error


def test_exceptions():
    contest = Contest(100000, {'A': 60000, 'B': 40000}, 1, ['A'], ContestType.MAJORITY)
    minerva = Minerva2(.1, .1, contest)
    with pytest.raises(ValueError):
        minerva.compute_min_winner_ballots(minerva.sub_audits['A-B'], 0)
    with pytest.raises(ValueError):
        minerva.compute_min_winner_ballots(minerva.sub_audits['A-B'], 10001)

    minerva.compute_min_winner_ballots(minerva.sub_audits['A-B'], 20)
    with pytest.raises(ValueError):
        minerva.compute_min_winner_ballots(minerva.sub_audits['A-B'], 20)
    with pytest.raises(ValueError):
        minerva.compute_min_winner_ballots(minerva.sub_audits['A-B'], 19)
    with pytest.raises(ValueError):
        minerva.compute_min_winner_ballots(minerva.sub_audits['A-B'], 10001)

    contest2 = Contest(100, {'A': 60, 'B': 30}, 1, ['A'], ContestType.MAJORITY)
    minerva2 = Minerva2(.1, 1.0, contest2)
    with pytest.raises(ValueError):
        minerva2.compute_min_winner_ballots(minerva2.sub_audits['A-B'], 91)
    minerva2.rounds = 10
    with pytest.raises(Exception):
        minerva2.compute_all_min_winner_ballots(minerva2.sub_audits['A-B'])
    minerva2.rounds = []
    with pytest.raises(Exception):
        minerva.compute_all_min_winner_ballots(minerva2.sub_audits['A-B'], [200])

    minerva = Minerva2(.1, .1, contest)
    with pytest.raises(Exception):
        minerva.stopping_condition_pairwise('A-B')
    minerva.rounds.append(10)
    with pytest.raises(ValueError):
        minerva.stopping_condition_pairwise('x')


def test_execute_round_minerva():
    contest = Contest(100000, {'A': 60000, 'B': 40000}, 1, ['A'], ContestType.MAJORITY)
    minerva = Minerva2(.1, .1, contest)
    assert not minerva.execute_round(100, {'A': 57, 'B': 43})
    assert not minerva.stopped
    assert minerva.sample_ballots['A'] == [57]
    assert minerva.sample_ballots['B'] == [43]
    assert not minerva.sub_audits['A-B'].stopped
    assert minerva.rounds == [100]
    assert not minerva.execute_round(200, {'A': 111, 'B': 89})
    assert not minerva.stopped
    assert minerva.sample_ballots['A'] == [57, 111]
    assert minerva.sample_ballots['B'] == [43, 89]
    assert not minerva.sub_audits['A-B'].stopped
    assert minerva.rounds == [100, 200]
    assert minerva.execute_round(400, {'A': 221, 'B': 179})
    assert minerva.stopped
    assert minerva.sample_ballots['A'] == [57, 111, 221]
    assert minerva.sample_ballots['B'] == [43, 89, 179]
    assert minerva.sub_audits['A-B'].stopped
    assert minerva.rounds == [100, 200, 400]
    assert minerva.get_risk_level() < 0.1


def test_minerva2_third_round_estimate():
    contest1 = Contest(100000, {'A': 60000, 'B': 40000}, 1, ['A'], ContestType.MAJORITY)
    minerva1 = Minerva2(.1, .1, contest1)
    minerva1.compute_min_winner_ballots(minerva1.sub_audits['A-B'], 100)
    minerva1.sample_ballots['A'].append(54)
    minerva1.sample_ballots['B'].append(100 - 54)
    minerva1.compute_min_winner_ballots(minerva1.sub_audits['A-B'], 200)
    minerva1.sample_ballots['A'].append(113)
    minerva1.sample_ballots['B'].append(200 - 113)
    contest2 = Contest(4504975 + 4617886, {'Trump': 4617886, 'Clinton': 4504975}, 1, ['Trump'], ContestType.PLURALITY)
    minerva2 = Minerva2(.1, 1.0, contest2)
    minerva2.compute_min_winner_ballots(minerva2.sub_audits['Trump-Clinton'], 45081)
    minerva2.sample_ballots['Trump'].append(22634)
    minerva2.sample_ballots['Clinton'].append(45081 - 22634)
    minerva2.compute_min_winner_ballots(minerva2.sub_audits['Trump-Clinton'], 50000)
    minerva2.sample_ballots['Trump'].append(25200)
    minerva2.sample_ballots['Clinton'].append(50000-25200)

    bound_on_binary_search_error = 15
    s1 = minerva1.next_sample_size()
    s2 = minerva2.next_sample_size()

    # From other code we have known approximate round sizes
    known_s1 = 284
    known_s2 = 73084
    assert s1 >= known_s1 - bound_on_binary_search_error \
        and s1 <= known_s1 + bound_on_binary_search_error
    bound_on_binary_search_error = 100
    assert s2 >= known_s2 - bound_on_binary_search_error \
        and s2 <= known_s2 + bound_on_binary_search_error
