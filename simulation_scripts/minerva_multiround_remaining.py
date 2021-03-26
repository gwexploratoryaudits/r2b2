"""
Computes the average number of remaining audits in each round
of the minerva multiround simulation
"""
import matplotlib.pyplot as plt

from r2b2.simulator import DBInterface
from r2b2.simulator import histogram
from r2b2.tests.util import parse_election

election = parse_election('data/2020_presidential/2020_presidential.json')

if __name__ == '__main__':
    db = DBInterface(port=27020,user='reader', pwd='icanread')
    risks = []
    sprobs = []
    margins = []

    max_rounds = 5

    for contest in election.contests:
        audit_id = db.audit_lookup('minerva', 0.1)
        reported_id = db.contest_lookup(election.contests[contest], qapp={'description': '2020 Presidential'})
        tied_sim = db.db.simulations.find_one({
            'reported': reported_id,
            'underlying': 'tie',
            'audit': audit_id,
            'description': 'Multi round Minerva (90% then 1.5x)',
            'invalid_ballots': True,
            'sample_mult':1.5,
            'max_rounds': max_rounds
        })
        if tied_sim is None:
            # For several low margin states, we didn't run simulations
            continue
        sprob_sim = db.db.simulations.find_one({
            'reported': reported_id,
            'underlying': 'reported',
            'audit': audit_id,
            'description': 'Multi round Minerva (90% then 1.5x)',
            'invalid_ballots': True,
            'sample_mult':1.5,
            'max_rounds': max_rounds
        })

        risks.append(tied_sim['analysis']['remaining_by_round'])

        sprobs.append(sprob_sim['analysis']['remaining_by_round'])

        winner_prop = election.contests[contest].tally[election.contests[contest].reported_winners[0]] / sum(
            election.contests[contest].tally.values())
        margins.append(winner_prop - (1.0 - winner_prop))

    # Risks
    print("\nRisks (average remaining for each round)")
    for r in range (1,max_rounds+2):
        remaining_for_this_round = []
        for s in range(len(risks)):
            remaining_for_this_round.append(risks[s][r-1])
        rem = sum(remaining_for_this_round) / len(remaining_for_this_round)
        print(str(r)+" "+str(rem))

    # Sprobs
    print("\nSprobs (average remaining for each round)")
    for r in range (1,max_rounds+2):
        remaining_for_this_round = []
        for s in range(len(sprobs)):
            remaining_for_this_round.append(sprobs[s][r-1])
        rem = sum(remaining_for_this_round) / len(remaining_for_this_round)
        print(str(r)+" "+str(rem))
