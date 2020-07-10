import pytest

from r2b2.contest import Contest
from r2b2.contest import ContestType
from r2b2.minerva import Minerva
from r2b2.sprob import Sprob


def test_simple_sprob():
    contest = Contest(100000, {'A': 80000, 'B': 20000}, 1, ['A'], ContestType.MAJORITY)
    round_sched = [10, 100, 200, 1000]
    kmin_sched = [10, 80, 155, 600]
    reported_sprob_obj = Sprob(round_sched, kmin_sched, contest)
    calc_sprobs = reported_sprob_obj.compute_sprobs()

    # From existing software
    goal_sprobs = [0.10737418240000005, 0.4789618496982295, 0.2758846676307867, 0.13777930027088128]
    for i in range(len(goal_sprobs)):
        assert abs(goal_sprobs[i] - calc_sprobs[i]) < .0000001
    assert abs(reported_sprob_obj.expectation() - 241.92616) < .0001


def test_sprob_minerva_agreement():
    contest_reported = Contest(100000, {'A': 60000, 'B': 40000}, 1, ['A'], ContestType.MAJORITY)
    contest_tied = Contest(100000, {'A': 50000, 'B': 50000}, 1, ['A'], ContestType.MAJORITY)
    minerva = Minerva(.1, .1, contest_reported)
    round_sched = [100, 200, 400]
    minerva.compute_min_winner_ballots(round_sched)
    kmin_sched = minerva.min_winner_ballots
    risk_sched = minerva.risk_schedule
    sprob_sched = minerva.stopping_prob_schedule
    reported_sprob_obj = Sprob(round_sched, kmin_sched, contest_reported)
    tied_sprob_obj = Sprob(round_sched, kmin_sched, contest_tied)
    calc_risk_sched = tied_sprob_obj.compute_sprobs()
    calc_sprob_sched = reported_sprob_obj.compute_sprobs()
    for i in range(len(sprob_sched)):
        assert abs(risk_sched[i] - calc_risk_sched[i]) < .0000001
        assert abs(sprob_sched[i] - calc_sprob_sched[i]) < .0000001


def test_exceptions():
    contest = Contest(100000, {'A': 80000, 'B': 20000}, 1, ['A'], ContestType.MAJORITY)
    with pytest.raises(Exception):
        sprob = Sprob([], [], contest)
        sprob.compute_sprobs()
    with pytest.raises(Exception):
        sprob = Sprob([10, 11], [10], contest)
        sprob.compute_sprobs()
    with pytest.raises(ValueError):
        sprob = Sprob([0], [0], contest)
        sprob.compute_sprobs()
    with pytest.raises(ValueError):
        sprob = Sprob([1], [0], contest)
        sprob.compute_sprobs()
    with pytest.raises(ValueError):
        sprob = Sprob([10, 10], [8, 9], contest)
        sprob.compute_sprobs()
    with pytest.raises(ValueError):
        sprob = Sprob([1], [2], contest)
        sprob.compute_sprobs()
    with pytest.raises(ValueError):
        sprob = Sprob([10, 11], [10, 12], contest)
        sprob.compute_sprobs()
