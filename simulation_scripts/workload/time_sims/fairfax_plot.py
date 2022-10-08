"""Generates plots for the Providence workload sims."""

import matplotlib.pyplot as plt
import numpy as np
plt.rcParams['mathtext.fontset'] = 'stix'
plt.rcParams['font.family'] = 'STIXGeneral'

from scipy.optimize import minimize
from scipy.optimize import curve_fit
from scipy.stats import beta

from r2b2.simulator import DBInterface
from r2b2.simulator import histogram
from r2b2.tests.util import parse_election
from r2b2.contest import Contest
from r2b2.contest import ContestType
import json


def mybeta(x,a,b,s):
    return beta.pdf(x, a, b)*s
# function used to estimate the minimum of a low 
# degree polynomial fit to a set of points
def estimate_min2(xs,ys,curve=False):
    res = curve_fit(mybeta, xs, ys)
    a = res[0][0]
    b = res[0][1]
    s = res[0][2]
    print(a,b)
    cxs = np.arange(0,1,.01)
    cys = [mybeta(x,a,b,s) for x in cxs]

    return (0, 0, cxs, cys)

    # for now, just return the actual minimum:
    return xs[np.where(ys==min(ys))[0][0]], min(ys)

    coefs = np.polyfit(xs, ys, np.shape(xs)[0]+1)
    #params = beta.fit(xs,ys)
    #print(params)
    #return 1, 0

    c = np.poly1d(coefs)

    fit = minimize(c, x0=.5, method='L-BFGS-B', bounds=((0,1),))
    #print(fit)

    if curve:
        return fit.x, fit.fun, c
    return fit.x, fit.fun

    crit = c.deriv().r
    r_crit = crit[crit.imag==0].real
    test = c.deriv(2)(r_crit) 

    # compute local minima 
    # excluding range boundaries
    x_min = r_crit[test>0]
    y_min = c(x_min)

    if x_min < .05:
        print(x_min)
        x_min = .05
        y_min = ys[np.where(xs==.05)]
    if x_min > .95:
        print(x_min)
        x_min = .95
        y_min = ys[np.where(xs==.95)]

    if curve:
        return (x_min, y_min, c)

    return (x_min, y_min)

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
audit_labels.update({audit_name: 'Providence'})
simulation_sprob_arg = 'sample_sprob'
sim_args = {'description':'Timing Per-precinct Providence'}
all_audit_specific_items.update({'minerva2':{'audit_name':audit_name,'simulation_sprob_arg':simulation_sprob_arg,'sim_args':sim_args,'marker':marker,'color':color,'linestyle':linestyle}})
# eor bravo
audit_name = 'eor_bravo'
marker = 'x'
color = 'r'
linestyle = '-.'
audits.append(audit_name)
audit_labels.update({audit_name: 'EOR BRAVO'})
simulation_sprob_arg = 'sample_sprob'
sim_args = {'description':'Timing Per-precinct eor bravo'}
all_audit_specific_items.update({'eor_bravo':{'audit_name':audit_name,'simulation_sprob_arg':simulation_sprob_arg,'sim_args':sim_args,'marker':marker,'color':color,'linestyle':linestyle}})
# so bravo
marker = 's'
color = 'g'
linestyle = '--'
audit_name = 'so_bravo'
audits.append(audit_name)
audit_labels.update({audit_name: 'SO BRAVO'})
simulation_sprob_arg = 'sample_sprob'
sim_args = {'description':'Timing Per-precinct so bravo'}
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




# expected number of ballots vs p
font = {'size'   : 17}
plt.rc('font', **font)
#colors= ['b','r','g','c','m']
#markers = ['o','x','s','d','*']
i = 0
for cur_audit in audits:
    ps = per_audit_results[cur_audit]['ps']
    costs = per_audit_results[cur_audit]['expbals']
    plt.plot(ps,
        np.array(costs)/1000,
        linestyle=all_audit_specific_items[cur_audit]['linestyle'],
        color=all_audit_specific_items[cur_audit]['color'],
        marker=all_audit_specific_items[cur_audit]['marker'],
        label=audit_labels[cur_audit])
    i += 1
