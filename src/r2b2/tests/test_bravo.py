import json
import math

import pytest
from click.testing import CliRunner

from r2b2.cli import cli
from r2b2.contest import Contest
from r2b2.contest import ContestType
from r2b2.bravo import BRAVO
from r2b2.tests import util as util

default_contest = util.generate_contest(10000)
tol = 0.000001


def test_simple_bravo():
    simple_bravo = BRAVO(.1, .1, default_contest)
    assert simple_bravo.alpha == .1
    assert simple_bravo.beta == 0.0
    assert simple_bravo.max_fraction_to_draw == .1
    assert len(simple_bravo.rounds) == 0
    assert len(simple_bravo.sub_audits) == 1
    assert simple_bravo.get_risk_level() is None
    simple_bravo.rounds.append(10)
    simple_bravo.stopped = True
    assert simple_bravo.next_sample_size() == 10
    assert simple_bravo.next_sample_size(verbose=True) == (10, 0, 1)


def test_bravo_kmins():
    contest = Contest(100000, {'A': 60000, 'B': 40000}, 1, ['A'], ContestType.MAJORITY)
    bravo = BRAVO(.1, .1, contest)
    bravo.compute_min_winner_ballots(bravo.sub_audits['A-B'], [100, 200, 400])

    # From existing software
    assert bravo.sub_audits['A-B'].min_winner_ballots == [61, 116, 226]


def test_min_sample_size():
    contest1 = Contest(100000, {'A': 60000, 'B': 40000}, 1, ['A'], ContestType.MAJORITY)
    bravo1 = BRAVO(.1, .1, contest1)
    contest2 = Contest(100000, {'A': 51000, 'B': 49000}, 1, ['A'], ContestType.MAJORITY)
    bravo2 = BRAVO(.05, .05, contest2)

    assert abs(bravo1.sub_audits['A-B'].min_sample_size - 13) <= 2
    assert abs(bravo2.sub_audits['A-B'].min_sample_size - 879) <= 40


def test_bravo_first_round_estimate():
    contest1 = Contest(100000, {'A': 60000, 'B': 40000}, 1, ['A'], ContestType.MAJORITY)
    bravo1 = BRAVO(.1, .1, contest1)
    contest2 = Contest(100000, {'A': 51000, 'B': 49000}, 1, ['A'], ContestType.MAJORITY)
    bravo2 = BRAVO(.1, .1, contest2)
    contest3 = Contest(10000000, {'A': 5040799, 'B': 10000000 - 5040799}, 1, ['A'], ContestType.MAJORITY)
    bravo3 = BRAVO(.1, 1.0, contest3)

    assert abs(bravo1.next_sample_size() - 342) <= 15
    assert abs(bravo2.next_sample_size() - 35707) <= 100
    assert abs(bravo3.next_sample_size() - 214389) <= 300


def test_bravo_second_round_estimate():
    contest1 = Contest(100000, {'A': 60000, 'B': 40000}, 1, ['A'], ContestType.MAJORITY)
    bravo1 = BRAVO(.1, .1, contest1)
    bravo1.compute_min_winner_ballots(bravo1.sub_audits['A-B'], [100])
    bravo1.sample_ballots['A'].append(54)
    bravo1.sample_ballots['B'].append(100 - 54)
    contest2 = Contest(4504975 + 4617886, {'Trump': 4617886, 'Clinton': 4504975}, 1, ['Trump'], ContestType.PLURALITY)
    bravo2 = BRAVO(.1, 1.0, contest2)
    bravo2.compute_min_winner_ballots(bravo2.sub_audits['Trump-Clinton'], [45081])
    bravo2.sample_ballots['Trump'].append(22634)
    bravo2.sample_ballots['Clinton'].append(45081 - 22634)

    assert abs(bravo1.next_sample_size() - 473) <= 10
    assert abs(bravo2.next_sample_size() - 160200) <= 300


def test_execute_round_bravo():
    contest = Contest(100000, {'A': 60000, 'B': 40000}, 1, ['A'], ContestType.MAJORITY)
    bravo = BRAVO(.1, .1, contest)
    assert not bravo.execute_round(100, {'A': 57, 'B': 43})
    assert not bravo.stopped
    assert bravo.sample_ballots['A'] == [57]
    assert bravo.sample_ballots['B'] == [43]
    assert not bravo.sub_audits['A-B'].stopped
    assert bravo.rounds == [100]
    assert not bravo.execute_round(200, {'A': 112, 'B': 88})
    assert not bravo.stopped
    assert bravo.sample_ballots['A'] == [57, 112]
    assert bravo.sample_ballots['B'] == [43, 88]
    assert not bravo.sub_audits['A-B'].stopped
    assert bravo.rounds == [100, 200]
    assert bravo.execute_round(400, {'A': 226, 'B': 174})
    assert bravo.stopped
    assert bravo.sample_ballots['A'] == [57, 112, 226]
    assert bravo.sample_ballots['B'] == [43, 88, 174]
    assert bravo.sub_audits['A-B'].stopped
    assert bravo.rounds == [100, 200, 400]
    assert bravo.get_risk_level() < 0.1
