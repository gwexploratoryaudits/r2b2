import json

from r2b2.contest import Contest
from r2b2.contest import ContestType
from r2b2.minerva import Minerva

tol = 0.000001


def test_minerva_arlo():
    with open('tests/data/arlo_tests.json', 'r') as tf:
        data = json.load(tf)
        for test in data:
            contest_data = data[test]['contest']
            contest = Contest(contest_data['contest_ballots'], contest_data['tally'], contest_data['num_winners'],
                              contest_data['reported_winners'], ContestType[contest_data['contest_type']])
            if data[test]['audit_type'] != 'minerva':
                pass
            audit = Minerva(data[test]['alpha'], 1.0, contest)
            for r in data[test]['rounds']:
                round_data = data[test]['rounds'][r]
                audit.execute_round(round_data['sample_size'], round_data['sample'])

            assert audit.stopped == bool(data[test]['expected']['stopped'])
            assert abs(audit.get_risk_level() - data[test]['expected']['pvalue']) < tol