plt.xlabel('Stopping probability, $p$')
plt.ylabel('Average total ballots sampled (x$10^3$)')
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
prov_costs = np.array(per_audit_results[cur_audit]['expbals'])

cur_audit = 'so_bravo'
ps = per_audit_results[cur_audit]['ps']
costs = np.divide(np.array(per_audit_results[cur_audit]['expbals']), prov_costs)
plt.plot(ps,np.array(costs),                linestyle=all_audit_specific_items[cur_audit]['linestyle'],
        color=all_audit_specific_items[cur_audit]['color'],
        marker=all_audit_specific_items[cur_audit]['marker'],
 
        label=audit_labels[cur_audit])
i += 1
cur_audit = 'eor_bravo'
ps = per_audit_results[cur_audit]['ps']
costs = np.divide(np.array(per_audit_results[cur_audit]['expbals']), prov_costs)
plt.plot(ps,np.array(costs),        linestyle=all_audit_specific_items[cur_audit]['linestyle'],
        color=all_audit_specific_items[cur_audit]['color'],
        marker=all_audit_specific_items[cur_audit]['marker'], label=audit_labels[cur_audit])
i += 1
cur_audit = 'minerva2'
ps = per_audit_results[cur_audit]['ps']
costs = np.divide(np.array(per_audit_results[cur_audit]['expbals']), prov_costs)
plt.plot(ps,np.array(costs), linestyle=all_audit_specific_items[cur_audit]['linestyle'],
        color=all_audit_specific_items[cur_audit]['color'],
        marker=all_audit_specific_items[cur_audit]['marker'], label=audit_labels[cur_audit])
plt.xlabel('Stopping Probability, p')
plt.ylabel('Total ballots fraction')
plt.axhline(y=1, linestyle='--')
plt.title('Average total ballots sampled \nas fraction of Providence total')
plt.legend(loc='upper left')
plt.tight_layout()
plt.show() 

# expected cost vs p (round cost only)
font = {'size'   : 17}
plt.rc('font', **font)
colors= ['b','r','g','c','m']
markers = ['o','x','s','d','*']
i = 0
for cur_audit in audits:
    ps = per_audit_results[cur_audit]['ps']
    costs = per_audit_results[cur_audit]['costs']
    plt.plot(ps,np.array(costs), linestyle=all_audit_specific_items[cur_audit]['linestyle'],
        color=all_audit_specific_items[cur_audit]['color'],
        marker=all_audit_specific_items[cur_audit]['marker'],  label=audit_labels[cur_audit])
    # also, let's go ahead and plot the estimate_min curve
    ps = np.array(ps)
    costs = np.array(costs)
    res = estimate_min2(ps, costs, curve=True)
    x_min = res[0]
    y_min = res[1]
    cxs = res[2]
    cys = res[3]
    plt.plot(cxs, cys, label='curve fit')
    #curve = res[2]
    #plt.plot(np.arange(0,1,.01), curve(np.arange(0,1,.01)), label='curve fit')
    i += 1
plt.xlabel('Stopping Probability, p')
plt.ylabel('Average Cost')
#plt.yscale('log') # need to ax
plt.title('Constant round cost of '+str(roundcost)+' ballots')
plt.legend(loc='upper right')
plt.yscale('log')
plt.tight_layout()
plt.show() 

# expected cost vs p (round cost and precinct cost)
font = {'size'   : 17}
plt.rc('font', **font)
colors= ['b','r','g','c','m']
markers = ['o','x','s','d','*']
i = 0
for cur_audit in audits:
    ps = per_audit_results[cur_audit]['ps']
    precinct_costs = per_audit_results[cur_audit]['precinct_costs']
    plt.plot(ps,np.array(precinct_costs), linestyle=all_audit_specific_items[cur_audit]['linestyle'],
        color=all_audit_specific_items[cur_audit]['color'],
        marker=all_audit_specific_items[cur_audit]['marker'], label=audit_labels[cur_audit])
    i += 1
