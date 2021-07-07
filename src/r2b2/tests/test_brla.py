import pytest

from r2b2.brla import BayesianRLA as BRLA
from r2b2.tests import util as util

default_contest = util.generate_contest(100)


def test_simple_brla():
    simplebrla = BRLA(0.1, 0.2, default_contest)
    assert simplebrla.alpha == 0.1
    assert simplebrla.beta == 0.0
    assert simplebrla.max_fraction_to_draw == 0.2
    assert not simplebrla.replacement
    assert simplebrla.contest is default_contest
    simplebrla.rounds.append(20)
    simplebrla.sample_ballots['a'].append(20)
    assert simplebrla.stopping_condition()
    simplebrla.sample_ballots['a'][0] = 0
    assert not simplebrla.stopping_condition()
    test_min_winner_ballots = simplebrla.next_min_winner_ballots_pairwise(simplebrla.sub_audits['a-b'], 20)
    assert test_min_winner_ballots >= 10
    assert test_min_winner_ballots <= 20
    bulk_min_winner_ballots = simplebrla.compute_all_min_winner_ballots(simplebrla.sub_audits['a-b'])
    assert len(bulk_min_winner_ballots) == (20 - simplebrla.sub_audits['a-b'].min_sample_size) + 1


def test_str():
    simplebrla = BRLA(0.1, 0.2, default_contest)
    brla_str = 'BayesianRLA without replacement\n-------------------------------\n'
    brla_str += 'Risk Limit: 0.1\nMaximum Fraction to Draw: 0.2\n'
    brla_str += str(default_contest)
    assert str(simplebrla) == brla_str


def test_exceptions():
    simplebrla = BRLA(0.1, 0.2, default_contest)
    with pytest.raises(Exception):
        simplebrla.stopping_condition(10)
    with pytest.raises(ValueError):
        simplebrla.compute_min_winner_ballots(simplebrla.sub_audits['a-b'], [])
    with pytest.raises(ValueError):
        simplebrla.compute_min_winner_ballots(simplebrla.sub_audits['a-b'], [0, 1])
    with pytest.raises(ValueError):
        simplebrla.compute_min_winner_ballots(simplebrla.sub_audits['a-b'], [10, 5])
    with pytest.raises(ValueError):
        simplebrla.compute_min_winner_ballots(simplebrla.sub_audits['a-b'], [100])
    with pytest.raises(ValueError):
        simplebrla.compute_all_min_winner_ballots(simplebrla.sub_audits['a-b'], 0)
