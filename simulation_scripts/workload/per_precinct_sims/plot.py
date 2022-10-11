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
# providence
audit_name = 'minerva2'
marker = 'o'
color = 'b'
linestyle = '-'
audits.append(audit_name)
audit_labels.update({audit_name: r'\textsc{Providence}'})
simulation_sprob_arg = 'sample_sprob'
sim_args = {'description':'Per-precinct Providence potentially fixed'}
all_audit_specific_items.update({'minerva2':{'audit_name':audit_name,'simulation_sprob_arg':simulation_sprob_arg,'sim_args':sim_args,'marker':marker,'color':color,'linestyle':linestyle}})
# eor bravo
audit_name = 'eor_bravo'
marker = 'x'
color = 'r'
linestyle = '-.'
audits.append(audit_name)
audit_labels.update({audit_name: r'EoR \textsc{BRAVO}'})
simulation_sprob_arg = 'sample_sprob'
sim_args = {'description':'Per-precinct eor bravo'}
all_audit_specific_items.update({'eor_bravo':{'audit_name':audit_name,'simulation_sprob_arg':simulation_sprob_arg,'sim_args':sim_args,'marker':marker,'color':color,'linestyle':linestyle}})
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

    # plot the workload for each round schedule parameter p 
    # (the round schedule's constant stopping probability)

    # workload model parameters:
    balworkload = 1
    # AT FIRST JUST PLOT THE NUM BALLOTS EXPECTED WITH NO ROUND COST
    roundworkload = 0

    # compute expected workloads for each round schedule (parameterized by p):
    numbals = np.array(numbals)
    numrounds = np.array(numrounds)
    workloads = balworkload * numbals + roundworkload * numrounds
    expbals = workloads
    """
    font = {'size'   : 17}
    plt.rc('font', **font)
    plt.plot(ps,np.array(workloads)/1000,linestyle='--', marker='o', color='b')
    plt.xlabel('Stopping Probability, p')
    plt.ylabel('Expected Ballots Sampled (x$10^3$)')
    plt.tight_layout()
    plt.show()
    """

    # workload model parameters:
    # now again for workload model
    balworkload = 1
    roundworkload = 1000

    # compute expected workloads for each round schedule (parameterized by p):
    numbals = np.array(numbals)
    numrounds = np.array(numrounds)
    workloads = balworkload * numbals + roundworkload * numrounds
    """
    font = {'size'   : 17}
    plt.rc('font', **font)
    plt.plot(ps,np.array(workloads)/1000,linestyle='--', marker='o', color='b')
    plt.xlabel('Stopping Probability, p')
    plt.ylabel('Expected Workload (x$10^3$)')
    plt.title('Round Workload of '+str(roundworkload))
    plt.tight_layout()
    plt.show()
    """

    # now compute the workload using the model where the round size workload
    # is part constant and part a linear function of the number of precincts
    # sampled from
    balworkload = 1
    newroundworkload = 1000
    precinctworkload = 2#TODO

    # compute expected workloads for each round schedule (parameterized by p):
    numbals = np.array(numbals)
    numrounds = np.array(numrounds)
    distinct_precinct_samples = np.array(distinct_precinct_samples)
    precinct_workloads = balworkload * numbals + roundworkload * numrounds + distinct_precinct_samples * precinctworkload
    """
    font = {'size'   : 17}
    plt.rc('font', **font)
    plt.plot(ps,np.array(workloads)/1000,linestyle='--', marker='o', color='b')
    plt.xlabel('Stopping Probability, p')
    plt.ylabel('Expected Workload (x$10^3$)')
    plt.title('Round Workload of '+str(roundworkload))
    plt.tight_layout()
    plt.show()
    """

    print(distinct_precinct_samples)
    cur_results = {cur_audit: { 
        'ps':ps,
        'expbals':list(expbals),
        'exprounds':list(numrounds),
        'expprecincts':list(distinct_precinct_samples),
        'workloads':list(workloads),
        'precinct_workloads':list(precinct_workloads)
    }}
    per_audit_results.update(cur_results)




