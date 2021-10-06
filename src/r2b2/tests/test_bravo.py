import json
import math

import pytest
from click.testing import CliRunner

from r2b2.cli import cli
from r2b2.contest import Contest
from r2b2.contest import ContestType
from r2b2.eor_bravo import EOR_BRAVO
from r2b2.tests import util as util

default_contest = util.generate_contest(10000)
tol = 0.000001


def test_simple_eor_bravo():
    simple_eor_bravo = EOR_BRAVO(.1, .1, default_contest)
    assert simple_eor_bravo.alpha == .1
    assert simple_eor_bravo.beta == 0.0
    assert simple_eor_bravo.max_fraction_to_draw == .1
    assert len(simple_eor_bravo.rounds) == 0
    assert len(simple_eor_bravo.sub_audits) == 1
    assert simple_eor_bravo.get_risk_level() is None
    simple_eor_bravo.rounds.append(10)
    simple_eor_bravo.stopped = True
    assert simple_eor_bravo.next_sample_size() == 10
    assert simple_eor_bravo.next_sample_size(verbose=True) == (10, 0, 1)


def test_eor_bravo_kmins():
    contest = Contest(100000, {'A': 60000, 'B': 40000}, 1, ['A'], ContestType.MAJORITY)
    eor_bravo = EOR_BRAVO(.1, .1, contest)
    eor_bravo.compute_min_winner_ballots(eor_bravo.sub_audits['A-B'], [100, 200, 400])

    # From existing software
    assert eor_bravo.sub_audits['A-B'].min_winner_ballots == [61, 116, 226]


def test_min_sample_size():
    contest1 = Contest(100000, {'A': 60000, 'B': 40000}, 1, ['A'], ContestType.MAJORITY)
    eor_bravo1 = EOR_BRAVO(.1, .1, contest1)
    contest2 = Contest(100000, {'A': 51000, 'B': 49000}, 1, ['A'], ContestType.MAJORITY)
    eor_bravo2 = EOR_BRAVO(.05, .05, contest2)

    assert abs(eor_bravo1.sub_audits['A-B'].min_sample_size - 13) <= 2
    assert abs(eor_bravo2.sub_audits['A-B'].min_sample_size - 879) <= 40


def test_eor_bravo_first_round_estimate():
    contest1 = Contest(100000, {'A': 60000, 'B': 40000}, 1, ['A'], ContestType.MAJORITY)
    eor_bravo1 = EOR_BRAVO(.1, .1, contest1)
    contest2 = Contest(100000, {'A': 51000, 'B': 49000}, 1, ['A'], ContestType.MAJORITY)
    eor_bravo2 = EOR_BRAVO(.1, .1, contest2)
    contest3 = Contest(10000000, {'A': 5040799, 'B': 10000000 - 5040799}, 1, ['A'], ContestType.MAJORITY)
    eor_bravo3 = EOR_BRAVO(.1, 1.0, contest3)

    assert abs(eor_bravo1.next_sample_size() - 342) <= 15
    assert abs(eor_bravo2.next_sample_size() - 35707) <= 100
    assert abs(eor_bravo3.next_sample_size() - 214389) <= 300


def test_eor_bravo_second_round_estimate():
    contest1 = Contest(100000, {'A': 60000, 'B': 40000}, 1, ['A'], ContestType.MAJORITY)
    eor_bravo1 = EOR_BRAVO(.1, .1, contest1)
    eor_bravo1.compute_min_winner_ballots(eor_bravo1.sub_audits['A-B'], [100])
    eor_bravo1.sample_ballots['A'].append(54)
    eor_bravo1.sample_ballots['B'].append(100 - 54)
    contest2 = Contest(4504975 + 4617886, {'Trump': 4617886, 'Clinton': 4504975}, 1, ['Trump'], ContestType.PLURALITY)
    eor_bravo2 = EOR_BRAVO(.1, 1.0, contest2)
    eor_bravo2.compute_min_winner_ballots(eor_bravo2.sub_audits['Trump-Clinton'], [45081])
    eor_bravo2.sample_ballots['Trump'].append(22634)
    eor_bravo2.sample_ballots['Clinton'].append(45081 - 22634)

    assert abs(eor_bravo1.next_sample_size() - 473) <= 10
    assert abs(eor_bravo2.next_sample_size() - 160200) <= 300


def test_execute_round_eor_bravo():
    contest = Contest(100000, {'A': 60000, 'B': 40000}, 1, ['A'], ContestType.MAJORITY)
    eor_bravo = EOR_BRAVO(.1, .1, contest)
    assert not eor_bravo.execute_round(100, {'A': 57, 'B': 43})
    assert not eor_bravo.stopped
    assert eor_bravo.sample_ballots['A'] == [57]
    assert eor_bravo.sample_ballots['B'] == [43]
    assert not eor_bravo.sub_audits['A-B'].stopped
    assert eor_bravo.rounds == [100]
    assert not eor_bravo.execute_round(200, {'A': 112, 'B': 88})
    assert not eor_bravo.stopped
    assert eor_bravo.sample_ballots['A'] == [57, 112]
    assert eor_bravo.sample_ballots['B'] == [43, 88]
    assert not eor_bravo.sub_audits['A-B'].stopped
    assert eor_bravo.rounds == [100, 200]
    assert eor_bravo.execute_round(400, {'A': 226, 'B': 174})
    assert eor_bravo.stopped
    assert eor_bravo.sample_ballots['A'] == [57, 112, 226]
    assert eor_bravo.sample_ballots['B'] == [43, 88, 174]
    assert eor_bravo.sub_audits['A-B'].stopped
    assert eor_bravo.rounds == [100, 200, 400]
    assert eor_bravo.get_risk_level() < 0.1
