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

def estimate_min(xs, ys):
    """
    given a sparse, discrete sampling of a continuous function, estimate
    the minimum of that function.

    useful when computing additional values of the function is difficult for 
    some reason. in our case that is because the function value is determined by 10^4
    trials of simulated audits which are relatively expensive.

    assumes xs are given in increasing order (could easily be modified to make this
    assumption not necessary by just sorting the lists upon arrival)

    returns the x value of the minimum
    """
    assert len(xs)==len(ys)
    xsl = list(xs)
    ysl = list(ys)
    xs = np.array(xs)
    ys = np.array(ys)

    ym = min(ysl)
    ymix = ysl.index(min(ysl))
    xm = xs[ymix]

    if ymix - 1 < 0:
        return xm
    if ymix + 1 >= len(xs):
        return xm

    # estimate first derivative around xm
    fd1 = (ys[ymix + 1] - ys[ymix]) / (xs[ymix + 1] - xs[ymix])
    fd2 = (ys[ymix] - ys[ymix - 1]) / (xs[ymix] - xs[ymix - 1])
    fd3 = (ys[ymix + 1] - ys[ymix - 1]) / (xs[ymix + 1] - xs[ymix - 1])
    fd = (fd1+fd2+fd3)/3
    
    # estimate second derivative around xm
    sd = (fd1 - fd2) / ((xs[ymix + 1] - xs[ymix - 1])/2)

    # estimate the function's values moving from the minimum point
    # to the second lowest point taking very small steps which will
    # first go down then start to rise.. when that happens we've found
    # the minimum as far as the estimate is concerned... make 
    # estimations using a degree 2 taylor polynomial
    divisions = 100
    if ys[ymix + 1] > ys[ymix - 1]:
        dx = (ys[ymix + 1] - ys[ymix]) / divisions
    else:
        dx = -(ys[ymix + 1] - ys[ymix]) / divisions
    prevy = ys[ymix]
    x = xm
    while True:
        # could make the first derivative fd be a funciton of x where the weight 
        # of the average chenage or something like that
        x += dx
        yest = ys[ymix] + fd*(x - xm) / 1 + sd*(x-xm)^2 / 2 # taylor series
        if yest > prevy:
            return yest
        prevy = yest

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

    return x_min



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
        if -1 not in sprobs:# plot the value of p which minimizes the workload for various values of 
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


# cost parameter roundcost
# TODO this could linearly interpolate to get better/smoother answers
balcost = 1
minimizing_ps = []
roundcosts = np.linspace(1,10000,num = 100000)#[1, 10, 100, 1000, 10000]
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
    minimizing_ps.append(estimate_min2(plotps, costs))

font = {'size'   : 17}
plt.rc('font', **font)
plt.plot(roundcosts, minimizing_ps, linestyle='-', color='b')
plt.xlabel('Round Cost, $c_r$')
plt.ylabel('Stopping Probability, $p$')
plt.xscale('log')
plt.tight_layout()
plt.show()


