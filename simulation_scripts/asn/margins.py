from r2b2.tests.util import parse_election

election = parse_election('../data/2020_presidential/2020_presidential.json')

lowest = 1
count = 0
for contest in election.contests:

    winner_prop = election.contests[contest].tally[election.contests[contest].reported_winners[0]] / sum(
        election.contests[contest].tally.values())
    margin = winner_prop - (1.0 - winner_prop)

    if margin > .05:
        if margin < lowest:
            lowest = margin
            lowestcontest = contest
        print(round(margin, 4), '   ', contest)
        count += 1

print(lowest, '   ', lowestcontest)

print('num above 5% margin:',count)
