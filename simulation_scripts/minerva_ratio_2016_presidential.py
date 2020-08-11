import json

from r2b2.simulator import DBInterface
from r2b2.tests.util import parse_election

election = parse_election('data/2016_presidential.json')

if __name__ == '__main__':
    db = DBInterface(user='reader', pwd='icanread')
    ratio_results = {}
    
    for contest in election.contests:
        if contest == 'Michigan' or contest == 'New Hampshire':
            continue

        audit_id = db.audit_lookup('minerva', 0.1)
        reported_id = db.contest_lookup(election.contests[contest], qapp={'description': '2016 Presidential'})
        tied_sim  = db.db.simulations.find_one({'reported': reported_id, 'underlying': 'tie', 'audit': audit_id, 'description': 'One round Minerva with given sample size (from PV MATLAB)'})
        sprob_sim = db.db.simulations.find_one({'reported': reported_id, 'underlying': 'reported', 'audit': audit_id, 'description': 'Stopping Probability 90%: One round Minerva with given sample size (from PV MATLAB)'})

        risk = tied_sim['analysis']
        sprob = sprob_sim['analysis']

        ratio_results[contest] = {'computed_risk': risk, 'computed_sprob': sprob, 'ratio': sprob/risk, '1/alpha': 10}
    
    with open('data/minerva_one_round_sprob_risk_ratio.json', 'w') as out:
        json.dump(ratio_results, out, indent=4)
