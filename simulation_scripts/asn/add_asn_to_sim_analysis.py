"""
Adds the ASN of an audit to its analysis in the simulation database.

Computes ASN using the audits with the underlying distribution same as reported.

Assumes that audits after 'considered_rounds' proceed to a full hand count 
(thus sampling all relevant contest ballots).
"""

import matplotlib.pyplot as plt

from r2b2.simulator import DBInterface
from r2b2.simulator import histogram
from r2b2.tests.util import parse_election

election = parse_election('../data/2020_presidential/2020_presidential.json')

if __name__ == '__main__':
    db = DBInterface(port=27018,user='reader', pwd='icanread')
    margins = []
    asns = []

    # We may have run it for more, but when we compute ASN, we will assume
    # that after considered_rounds rounds, election officials proceed to a 
    # full hand count. For audits the proceed to a full hand count, we assign
    # the total number of relevant ballots in the contest when computing ASN.
    considered_rounds = 3

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
            'description': 'Multi round Minerva (90% then 1.0x)',
            'invalid_ballots': True,
            'sample_mult':1.0,
        })
        if sprob_sim is None:
            # For several low margin states, we didn't run simulations
            continue
        trials = db.trial_lookup(sprob_sim['_id'])

        sample_nums = []
        for trial in trials:
            if not trial['stop'] or len(trial['relevant_sample_size_sched']) > 3: # (Make sure it actually did stop)
                tot_rel_bals = sum(election.contests[contest].tally.values())
                sample_num = tot_rel_bals
            else:
                # NOTE that the 'relevant_sample_size_sched' is in fact the cumulative round schedule of relevant ballots
                sample_num = trial['relevant_sample_size_sched'][-1]
            sample_nums.append(sample_num)

        asn = sum(sample_nums) / len(sample_nums)
        print("margin:",margin," asn:",asn)

        # TODO Add this asn value to the analysis entry of this simulation in the database
        # TODO later

        # Append to lists
        margins.append(margin)
        asns.append(asn)

    # Plot the ASNs for the various margins
    plt.plot(margins, asns, 'bo')
    plt.xlabel('Margin')
    title = 'Experimental ASN for Various Margins (Minerva, 90% then 1.5x)'
    plt.title(title)
    plt.ylabel('Experimental ASN')
    plt.grid()
    plt.show()


    print(asns)
    print(margins)

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

