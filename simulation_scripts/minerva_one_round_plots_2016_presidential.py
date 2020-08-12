"""Generates plots, histograms for the 1-round Minerva risk, stopping probability sims."""

import json
import matplotlib.pyplot as plt

from r2b2.simulator import DBInterface
from r2b2.simulator import histogram
from r2b2.tests.util import parse_election

election = parse_election('data/2016_presidential.json')

if __name__ == '__main__':
    db = DBInterface(user='reader', pwd='icanread')
    risks = []
    sprobs = []
    margins = []
    
    for contest in election.contests:
        if contest == 'Michigan' or contest == 'New Hampshire':
            continue

        audit_id = db.audit_lookup('minerva', 0.1)
        reported_id = db.contest_lookup(election.contests[contest], qapp={'description': '2016 Presidential'})
        tied_sim  = db.db.simulations.find_one({'reported': reported_id, 'underlying': 'tie', 'audit': audit_id, 'description': 'One round Minerva with given sample size (from PV MATLAB)', 'invalid_ballots': True})
        sprob_sim = db.db.simulations.find_one({'reported': reported_id, 'underlying': 'reported', 'audit': audit_id, 'description': 'Stopping Probability 90%: One round Minerva with given sample size (from PV MATLAB)', 'invalid_ballots': True})

        risks.append(tied_sim['analysis'])
        sprobs.append(sprob_sim['analysis'])

        winner_prop = election.contests[contest].tally[election.contests[contest].reported_winners[0]]/sum(election.contests[contest].tally.values())
        margins.append(winner_prop - (1.0 - winner_prop))

    # Plot risks vs. margins
    plt.plot(margins, risks, 'bo')
    plt.xlabel('Reported Margin')
    plt.ylabel('Experimental Risk (One-round Minerva, Alpha=10%)')
    plt.grid()
    plt.show()

    # Plot sprobs vs. margins
    plt.plot(margins, sprobs, 'bo')
    plt.xlabel('Reported Margin')
    plt.ylabel('Experimental Stopping Probability (90% One-Round Minerva)')
    plt.grid()
    plt.show()

    # Histogram of sprobs
    histogram(sprobs, 'Stopping Probabilities (90% One-round Minerva)', bins=20)

    # Histogram of risks
    histogram(risks, 'Experimental Risks (One-round Minerva, Alpha=10%)', bins=20)

