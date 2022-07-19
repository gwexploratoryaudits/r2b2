"""Generates plots for the Providence workload sims."""

import matplotlib.pyplot as plt
import numpy as np

from r2b2.simulator import DBInterface
from r2b2.simulator import histogram
from r2b2.tests.util import parse_election

election = parse_election('data/2020_presidential/2020_presidential.json')

if __name__ == '__main__':
    db = DBInterface(port=27018,user='reader', pwd='icanread')
    contest = 'Michigan'
    audit_id = db.audit_lookup('minerva2', 0.1)
    reported_id = db.contest_lookup(election.contests[contest], qapp={'description': '2020 Presidential', 'name': contest})

    numbals = []
    numrounds = []
    ps = [.1,.2,.3,.4,.5,.6,.7,.8,.9]
    for p in ps:
        sprob_sim = db.db.simulations.find_one({
            'reported': reported_id,
            'underlying': 'reported',
            'audit': audit_id,
            'description': 'Providence paper workload section',
            'invalid_ballots': True,
            'sample_sprob':p,
            'max_rounds': 100
        })

        # now get the relevant pieces of information we want for this simulation
        # for right now that includes:
        # 1. the expected number of rounds (average num rounds)
        # 2. expected number of ballots (average num ballots)
        sprob_analysis = sprob_sim['analysis']

        # 1. the expected number of rounds (average num rounds)
        numbals.append(sprob_analysis['asn'])

        # 2. expected number of ballots (average num ballots)
        sprobs = sprob_analysis['sprob_by_round']
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
costs = balcost * numbals + roundcost * numrounds
plt.plot(ps,costs)
plt.xlabel('p (stopping probablility)')
plt.ylabel('cost')
plt.show()




""" old plots for reference:


# Plot the total sprob across all rounds (this should just be 1... since we are
# running the sprob trials to audit completion (100 rounds allowed...))
total_sprobs = []
for s in range(len(sprobs)):
    total_sprob = sum(sprob_stops[s]) / total_to_start
    total_sprobs.append(total_sprob)
plt.plot(margins, total_sprobs, 'bo')
plt.xlabel('Reported Margin')
title = 'Experimental Total Stopping Probability (90% Minerva2)'
plt.title(title)
plt.ylabel('Experimental Stopping Probability')
plt.grid()
plt.show()

# Plot absolute sprobs vs. margins
for r in range (1,max_rounds+1):
    sprobs_for_this_round = [] #conditional sprobs
    absolute_sprobs_for_this_round = [] #absolute sprobs
    for s in range(len(sprobs)):
        absolute_sprob = sprob_stops[s][r-1] / total_to_start
        if absolute_sprob > 1:
            print('sprob_stops[s][r-1]', sprob_stops[s][r-1])
            print('total_to_start', total_to_start)
        absolute_sprobs_for_this_round.append(absolute_sprob)
    # Uncomment the line below to fix the y-axis scale
    #plt.ylim(.65,1)
    #plt.plot(margins, sprobs_for_this_round, 'bo')
    plt.plot(margins, absolute_sprobs_for_this_round, 'bo')
    plt.xlabel('Reported Margin')
    title = 'Round '+str(r)+' Experimental Absolute Stopping Probability (90% Minerva2)'
    plt.title(title)
    plt.ylabel('Experimental Stopping Probability')
    plt.grid()
    plt.show()

# Plot conditional sprobs vs. margins
#for r in range (1,max_rounds+1):
for r in range (1,5+1):
    sprobs_for_this_round = [] #conditional sprobs
    absolute_sprobs_for_this_round = [] #absolute sprobs
    plot_margins = []
    for s in range(len(sprobs)):
        if sprobs[s][r-1] != -1: # aka as long as we have a meaningful sprob
            sprobs_for_this_round.append(sprobs[s][r-1]) #conditional sprobs
            plot_margins.append(margins[s])
    # Uncomment the line below to fix the y-axis scale
    #plt.ylim(.65,1)
    plt.plot(plot_margins, sprobs_for_this_round, 'bo')
    plt.xlabel('Reported Margin')
    title = 'Round '+str(r)+' Conditional Stopping Probability (90% Providence)'
    plt.title(title)
    plt.ylabel('Experimental Conditional Stopping Probability')
    plt.grid()
    plt.show()

# Plot first 3 rounds conditional sprobs vs. margins
colors= ['b','r','g','c','m']
markers = ['o','x','s','d','*']
for r in range (1,5+1-2):
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
    title = 'Proportion of Audits that Stopped by Round (90% Providence, Reported)'
    plt.title(title)
    plt.ylabel('Proportion that Stopped')
    plt.grid()
    plt.axhline(y=avg_for_this_round, color=colors[r-1], linestyle='--', label='Average for Round '+str(r))
    #plt.axhline(y=.9, color='black', linestyle='--')
    plt.legend(loc='lower right')
    plt.show()
"""
