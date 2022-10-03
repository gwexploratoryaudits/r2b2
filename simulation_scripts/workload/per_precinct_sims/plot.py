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
import json


# audit-specific items:
all_audit_specific_items = {}
audits = []
# providence
audit_name = 'minerva2'
audits.append(audit_name)
simulation_sprob_arg = 'sample_sprob'
sim_args = {'description':'Per-precinct Providence'}
all_audit_specific_items.update({'minerva2':{'audit_name':audit_name,'simulation_sprob_arg':simulation_sprob_arg,'sim_args':sim_args}})
# eor bravo
audit_name = 'eor_bravo'
audits.append(audit_name)
simulation_sprob_arg = 'sample_sprob'
sim_args = {'description':'Per-precinct eor bravo'}
all_audit_specific_items.update({'eor_bravo':{'audit_name':audit_name,'simulation_sprob_arg':simulation_sprob_arg,'sim_args':sim_args}})
# so bravo
audit_name = 'so_bravo'
audits.append(audit_name)
simulation_sprob_arg = 'sample_sprob'
sim_args = {'description':'Per-precinct so bravo'}
all_audit_specific_items.update({'so_bravo':{'audit_name':audit_name,'simulation_sprob_arg':simulation_sprob_arg,'sim_args':sim_args}})
# minerva
audit_name = 'minerva'
audits.append(audit_name)
simulation_sprob_arg = 'first_round_sprob'
sim_args = {'description':'Per-precinct minerva (90% then 1.5)'}
all_audit_specific_items.update({'minerva':{'audit_name':audit_name,'simulation_sprob_arg':simulation_sprob_arg,'sim_args':sim_args}})

# per_audit_results
per_audit_results = {}

for cur_audit in audits:
    audit_specific_items = all_audit_specific_items[cur_audit]
    
    db = DBInterface(port=27017,user='reader', pwd='icanread')
    contest_name = 'Virginia 2016 presidential contest'
    tally = {'Hillary R. Clinton': 1981473, 'Donald J. Trump': 1769443, 'Gary Johnson': 118274, 'Evan McMullin':54054, 'Jill Stein':27638, 'All Others':33749}
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
    with open('bals.json') as f:
        per_precinct_ballots = json.load(f)["bals"]
    with open('precinct_list.json') as f:
        precinct_list = json.load(f)["precinct_list"]

    audit_id = db.audit_lookup(audit_specific_items['audit_name'], 0.1)
    reported_id = db.contest_lookup(contest, qapp={'description': '2020 Presidential'})

    numbals = []
    numrounds = []
    ps = [.05,.1,.15,.2,.25,.3,.35,.4,.45,.5,.55,.6,.65,.7,.75,.8,.85,.9,.95]
    for p in ps:
        query = {
            'reported': reported_id,
            'underlying': 'reported',
            'audit': audit_id,
            'invalid_ballots': True,
            'max_rounds': 1000
        }
        query.update({audit_specific_items['simulation_sprob_arg']:p})
        query.update(audit_specific_items['sim_args'])
        sprob_sim = db.db.simulations.find_one(query)

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
    # AT FIRST JUST PLOT THE NUM BALLOTS EXPECTED WITH NO ROUND COST
    roundcost = 0

    # compute expected costs for each round schedule (parameterized by p):
    numbals = np.array(numbals)
    numrounds = np.array(numrounds)
    costs = balcost * numbals + roundcost * numrounds
    expbals = costs
    """
    font = {'size'   : 17}
    plt.rc('font', **font)
    plt.plot(ps,np.array(costs)/1000,linestyle='--', marker='o', color='b')
    plt.xlabel('Stopping Probability, p')
    plt.ylabel('Expected Ballots Sampled (x$10^3$)')
    plt.tight_layout()
    plt.show()
    """

    # workload model parameters:
    # now again for cost model
    balcost = 1
    roundcost = 50

    # compute expected costs for each round schedule (parameterized by p):
    numbals = np.array(numbals)
    numrounds = np.array(numrounds)
    costs = balcost * numbals + roundcost * numrounds
    """
    font = {'size'   : 17}
    plt.rc('font', **font)
    plt.plot(ps,np.array(costs)/1000,linestyle='--', marker='o', color='b')
    plt.xlabel('Stopping Probability, p')
    plt.ylabel('Expected Cost (x$10^3$)')
    plt.title('Round Cost of '+str(roundcost))
    plt.tight_layout()
    plt.show()
    """

    cur_results = {cur_audit: { 
        'ps':ps,
        'expbals':list(expbals),
        'costs':list(costs)
    }}
    per_audit_results.update(cur_results)

font = {'size'   : 17}
plt.rc('font', **font)
colors= ['b','r','g','c','m']
markers = ['o','x','s','d','*']
i = 0
for cur_audit in audits:
    ps = per_audit_results[cur_audit]['ps']
    costs = per_audit_results[cur_audit]['expbals']
    plt.plot(ps,np.array(costs)/1000,linestyle='--', marker=markers[i], color=colors[i], label=cur_audit)
    i += 1
plt.xlabel('Stopping Probability, p')
plt.ylabel('Expected Ballots Sampled (x$10^3$)')
plt.title('Expected number of ballots sampled')
plt.legend(loc='upper right')
plt.tight_layout()
plt.show() 

font = {'size'   : 17}
plt.rc('font', **font)
colors= ['b','r','g','c','m']
markers = ['o','x','s','d','*']
i = 0
for cur_audit in audits:
    ps = per_audit_results[cur_audit]['ps']
    costs = per_audit_results[cur_audit]['costs']
    plt.plot(ps,np.array(costs)/1000,linestyle='--', marker=markers[i], color=colors[i], label=cur_audit)
    i += 1
plt.xlabel('Stopping Probability, p')
plt.ylabel('Expected Ballots Sampled (x$10^3$)')
#ax.set_yscale('log') # need to ax
plt.title('Constant round cost of 50 ballots')
plt.legend(loc='upper right')
plt.tight_layout()
plt.show() 








