"""Generates plots for the 90% multiround EOR_BRAVO risk, stopping probability sims."""

import matplotlib.pyplot as plt

from r2b2.simulator import DBInterface
from r2b2.simulator import histogram
from r2b2.tests.util import parse_election

election = parse_election('../data/2020_presidential/2020_presidential.json')

if __name__ == '__main__':
    db = DBInterface(port=27018,user='reader', pwd='icanread')
    risks = []
    risk_stops = []
    ratios = []
    margins = []

    risk_limit = .1

    total_to_start = 10000

    max_rounds = 5

    for contest in election.contests:
        audit_id = db.audit_lookup('so_bravo', 0.1)
        reported_id = db.contest_lookup(election.contests[contest], qapp={'description': '2020 Presidential'})
        tied_sim = db.db.simulations.find_one({
            'reported': reported_id,
            'underlying': 'tie',
            'audit': audit_id,
            'description': 'Multiround SO_BRAVO (90%)',
            'invalid_ballots': True,
            'sample_sprob':.9,
            'max_rounds': max_rounds
        })
        if tied_sim is None:
            # For several low margin states, we didn't run simulations
            continue
        if 'analysis' not in tied_sim.keys():
            continue

        risk_analysis = tied_sim['analysis']
        risks.append(risk_analysis['risk_by_round'])
        risk_stops.append(risk_analysis['stopped_by_round'])

        total_to_start = risk_analysis['remaining_by_round'][0]

        winner_prop = election.contests[contest].tally[election.contests[contest].reported_winners[0]] / sum(
            election.contests[contest].tally.values())
        margins.append(winner_prop - (1.0 - winner_prop))

    # Plot the total risk across all rounds
    total_risks = []
    for s in range(len(risks)):
        total_risk = sum(risk_stops[s]) / total_to_start
        total_risks.append(total_risk)
    plt.plot(margins, total_risks, 'bo')
    plt.xlabel('Reported Margin')
    title = 'Proportion of Audits that Stopped (across 5 rounds) (SO BRAVO, Tie)'
    plt.title(title)
    plt.ylabel('Proportion that Stopped')
    plt.grid()
    plt.ylim(0,.11)
    plt.axhline(y=risk_limit, color='b', linestyle='--', label='Risk Limit')
    plt.show()




