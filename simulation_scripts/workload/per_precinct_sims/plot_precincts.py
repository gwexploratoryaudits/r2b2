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
    roundcost = 1000

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

    print(distinct_precinct_samples)
    cur_results = {cur_audit: { 
        'ps':ps,
        'expbals':list(expbals),
        'exprounds':list(numrounds),
        'expprecincts':list(distinct_precinct_samples),
        'costs':list(costs),
        'precinct_costs':list(precinct_costs)
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
colors= ['b','r','g','c','m']
markers = ['x','o','s','d','*']
# optimals ps for all three audits under the per-precinct model
optimums = {}
i=0
linestyles=['-','--','-.']
for cur_audit in audits:
    ps = per_audit_results[cur_audit]['ps']
    precinct_costs = per_audit_results[cur_audit]['precinct_costs']
    #plt.plot(ps,np.array(precinct_costs),linestyle='--', marker=markers[i], color=colors[i], label=audit_labels[cur_audit])
    audit = cur_audit
    costs = per_audit_results[audit]['costs']
    numbals = per_audit_results[audit]['expbals']
    numrounds = per_audit_results[audit]['exprounds']
    expprecincts = np.array(per_audit_results[audit]['expprecincts'])
    balcost = 1
    roundcost = 1000
    minimizing_ps = []
    minimal_costs = []
    precinctcosts = np.linspace(0,50,num=100)#[1, 10, 100, 1000, 10000]
    print(cur_audit)
    print(expprecincts)

    for precinctcost in precinctcosts:
        # compute expected costs for each round schedule (parameterized by p):
        numbals = np.array(numbals)
        numrounds = np.array(numrounds)
        #costs = balcost * numbals + roundcost * numrounds
        costs = balcost * numbals + roundcost * numrounds + expprecincts * precinctcost

        # find the value of p which achieves the minimum cost in costs
        """
        minidx = list(costs).index(min(costs))
        minimizing_ps.append(ps[minidx])
        """
        minimizing_ps.append(estimate_min2(ps, costs)[0])
        minimal_costs.append(estimate_min2(ps, costs)[1])

    optimums.update({cur_audit:{'minimizing_ps':minimizing_ps,'minimal_costs':minimal_costs}})
    i += 1

# minimal cost ps
font = {'size'   : 17}
plt.rc('font', **font)
i = 0
for cur_audit in audits:
    plt.plot(precinctcosts, optimums[cur_audit]['minimizing_ps'], linestyle=linestyles[i], color=colors[i], label=audit_labels[cur_audit])
    i += 1
plt.xlabel('Precinct Cost, $c_p$')
plt.ylabel('Stopping Probability, $p$')
plt.title('Optimal stopping probability $p$') 
plt.xscale('log')
plt.legend(loc='upper right')
plt.tight_layout()
plt.show()

# minimal costs as fraction
font = {'size'   : 17}
plt.rc('font', **font)
i = 0
for cur_audit in audits:
    plt.plot(precinctcosts, np.array(optimums[cur_audit]['minimal_costs']) / np.array(optimums['minerva2']['minimal_costs']), linestyle=linestyles[i], color=colors[i], label=audit_labels[cur_audit])
    i += 1
plt.xlabel('Precinct Cost, $c_p$')
plt.ylabel('Optimal cost')
plt.title('Optimal cost as fraction of Providence cost') 
plt.legend(loc='upper right')
plt.xscale('log')
plt.tight_layout()
plt.show()


# minimal costs
font = {'size'   : 17}
plt.rc('font', **font)
i = 0
for cur_audit in audits:
    plt.plot(precinctcosts, np.array(optimums[cur_audit]['minimal_costs']), linestyle=linestyles[i], color=colors[i], label=audit_labels[cur_audit])
    i += 1
plt.xlabel('Precinct Cost, $c_p$')
plt.ylabel('Optimal cost')
plt.title('Optimal cost for varying per-precinct costs') 
plt.legend(loc='upper left')
plt.xscale('log')
plt.tight_layout()
plt.show()












