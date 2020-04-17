import r2b2.tests.util as util
from r2b2.contest import Contest
from r2b2.contest import ContestType
from r2b2.minerva import Minerva

default_contest = util.generate_contest(100000)


def test_simple_minerva():
    simple_minerva = Minerva(.1, .1, default_contest)
    assert simple_minerva.alpha == .1
    assert simple_minerva.beta == 0.0
    assert simple_minerva.max_fraction_to_draw == .1
    assert len(simple_minerva.rounds) == 0
    assert len(simple_minerva.min_winner_ballots) == 0


def test_min_sample_size():
    contest1 = Contest(100000, {'A': 60000, 'B': 40000}, 1, ['A'], ContestType.MAJORITY)
    minerva1 = Minerva(.1, .1, contest1)
    contest2 = Contest(100000, {'A': 100000, 'B': 0}, 1, ['A'], ContestType.MAJORITY)
    minerva2 = Minerva(.05, .2, contest2)
    contest3 = Contest(100000, {'A': 51000, 'B': 49000}, 1, ['A'], ContestType.MAJORITY)
    minerva3 = Minerva(.05, .05, contest3)

    # Numbers x below satisfy: (p1 / p0)^x > 1 / alpha yet (p1 / p0)^(x-1) <= 1 / alpha.
    assert minerva1.min_sample_size == 13
    assert minerva2.min_sample_size == 5
    assert minerva3.min_sample_size == 152