"""
# something that really should have been constant among each of the different audits for a given stopping probability p 
# is the stopping probability p and thus the number of rounds. it would be bad if we were incorrectly selecting round sizes
# in a ceratin direction for one audit or another and so i will show that here as a sanity check
font = {'size'   : 17}
plt.rc('font', **font)
colors= ['b','r','g','c','m']
markers = ['x','o','s','d','*']
i = 0
prov_exp_rounds = np.array(per_audit_results['eor_bravo']['exprounds'])
for cur_audit in audits:
    ps = per_audit_results[cur_audit]['ps']
    exprounds = per_audit_results[cur_audit]['exprounds']
    plt.plot(ps,np.array(exprounds)/prov_exp_rounds,linestyle='-.', marker=markers[i], color=colors[i], label=audit_labels[cur_audit])
    i += 1
plt.xlabel('Stopping Probability, p')
plt.ylabel('Expected total rounds as fraction')
plt.title('expected total rounds as fraction of eor bravo exp rounds')
plt.legend(loc='upper left')
plt.tight_layout()
plt.show() 
"""




# expected number of ballots vs p
font = {'size'   : 17}
plt.rc('font', **font)
#colors= ['b','r','g','c','m']
#markers = ['o','x','s','d','*']
i = 0
for cur_audit in audits:
    ps = per_audit_results[cur_audit]['ps']
    workloads = per_audit_results[cur_audit]['expbals']
    plt.plot(ps,
        np.array(workloads)/1000,
        linestyle=all_audit_specific_items[cur_audit]['linestyle'],
        color=all_audit_specific_items[cur_audit]['color'],
        marker=all_audit_specific_items[cur_audit]['marker'],
        label=audit_labels[cur_audit])
    i += 1
plt.xlabel('Stopping probability, $p$')
plt.ylabel(r'Average total ballots sampled ($\times 10^3$)')
plt.title('Average total number of ballots sampled')
plt.legend(loc='upper left')
plt.tight_layout()
plt.show() 

# expected number of ballots vs p as a ratio of the prov exp bals
font = {'size'   : 17}
plt.rc('font', **font)
colors= ['b','r','g','c','m']
markers = ['o','x','s','d','*']
i = 0
cur_audit = 'minerva2'
ps = per_audit_results[cur_audit]['ps']
prov_workloads = np.array(per_audit_results[cur_audit]['expbals'])

cur_audit = 'so_bravo'
ps = per_audit_results[cur_audit]['ps']
workloads = np.divide(np.array(per_audit_results[cur_audit]['expbals']), prov_workloads)
plt.plot(ps,np.array(workloads),                linestyle=all_audit_specific_items[cur_audit]['linestyle'],
        color=all_audit_specific_items[cur_audit]['color'],
        marker=all_audit_specific_items[cur_audit]['marker'],
 
        label=audit_labels[cur_audit])
i += 1
cur_audit = 'eor_bravo'
ps = per_audit_results[cur_audit]['ps']
workloads = np.divide(np.array(per_audit_results[cur_audit]['expbals']), prov_workloads)
plt.plot(ps,np.array(workloads),        linestyle=all_audit_specific_items[cur_audit]['linestyle'],
        color=all_audit_specific_items[cur_audit]['color'],
        marker=all_audit_specific_items[cur_audit]['marker'], label=audit_labels[cur_audit])
i += 1
cur_audit = 'minerva2'
ps = per_audit_results[cur_audit]['ps']
workloads = np.divide(np.array(per_audit_results[cur_audit]['expbals']), prov_workloads)
plt.plot(ps,np.array(workloads), linestyle=all_audit_specific_items[cur_audit]['linestyle'],
        color=all_audit_specific_items[cur_audit]['color'],
        marker=all_audit_specific_items[cur_audit]['marker'], label=audit_labels[cur_audit])
plt.xlabel('Stopping Probability, p')
plt.ylabel('Total ballots fraction')
plt.axhline(y=1, linestyle='--')
plt.title('Average total ballots sampled \nas fraction of '+r'\textsc{Providence} total')
plt.legend(loc='upper left')
plt.tight_layout()
plt.show() 