plt.xlabel('Stopping Probability, p')
plt.ylabel('Average Cost')
#plt.yscale('log')
plt.title('Round cost '+str(newroundcost)+' and precinct cost '+str(precinctcost))
plt.legend(loc='upper right')
plt.tight_layout()
plt.show() 

# optimals ps for all three audits
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
    balcost = 1
    minimizing_ps = []
    minimal_costs = []
    roundcosts = np.linspace(1,100000,num = 100)#[1, 10, 100, 1000, 10000]

    for roundcost in roundcosts:
        # compute expected costs for each round schedule (parameterized by p):
        numbals = np.array(numbals)
        numrounds = np.array(numrounds)
        costs = balcost * numbals + roundcost * numrounds

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
    plt.plot(roundcosts, optimums[cur_audit]['minimizing_ps'],  linestyle=all_audit_specific_items[cur_audit]['linestyle'],
        color=all_audit_specific_items[cur_audit]['color'],
         label=audit_labels[cur_audit])
    i += 1
plt.xlabel('Round Cost, $c_r$')
plt.ylabel('Stopping Probability, $p$')
plt.title('Optimal stopping probability $p$') 
plt.xscale('log')
plt.legend(loc='upper left')
plt.tight_layout()
plt.show()

# minimal costs
font = {'size'   : 17}
plt.rc('font', **font)
i = 0
for cur_audit in audits:
    plt.plot(roundcosts, np.array(optimums[cur_audit]['minimal_costs']) / np.array(optimums['minerva2']['minimal_costs']), linestyle=all_audit_specific_items[cur_audit]['linestyle'],
        color=all_audit_specific_items[cur_audit]['color'],
 label=audit_labels[cur_audit])
    i += 1
plt.xlabel('Round Cost, $c_r$')
plt.ylabel('Optimal cost')
plt.title('Optimal cost as fraction of Providence cost') 
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
    precinct_costs = per_audit_results[cur_audit]['precinct_costs']
    #plt.plot(ps,np.array(precinct_costs),linestyle='--', marker=markers[i], color=colors[i], label=audit_labels[cur_audit])
    audit = cur_audit
    costs = per_audit_results[audit]['costs']
    numbals = per_audit_results[audit]['expbals']
    numrounds = per_audit_results[audit]['exprounds']
    balcost = 1
    roundcost = 1000
    minimizing_ps = []
    minimal_costs = []
    precinctcosts = np.linspace(0,5,num=100)#[1, 10, 100, 1000, 10000]

    for precinctcost in precinctcosts:
        # compute expected costs for each round schedule (parameterized by p):
        numbals = np.array(numbals)
        numrounds = np.array(numrounds)
        #costs = balcost * numbals + roundcost * numrounds
        costs = balcost * numbals + roundcost * numrounds + distinct_precinct_samples * precinctcost

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
    plt.plot(precinctcosts, optimums[cur_audit]['minimizing_ps'], linestyle=all_audit_specific_items[cur_audit]['linestyle'],
        color=all_audit_specific_items[cur_audit]['color'], label=audit_labels[cur_audit])
    i += 1
plt.xlabel('Precinct Cost, $c_p$')
plt.ylabel('Stopping Probability, $p$')
plt.title('Optimal stopping probability $p$') 
plt.xscale('log')
plt.legend(loc='upper left')
plt.tight_layout()
plt.show()

# minimal costs
font = {'size'   : 17}
plt.rc('font', **font)
i = 0
for cur_audit in audits:
    plt.plot(precinctcosts, np.array(optimums[cur_audit]['minimal_costs']) / np.array(optimums['minerva2']['minimal_costs']), linestyle=all_audit_specific_items[cur_audit]['linestyle'],
        color=all_audit_specific_items[cur_audit]['color'], label=audit_labels[cur_audit])
    i += 1
plt.xlabel('Precinct Cost, $c_p$')
plt.ylabel('Optimal cost')
plt.title('Optimal cost as fraction of Providence cost') 
plt.legend(loc='upper left')
plt.xscale('log')
plt.tight_layout()
plt.show()












