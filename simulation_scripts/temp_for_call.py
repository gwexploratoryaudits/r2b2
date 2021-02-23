"""Generates plots, histograms for the 1-round Minerva risk, stopping probability sims."""

import matplotlib.pyplot as plt

from r2b2.simulator import DBInterface
from r2b2.simulator import histogram
from r2b2.tests.util import parse_election

election = parse_election('data/2020_presidential/2020_presidential.json')

if __name__ == '__main__':
    risks = []
    sprobs = []
    ratios = []
    margins = []
    dc_risk = 0.0
    dc_sprob = 0.0

    with open 'data.json' as data:
    for contest in election.contests:
        if contest == 'Georgia' or contest == 'Wisconsin' or contest == 'Arizona':
            continue

        audit_id = db.audit_lookup('minerva', 0.1)
        reported_id = db.contest_lookup(election.contests[contest], qapp={'description': '2020 Presidential'})
        tied_sim = db.db.simulations.find_one({
            'reported': reported_id,
            'underlying': 'tie',
            'audit': audit_id,
            'description': 'Two round Minerva (90% then 1.5x) (2020)',
            'invalid_ballots': True,
            'sample_mult':1.5,
            'max_rounds':2
        })
        if tied_sim is None:
            # For several low margin states, we didn't run simulations
            continue
        """
        sprob_sim = db.db.simulations.find_one({
            'reported': reported_id,
            'underlying': 'reported',
            'audit': audit_id,
            'description': 'Stopping Probability 90%: One round Minerva with given sample size (from PV MATLAB)',
            'invalid_ballots': True
        })
        """

        risks.append(tied_sim['analysis'])
        """
        sprobs.append(sprob_sim['analysis'])
        ratios.append(sprob_sim['analysis'] / tied_sim['analysis'])
        """

        winner_prop = election.contests[contest].tally[election.contests[contest].reported_winners[0]] / sum(
            election.contests[contest].tally.values())
        margins.append(winner_prop - (1.0 - winner_prop))

        if contest == 'District of Columbia':
            dc_risk = tied_sim['analysis']
            """
            dc_sprob = sprob_sim['analysis']
            """

    # Plot risks vs. margins
    plt.plot(margins, risks, 'bo')
    plt.xlabel('Reported Margin')
    plt.ylabel('Experimental Risk (One-round Minerva, Alpha=10%)')
    plt.grid()
    plt.show()

    """
    # Plot sprobs vs. margins
    plt.plot(margins, sprobs, 'bo')
    plt.xlabel('Reported Margin')
    plt.ylabel('Experimental Stopping Probability (90% One-Round Minerva)')
    plt.grid()
    plt.show()

    # Plot ratio vs. margin
    plt.plot(margins, ratios, 'bo')
    plt.xlabel('Reported Margin')
    plt.ylabel('Ratio Stop. Prob. to Risk (90% One-round Minerva, Alpha=10%)')
    plt.grid()
    plt.show()

    # Histogram of sprobs
    histogram(sprobs, 'Stopping Probabilities (90% One-round Minerva)', bins=20)

    """

    # Histogram of risks
    histogram(risks, 'Experimental Risks (One-round Minerva, Alpha=10%)', bins=20)

    # Analysis
    avg_risk = 'Average Risk: {:%}\n'.format(sum(risks) / len(risks))
    """
    avg_sprob = 'Average Stopping Prob: {:%}\n'.format(sum(sprobs) / len(sprobs))
    no_dc_risk = 'Average Risk (without DC): {:%}\n'.format((sum(risks) - dc_risk) / (len(risks) - 1))
    no_dc_sprob = 'Average Stopping Prob (without DC): {:%}\n'.format((sum(sprobs) - dc_sprob) / (len(sprobs) - 1))
    print(avg_risk + avg_sprob + no_dc_risk + no_dc_sprob)
    """