# expected workload vs p (round workload only)
font = {'size'   : 17}
plt.rc('font', **font)
colors= ['b','r','g','c','m']
markers = ['o','x','s','d','*']
i = 0
for cur_audit in audits:
    ps = per_audit_results[cur_audit]['ps']
    workloads = per_audit_results[cur_audit]['workloads']
    plt.plot(ps,np.array(workloads), linestyle=all_audit_specific_items[cur_audit]['linestyle'],
        color=all_audit_specific_items[cur_audit]['color'],
        marker=all_audit_specific_items[cur_audit]['marker'],  label=audit_labels[cur_audit])
    i += 1
plt.xlabel('Stopping probability, p')
plt.ylabel(r'Average workload ($\times 10^3$)')
#plt.yscale('log') # need to ax
plt.title('Constant round workload of '+str(roundworkload)+' ballots')
plt.legend(loc='upper right')
plt.yscale('log')
plt.tight_layout()
plt.show() 

# expected workload vs p (round workload and precinct workload)
font = {'size'   : 17}
plt.rc('font', **font)
colors= ['b','r','g','c','m']
markers = ['o','x','s','d','*']
i = 0
for cur_audit in audits:
    ps = per_audit_results[cur_audit]['ps']
    precinct_workloads = per_audit_results[cur_audit]['precinct_workloads']
    plt.plot(ps,np.array(precinct_workloads)/1000, linestyle=all_audit_specific_items[cur_audit]['linestyle'],
        color=all_audit_specific_items[cur_audit]['color'],
        marker=all_audit_specific_items[cur_audit]['marker'], label=audit_labels[cur_audit])
    i += 1
plt.xlabel('Stopping probability, p')
plt.ylabel(r'Average workload ($\times 10^3$)')
#plt.yscale('log')
plt.title('Round workload '+str(newroundworkload)+' and precinct workload '+str(precinctworkload))
plt.legend(loc='upper right')
plt.tight_layout()
plt.show() 

# optimals ps for all three audits
optimums = {}
i=0
linestyles=['-','--','-.']
for cur_audit in audits:
    ps = per_audit_results[cur_audit]['ps']
    precinct_workloads = per_audit_results[cur_audit]['precinct_workloads']
    #plt.plot(ps,np.array(precinct_workloads),linestyle='--', marker=markers[i], color=colors[i], label=audit_labels[cur_audit])
    audit = cur_audit
    workloads = per_audit_results[audit]['workloads']
    numbals = per_audit_results[audit]['expbals']
    numrounds = per_audit_results[audit]['exprounds']
    balworkload = 1
    minimizing_ps = []
    minimal_workloads = []
    roundworkloads = np.linspace(1,100000,num = 100000)#[1, 10, 100, 1000, 10000]

    for roundworkload in roundworkloads:
        # compute expected workloads for each round schedule (parameterized by p):
        numbals = np.array(numbals)
        numrounds = np.array(numrounds)
        workloads = balworkload * numbals + roundworkload * numrounds

        # find the value of p which achieves the minimum workload in workloads
        """
        minidx = list(workloads).index(min(workloads))
        minimizing_ps.append(ps[minidx])
        """
        minimizing_ps.append(estimate_min2(ps, workloads)[0])
        minimal_workloads.append(estimate_min2(ps, workloads)[1])

    optimums.update({cur_audit:{'minimizing_ps':minimizing_ps,'minimal_workloads':minimal_workloads}})
    i += 1

# minimal workload ps
font = {'size'   : 17}
plt.rc('font', **font)
i = 0
for cur_audit in audits:
    plt.plot(roundworkloads, optimums[cur_audit]['minimizing_ps'],  
        linestyle=all_audit_specific_items[cur_audit]['linestyle'],#linestyle='None',
        #marker=all_audit_specific_items[cur_audit]['marker'],
        color=all_audit_specific_items[cur_audit]['color'],
         label=audit_labels[cur_audit])
    i += 1
