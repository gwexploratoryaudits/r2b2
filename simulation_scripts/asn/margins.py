from r2b2.tests.util import parse_election

election = parse_election('../data/2020_presidential/2020_presidential.json')

lowest = 1
count = 0
for contest in election.contests:
    if contest == 'Texas' or contest == 'Missouri' or contest == 'Massachusetts':

        winner_prop = election.contests[contest].tally[election.contests[contest].reported_winners[0]] / sum(
            election.contests[contest].tally.values())
        margin = winner_prop - (1.0 - winner_prop)
        print(contest, margin)
