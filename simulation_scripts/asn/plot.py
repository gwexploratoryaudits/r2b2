"""
Plots the stopping probability of each audit versus the number of ballots sampled.
"""

import matplotlib.pyplot as plt

from r2b2.simulator import DBInterface
from r2b2.simulator import histogram
from r2b2.tests.util import parse_election

election = parse_election('../data/2020_presidential/2020_presidential.json')

if __name__ == '__main__':
    db = DBInterface(port=27018,user='reader', pwd='icanread')
    margins = []
    avg_sampled_minerva_1p0 = [ [] for _ in range(5) ] 
    abs_sprob_minerva_1p0 = [ [] for _ in range(5) ] 

    # TODO other simulations
    avg_sampled_minerva_1p5 = []
    avg_sampled_eor_bravo = []
    avg_sampled_so_bravo = []

    for contest in election.contests:
        audit_id = db.audit_lookup('minerva', 0.1)
        reported_id = db.contest_lookup(election.contests[contest], qapp={'description': '2020 Presidential'})
        winner_prop = election.contests[contest].tally[election.contests[contest].reported_winners[0]] / sum(
            election.contests[contest].tally.values())
        margin = winner_prop - (1.0 - winner_prop)
        sprob_sim = db.db.simulations.find_one({
            'reported': reported_id,
            'underlying': 'reported',
            'audit': audit_id,
            'description': 'Multi round Minerva (90% then 1.0x)',
            'invalid_ballots': True,
            'sample_mult':1.0,
        })
        if sprob_sim is None:
            # For several low margin states, we didn't run simulations
            continue
        sim_id = sprob_sim['_id']
        margins.append(margin)
        analysis = sprob_sim['analysis']
        if 'avg_sampled_by_round' not in analysis.keys():
            continue
        for i in range(5):
            avg_sampled_minerva_1p0[i].append(analysis['avg_sampled_by_round'][i])
        stopped_so_far = 0
        total_to_start = analysis['remaining_by_round'][0]
        for i in range(5):
            stopped_so_far += analysis['stopped_by_round'][i]
            abs_sprob_minerva_1p0[i].append(stopped_so_far / total_to_start)

# index by margin rather than round
points_by_margin = []
for m in range(len(avg_sampled_minerva_1p0[0])):
    sprobs_for_m = []
    samnums_for_m = []
    for i in range(5):
        sprobs_for_m.append(avg_sampled_minerva_1p0[i][m])
        samnums_for_m.append(abs_sprob_minerva_1p0[i][m])
    points_by_margin.append((sprobs_for_m, samnums_for_m))

"""
for i in range(5):
    plt.plot(avg_sampled_minerva_1p0[i], abs_sprob_minerva_1p0[i], 'bo', label='Round '+str(i+1))
"""
colors= ['b','r','g','c','m']
markers = ['o','x','s','d','*']
for m in range(len(points_by_margin)):
    if m >= len(colors):
        break
    plt.plot(points_by_margin[m][0], points_by_margin[m][1], colors[m]+markers[m], label='Margin '+str(margins[m]))
title = 'Proportion of Audits that Stopped vs. Average Number of Ballots Sampled (only Minerva, 90% then 1.0x)'
plt.title(title)
plt.xlabel('Average Number of Ballots Sampled')
plt.ylabel('Proportion of Audits that Stopped')
plt.grid()
plt.legend()
plt.show()




"""


    # Plot conditional sprobs vs. margins
    colors= ['b','r','g','c','m']
    markers = ['o','x','s','d','*']
    for r in range (1,max_rounds+1-2):
        sprobs_for_this_round = [] #conditional sprobs
        absolute_sprobs_for_this_round = [] #absolute sprobs
        plot_margins = []
        for s in range(len(sprobs)):
            if sprobs[s][r-1] != -1: # aka as long as we have a meaningful sprob
                sprobs_for_this_round.append(sprobs[s][r-1]) #conditional sprobs
                plot_margins.append(margins[s])
        avg_for_this_round = sum(sprobs_for_this_round) / len(sprobs_for_this_round)
        # Uncomment the line below to fix the y-axis scale
        #plt.ylim(.65,1)
        plt.plot(plot_margins, sprobs_for_this_round, marker=markers[r-1], color=colors[r-1], label='Round '+str(r), linestyle='None')
        plt.xlabel('Reported Margin')
        title = 'Proportion of Audits that Stopped by Round (EoR BRAVO, Reported)'
        plt.title(title)
        plt.ylabel('Proportion that Stopped')
        plt.grid()
        plt.axhline(y=avg_for_this_round, color=colors[r-1], linestyle='--', label='Average for Round '+str(r))
    #plt.axhline(y=.9, color='black', linestyle='--')
    plt.legend(loc='lower right')
    plt.show()


"""
