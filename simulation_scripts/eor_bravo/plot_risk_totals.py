"""Generates plots for the 90% sprob multiround EOR_BRAVO risk, stopping probability sims."""

import matplotlib.pyplot as plt

from r2b2.simulator import DBInterface
from r2b2.simulator import histogram
from r2b2.tests.util import parse_election

election = parse_election('../data/2020_presidential/2020_presidential.json')

if __name__ == '__main__':
    db = DBInterface(port=27018,user='reader', pwd='icanread')
    risks_eor = []
    risks_so = []
    risk_stops_eor = []
    risk_stops_so = []
    sprobs = []
    sprob_stops_eor = []
    sprob_stops_so = []
    ratios = []
    margins = []
    margins_so = []

    risk_limit = .1

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
        risks_eor.append(risk_analysis['risk_by_round'])
        risk_stops_eor.append(risk_analysis['stopped_by_round'])

        total_to_start = risk_analysis['remaining_by_round'][0]

        winner_prop = election.contests[contest].tally[election.contests[contest].reported_winners[0]] / sum(
            election.contests[contest].tally.values())
        margins.append(winner_prop - (1.0 - winner_prop))

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
        risks_so.append(risk_analysis['risk_by_round'])
        risk_stops_so.append(risk_analysis['stopped_by_round'])

        total_to_start = risk_analysis['remaining_by_round'][0]

        winner_prop = election.contests[contest].tally[election.contests[contest].reported_winners[0]] / sum(
            election.contests[contest].tally.values())
        margins_so.append(winner_prop - (1.0 - winner_prop))

    # Plot SO risks
    total_risks_so = []
    for s in range(len(risks_so)):
        total_risk = sum(risk_stops_so[s]) / total_to_start
        total_risks_so.append(total_risk)
    plt.plot(margins_so, total_risks_so, 'bo', label='SO BRAVO')

    # Plot EoR risks
    total_risks_eor = []
    for s in range(len(risks_eor)):
        total_risk = sum(risk_stops_eor[s]) / total_to_start
        total_risks_eor.append(total_risk)
    plt.plot(margins, total_risks_eor, 'rx', label='EoR BRAVO')
 
    plt.xlabel('Reported Margin')
    title = 'Proportion of Audits that Stopped (SO and Eor BRAVO, Tie)'
    plt.title(title)
    plt.ylabel('Proportion that Stopped')
    plt.grid()
    plt.ylim(0,.11)
    plt.axhline(y=risk_limit, color='b', linestyle='--', label='Risk Limit')
    plt.legend()
    plt.show()
