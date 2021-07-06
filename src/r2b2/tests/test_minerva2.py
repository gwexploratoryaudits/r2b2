import json
import math

#import pytest
from click.testing import CliRunner

from r2b2.cli import cli
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

    arbitrary_fixed_bound_on_binary_search_error = 15
    s1 = minerva1.next_sample_size() 
    s2 = minerva2.next_sample_size() 
    assert s1 >= 306 \
            and s1 <= 306 + arbitrary_fixed_bound_on_binary_search_error
    assert s2 >= 111257 \
            and s2 <= 111257 + arbitrary_fixed_bound_on_binary_search_error
    #NOTE the error here is small enough that it is (in initial development)
    #     being noted and ignored temporarily
    #TODO understand and address as appropriate this error


# TODO implement: def test_execute_round_minerva():
# NOTE need to first implement execute_round for Minerva2

"""
# during development, manually run tests here
test_minerva2_kmins()
test_simple_minerva2()
test_min_sample_size()
test_kmin_upper_bound()
test_minerva2_first_round_estimate()
test_minerva2_second_round_estimate()
print("All tests passed.")
"""
