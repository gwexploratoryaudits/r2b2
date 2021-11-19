"""Generates plots for the 90% sprob multiround EOR_BRAVO risk, stopping probability sims."""

import matplotlib.pyplot as plt

from r2b2.simulator import DBInterface
from r2b2.simulator import histogram
from r2b2.tests.util import parse_election

election = parse_election('../data/2020_presidential/2020_presidential.json')

if __name__ == '__main__':
    db = DBInterface(port=27020,user='reader', pwd='icanread')
    risks = []
    risk_stops = []
    sprobs = []
    sprob_stops = []
    ratios = []
    margins = []

    total_to_start = 10000

    max_rounds = 5

    for contest in election.contests:
        audit_id = db.audit_lookup('eor_bravo', 0.1)
        reported_id = db.contest_lookup(election.contests[contest], qapp={'description': '2020 Presidential'})
        tied_sim = db.db.simulations.find_one({
            'reported': reported_id,
            'underlying': 'tie',
            'audit': audit_id,
            'description': 'Multiround EOR_BRAVO (90%) Corrected',
            'invalid_ballots': True,
            'sample_sprob':.9,
            'max_rounds': max_rounds
        })
        if tied_sim is None:
            # For several low margin states, we didn't run simulations
            continue
        sprob_sim = db.db.simulations.find_one({
            'reported': reported_id,
            'underlying': 'reported',
            'audit': audit_id,
            'description': 'Multiround EOR_BRAVO (90%) Corrected',
            'invalid_ballots': True,
            'sample_sprob':.9,
            'max_rounds': max_rounds+95
        })

        if 'analysis' not in tied_sim.keys():
            continue

        risk_analysis = tied_sim['analysis']
        risks.append(risk_analysis['risk_by_round'])
        risk_stops.append(risk_analysis['stopped_by_round'])

        sprob_analysis = sprob_sim['analysis']
        sprobs.append(sprob_analysis['sprob_by_round'])
        sprob_stops.append(sprob_analysis['stopped_by_round'])

        total_to_start = risk_analysis['remaining_by_round'][0]

        winner_prop = election.contests[contest].tally[election.contests[contest].reported_winners[0]] / sum(
            election.contests[contest].tally.values())
        margins.append(winner_prop - (1.0 - winner_prop))


    # Plot conditional sprobs vs. margins
    colors= ['b','r','g','c','m']
    markers = ['o','x','s','d','*']
    for r in range (1,max_rounds+1-2):
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
        title = 'Proportion of Audits that Stopped by Round (EoR BRAVO, Reported)'
        plt.title(title)
        plt.ylabel('Proportion that Stopped')
        plt.grid()
        plt.axhline(y=avg_for_this_round, color=colors[r-1], linestyle='--', label='Average for Round '+str(r))
    #plt.axhline(y=.9, color='black', linestyle='--')
    plt.legend(loc='lower right')
    plt.show()


