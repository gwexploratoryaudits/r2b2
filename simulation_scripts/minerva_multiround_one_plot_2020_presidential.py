"""Generates plots, histograms for the 1-round Minerva risk, stopping probability sims."""

import matplotlib.pyplot as plt

from r2b2.simulator import DBInterface
from r2b2.simulator import histogram
from r2b2.tests.util import parse_election

election = parse_election('data/2020_presidential/2020_presidential.json')

if __name__ == '__main__':
    db = DBInterface(port=27020,user='reader', pwd='icanread')
    risks = []
    sprobs = []
    #ratios = []
    margins = []

    max_rounds = 5

    for contest in election.contests:
        audit_id = db.audit_lookup('minerva', 0.1)
        reported_id = db.contest_lookup(election.contests[contest], qapp={'description': '2020 Presidential'})
        tied_sim = db.db.simulations.find_one({
            'reported': reported_id,
            'underlying': 'tie',
            'audit': audit_id,
            'description': 'Multi round Minerva (90% then 1.5x)',
            'invalid_ballots': True,
            'sample_mult':1.5,
            'max_rounds': max_rounds
        })
        if tied_sim is None:
            # For several low margin states, we didn't run simulations
            continue
        sprob_sim = db.db.simulations.find_one({
            'reported': reported_id,
            'underlying': 'reported',
            'audit': audit_id,
            'description': 'Multi round Minerva (90% then 1.5x)',
            'invalid_ballots': True
        })

        risks.append(tied_sim['analysis']['risk_by_round'])

        sprobs.append(sprob_sim['analysis']['sprob_by_round'])

        winner_prop = election.contests[contest].tally[election.contests[contest].reported_winners[0]] / sum(
            election.contests[contest].tally.values())
        margins.append(winner_prop - (1.0 - winner_prop))

    # PLOT THE RISKS
    plt.ylim(0,.1)
    colors= ['b','r','g','c','m']
    markers = ['o','x','s','d','*']
    fig = plt.figure()
    ax = fig.add_subplot(111)

    # Plot risks vs. margins
    for r in range (1,max_rounds+1):
        risks_for_this_round = []
        for s in range(len(risks)):
            risks_for_this_round.append(risks[s][r-1])
        ax.scatter(margins, 
                   risks_for_this_round, 
                   s=len(margins),
                   c=colors[r-1], 
                   marker=markers[r-1], 
                   label='Round'+str(r))
    
    title = '5 Rounds Experimental Risks (90% then 1.5x Minerva)'
    plt.title(title)
    plt.ylabel('Experimental Risk')
    plt.xlabel('Reported Margin')
    plt.grid()
    plt.legend(loc='upper right')
    plt.show()

    # PLOT THE SPROBS
    plt.ylim(.65,.95)
    colors= ['b','r','g','c','m']
    markers = ['o','x','s','d','*']
    fig = plt.figure()
    ax = fig.add_subplot(111)

    # Plot sprobs vs. margins
    for r in range (1,max_rounds+1):
        sprobs_for_this_round = []
        for s in range(len(sprobs)):
            sprobs_for_this_round.append(sprobs[s][r-1])
        ax.scatter(margins, 
                   sprobs_for_this_round, 
                   s=len(margins),
                   c=colors[r-1], 
                   marker=markers[r-1], 
                   label='Round'+str(r))
    
    title = '5 Rounds Experimental Stopping Probability (90% then 1.5x Minerva)'
    plt.title(title)
    plt.ylabel('Experimental Stopping Probability')
    plt.xlabel('Reported Margin')
    plt.grid()
    plt.legend(loc='lower right')
    plt.show()


    """
    # Plot ratio vs. margin
    #plt.plot(margins, ratios, 'bo')
    plt.xlabel('Reported Margin')
    plt.ylabel('Ratio Stop. Prob. to Risk (90% One-round Minerva, Alpha=10%)')
    plt.grid()
    plt.show()

    # Histogram of sprobs
    histogram(sprobs, 'Stopping Probabilities (90% One-round Minerva)', bins=20)


    # Histogram of risks
    histogram(risks, 'Experimental Risks', bins=20)

    # Analysis
    avg_risk = 'Average Risk: {:%}\n'.format(sum(risks) / len(risks))
    avg_sprob = 'Average Stopping Prob: {:%}\n'.format(sum(sprobs) / len(sprobs))
    print(avg_risk + avg_sprob)
    """
