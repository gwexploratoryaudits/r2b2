"""
Plots the stopping probability of each audit versus the number of ballots sampled.
"""

import matplotlib.pyplot as plt

from r2b2.simulator import DBInterface
from r2b2.simulator import histogram
from r2b2.tests.util import parse_election

election = parse_election('../data/2020_presidential/2020_presidential.json')

# function to get the 
def get_lists(audit_name, description, max_rounds=None):
    avg_sampled_minerva_1p0 = [ [] for _ in range(5) ] 
    abs_sprob_minerva_1p0 = [ [] for _ in range(5) ] 
    margins = []
    for contest in election.contests:
        audit_id = db.audit_lookup(audit_name, 0.1)
        reported_id = db.contest_lookup(election.contests[contest], qapp={'description': '2020 Presidential'})
        winner_prop = election.contests[contest].tally[election.contests[contest].reported_winners[0]] / sum(
            election.contests[contest].tally.values())
        margin = winner_prop - (1.0 - winner_prop)
        if max_rounds is None:
            sprob_sim = db.db.simulations.find_one({
                'reported': reported_id,
                'underlying': 'reported',
                'audit': audit_id,
                'description': description,
                'invalid_ballots': True
            })
        else:
            sprob_sim = db.db.simulations.find_one({
                'reported': reported_id,
                'underlying': 'reported',
                'audit': audit_id,
                'description': description,
                'invalid_ballots': True,
                'max_rounds':max_rounds
            })
        if sprob_sim is None:
            # For several low margin states, we didn't run simulations
            continue
        sim_id = sprob_sim['_id']
        margins.append(margin)
        if 'analysis' not in sprob_sim.keys():
            continue
        analysis = sprob_sim['analysis']
        if 'avg_sampled_by_round' not in analysis.keys():
            continue
        for i in range(5):
            avg_sampled_minerva_1p0[i].append(analysis['avg_sampled_by_round'][i])
        stopped_so_far = 0
        total_to_start = analysis['remaining_by_round'][0]
        for i in range(5):
            stopped_so_far += analysis['stopped_by_round'][i]
            abs_sprob_minerva_1p0[i].append(stopped_so_far / total_to_start)

    # index by margin rather than round
    points_by_margin = []
    for m in range(len(avg_sampled_minerva_1p0[0])):
        sprobs_for_m = []
        samnums_for_m = []
        for i in range(5):
            sprobs_for_m.append(avg_sampled_minerva_1p0[i][m])
            samnums_for_m.append(abs_sprob_minerva_1p0[i][m])
        points_by_margin.append((sprobs_for_m, samnums_for_m))

    return points_by_margin, margins

if __name__ == '__main__':
    db = DBInterface(port=27018,user='reader', pwd='icanread')
    colors= ['b','r','g','c','m']
    markers = ['o','x','s','d','*']
 
    # MINERVA 1.0X 
    minerva1p0_points, margins = get_lists('minerva', 'Multi round Minerva (90% then 1.0x)')
    minerva1p0_name = 'Minerva, 90% then 1.5x'
    for m in range(len(minerva1p0_points)):
        if m >= len(colors):
            break
        plt.plot(minerva1p0_points[m][0], minerva1p0_points[m][1], colors[m]+markers[m], label=minerva1p0_name+': Margin '+str(round(margins[m], 2)))

    """
    # SO BRAVO
    so_bravo_points = get_lists('so_bravo', 'Multiround SO_BRAVO (90%)', max_rounds=100) # a few old 5 round so bravo sprob sims in db
    so_bravo_name = 'SO BRAVO, 90%'
    for m in range(len(so_bravo_points)):
        if m >= len(colors):
            break
        plt.plot(so_bravo_points[m][0], so_bravo_points[m][1], colors[m]+markers[m], label=eor_bravo_name+': Margin '+str(round(margins[m], 2)))

    # EOR BRAVO
    eor_bravo_points = get_lists('eor_bravo', 'Multiround EOR_BRAVO (90%) Corrected')
    eor_bravo_name = 'EOR BRAVO, 90%'
    for m in range(len(so_bravo_points)):
        if m >= len(colors):
            break
        plt.plot(so_bravo_points[m][0], so_bravo_points[m][1], colors[m]+markers[m], label=so_bravo_name+': Margin '+str(round(margins[m], 2)))
    """

    title = 'Proportion of Audits that Stopped vs. Average Number of Ballots Sampled '
    plt.title(title)
    plt.xlabel('Average Number of Ballots Sampled')
    plt.ylabel('Proportion of Audits that Stopped')
    plt.grid()
    plt.legend()
    plt.show()