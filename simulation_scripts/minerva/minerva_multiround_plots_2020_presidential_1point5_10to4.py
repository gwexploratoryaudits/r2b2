"""Generates plots, histograms for the 1-round Minerva risk, stopping probability sims."""

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

    total_to_start = 100000

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
            'invalid_ballots': True,
            'sample_mult':1.5,
            'max_rounds': max_rounds
        })

        risk_analysis = tied_sim['analysis']['10^4 analysis']
        risks.append(risk_analysis['risk_by_round'])
        risk_stops.append(risk_analysis['stopped_by_round'])

        sprob_analysis = sprob_sim['analysis']['10^4 analysis']
        sprobs.append(sprob_analysis['sprob_by_round'])
        sprob_stops.append(sprob_analysis['stopped_by_round'])

        total_to_start = risk_analysis['remaining_by_round'][0]

        winner_prop = election.contests[contest].tally[election.contests[contest].reported_winners[0]] / sum(
            election.contests[contest].tally.values())
        margins.append(winner_prop - (1.0 - winner_prop))

    """
    # Plot absolute risks vs. margins
    for r in range (1,max_rounds+1):
        #risks_for_this_round = [] #conditional risks
        absolute_risks_for_this_round = [] #absolute risks
        for s in range(len(risks)):
            #risks_for_this_round.append(risks[s][r-1]) #conditional risks
            absolute_risk = risk_stops[s][r-1] / total_to_start
            absolute_risks_for_this_round.append(absolute_risk)
        # Uncomment the line below to fix the y-axis scale
        #plt.ylim(0,.12)
        #plt.plot(margins, risks_for_this_round, 'bo') #conditional
        plt.plot(margins, absolute_risks_for_this_round, 'bo')
        plt.xlabel('Reported Margin')
        title = 'Round '+str(r)+' Experimental Risk (90% then 1.5x Minerva)'
        plt.title(title)
        plt.ylabel('Proportion of Audits that Stopped in Round '+str(r))
        plt.axhline(y=.1, label='Risk Limit', linestyle='--')
        plt.ylim(0,.11)
        plt.grid()
        plt.legend(loc='upper right')
        plt.show()
    # Plot the total risk across all rounds
    total_risks = []
    for s in range(len(risks)):
        total_risk = sum(risk_stops[s]) / total_to_start
        total_risks.append(total_risk)
    plt.plot(margins, total_risks, 'b+')
    plt.xlabel('Reported Margin')
    title = 'Proportion of Audits that Stopped (Minerva (1.5x), Tie)'
    plt.title(title)
    #plt.ylim(.04,.1)
    plt.ylim(0,.11)
    risk_limit = .1
    plt.axhline(y=risk_limit, color='b', linestyle='--', label='Risk Limit')
 
    plt.ylabel('Proportion that Stopped')
    plt.grid()
    plt.show()

    # Plot the total sprob across all rounds
    total_sprobs = []
    for s in range(len(sprobs)):
        total_sprob = sum(sprob_stops[s]) / total_to_start
        total_sprobs.append(total_sprob)
    plt.plot(margins, total_sprobs, 'bo')
    plt.xlabel('Reported Margin')
    title = 'Experimental Total Stopping Probability (across 5 rounds) (90% then 1.5x Minerva)'
    plt.title(title)
    plt.ylabel('Experimental Stopping Probability')
    plt.grid()
    plt.show()


    # Plot absolute sprobs vs. margins
    for r in range (1,max_rounds+1):
        sprobs_for_this_round = [] #conditional sprobs
        absolute_sprobs_for_this_round = [] #absolute sprobs
        for s in range(len(sprobs)):
            #sprobs_for_this_round.append(sprobs[s][r-1]) #conditional sprobs
            absolute_sprob = sprob_stops[s][r-1] / total_to_start
            absolute_sprobs_for_this_round.append(absolute_sprob)
        # Uncomment the line below to fix the y-axis scale
        #plt.ylim(.65,1)
        #plt.plot(margins, sprobs_for_this_round, 'bo')
        plt.plot(margins, absolute_sprobs_for_this_round, 'bo')
        plt.xlabel('Reported Margin')
        title = 'Round '+str(r)+' Experimental Absolute Stopping Probability (90% then 1.5x Minerva)'
        plt.title(title)
        plt.ylabel('Experimental Stopping Probability')
        plt.grid()
        plt.show()

    # Plot conditional sprobs vs. margins (sprob given that the audit reached the current round)
    for r in range (1,max_rounds+1):
        sprobs_for_this_round = [] #conditional sprobs
        for s in range(len(sprobs)):
            sprobs_for_this_round.append(sprobs[s][r-1]) #conditional sprobs
        # Uncomment the line below to fix the y-axis scale
        plt.ylim(.65,1)
        plt.plot(margins, sprobs_for_this_round, 'bo')
        plt.xlabel('Reported Margin')
        title = 'Round '+str(r)+' Stopping Probability (90% then 1.5x Minerva)'
        plt.title(title)
        plt.ylabel('Proportion of Audits that Stopped')
        plt.grid()
        plt.show()


    # Plot ratios vs. margins
    for r in range (1,max_rounds+1):
        ratios_for_this_round = []
        plot_margins = []
        for s in range(len(sprobs)):
            if sprob_stops[s][r-1] != 0:
                ratio = risk_stops[s][r-1] / sprob_stops[s][r-1]
                ratios_for_this_round.append(ratio)
                plot_margins.append(margins[s])
        # Uncomment the line below to fix the y-axis scale
        #plt.ylim(0,.12)
        plt.plot(plot_margins, ratios_for_this_round, 'bo')
        plt.xlabel('Reported Margin')
        title = 'Round '+str(r)+' Experimental Minerva Ratio (90% then 1.5x Minerva)'
        plt.title(title)
        plt.ylabel('Experimental Minerva Ratio')
        plt.grid()
        plt.show()

    # Plot first 3 rounds conditional sprobs vs. margins
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
        plt.plot(plot_margins, sprobs_for_this_round, marker=markers[r-1], color=colors[r-1], label='Round'+str(r), linestyle='None')
        plt.xlabel('Reported Margin')
        title = 'Conditional Stopping Probability by Round (90% EOR_BRAVO)'
        plt.title(title)
        plt.ylabel('Proportion of Audits that Stopped')
        plt.grid()
        plt.axhline(y=avg_for_this_round, color=colors[r-1], linestyle='--', label='Average for Round'+str(r))
    #plt.axhline(y=.9, color='black', linestyle='--')
    plt.legend(loc='lower right')
    plt.show()

    """
    # Plot first 3 rounds conditional sprobs vs. margins
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
        title = 'Proportion of Audits that Stopped by Round (Minerva (1.5x), Reported)'
        plt.title(title)
        plt.ylabel('Proportion that Stopped')
        plt.grid()
        plt.axhline(y=avg_for_this_round, color=colors[r-1], linestyle='--', label='Average for Round '+str(r))
    #plt.axhline(y=.9, color='black', linestyle='--')
    plt.legend(loc='lower right')
    plt.ylim(.63,.96)
    plt.show()


