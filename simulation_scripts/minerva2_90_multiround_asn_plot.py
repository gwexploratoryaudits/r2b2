"""Generates plots for the 90% sprob multiround Minerva2 risk, stopping probability sims."""

import matplotlib.pyplot as plt

from r2b2.simulator import DBInterface
from r2b2.simulator import histogram
from r2b2.tests.util import parse_election

election = parse_election('data/2020_presidential/2020_presidential.json')

if __name__ == '__main__':
    db = DBInterface(port=27020,user='reader', pwd='icanread')
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
    plt.plot(margins, asns, 'bo')
    plt.xlabel('Reported Margin')
    title = 'Minerva 2.0 ASN (90% Stopping Probability Round Sizes)'
    plt.title(title)
    plt.ylabel('ASN')
    plt.grid()
    plt.show()
