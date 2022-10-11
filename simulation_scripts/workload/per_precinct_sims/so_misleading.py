"""Generates plots for the Providence workload sims."""

import matplotlib.pyplot as plt
import numpy as np
plt.rcParams['mathtext.fontset'] = 'stix'
plt.rcParams['font.family'] = 'STIXGeneral'
plt.rcParams['text.usetex'] = True

from r2b2.simulator import DBInterface
from r2b2.simulator import histogram
from r2b2.tests.util import parse_election
from r2b2.contest import Contest
from r2b2.contest import ContestType
import json

def estimate_min2(xs,ys):
    return xs[np.where(ys==min(ys))[0][0]], min(ys)

# audit-specific items:
all_audit_specific_items = {}
audits = []
audit_labels = {}
# so bravo
marker = 's'
color = 'g'
linestyle = '--'
audit_name = 'so_bravo'
audits.append(audit_name)
audit_labels.update({audit_name: r'SO \textsc{BRAVO}'})
simulation_sprob_arg = 'sample_sprob'
sim_args = {'description':'Per-precinct so bravo'}
all_audit_specific_items.update({'so_bravo':{'audit_name':audit_name,'simulation_sprob_arg':simulation_sprob_arg,'sim_args':sim_args,'marker':marker,'color':color,'linestyle':linestyle}})
"""
# minerva
audit_name = 'minerva'
audits.append(audit_name)
audit_labels.update({audit_name: 'Minerva'})
simulation_sprob_arg = 'first_round_sprob'
sim_args = {'description':'Per-precinct minerva (90% then 1.5)'}
all_audit_specific_items.update({'minerva':{'audit_name':audit_name,'simulation_sprob_arg':simulation_sprob_arg,'sim_args':sim_args}})
"""

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
    distinct_precinct_samples = []
    ps = [.05,.1,.15,.2,.25,.3,.35,.4,.45,.5,.55,.6,.65,.7,.75,.8,.85,.9,.95]
    so_misleading_props = []
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
        print(str(cur_audit)+' '+str(p)+' with '+str(sprob_analysis['remaining_by_round'][0])+' trials')

        so_misleading_props.append(sprob_analysis['prop_misleading'])

    print(so_misleading_props)
    cur_results = {cur_audit: { 
        'ps':ps,
        'so_misleading_props':so_misleading_props
    }}
    per_audit_results.update(cur_results)



# expected number of ballots vs p
font = {'size'   : 17}
plt.rc('font', **font)
#colors= ['b','r','g','c','m']
#markers = ['o','x','s','d','*']
i = 0
for cur_audit in audits:
    ps = per_audit_results[cur_audit]['ps']
    prop_misleadings = per_audit_results[cur_audit]['so_misleading_props']
    plt.plot(ps,
        np.array(prop_misleadings),
        linestyle=all_audit_specific_items[cur_audit]['linestyle'],
        color=all_audit_specific_items[cur_audit]['color'],
        marker=all_audit_specific_items[cur_audit]['marker'],
        label=audit_labels[cur_audit])
    i += 1
plt.xlabel('Stopping probability, $p$')
plt.ylabel('Proportion')
plt.title('Proportion of audits with an \nSO'+r' \textsc{BRAVO} \emph{misleading sequence}')
plt.legend(loc='upper right')
plt.tight_layout()
plt.show() 

