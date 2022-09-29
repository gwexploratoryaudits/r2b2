"""
SO BRAVO
"""

import matplotlib.pyplot as plt

from r2b2.simulator import DBInterface
from r2b2.simulator import histogram
from r2b2.tests.util import parse_election

import sys

election = parse_election('../../data/2020_presidential/2020_presidential.json')

if __name__ == '__main__':
    db = DBInterface(port=27018,user='sarah', pwd='haras')
    #counter = 0
    #if counter == 1:
    #    break
    #counter += 1
    if len(sys.argv) < 2:
        print('Provide a state as command line argument')
        exit()
    contest = sys.argv[1]
    print('Doing the analysis for', contest)
    for p in [.05,.1,.15,.2,.3,.4,.5,.6,.7,.8,.9,.25,.35,.45,.55,.65,.75,.85,.95]:
        #contest = 'Texas'
        audit_id = db.audit_lookup('so_bravo', 0.1)
        print(audit_id)
        reported_id = db.contest_lookup(election.contests[contest], qapp={'description': '2020 Presidential'})
        print(reported_id)
        winner_prop = election.contests[contest].tally[election.contests[contest].reported_winners[0]] / sum(
            election.contests[contest].tally.values())
        margin = winner_prop - (1.0 - winner_prop)
        sprob_sim = db.db.simulations.find_one({
            'reported': reported_id,
            'underlying': 'reported',
            'audit': audit_id,
            'description': 'so bravo workload',
            'sample_sprob':p
        })

        if sprob_sim is None:
            # For several low margin states, we didn't run simulations
            print('No sim for this state:',contest)
            continue

        print('Got the sim entry')

        sim_id = sprob_sim['_id']
        analysis = sprob_sim['analysis']
        # Five empty lists, a list for each round to be filled with the number of ballots sampled for each audit
        trials = db.db.trials.find({'simulation': sprob_sim['_id']})
        print('Got the trials, now analyzing')
        sampled = [ [] for _ in range(5) ] 
        for trial in trials:
            # Now instead of using just ASN, we are looking at the average number
            # of ballots sampled cumulatively through each round...

            # The first round is always drawn
            sampled[0].append(trial['relevant_sample_size_sched'][0])

            # Then subsequent rounds may require more ballots for some audits
            for i in range(1,len(sampled)):
                if len(trial['relevant_sample_size_sched']) > i: 
                    # If this audit went this far, we add this cumulative sample to our list
                    sampled[i].append(trial['relevant_sample_size_sched'][i])
                else:
                    # Otherwise, the number of ballots sampled stays the same (no change)
                    sampled[i].append(sampled[i - 1][-1])

        # Compute averages from these lists
        avg_sampled = [0]*5
        for i in range(len(avg_sampled)):
            avg_sampled[i] = sum(sampled[i]) / len(sampled[i])

        # Add avg_sampled to the analysis dict
        #print(avg_sampled)
        analysis['avg_sampled_by_round'] = avg_sampled

        # Update simulation entry to include analysis
        db.update_analysis(sim_id, analysis)
