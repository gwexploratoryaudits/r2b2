"""Generates plots for the 90% sprob multiround Minerva2 risk, stopping probability sims."""

import matplotlib.pyplot as plt
plt.rcParams['mathtext.fontset'] = 'stix'
plt.rcParams['font.family'] = 'STIXGeneral'


from r2b2.simulator import DBInterface
from r2b2.simulator import histogram
from r2b2.tests.util import parse_election

election = parse_election('data/2020_presidential/2020_presidential.json')

if __name__ == '__main__':
    db = DBInterface(port=27018,user='reader', pwd='icanread')
    risks = []
    risk_stops = []
    sprobs = []
    sprob_stops = []
    ratios = []
    margins = []

    #max_rounds = 100

    for contest in election.contests:
        audit_id = db.audit_lookup('minerva2', 0.1)
        reported_id = db.contest_lookup(election.contests[contest], qapp={'description': '2020 Presidential'})
        tied_sim = db.db.simulations.find_one({
            'reported': reported_id,
            'underlying': 'tie',
            'audit': audit_id,
            'description': 'Multiround Minerva2 (90%) Corrected',
            'invalid_ballots': True,
            'sample_sprob':.9,
            'max_rounds': 5
        })
        if tied_sim is None:
            # For several low margin states, we didn't run simulations
            continue
        sprob_sim = db.db.simulations.find_one({
            'reported': reported_id,
            'underlying': 'reported',
            'audit': audit_id,
            'description': 'Multiround Minerva2 (90%) Corrected',
            'invalid_ballots': True,
            'sample_sprob':.9,
            'max_rounds': 100
        })
        if sprob_sim is None:
            # Some low margin states were not used
            continue

        risk_analysis = tied_sim['analysis']
        risks.append(risk_analysis['risk_by_round'])
        risk_stops.append(risk_analysis['stopped_by_round'])
        print(risk_analysis)

        sprob_analysis = sprob_sim['analysis']
        sprobs.append(sprob_analysis['sprob_by_round'])
        sprob_stops.append(sprob_analysis['stopped_by_round'])

        if sprob_analysis is None:
            print('no sprob analysis found')

        total_to_start = sprob_analysis['remaining_by_round'][0]

        winner_prop = election.contests[contest].tally[election.contests[contest].reported_winners[0]] / sum(
            election.contests[contest].tally.values())
        margins.append(winner_prop - (1.0 - winner_prop))

    """
    # Plot risks vs. margins
    for r in range (1,6):
        #risks_for_this_round = [] #conditional risks
        absolute_risks_for_this_round = [] #absolute risks
        for s in range(len(risks)):
            #risks_for_this_round.append(risks[s][r-1]) #conditional risks
            absolute_risk = risk_stops[s][r-1] / total_to_start
            absolute_risks_for_this_round.append(absolute_risk)
        # Uncomment the line below to fix the y-axis scale
        plt.ylim(0,.11)
        #plt.plot(margins, risks_for_this_round, 'bo') #conditional
        plt.plot(margins, absolute_risks_for_this_round, 'bo')
        plt.xlabel('Reported Margin')
        title = 'Round '+str(r)+' Experimental Absolute Risk (90% Minerva2)'
        plt.title(title)
        plt.ylabel('Experimental Risk')
        plt.grid()
        plt.show()
    """

    font = {'size'   : 17}
    plt.rc('font', **font)
    #plt.plot(ps,np.array(costs)/1000,linestyle='--', marker='o', color='b')
    #plt.xlabel('Stopping Probability, p')
    #plt.ylabel('Expected Cost (x$10^3$)')

    # Plot the total risk across all rounds
    total_risks = []
    for s in range(len(risks)):
        total_risk = sum(risk_stops[s]) / total_to_start
        total_risks.append(total_risk)
    if len(total_risks) == 0:
        print('no risks')
    plt.plot(margins, total_risks, 'bo')
    plt.xlabel('Reported Margin')
    title = 'Experimental Risk'
    plt.title(title)
    plt.ylim(0,.11)
    risk_limit = .1
    plt.axhline(y=risk_limit, color='b', linestyle='--', label='Risk Limit')
 
    plt.ylabel('Proportion that Stopped')
    plt.grid()
    plt.tight_layout()
    plt.show()

    """
    # Plot the total sprob across all rounds (this should just be 1... since we are
    # running the sprob trials to audit completion (100 rounds allowed...))
    total_sprobs = []
    for s in range(len(sprobs)):
        total_sprob = sum(sprob_stops[s]) / total_to_start
        total_sprobs.append(total_sprob)
    plt.plot(margins, total_sprobs, 'bo')
    plt.xlabel('Reported Margin')
    title = 'Experimental Total Stopping Probability (90% Minerva2)'
    plt.title(title)
    plt.ylabel('Experimental Stopping Probability')
    plt.grid()
    plt.show()

    # Plot absolute sprobs vs. margins
    for r in range (1,max_rounds+1):
        sprobs_for_this_round = [] #conditional sprobs
        absolute_sprobs_for_this_round = [] #absolute sprobs
        for s in range(len(sprobs)):
            absolute_sprob = sprob_stops[s][r-1] / total_to_start
            if absolute_sprob > 1:
                print('sprob_stops[s][r-1]', sprob_stops[s][r-1])
                print('total_to_start', total_to_start)
            absolute_sprobs_for_this_round.append(absolute_sprob)
        # Uncomment the line below to fix the y-axis scale
        #plt.ylim(.65,1)
        #plt.plot(margins, sprobs_for_this_round, 'bo')
        plt.plot(margins, absolute_sprobs_for_this_round, 'bo')
        plt.xlabel('Reported Margin')
        title = 'Round '+str(r)+' Experimental Absolute Stopping Probability (90% Minerva2)'
        plt.title(title)
        plt.ylabel('Experimental Stopping Probability')
        plt.grid()
        plt.show()

    # Plot conditional sprobs vs. margins
    #for r in range (1,max_rounds+1):
    for r in range (1,5+1):
        sprobs_for_this_round = [] #conditional sprobs
        absolute_sprobs_for_this_round = [] #absolute sprobs
        plot_margins = []
        for s in range(len(sprobs)):
            if sprobs[s][r-1] != -1: # aka as long as we have a meaningful sprob
                sprobs_for_this_round.append(sprobs[s][r-1]) #conditional sprobs
                plot_margins.append(margins[s])
        # Uncomment the line below to fix the y-axis scale
        #plt.ylim(.65,1)
        plt.plot(plot_margins, sprobs_for_this_round, 'bo')
        plt.xlabel('Reported Margin')
        title = 'Round '+str(r)+' Conditional Stopping Probability (90% Providence)'
        plt.title(title)
        plt.ylabel('Experimental Conditional Stopping Probability')
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
        title = 'Round '+str(r)+' Experimental Minerva2 Ratio (90% Minerva2)'
        plt.title(title)
        plt.ylabel('Experimental Minerva2 Ratio')
        plt.grid()
        plt.show()

    """
    # Plot first 3 rounds conditional sprobs vs. margins

    colors= ['b','r','g','c','m']
    markers = ['o','x','s','d','*']
    for r in range (1,5+1-2):
        sprobs_for_this_round = [] #conditional sprobs
        absolute_sprobs_for_this_round = [] #absolute sprobs
        plot_margins = []
        for s in range(len(sprobs)):
            if sprobs[s][r-1] != -1: # aka as long as we have a meaningful sprob
                sprobs_for_this_round.append(sprobs[s][r-1]) #conditional sprobs
                plot_margins.append(margins[s])
        avg_for_this_round = sum(sprobs_for_this_round) / len(sprobs_for_this_round)
        print('average for round'+str(r))
        print(avg_for_this_round)
        # Uncomment the line below to fix the y-axis scale
        #plt.ylim(.65,1)
        plt.plot(plot_margins, sprobs_for_this_round, marker=markers[r-1], color=colors[r-1], label='Round '+str(r), linestyle='None')
        plt.xlabel('Reported Margin')
        title = 'Experimental Stopping Probability'
        #plt.title(title)
        plt.ylabel('Proportion that Stopped')
        plt.grid()
        #plt.axhline(y=avg_for_this_round, color=colors[r-1], linestyle='--')#, label='Average for Round '+str(r))
    #plt.axhline(y=.9, color='black', linestyle='--')
    #plt.legend(bbox_transform=fig., loc='upper left')
    plt.legend(loc=(0,1),mode='expand',ncol=3,title = 'Experimental Stopping Probability',frameon=False)
    plt.tight_layout()
    plt.show()


