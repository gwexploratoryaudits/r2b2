"""
Go through the sprob simulations (multiround) that I did and redo the analysis
by computing the stopping probability by round as well as how many
audits remained in each round.
"""

import matplotlib.pyplot as plt

from r2b2.simulator import DBInterface
from r2b2.simulator import histogram
from r2b2.tests.util import parse_election

election = parse_election('../data/2020_presidential/2020_presidential.json')

if __name__ == '__main__':
    db = DBInterface(port=27020,user='sarah', pwd='haras')
    sprob_analyses = []
    margins = []

    max_rounds = 5

    for contest in election.contests:
        print(contest)
        audit_id = db.audit_lookup('minerva', 0.1)
        reported_id = db.contest_lookup(election.contests[contest], qapp={'description': '2020 Presidential'})
        sprob_sim = db.db.simulations.find_one({
            'reported': reported_id,
            'underlying': 'reported',
            'audit': audit_id,
            'description': 'Multi round Minerva (90% then 1.5x)',
            'invalid_ballots': True,
            'sample_mult':1.5,
            'max_rounds': max_rounds
        })

        if sprob_sim is None:
            # For several low margin states, we didn't run simulations
            continue

        analysis = sprob_sim['analysis']

        # new analysis code begins

        num_trials = 0
        stopped = 0
        rounds_stopped = []

        sim_id = sprob_sim['_id']
        trials = db.trial_lookup(sim_id)

        # count up the stopping information from all the trials...
        # here, compute the analysis of just the first 10^4 trials
        counter = 0
        for trial in trials:
            counter += 1
            if counter > 10**4:
                break
            num_trials += 1
            if trial['stop']:
                stopped += 1
                rounds_stopped.append(trial['round'])

        # Find stopping probability for each round
        sprob_by_round = [0]*max_rounds
        stopped_by_round = [0]*max_rounds
        remaining_by_round = [0]*(max_rounds+1)
        remaining_by_round[0] = num_trials #first round has all remaining
        for r in range(1,max_rounds+1):
            stopped_this_round = rounds_stopped.count(r)
            stopped_by_round[r-1] = stopped_this_round
            if remaining_by_round[r-1] != 0:
                sprob_by_round[r-1] =stopped_this_round/remaining_by_round[r-1]
            else:
                sprob_by_round[r-1] = -1
            remaining_by_round[r] = remaining_by_round[r-1]-stopped_this_round

        tentofourthanalysis = { 
            'sprob': stopped / num_trials,
            'sprob_by_round': sprob_by_round,
            'remaining_by_round': remaining_by_round,
            'stopped_by_round': stopped_by_round
        }

        analysis['10^4 analysis'] = tentofourthanalysis

        # Update simulation entry to include analysis
        db.update_analysis(sim_id, analysis)

        print(analysis)
















