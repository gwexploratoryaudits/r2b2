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

# function used to estimate the minimum of a low 
# degree polynomial fit to a set of points
def estimate_min2(xs,ys):
    coefs = np.polyfit(xs, ys, 2)

    c = np.poly1d(coefs)

    crit = c.deriv().r
    r_crit = crit[crit.imag==0].real
    test = c.deriv(2)(r_crit) 

    # compute local minima 
    # excluding range boundaries
    x_min = r_crit[test>0]
    y_min = c(x_min)

    return (x_min, y_min)

# audit-specific items:
all_audit_specific_items = {}
audits = []
audit_labels = {}
# providence
audit_name = 'minerva2'
audits.append(audit_name)
audit_labels.update({audit_name: 'Providence'})
simulation_sprob_arg = 'sample_sprob'
sim_args = {'description':'prov pilot workload'}
all_audit_specific_items.update({'minerva2':{'audit_name':audit_name,'simulation_sprob_arg':simulation_sprob_arg,'sim_args':sim_args}})
# eor bravo
audit_name = 'eor_bravo'
audits.append(audit_name)
audit_labels.update({audit_name: 'EOR BRAVO'})
simulation_sprob_arg = 'sample_sprob'
sim_args = {'description':'eor bravo pilot workload'}
all_audit_specific_items.update({'eor_bravo':{'audit_name':audit_name,'simulation_sprob_arg':simulation_sprob_arg,'sim_args':sim_args}})
# so bravo
audit_name = 'so_bravo'
audits.append(audit_name)
audit_labels.update({audit_name: 'SO BRAVO'})
simulation_sprob_arg = 'sample_sprob'
sim_args = {'description':'so bravo pilot workload'}
all_audit_specific_items.update({'so_bravo':{'audit_name':audit_name,'simulation_sprob_arg':simulation_sprob_arg,'sim_args':sim_args}})
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
    if cur_audit != 'minerva2':
        continue
 
    audit_specific_items = all_audit_specific_items[cur_audit]
    
    db = DBInterface(port=27018,user='reader', pwd='icanread')
    contest_name = "\nSchool Construction and Renovation Projects"
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
    reported_id = db.contest_lookup(contest, qapp={'description': '2020 Presidential'})
    winner_prop = winner_votes / total_relevant

    audit_id = db.audit_lookup(audit_specific_items['audit_name'], 0.1)
    reported_id = db.contest_lookup(contest, qapp={'description': '2020 Presidential'})

    numbals = []
    numrounds = []
    distinct_precinct_samples = []
    #ps = [.05,.1,.15,.2,.25,.3,.35,.4,.45,.5,.55,.6,.65,.7,.75,.8,.85,.9,.95]
    ps = [.45,.55,.65,.75,.85,.95]
    prop_misleadings = []
    for p in ps:
        query = {
            'reported': reported_id,
            'underlying': 'reported',
            'audit': audit_id,
            'invalid_ballots': True,
            #'max_rounds': 1000
        }
        query.update({audit_specific_items['simulation_sprob_arg']:p})
        query.update(audit_specific_items['sim_args'])
        sprob_sim = db.db.simulations.find_one(query)

        sim_id = sprob_sim['_id']
        analysis = sprob_sim['analysis']

        prop_misleadings.append(analysis['prop_misleading'])

    cur_results = {cur_audit: { 
        'ps':ps,
        'prop_misleadings':prop_misleadings
    }}
    per_audit_results.update(cur_results)




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

# function used to estimate the minimum of a low 
# degree polynomial fit to a set of points
def estimate_min2(xs,ys):
    coefs = np.polyfit(xs, ys, 2)

    c = np.poly1d(coefs)

    crit = c.deriv().r
    r_crit = crit[crit.imag==0].real
    test = c.deriv(2)(r_crit) 

    # compute local minima 
    # excluding range boundaries
    x_min = r_crit[test>0]
    y_min = c(x_min)

    return (x_min, y_min)

# audit-specific items:
all_audit_specific_items = {}
audits = []
audit_labels = {}
# providence
audit_name = 'minerva2'
audits.append(audit_name)
audit_labels.update({audit_name: 'Providence'})
simulation_sprob_arg = 'sample_sprob'
sim_args = {'description':'Per-precinct Providence potentially fixed'}
all_audit_specific_items.update({'minerva2':{'audit_name':audit_name,'simulation_sprob_arg':simulation_sprob_arg,'sim_args':sim_args}})
# eor bravo
audit_name = 'eor_bravo'
audits.append(audit_name)
audit_labels.update({audit_name: 'EOR BRAVO'})
simulation_sprob_arg = 'sample_sprob'
sim_args = {'description':'Per-precinct eor bravo'}
all_audit_specific_items.update({'eor_bravo':{'audit_name':audit_name,'simulation_sprob_arg':simulation_sprob_arg,'sim_args':sim_args}})
# so bravo
audit_name = 'so_bravo'
audits.append(audit_name)
audit_labels.update({audit_name: 'SO BRAVO'})
simulation_sprob_arg = 'sample_sprob'
sim_args = {'description':'Per-precinct so bravo'}
all_audit_specific_items.update({'so_bravo':{'audit_name':audit_name,'simulation_sprob_arg':simulation_sprob_arg,'sim_args':sim_args}})
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
per_audit_results2 = {}

for cur_audit in audits:
    if cur_audit != 'minerva2':
        continue
 
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
    prop_misleadings = []
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

        sim_id = sprob_sim['_id']
        analysis = sprob_sim['analysis']

        prop_misleadings.append(analysis['prop_misleading'])

    cur_results = {cur_audit: { 
        'ps':ps,
        'prop_misleadings':prop_misleadings
    }}
    per_audit_results2.update(cur_results)

# expected number of ballots vs p
font = {'size'   : 17}
plt.rc('font', **font)
colors= ['b','r','g','c','m']
markers = ['o','x','s','d','*']
i = 0
for cur_audit in audits:
    if cur_audit != 'minerva2':
        continue
    ps = per_audit_results[cur_audit]['ps']
    prop_misleadings = per_audit_results[cur_audit]['prop_misleadings']
    print(prop_misleadings)
    plt.plot(ps,np.array(prop_misleadings),linestyle='--', marker=markers[i], color=colors[i], label='Providence (pilot)')
    i += 1
font = {'size'   : 17}
plt.rc('font', **font)
colors= ['b','r','g','c','m']
markers = ['o','x','s','d','*']
i = 0
for cur_audit in audits:
    if cur_audit != 'minerva2':
        continue
    ps = per_audit_results2[cur_audit]['ps']
    prop_misleadings = per_audit_results2[cur_audit]['prop_misleadings']
    print(prop_misleadings)
    plt.plot(ps,np.array(prop_misleadings),linestyle='--', marker='s', color=colors[i], label='Providence (Virginia)')
    #plt.yscale("log")
    i += 1

plt.xlabel('Stopping probability, $p$')
plt.ylabel('Proportion')
plt.title('Proportion of audits with a misleading sample')
plt.axhline(y=.1, linestyle='--', label='Misleading Limits (.1, .01, .001)')
plt.axhline(y=.01, linestyle='--')#, label='Misleading Limit = .01')
plt.axhline(y=.001, linestyle='--')#, label='Misleading Limit = .001')
plt.legend(loc='upper right')
plt.tight_layout()
plt.show() 


