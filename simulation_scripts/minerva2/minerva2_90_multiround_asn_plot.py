"""Generates plots for the 90% sprob multiround Minerva2 risk, stopping probability sims."""

import matplotlib.pyplot as plt

from r2b2.simulator import DBInterface
from r2b2.simulator import histogram
from r2b2.tests.util import parse_election

election = parse_election('data/2020_presidential/2020_presidential.json')

if __name__ == '__main__':
    db = DBInterface(port=27018,user='reader', pwd='icanread')
    margins = []
    asns = []

    max_rounds = 100

    for contest in election.contests:
        audit_id = db.audit_lookup('minerva2', 0.1)
        reported_id = db.contest_lookup(election.contests[contest], qapp={'description': '2020 Presidential'})
        sprob_sim = db.db.simulations.find_one({
            'reported': reported_id,
            'underlying': 'reported',
            'audit': audit_id,
            'description': 'Multiround Minerva2 (90%)',
            'invalid_ballots': True,
            'sample_sprob':.9,
            'max_rounds': max_rounds
        })
        if sprob_sim is None:
            # Some low margin states were not used
            continue

        #TODO filter out asns that aren't numbers
        #if sprob_sim['analysis']['asn'] is not  (check
        # For now, assume that we have a valid asn (which we do in all tests so far)
        if 'asn' in sprob_sim['analysis'].keys():
            asns.append(sprob_sim['analysis']['asn'])

            winner_prop = election.contests[contest].tally[election.contests[contest].reported_winners[0]] / sum(
                election.contests[contest].tally.values())
            margins.append(winner_prop - (1.0 - winner_prop))

    # Plot conditional sprobs vs. margins
    # Plot the total risk across all rounds
    font = {'size'   : 17}
    plt.rc('font', **font)
    plt.plot(margins, asns, 'bo')
    plt.xlabel('Reported Margin')
    title = 'Minerva 2.0 ASN (90% Stopping Probability Round Sizes)'
    plt.title(title)
    plt.ylabel('ASN')
    plt.grid()
    plt.show()


"""
    # ref
   total_risks = []
    for s in range(len(risks)):
        total_risk = sum(risk_stops[s]) / total_to_start
        total_risks.append(total_risk)
    if len(total_risks) == 0:
 
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
        plt.plot(plot_margins, np.array(sprobs_for_this_round)*100, marker=markers[r-1], color=colors[r-1], label='Round '+str(r), linestyle='None')
        plt.xlabel('Reported Margin')
        title = 'Experimental Stopping Probability'
        #plt.title(title)
        plt.ylabel('Audits that Stopped (%)')
        plt.grid()
        #plt.axhline(y=avg_for_this_round, color=colors[r-1], linestyle='--')#, label='Average for Round '+str(r))
    #plt.axhline(y=.9, color='black', linestyle='--')
    #plt.legend(bbox_transform=fig., loc='upper left')
    plt.legend(loc=(0,1),mode='expand',ncol=3,title = 'Experimental Stopping Probability',frameon=False)
    plt.tight_layout(pad=0.2, w_pad=0.2, h_pad=1.0)
    plt.show()


"""
