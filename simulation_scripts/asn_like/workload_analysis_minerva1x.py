"""
Adds the ASN of an audit to its analysis in the simulation database.

Computes ASN using the audits with the underlying distribution same as reported.

Assumes that audits after 'considered_rounds' proceed to a full hand count 
(thus sampling all relevant contest ballots).
"""

import matplotlib.pyplot as plt

from r2b2.simulator import DBInterface
from r2b2.simulator import histogram
from r2b2.tests.util import parse_election

election = parse_election('../data/2020_presidential/2020_presidential.json')

if __name__ == '__main__':
    db = DBInterface(port=27017,user='sarah', pwd='haras')
    #counter = 0
    for contest in election.contests:
        #if counter == 1:
        #    break
        #counter += 1
        audit_id = db.audit_lookup('minerva', 0.1)
        reported_id = db.contest_lookup(election.contests[contest], qapp={'description': '2020 Presidential'})
        winner_prop = election.contests[contest].tally[election.contests[contest].reported_winners[0]] / sum(
            election.contests[contest].tally.values())
        margin = winner_prop - (1.0 - winner_prop)
        sprob_sim = db.db.simulations.find_one({
            'reported': reported_id,
            'underlying': 'reported',
            'audit': audit_id,
            'description': 'Prov paper: Minerva workload',
            'invalid_ballots': True,
            'sample_mult':1.0,
        })
        if sprob_sim is None:
            # For several low margin states, we didn't run simulations
            continue
        sim_id = sprob_sim['_id']
        analysis = sprob_sim['analysis']
        trials = db.trial_lookup(sprob_sim['_id']) #this function is slowwwww
        # Five empty lists, a list for each round to be filled with the number of ballots sampled for each audit
        sampled = [ [] for _ in range(5) ] 
        #countertwo = 0
        for trial in trials:
            #print(trial)
            #countertwo += 1
            #if countertwo == 15:
            #    break
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
