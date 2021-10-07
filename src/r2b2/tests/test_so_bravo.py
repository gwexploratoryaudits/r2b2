import json
import math

import pytest
from click.testing import CliRunner

from r2b2.cli import cli
from r2b2.contest import Contest
from r2b2.contest import ContestType
from r2b2.so_bravo import SO_BRAVO
from r2b2.tests import util as util

default_contest = util.generate_contest(10000)
tol = 0.000001


def test_simple_so_bravo():
    simple_so_bravo = SO_BRAVO(.1, .1, default_contest)
    assert simple_so_bravo.alpha == .1
    assert simple_so_bravo.beta == 0.0
    assert simple_so_bravo.max_fraction_to_draw == .1
    assert len(simple_so_bravo.rounds) == 0
    assert len(simple_so_bravo.sub_audits) == 1
    assert simple_so_bravo.get_risk_level() is None
    simple_so_bravo.rounds.append(10)
    simple_so_bravo.stopped = True
    assert simple_so_bravo.next_sample_size() == 10
    assert simple_so_bravo.next_sample_size(verbose=True) == (10, 0, 1)


def test_so_bravo_kmins():
    contest = Contest(100000, {'A': 60000, 'B': 40000}, 1, ['A'], ContestType.MAJORITY)
    so_bravo = SO_BRAVO(.1, .1, contest)
    so_bravo.compute_min_winner_ballots(so_bravo.sub_audits['A-B'], [100, 200, 400])

    # From existing software
    assert so_bravo.sub_audits['A-B'].min_winner_ballots == [61, 116, 226]


def test_min_sample_size():
    contest1 = Contest(100000, {'A': 60000, 'B': 40000}, 1, ['A'], ContestType.MAJORITY)
    so_bravo1 = SO_BRAVO(.1, .1, contest1)
    contest2 = Contest(100000, {'A': 51000, 'B': 49000}, 1, ['A'], ContestType.MAJORITY)
    so_bravo2 = SO_BRAVO(.05, .05, contest2)

    assert abs(so_bravo1.sub_audits['A-B'].min_sample_size - 13) <= 2
    assert abs(so_bravo2.sub_audits['A-B'].min_sample_size - 879) <= 40


def test_so_bravo_first_round_estimate():
    contest1 = Contest(100000, {'A': 60000, 'B': 40000}, 1, ['A'], ContestType.MAJORITY)
    so_bravo1 = SO_BRAVO(.1, .1, contest1)
    contest2 = Contest(100000, {'A': 51000, 'B': 49000}, 1, ['A'], ContestType.MAJORITY)
    so_bravo2 = SO_BRAVO(.1, .1, contest2)
    contest3 = Contest(10000000, {'A': 5040799, 'B': 10000000 - 5040799}, 1, ['A'], ContestType.MAJORITY)
    so_bravo3 = SO_BRAVO(.1, 1.0, contest3)

    assert abs(so_bravo1.next_sample_size() - 342) <= 15
    assert abs(so_bravo2.next_sample_size() - 35707) <= 100
    assert abs(so_bravo3.next_sample_size() - 214389) <= 300


def test_so_bravo_second_round_estimate():
    contest1 = Contest(100000, {'A': 60000, 'B': 40000}, 1, ['A'], ContestType.MAJORITY)
    so_bravo1 = SO_BRAVO(.1, .1, contest1)
    so_bravo1.compute_min_winner_ballots(so_bravo1.sub_audits['A-B'], [100])
    so_bravo1.sample_ballots['A'].append(54)
    so_bravo1.sample_ballots['B'].append(100 - 54)
    contest2 = Contest(4504975 + 4617886, {'Trump': 4617886, 'Clinton': 4504975}, 1, ['Trump'], ContestType.PLURALITY)
    so_bravo2 = SO_BRAVO(.1, 1.0, contest2)
    so_bravo2.compute_min_winner_ballots(so_bravo2.sub_audits['Trump-Clinton'], [45081])
    so_bravo2.sample_ballots['Trump'].append(22634)
    so_bravo2.sample_ballots['Clinton'].append(45081 - 22634)

    assert abs(so_bravo1.next_sample_size() - 473) <= 10
    assert abs(so_bravo2.next_sample_size() - 160200) <= 300


def test_execute_round_so_bravo():
    contest = Contest(100000, {'A': 60000, 'B': 40000}, 1, ['A'], ContestType.MAJORITY)
    so_bravo = SO_BRAVO(.1, .1, contest)
    assert not so_bravo.execute_round(100, {'A': 57, 'B': 43})
    assert not so_bravo.stopped
    assert so_bravo.sample_ballots['A'] == [57]
    assert so_bravo.sample_ballots['B'] == [43]
    assert not so_bravo.sub_audits['A-B'].stopped
    assert so_bravo.rounds == [100]
    assert not so_bravo.execute_round(200, {'A': 112, 'B': 88})
    assert not so_bravo.stopped
    assert so_bravo.sample_ballots['A'] == [57, 112]
    assert so_bravo.sample_ballots['B'] == [43, 88]
    assert not so_bravo.sub_audits['A-B'].stopped
    assert so_bravo.rounds == [100, 200]
    assert so_bravo.execute_round(400, {'A': 226, 'B': 174})
    assert so_bravo.stopped
    assert so_bravo.sample_ballots['A'] == [57, 112, 226]
    assert so_bravo.sample_ballots['B'] == [43, 88, 174]
    assert so_bravo.sub_audits['A-B'].stopped
    assert so_bravo.rounds == [100, 200, 400]
    assert so_bravo.get_risk_level() < 0.1

def test_find_sprob_first_round():
    # Test data from github at:
    # gwexploratoryaudits/brla_explore/blob/master/B2Audits/Tables/BRAVO%20Table%20I.pdf
    ps = [.7, .65, .6, .58, .55]
    n_90perc = [60, 108, 244, 381, 974]
    for i in range(len(ps)):
        N = 1000
        A_tally = int(N*ps[i])
        B_tally = N - A_tally
        contest = Contest(N, {'A': A_tally, 'B': B_tally}, 1, ['A'], ContestType.MAJORITY)
        so_bravo = SO_BRAVO(.1, .1, contest)
        assert abs(so_bravo.find_sprob(n_90perc[i], so_bravo.sub_audits['A-B'])[1] - .9) <= .005

def test_next_sample_size_first_round():
    # Test data from github at:
    # gwexploratoryaudits/brla_explore/blob/master/B2Audits/Tables/BRAVO%20Table%20I.pdf
    ps = [.7, .65, .6, .58, .55]
    desired_sprob = .9
    n_90perc = [60, 108, 244, 381, 974]
    for i in range(len(ps)):
        N = 1000
        A_tally = int(N*ps[i])
        B_tally = N - A_tally
        contest = Contest(N, {'A': A_tally, 'B': B_tally}, 1, ['A'], ContestType.MAJORITY)
        so_bravo = SO_BRAVO(.1, .1, contest)
        assert abs(so_bravo.next_sample_size(sprob=desired_sprob) - n_90perc[i]) <= 0

test_simple_so_bravo()
test_so_bravo_kmins()
test_min_sample_size()
test_so_bravo_first_round_estimate()
test_so_bravo_second_round_estimate()
test_execute_round_so_bravo()
test_find_sprob_first_round()
test_next_sample_size_first_round()
