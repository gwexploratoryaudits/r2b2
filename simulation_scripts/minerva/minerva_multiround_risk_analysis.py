"""
Go through the risk simulations (multiround) that I did and redo the analysis
by computing the stopping probability by round as well as how many
audits remained in each round.
"""

import matplotlib.pyplot as plt

from r2b2.simulator import DBInterface
from r2b2.simulator import histogram
from r2b2.tests.util import parse_election

election = parse_election('data/2020_presidential/2020_presidential.json')

if __name__ == '__main__':
    db = DBInterface(port=27020,user='sarah', pwd='haras')
    risks = []
    margins = []

    max_rounds = 5

    for contest in election.contests:
        print(contest)
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

        risks.append(tied_sim['analysis'])

        # new analysis code begins

        num_trials = 0
        stopped = 0
        rounds_stopped = []

        sim_id = tied_sim['_id']
        trials = db.trial_lookup(sim_id)

        # count up the stopping information from all the trials...
        for trial in trials:
            num_trials += 1
            if trial['stop']:
                stopped += 1
                rounds_stopped.append(trial['round'])

        # Find risk for each round
        risk_by_round = [0]*max_rounds
        stopped_by_round = [0]*max_rounds
        remaining_by_round = [0]*(max_rounds+1)
        remaining_by_round[0] = num_trials #first round has all remaining
        for r in range(1,max_rounds+1):
            stopped_this_round = rounds_stopped.count(r)
            stopped_by_round[r-1] = stopped_this_round
            if remaining_by_round[r-1] is not 0:
                risk_by_round[r-1] = stopped_this_round/remaining_by_round[r-1]
                print("stopped in round "+str(r-1)+": "+str(stopped_this_round))
                print("remaining in round "+str(r-1)+": "+str(remaining_by_round[r-1]))
            else:
                risk_by_round[r-1] = -1
            remaining_by_round[r] = remaining_by_round[r-1] - stopped_this_round

        analysis = { 
            'risk': stopped / num_trials,
            'risk_by_round': risk_by_round,
            'remaining_by_round': remaining_by_round,
            'stopped_by_round': stopped_by_round
        }

        # Update simulation entry to include analysis
        db.update_analysis(sim_id, analysis)

        print(analysis)

