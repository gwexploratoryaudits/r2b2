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
"""
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

    with open('bals.json') as f:
        per_precinct_ballots = json.load(f)["bals"]
    with open('precinct_list.json') as f:
        precinct_list = json.load(f)["precinct_list"]

    audit_id = db.audit_lookup(audit_specific_items['audit_name'], 0.1)
    reported_id = db.contest_lookup(contest, qapp={'description': '2020 Presidential'})

    numbals = []
    numrounds = []
    distinct_precinct_samples = []
    ps = [.45,.55,.65,.75,.85,.95]
    prop_misleadings = []
    for p in ps:
        query = {
            'reported': reported_id,
            'underlying': 'reported',
            'audit': audit_id,
            'invalid_ballots': True
        }
        query.update({audit_specific_items['simulation_sprob_arg']:p})
        query.update(audit_specific_items['sim_args'])
        sprob_sim = db.db.simulations.find_one(query)


        # now go thru all the trials and count the samples that had fewer ballots for hillary than for trump
        sim_id = sprob_sim['_id']
        trials = db.trial_lookup(sim_id) #this function is slowwwww
        print(cur_audit)
        print('got trials')
        misleading_count = 0
        for trial in trials:
            sample = trial['winner_ballots_drawn_sched']
            misleading = False
            for i in range(len(sample['Approve'])):
                if sample['Approve'][i] < sample['Reject'][i]:
                    misleading = True
                    break
            if misleading:
                misleading_count += 1
        print('got misleading count:')
        print(misleading_count)
        num_trials = sprob_sim['analysis']['remaining_by_round'][0]
        prop_misleading = misleading_count / num_trials
        
        prop_misleadings.append(prop_misleading)

        analysis = sprob_sim['analysis']
        analysis.update({'misleading_count':misleading_count,'prop_misleading':prop_misleading})
        db.update_analysis(sim_id, analysis)

        """
        # now get the relevant pieces of information we want for this simulation
        # for right now that includes:
        # 1. the expected number of rounds (average num rounds)
        # 2. expected number of ballots (average num ballots)
        sprob_analysis = sprob_sim['analysis']
        print(str(cur_audit)+' '+str(p)+' with '+str(sprob_analysis['remaining_by_round'][0])+' trials')

        # 1. the expected number of ballots (average num ballots)
        numbals.append(sprob_analysis['asn'])

        # 2. expected number of rounds (average num rounds)
        sprobs = sprob_analysis['sprob_by_round']
        last = sprobs.index(-1)
        curnumrounds = 0
        r = 1
        pr_make_it = 1
        for sprob in sprobs:
            if sprob == -1:
                break
            pr_stop = pr_make_it * sprob
            curnumrounds += r * pr_stop
            pr_make_it *= (1-sprob)
            r += 1
        numrounds.append(curnumrounds)

        # 3. and now also think about the number of precincts sampled from in each round
        avg_precincts_per_round = sprob_analysis['avg_precincts_sampled_by_round']
        distinct_precinct_samples.append(sum(avg_precincts_per_round))
        """
    plt.plot(ps, prop_misleadings)
    plt.show()

    """
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

    # workload model parameters:
    # now again for cost model
    balcost = 1
    roundcost = 1000

    # compute expected costs for each round schedule (parameterized by p):
    numbals = np.array(numbals)
    numrounds = np.array(numrounds)
    costs = balcost * numbals + roundcost * numrounds
    # now compute the workload using the model where the round size cost
    # is part constant and part a linear function of the number of precincts
    # sampled from
    balcost = 1
    newroundcost = 1000
    precinctcost = 2#TODO

    # compute expected costs for each round schedule (parameterized by p):
    numbals = np.array(numbals)
    numrounds = np.array(numrounds)
    distinct_precinct_samples = np.array(distinct_precinct_samples)
    precinct_costs = balcost * numbals + roundcost * numrounds + distinct_precinct_samples * precinctcost


    cur_results = {cur_audit: { 
        'ps':ps,
        'expbals':list(expbals),
        'exprounds':list(numrounds),
        'expprecincts':list(distinct_precinct_samples),
        'costs':list(costs),
        'precinct_costs':list(precinct_costs)
    }}
    per_audit_results.update(cur_results)





# expected number of ballots vs p
font = {'size'   : 17}
plt.rc('font', **font)
colors= ['b','r','g','c','m']
markers = ['o','x','s','d','*']
i = 0
for cur_audit in audits:
    ps = per_audit_results[cur_audit]['ps']
    costs = per_audit_results[cur_audit]['expbals']
    plt.plot(ps,np.array(costs)/1000,linestyle='--', marker=markers[i], color=colors[i], label=audit_labels[cur_audit])
    i += 1
plt.xlabel('Stopping probability, $p$')
plt.ylabel('Average total ballots sampled (x$10^3$)')
plt.title('Average total number of ballots sampled')
plt.legend(loc='upper left')
plt.tight_layout()
plt.show() 





    """






