import json

from r2b2.contest import Contest
from r2b2.contest import ContestType
from r2b2.minerva import Minerva


def test_minerva_second_round_estimate_2016():
    with open('tests/data/2016_pres_trials.json', 'r') as json_file:
        data = json.load(json_file)

    out = {}
    out['data_check'] = {}

    for state in data:
        out['data_check'][state] = {}

        clinton = data[state]['tally']['Clinton']
        trump = data[state]['tally']['Trump']
        print(state)
        tally = {"Clinton": clinton, "Trump": trump}
        margin = abs((clinton - trump) / (clinton + trump))
        if margin < .10:
            continue

        contest = Contest(clinton + trump, tally, 1, [max(tally, key=tally.get)], ContestType.PLURALITY)
        if tally['Clinton'] > tally['Trump']:
            rep_winner = 'Clinton'
            rep_loser = 'Trump'
        else:
            rep_winner = 'Trump'
            rep_loser = 'Clinton'

        for sim_type in ['underlying_reported_first_5', 'underlying_reported_not_stop_5', 'underlying_tied_first_5']:
            out['data_check'][state][sim_type] = []
            for trial in data[state][sim_type]:
                n = trial['relevant_sample_size']
                k = trial['winner_ballots']
                minerva = Minerva(.1, 1.0, contest)
                minerva.execute_round(n, {rep_winner: k, rep_loser: n-k})
                p_value = minerva.get_risk_level()
                stop = minerva.stopped
                if stop:
                    minerva.next_min_winner_ballots()
                    minerva.truncate_dist_null()
                    minerva.truncate_dist_reported()
                next_round_data = minerva.next_sample_size(verbose=True)
                out['data_check'][state][sim_type].append(
                    {"n": n, "k": k, "p_value": p_value, "stop": bool(stop),
                        "kmin": minerva.sub_audits[rep_winner+'-'+rep_loser].min_winner_ballots[-1],
                        "next_round_size": next_round_data[0], "next_round_kmin": next_round_data[1],
                        "next_round_sprob": next_round_data[2]})

            with open('tests/data/test_minerva_second_round_estimate_2016.json', 'w') as output:
                json.dump(out, output, sort_keys=True, indent=4)

    # Now that the file has been generated, compare to PV version.
    with open('tests/data/gm_test_minerva_second_round_estimate_2016.json', 'r') as json_file:
        data_canonical = json.load(json_file)
    with open('tests/data/test_minerva_second_round_estimate_2016.json', 'r') as json_file:
        data_test = json.load(json_file)

    for state in data_canonical['data_check']:
        if data_canonical['data_check'][state] == {}:
            continue
        for sim_type in ['underlying_reported_first_5', 'underlying_reported_not_stop_5', 'underlying_tied_first_5']:
            for i in range(5):
                assert data_canonical['data_check'][state][sim_type][i]['n'] == data_test['data_check'][state][sim_type][i]['n']
                assert data_canonical['data_check'][state][sim_type][i]['k'] == data_test['data_check'][state][sim_type][i]['k']
                assert data_canonical['data_check'][state][sim_type][i]['kmin'] == data_test['data_check'][state][sim_type][i]['kmin']
                assert data_canonical['data_check'][state][sim_type][i]['stop'] == data_test['data_check'][state][sim_type][i]['stop']
                assert data_canonical['data_check'][state][sim_type][i]['next_round_size'] == \
                    data_test['data_check'][state][sim_type][i]['next_round_size']
                assert abs(data_canonical['data_check'][state][sim_type][i]['p_value'] -
                           data_test['data_check'][state][sim_type][i]['p_value']) < .000001
                assert abs(data_canonical['data_check'][state][sim_type][i]['next_round_sprob'] -
                           data_test['data_check'][state][sim_type][i]['next_round_sprob']) < .000001
