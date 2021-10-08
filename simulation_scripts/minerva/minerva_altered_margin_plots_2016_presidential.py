"""Generates plots, histograms for the 1-round Minerva risk, stopping probability sims."""

import matplotlib.pyplot as plt

from r2b2.simulator import DBInterface
from r2b2.tests.util import parse_election

election = parse_election('data/2016_presidential.json')

if __name__ == '__main__':
    db = DBInterface(user='reader', pwd='icanread', port=27018)
    p10_avg_p_vals = []
    m10_avg_p_vals = []
    p10_sprobs = []
    m10_sprobs = []
    sprobs = []
    p10_margins = []
    m10_margins = []

    for contest in election.contests:
        if contest == 'Michigan' or contest == 'New Hampshire':
            continue

        audit_id = db.audit_lookup('minerva', 0.1)
        reported_id = db.contest_lookup(election.contests[contest], qapp={'description': '2016 Presidential'})

        plus10_sim = db.db.simulations.find_one({
            'reported': reported_id,
            'audit': audit_id,
            'description': 'Altered Margin+10%: One round Minerva with given sample size (from PV MATLAB)',
            'invalid_ballots': True
        })

        minus10_sim = db.db.simulations.find_one({
            'reported': reported_id,
            'audit': audit_id,
            'description': 'Altered Margin-10%: One round Minerva with given sample size (from PV MATLAB)',
            'invalid_ballots': True
        })

        sprob_sim = db.db.simulations.find_one({
            'reported': reported_id,
            'underlying': 'reported',
            'audit': audit_id,
            'description': 'Stopping Probability 90%: One round Minerva with given sample size (from PV MATLAB)',
            'invalid_ballots': True
        })

        p10_avg_p_vals.append(plus10_sim['analysis']['avg_p_value'])
        m10_avg_p_vals.append(minus10_sim['analysis']['avg_p_value'])
        p10_sprobs.append(plus10_sim['analysis']['sprob'])
        m10_sprobs.append(minus10_sim['analysis']['sprob'])
        sprobs.append(sprob_sim['analysis'])
        p10_margins.append(plus10_sim['underlying']['margin'])
        m10_margins.append(minus10_sim['underlying']['margin'])

    # Histogram of sprobs
    bins = 'auto'
    plt.hist(p10_sprobs, bins=bins, label='Margin+10%')
    plt.hist(m10_sprobs, bins=bins, label='Margin-10%')
    plt.hist(sprobs, bins=bins, label='Margin')
    plt.xlabel('Stopping Probabilities')
    plt.ylabel('Frequency')
    plt.grid(axis='y')
    plt.legend(loc='upper right')
    plt.savefig('minerva_altered_margin_sprob.svg')
