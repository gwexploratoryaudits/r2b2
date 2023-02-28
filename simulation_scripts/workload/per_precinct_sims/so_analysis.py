"""
Finding the frequency with which we obtained samples that stopped by SO BRAVO condition but not
by the EOR BRAVO condition, meaning that they had the misleading sequence stopping situation arise.
"""

import matplotlib.pyplot as plt
import math
from r2b2.simulator import DBInterface
from r2b2.simulator import histogram
from r2b2.tests.util import parse_election
from r2b2.contest import Contest
from r2b2.contest import ContestType
import statistics

election = parse_election('../data/2020_presidential/2020_presidential.json')

if __name__ == '__main__':
    db = DBInterface(port=27017,user='writer', pwd='icanwrite')
    #counter = 0
    # manually construct contest object from known values
    contest_name = 'Virginia 2016 presidential contest'
    tally = {'Hillary R. Clinton': 1981473, 'Donald J. Trump': 1769443, 'Gary Johnson': 118274, 'Evan McMullin':54054, 'Jill Stein':27638, 'All Others':33749}
    reported_winner = max(tally, key=tally.get)
    winner_votes = tally[reported_winner]
    total_relevant = sum(tally.values())
    total_relevant_winner_prop = (1981473+1769443)
    loser_votes = total_relevant - winner_votes
    margin = (winner_votes / total_relevant) - (loser_votes / total_relevant)
    winner_prop = winner_votes / total_relevant_winner_prop
    # Make the contest object
    contest = Contest(total_relevant,
                                tally,
                                num_winners=1,
                                reported_winners=[reported_winner],
                                contest_type=ContestType.PLURALITY)
 
    audit_id = db.audit_lookup('so_bravo', 0.1)
    reported_id = db.contest_lookup(contest, qapp={'description': '2020 Presidential'})
    margin = winner_prop - (1.0 - winner_prop)

    sprobs = [.95,.85,.75,.65,.55,.45,.35,.25,.15,.05]
    #sprobs = [.95,.9,.85,.8,.75,.7,.65,.6,.55,.5,.45,.4,.35,.3,.25,.2,.15,.1,.05]
    for sprob in sprobs:
        print(sprob)
        sprob_sim = db.db.simulations.find_one({
            'reported': reported_id,
            'underlying': 'reported',
            'audit': audit_id,
            'description': 'Per-precinct so bravo',
            'invalid_ballots': True,
            'sample_sprob':sprob,
            'max_rounds':1000
        })

        if sprob_sim is None:
            # For several low margin states, we didn't run simulations
            print('why here 01234198172354')
            exit()

        sim_id = sprob_sim['_id']
        analysis = sprob_sim['analysis']
        trials = db.trial_lookup(sprob_sim['_id']) #this function is slowwwww
        # Five empty lists, a list for each round to be filled with the number of ballots sampled for each audit
        sampled = [ [] for _ in range(5) ] 
        #countertwo = 0

        num_trials = 0
        stopped = 0
        rounds_stopped = []
        totals_sampled = []
        all_stopped = True
        misleading_cases = 0
        for trial in trials:
            num_trials += 1
            if trial['stop']:
                stopped += 1
                rounds_stopped.append(trial['round'])
                totals_sampled.append(trial['relevant_sample_size_sched'][-1])
                k = trial['winner_ballots_drawn_sched']['Hillary R. Clinton'][-1]
                n = k + trial['winner_ballots_drawn_sched']['Donald J. Trump'][-1]
                alpha = .1
                p = winner_prop
                eor_would_not_stop = math.log(alpha) + k*math.log(p)+(n-k)*math.log(1-p) < n*math.log(1/2)
                if eor_would_not_stop:
                    misleading_cases += 1
                    print(misleading_cases)
            else:
                all_stopped = False
            # TODO: Extract more data from trial


        # Compute ASN
        if not all_stopped:
            asn = 'Not all audits stopped.'
        else:
            assert num_trials == len(totals_sampled)
            asn = sum(totals_sampled) / num_trials
            asn_std = statistics.pstdev(totals_sampled)

        print(asn)

        analysis['asn'] = asn
        analysis['asn_std'] = asn_std
        analysis['so_misleading_cases'] = misleading_cases
        analysis['so_misleading_prop'] = misleading_cases / num_trials

        # Update simulation entry to include analysis
        db.update_analysis(sim_id, analysis)

