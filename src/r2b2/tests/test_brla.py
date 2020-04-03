import pytest

import r2b2.tests.util as util
from r2b2.brla import BayesianRLA as BRLA

default_contest = util.generate_contest(100)


def test_simple_brla():
    simplebrla = BRLA(0.1, 0.2, default_contest)
    assert simplebrla.alpha == 0.1
    assert simplebrla.beta == 0.0
    assert simplebrla.max_fraction_to_draw == 0.2
    assert not simplebrla.replacement
    assert simplebrla.contest is default_contest
    simplebrla.rounds.append(20)
    assert simplebrla.stopping_condition(20)
    assert not simplebrla.stopping_condition(0)
    test_min_winner_ballots = simplebrla.next_min_winner_ballots(20)
    assert test_min_winner_ballots >= 10
    assert test_min_winner_ballots <= 20
    # FIXME: Following tests simply verify that the distribution functions do not modify the brla
    # because it is without replacement
    simplebrla.current_dist_null(18)
    simplebrla.current_dist_reported(18)
    assert simplebrla.distribution_null == [1.0]
    assert simplebrla.distribution_reported_tally == [1.0]
    assert len(simplebrla.risk_schedule) == 0
    assert len(simplebrla.stopping_prob_schedule) == 0


def test_exceptions():
    simplebrla = BRLA(0.1, 0.2, default_contest)
    with pytest.raises(Exception):
        simplebrla.stopping_condition(10)
    with pytest.raises(ValueError):
        simplebrla.compute_min_winner_ballots([])
    with pytest.raises(ValueError):
        simplebrla.compute_min_winner_ballots([0, 1])
    with pytest.raises(ValueError):
        simplebrla.compute_min_winner_ballots([10, 5])
    with pytest.raises(ValueError):
        simplebrla.compute_min_winner_ballots([100])
