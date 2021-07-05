import json
import math

#import pytest
from click.testing import CliRunner

from r2b2.cli import cli
from r2b2.contest import Contest
from r2b2.contest import ContestType
from r2b2.minerva2 import Minerva2
from r2b2.tests import util as util

def test_minerva2_kmins():
    contest = Contest(100000, {'A': 60000, 'B': 40000}, 1, ['A'], ContestType.MAJORITY)
    minerva2 = Minerva2(.1, .1, contest)
    minerva2.compute_min_winner_ballots(minerva2.sub_audits['A-B'], 100)

    # From existing software
    assert minerva2.sub_audits['A-B'].min_winner_ballots == [58]


# during development... manually run tests here
test_minerva2_kmins()
