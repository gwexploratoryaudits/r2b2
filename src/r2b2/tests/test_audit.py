import pytest

from r2b2.audit import Audit
from r2b2.contest import Contest


class SimpleAudit(Audit):
    """For testing purposes only."""

    def __init__(self, alpha: float, beta: float, max_fraction_to_draw: int, replacement: bool, contest: Contest):
        super().__init__(alpha, beta, max_fraction_to_draw, replacement, contest)

    def compute_risk(self):
        return 0.1

    def compute_sample_size(self):
        return 100


def test_simple_audit():
    simpleaudit1 = SimpleAudit(0.1, 0.05, 0.1, True, None)
    assert simpleaudit1.alpha == 0.1
    assert simpleaudit1.beta == 0.05
    assert simpleaudit1.max_fraction_to_draw == 0.1
    assert simpleaudit1.replacement
    assert simpleaudit1.contest is None
    assert simpleaudit1.compute_risk() == 0.1
    assert simpleaudit1.compute_sample_size() == 100


def test_initialization_errors():
    # alpha TypeError tests
    with pytest.raises(TypeError):
        SimpleAudit('a', 0.05, 0.1, True, None)
    with pytest.raises(TypeError):
        SimpleAudit(True, 0.05, 0.1, True, None)
    with pytest.raises(TypeError):
        SimpleAudit(22, 0.05, 0.1, True, None)
    # beta TypeError tests
    with pytest.raises(TypeError):
        SimpleAudit(0.1, 'b', 0.1, True, None)
    with pytest.raises(TypeError):
        SimpleAudit(0.1, False, 0.1, True, None)
    with pytest.raises(TypeError):
        SimpleAudit(0.1, -3, 0.1, True, None)
    # max_fraction_to_draw TypeError tests
    with pytest.raises(TypeError):
        SimpleAudit(0.1, 0.05, 'c', True, None)
    with pytest.raises(TypeError):
        SimpleAudit(0.1, 0.05, 2, True, None)
    with pytest.raises(TypeError):
        SimpleAudit(0.1, 0.5, False, True, None)
    # replacement TypeError tests
    with pytest.raises(TypeError):
        SimpleAudit(0.1, 0.05, 0.1, 10, None)
    with pytest.raises(TypeError):
        SimpleAudit(0.1, 0.05, 0.1, 'd', None)
    # alpha ValueError tests
    with pytest.raises(ValueError):
        SimpleAudit(-1.5, 0.05, 0.1, True, None)
    with pytest.raises(ValueError):
        SimpleAudit(2.4, 0.05, 0.1, True, None)
    # beta ValueError tests
    with pytest.raises(ValueError):
        SimpleAudit(0.1, -2.5, 0.1, True, None)
    with pytest.raises(ValueError):
        SimpleAudit(0.1, 5.3, 0.1, True, None)
    # max_fraction_to_draw ValueError tests
    with pytest.raises(ValueError):
        SimpleAudit(0.1, 0.05, -0.1, True, None)
    with pytest.raises(ValueError):
        SimpleAudit(0.1, 0.05, 1.5, True, None)
