import pytest

import r2b2.tests.util as util
from r2b2.audit import Audit
from r2b2.contest import Contest

default_contest = util.generate_contest(100)


class SimpleAudit(Audit):
    """For testing purposes only."""
    def __init__(self, alpha: float, beta: float, max_fraction_to_draw: int,
                 replacement: bool, contest: Contest):
        super().__init__(alpha, beta, max_fraction_to_draw, replacement,
                         contest)

    def get_min_sample_size(self):
        return 5

    def next_sample_size(self):
        return 20

    def stopping_condition(self, votes_for_winner: int) -> bool:
        return True

    def next_min_winner_ballots(self):
        return 10

    def compute_risk(self):
        return 0.1

    def compute_min_winner_ballots(self):
        return 60

    def compute_all_min_winner_ballots(self):
        return [1, 2, 3, 4]


def test_simple_audit():
    """Tests creation of a basic Audit object."""
    simpleaudit1 = SimpleAudit(0.1, 0.05, 0.1, True, default_contest)
    assert simpleaudit1.alpha == 0.1
    assert simpleaudit1.beta == 0.05
    assert simpleaudit1.max_fraction_to_draw == 0.1
    assert simpleaudit1.replacement
    assert simpleaudit1.contest is default_contest
    assert simpleaudit1.min_sample_size == 1
    simpleaudit1.min_sample_size = simpleaudit1.get_min_sample_size()
    assert simpleaudit1.min_sample_size == 5
    assert simpleaudit1.next_sample_size() == 20
    assert simpleaudit1.stopping_condition(10)
    assert simpleaudit1.next_min_winner_ballots() == 10
    assert simpleaudit1.compute_risk() == 0.1
    assert simpleaudit1.compute_min_winner_ballots() == 60


def test_simple_audit_execution():
    """Test basic properties of updating attributes."""
    simpleaudit1 = SimpleAudit(0.1, 0.05, 0.5, True, default_contest)
    simpleaudit2 = SimpleAudit(0.1, 0.05, 0.1, False, default_contest)
    for i in range(1, 6):
        simpleaudit1.rounds.append(10 * i)
        simpleaudit1.current_dist_null((10 * i) - 5)
        assert len(simpleaudit1.risk_schedule) == i
        assert simpleaudit1.risk_schedule[i - 1] >= 0.0
        assert simpleaudit1.risk_schedule[i - 1] <= 1.0
        assert len(simpleaudit1.distribution_null) == (10 * i) - 4
        simpleaudit1.current_dist_reported((10 * i) - 5)
        assert len(simpleaudit1.stopping_prob_schedule) == i
        assert simpleaudit1.stopping_prob_schedule[i - 1] >= 0.0
        assert simpleaudit1.stopping_prob_schedule[i - 1] <= 1.0
        assert len(simpleaudit1.distribution_reported_tally) == (10 * i) - 4
        simpleaudit2.rounds.append(10 * i)
        simpleaudit2.current_dist_null((10 * i) - 5)
        assert len(simpleaudit2.risk_schedule) == i
        assert simpleaudit2.risk_schedule[i - 1] >= 0.0
        assert simpleaudit2.risk_schedule[i - 1] <= 1.0
        assert len(simpleaudit2.distribution_null) == (10 * i) - 4
        simpleaudit2.current_dist_reported((10 * i) - 5)
        assert len(simpleaudit2.stopping_prob_schedule) == i
        assert simpleaudit2.stopping_prob_schedule[i - 1] >= 0.0
        assert simpleaudit2.stopping_prob_schedule[i - 1] <= 1.0
        assert len(simpleaudit2.distribution_reported_tally) == (10 * i) - 4


def test_initialization_errors():
    """Tests exceptions are raised correctly by __init__()."""
    # alpha TypeError tests
    with pytest.raises(TypeError):
        SimpleAudit('a', 0.05, 0.1, True, default_contest)
    with pytest.raises(TypeError):
        SimpleAudit(True, 0.05, 0.1, True, default_contest)
    with pytest.raises(TypeError):
        SimpleAudit(22, 0.05, 0.1, True, default_contest)
    # beta TypeError tests
    with pytest.raises(TypeError):
        SimpleAudit(0.1, 'b', 0.1, True, default_contest)
    with pytest.raises(TypeError):
        SimpleAudit(0.1, False, 0.1, True, default_contest)
    with pytest.raises(TypeError):
        SimpleAudit(0.1, -3, 0.1, True, default_contest)
    # max_fraction_to_draw TypeError tests
    with pytest.raises(TypeError):
        SimpleAudit(0.1, 0.05, 'c', True, default_contest)
    with pytest.raises(TypeError):
        SimpleAudit(0.1, 0.05, 2, True, default_contest)
    with pytest.raises(TypeError):
        SimpleAudit(0.1, 0.5, False, True, default_contest)
    # replacement TypeError tests
    with pytest.raises(TypeError):
        SimpleAudit(0.1, 0.05, 0.1, 10, default_contest)
    with pytest.raises(TypeError):
        SimpleAudit(0.1, 0.05, 0.1, 'd', default_contest)
    # contest TypeError tests:
    with pytest.raises(TypeError):
        SimpleAudit(0.1, 0.05, 0.1, True, 'Contest')
    with pytest.raises(TypeError):
        SimpleAudit(0.1, 0.05, 0.1, True, 20)
    with pytest.raises(TypeError):
        SimpleAudit(0.1, 0.05, 0.1, True, None)
    # alpha ValueError tests
    with pytest.raises(ValueError):
        SimpleAudit(-1.5, 0.05, 0.1, True, default_contest)
    with pytest.raises(ValueError):
        SimpleAudit(2.4, 0.05, 0.1, True, default_contest)
    # beta ValueError tests
    with pytest.raises(ValueError):
        SimpleAudit(0.1, -2.5, 0.1, True, default_contest)
    with pytest.raises(ValueError):
        SimpleAudit(0.1, 5.3, 0.1, True, default_contest)
    # max_fraction_to_draw ValueError tests
    with pytest.raises(ValueError):
        SimpleAudit(0.1, 0.05, -0.1, True, default_contest)
    with pytest.raises(ValueError):
        SimpleAudit(0.1, 0.05, 1.5, True, default_contest)


def test_get_interval():
    # TODO: Test _get_interval gets correct intervals
    pass


def test_current_dist_null():
    # TODO: Test distribution function (with and without replacement)
    pass


def test_current_dist_reported():
    # TODO: Test distribution function (with and without replacement)
    pass
