import pytest

from r2b2.audit import Audit
from r2b2.contest import Contest


class SimpleAudit(Audit):
    """For testing purposes only."""

    def __init__(self, alpha: float, beta: float, max_to_draw: int, replacement: bool, contest: Contest):
        super().__init__(alpha, beta, max_to_draw, replacement, contest)

    def compute_risk(self):
        return 0.1

    def compute_sample_size(self):
        return 100


def test_simple_audit():
    simpleaudit1 = SimpleAudit(0.1, 0.05, 200, True, None)
    assert simpleaudit1.alpha == 0.1
    assert simpleaudit1.beta == 0.05
    assert simpleaudit1.max_to_draw == 200
    assert simpleaudit1.replacement
    assert simpleaudit1.contest is None
    assert simpleaudit1.compute_risk() == 0.1
    assert simpleaudit1.compute_sample_size() == 100


def test_initialization_errors():
    with pytest.raises(TypeError):
        SimpleAudit('a', 0.05, 200, True, None)
    with pytest.raises(TypeError):
        SimpleAudit(True, 0.05, 200, True, None)
    with pytest.raises(TypeError):
        SimpleAudit(22, 0.05, 200, True, None)
    with pytest.raises(TypeError):
        SimpleAudit(0.1, 'b', 200, True, None)
    with pytest.raises(TypeError):
        SimpleAudit(0.1, False, 200, True, None)
    with pytest.raises(TypeError):
        SimpleAudit(0.1, -3, 200, True, None)
    with pytest.raises(TypeError):
        SimpleAudit(0.1, 0.05, 'c', True, None)
    with pytest.raises(TypeError):
        SimpleAudit(0.1, 0.05, 2.5, True, None)
    with pytest.raises(TypeError):
        SimpleAudit(0.1, 0.5, False, True, None)
    with pytest.raises(TypeError):
        SimpleAudit(0.1, 0.05, 200, 10, None)
    with pytest.raises(TypeError):
        SimpleAudit(0.1, 0.05, 200, 'd', None)
    with pytest.raises(ValueError):
        SimpleAudit(-1.5, 0.05, 200, True, None)
    with pytest.raises(ValueError):
        SimpleAudit(2.4, 0.05, 200, True, None)
    with pytest.raises(ValueError):
        SimpleAudit(0.1, -2.5, 200, True, None)
    with pytest.raises(ValueError):
        SimpleAudit(0.1, 5.3, 200, True, None)