plt.xlabel('Round workload, $c_r$')
plt.ylabel('Stopping probability, $p$')
plt.title('Optimal stopping probability $p$') 
plt.xscale('log')
plt.legend(loc='upper left')
plt.tight_layout()
plt.show()

# minimal workloads
font = {'size'   : 17}
plt.rc('font', **font)
i = 0
for cur_audit in audits:
    plt.plot(roundworkloads, np.array(optimums[cur_audit]['minimal_workloads']) / np.array(optimums['minerva2']['minimal_workloads']), linestyle=all_audit_specific_items[cur_audit]['linestyle'],
        color=all_audit_specific_items[cur_audit]['color'],
 label=audit_labels[cur_audit])
    i += 1
plt.xlabel('Round workload, $c_r$')
plt.ylabel('Optimal workload fraction')
plt.title('Optimal workload as fraction \nof optimal '+r'\textsc{Providence} workload') 
plt.legend(loc='upper left')
plt.xscale('log')
plt.tight_layout()
plt.show()



# optimals ps for all three audits under the per-precinct model
optimums = {}
i=0
linestyles=['-','--','-.']
for cur_audit in audits:
    ps = per_audit_results[cur_audit]['ps']
    precinct_workloads = per_audit_results[cur_audit]['precinct_workloads']
    #plt.plot(ps,np.array(precinct_workloads),linestyle='--', marker=markers[i], color=colors[i], label=audit_labels[cur_audit])
    audit = cur_audit
    workloads = per_audit_results[audit]['workloads']
    numbals = per_audit_results[audit]['expbals']
    numrounds = per_audit_results[audit]['exprounds']
    expprecincts = per_audit_results[audit]['expprecincts']
    balworkload = 1
    roundworkload = 1000
    minimizing_ps = []
    minimal_workloads = []
    precinctworkloads = np.linspace(0,50,num=100)#[1, 10, 100, 1000, 10000]

    for precinctworkload in precinctworkloads:
        # compute expected workloads for each round schedule (parameterized by p):
        numbals = np.array(numbals)
        numrounds = np.array(numrounds)
        expprecincts = np.array(expprecincts)
        #workloads = balworkload * numbals + roundworkload * numrounds
        workloads = balworkload * numbals + roundworkload * numrounds + precinctworkload * expprecincts

        # find the value of p which achieves the minimum workload in workloads
        """
        minidx = list(workloads).index(min(workloads))
        minimizing_ps.append(ps[minidx])
        """
        minimizing_ps.append(estimate_min2(ps, workloads)[0])
        minimal_workloads.append(estimate_min2(ps, workloads)[1])

    optimums.update({cur_audit:{'minimizing_ps':minimizing_ps,'minimal_workloads':minimal_workloads}})
    i += 1

# minimal workload ps
font = {'size'   : 17}
plt.rc('font', **font)
i = 0
for cur_audit in audits:
    plt.plot(precinctworkloads, optimums[cur_audit]['minimizing_ps'], linestyle=all_audit_specific_items[cur_audit]['linestyle'],
        color=all_audit_specific_items[cur_audit]['color'], label=audit_labels[cur_audit])
    i += 1
plt.xlabel('Precinct workload, $c_p$')
plt.ylabel('Stopping probability, $p$')
plt.title('Optimal stopping probability $p$') 
plt.xscale('log')
plt.legend(loc='upper right')
plt.tight_layout()
plt.show()

# minimal workloads
font = {'size'   : 17}
plt.rc('font', **font)
i = 0
for cur_audit in audits:
    plt.plot(precinctworkloads, np.array(optimums[cur_audit]['minimal_workloads']) / np.array(optimums['minerva2']['minimal_workloads']), linestyle=all_audit_specific_items[cur_audit]['linestyle'],
        color=all_audit_specific_items[cur_audit]['color'], label=audit_labels[cur_audit])
    i += 1
plt.xlabel('Precinct workload, $c_p$')
plt.ylabel('Optimal workload')
plt.title('Optimal workload as fraction \nof optimal '+r'\textsc{Providence} workload') 
plt.legend(loc='upper right')
#plt.xscale('log')
plt.tight_layout()
plt.show()



