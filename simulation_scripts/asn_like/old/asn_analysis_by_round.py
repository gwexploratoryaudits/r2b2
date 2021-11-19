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
    db = DBInterface(port=27017,user='reader', pwd='icanread')
    margins = []
    asns3 = [] #asns assuming we did 3 rounds
    asns4 = [] #asns assuming we did 3 rounds
    asns5 = [] #asns assuming we did 3 rounds

    # We may have run it for more, but when we compute ASN, we will assume
    # that after considered_rounds rounds, election officials proceed to a 
    # full hand count. For audits the proceed to a full hand count, we assign
    # the total number of relevant ballots in the contest when computing ASN.
    #considered_rounds = 3,4,5
    margins.append([])
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
        sim_id = sprob_sim['_id']
        if sprob_sim is None:
            # For several low margin states, we didn't run simulations
            continue
        anal = sprob_sim['analysis']
        trials = db.trial_lookup(sprob_sim['_id'])

        """
        sample_nums3 = []
        sample_nums4 = []
        sample_nums5 = []
        """
        avg_sampled = [ [] ] * 5 #an empty list for each round
        for trial in trials:
            # Now instead of using just ASN, we are looking at the average number
            # of ballots sampled cumulatively through each round...

            # The first round is always drawn
            sampled[0] = trial['relevant_sample_size_sched'][0]

            # Then subsequent rounds may require more ballots for some audits
            for i in range(1,len(avg_sampled)):
                if len(trial['relevant_sample_size_sched']) > i: 
                    # If this audit went this far, we add the new ballots to the total
                    avg_sampled[i] = trial['relevant_sample_size_sched']
                else:
                    # Otherwise, the same number has been sampled so far
                    avg_sampled[i] = avg_sampled[i - 1]
                    


            """
            # While we're here, let's compute the ASN info too since we can
            if not trial['stop']:
                # This audit did not stop at all, so we had to sample all ballots in all cases
                tot_rel_bals = sum(election.contests[contest].tally.values())
                sample_nums5.append(tot_rel_bals)
                sample_nums4.append(tot_rel_bals)
                sample_nums3.append(tot_rel_bals)
            elif trial['round'] > 5:
                # The audit stopped after the 5th round, so sample_num 3 and 4 and 5 is all ballots
                tot_rel_bals = sum(election.contests[contest].tally.values())
                sample_nums5.append(tot_rel_bals)
                sample_nums4.append(tot_rel_bals)
                sample_nums3.append(tot_rel_bals)
            elif trial['round'] > 4:
                # The audit stopped after the 4th round, so sample_num 3 and 4 is all ballots
                # but sample_num5 stopped with just the sampled_ballots
                sampled_ballots = trial['relevant_sample_size_sched'][-1]
                tot_rel_bals = sum(election.contests[contest].tally.values())
                sample_nums5.append(sampled_ballots)
                sample_nums4.append(tot_rel_bals)
                sample_nums3.append(tot_rel_bals)
            elif trial['round'] > 3:
                # The audit stopped after the 3rd round, so sample_num 3 is all ballots
                # but sample_num 4 and 5 stopped with just the sampled_ballots
                sampled_ballots = trial['relevant_sample_size_sched'][-1]
                tot_rel_bals = sum(election.contests[contest].tally.values())
                sample_nums5.append(sampled_ballots)
                sample_nums4.append(sampled_ballots)
                sample_nums3.append(tot_rel_bals)
            else:
                # If we get to here, the audit stopped within the first 3 rounds. hip hip hurray
                # this means that only sampled_ballots were sampled in all these cases 
                # (3,4,or 5 round audits all concluded nicely)
                # 'relevant_sample_size_sched' is the cumulative round schedule of relevant ballots
                sample_num = trial['relevant_sample_size_sched'][-1]
                sample_nums3.append(sample_num)
                sample_nums4.append(sample_num)
                sample_nums5.append(sample_num)
            """

        """
        asn3 = sum(sample_nums3) / len(sample_nums3)
        asn4 = sum(sample_nums4) / len(sample_nums4)
        asn5 = sum(sample_nums5) / len(sample_nums5)
        print("margin:",margin,"  asn3:",asn3, "  asn4:",asn4,"  asn5:",asn5)

        # TODO Add this asn value to the analysis entry of this simulation in the database
        anal['asn_3rounds'] = asn3
        anal['asn_4rounds'] = asn4
        anal['asn_5rounds'] = asn5
        """

        # Update simulation entry to include analysis
        db.update_analysis(sim_id, anal)




"""
# Plot the ASNs for the various margins
#TODO
plt.plot(margins[cr_idx], asns[cr_idx], 'bo')
plt.xlabel('Margin')
title = 'Experimental ASN for Various Margins (Minerva, 90% then 1.5x)'
plt.title(title)
plt.ylabel('Experimental ASN')
plt.grid()
plt.show()


print(asns[cr_idx])
print(margins[cr_idx)
"""

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

