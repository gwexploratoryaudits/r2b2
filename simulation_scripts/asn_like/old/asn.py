"""
Finds the equivalent to ASN for Minerva using the 90% sprob round size
simulations in the Nimbus simulation database. (1 million trials each
2020 presidential state)
"""

import matplotlib.pyplot as plt

from r2b2.simulator import DBInterface
from r2b2.simulator import histogram
from r2b2.tests.util import parse_election

election = parse_election('data/2020_presidential/2020_presidential.json')

if __name__ == '__main__':
    db = DBInterface(port=27020,user='reader', pwd='icanread')
    margins = []
    asns = []

    # We may have run it for more, but when we compute ASN, we will assume
    # that after considered_rounds rounds, election officials proceed to a 
    # full hand count. For audits the proceed to a full hand count, we assign
    # the total number of relevant ballots in the contest when computing ASN.
    considered_rounds = 5

    for contest in election.contests:
        audit_id = db.audit_lookup('minerva', 0.1)
        reported_id = db.contest_lookup(election.contests[contest], qapp={'description': '2020 Presidential'})
        winner_prop = election.contests[contest].tally[election.contests[contest].reported_winners[0]] / sum(
            election.contests[contest].tally.values())
        margin = winner_prop - (1.0 - winner_prop)
        sprob_sim = db.db.simulations.find_one({
            'reported': reported_id,
            'underlying': 'reported',
            'audit': audit_id,
            'description': 'Multiround Minerva (90%)',
            'invalid_ballots': True,
            'sample_sprob':.9,
        })
        if sprob_sim is None:
            # For several low margin states, we didn't run simulations
            continue
        trials = db.trial_lookup(sprob_sim['_id'])

        sample_nums = []
        for trial in trials:
            if not trial['stop']: # (Make sure it actually did stop)
                print("one didn't stop")
                continue
            sample_num = sum(trial['relevant_sample_size_sched'])
            sample_nums.append(sample_num)

        asn = sum(sample_nums) / len(sample_nums)
        print("margin:",margin," asn:",asn)

        # Append to lists
        margins.append(margin)
        asns.append(asn)

    # Plot the ASNs for the various margins
    plt.plot(margins, asns, 'bo')
    plt.xlabel('Margin')
    title = 'Experimental ASN for Various Margins (90% Minerva)'
    plt.title(title)
    plt.ylabel('Experimental ASN')
    plt.grid()
    plt.show()

"""
import re
import json

asnfile = open('asn.txt')
asnlines = asnfile.readlines()

data = {}
data['margins'] = []
data['minerva_asns'] = []

for line in asnlines:
    if "didn't" in line:
        continue
    margin = float(line[8:line.index("asn")-1])
    asn = float(line[line.index("asn") + 5:])

    data['margins'].append(margin)
    data['minerva_asns'].append(asn)

    #print(margin)
    #print(asn)

with open('asn.json', 'w') as outfile:
    json.dump(data, outfile)

"""

