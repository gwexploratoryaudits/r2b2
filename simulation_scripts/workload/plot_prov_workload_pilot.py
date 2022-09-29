"""Generates plots for the Providence workload sims."""

import matplotlib.pyplot as plt
import numpy as np
plt.rcParams['mathtext.fontset'] = 'stix'
plt.rcParams['font.family'] = 'STIXGeneral'

from r2b2.simulator import DBInterface
from r2b2.simulator import histogram
from r2b2.tests.util import parse_election
from r2b2.contest import Contest
from r2b2.contest import ContestType



election = parse_election('data/2020_presidential/2020_presidential.json')

if __name__ == '__main__':
    db = DBInterface(port=27018,user='reader', pwd='icanread')

    contest_name = "School Construction and Renovation Projects"
    tally = {'Approve' : 2391, 'Reject' : 1414}
    reported_winner = max(tally, key=tally.get)
    winner_votes = tally[reported_winner]
    total_relevant = sum(tally.values())
    loser_votes = total_relevant - winner_votes
    margin = (winner_votes / total_relevant) - (loser_votes / total_relevant)
    # Make the contest object
    contest = Contest(total_relevant,
                                tally,
                                num_winners=1,
                                reported_winners=[reported_winner],
                                contest_type=ContestType.PLURALITY)
 
    audit_id = db.audit_lookup('minerva2', 0.1)
    reported_id = db.contest_lookup(contest, qapp={'name': "Pilot"})
    #election.contests[contest], qapp={'description': '2020 Presidential', 'name': contest})

    numbals = []
    numrounds = []
    ps = [.05,.1,.15,.2,.25,.3,.35,.4,.45,.5,.55,.6,.65,.7,.75,.8,.85,.9,.95]
    plotps = []
    for p in ps:
        sprob_sim = db.db.simulations.find_one({
            'reported': reported_id,
            'underlying': 'reported',
            'audit': audit_id,
            'description': 'prov pilot workload',
            'invalid_ballots': True,
            'sample_sprob':p,
            'max_rounds': 100
        })

        # now get the relevant pieces of information we want for this simulation
        # for right now that includes:
        # 1. the expected number of rounds (average num rounds)
        # 2. expected number of ballots (average num ballots)
        if sprob_sim is None:
            continue # whoops forgot .1 but that's ok would not have all stopped anyhow
        sprob_analysis = sprob_sim['analysis']

        # 1. the expected number of rounds (average num rounds)
        curnumbals = sprob_analysis['asn']

        # 2. expected number of ballots (average num ballots)
        sprobs = sprob_analysis['sprob_by_round']
        if -1 not in sprobs:
            # for some of the lower stopping probability audits, some of the audits did not finish
            continue


        numbals.append(curnumbals)#adding this from step 1 down here in case step 2 fails and ocntineus
        plotps.append(p)


        last = sprobs.index(-1)
        curnumrounds = 0
        r = 1
        for sprob in sprobs:
            if sprob == -1:
                break
            curnumrounds += r * sprob
            r += 1
        numrounds.append(curnumrounds)

# plot the cost for each round schedule parameter p 
# (the round schedule's constant stopping probability)

# workload model parameters:
balcost = 1
roundcost = 10

# compute expected costs for each round schedule (parameterized by p):
numbals = np.array(numbals)
numrounds = np.array(numrounds)
print(numbals)
print(numrounds)
costs = balcost * numbals + roundcost * numrounds

font = {'size'   : 17}
plt.rc('font', **font)
plt.plot(plotps,np.array(costs)/1000,linestyle='--', marker='o', color='b')
plt.xlabel('Stopping Probability, p')
plt.ylabel('Expected Cost (x$10^3$)')
plt.tight_layout()
plt.show()


