"""
Quick script to convert Poorvi's json to the election format r2b2 uses.
"""
import json
"""
Sample of the election format needed:
{
    "name": "2016 Presidential",
    "total_ballots": 136669237,
    "contests": {
        "Alabama": {
            "contest_ballots": 2123372,
            "tally": {
                "Clinton": 729547,
                "Trump": 1318255
            },
            "num_winners": 1,
            "reported_winners": [
                "Trump"
            ],
            "contest_type": "PLURALITY"
        },
"""
"""
Sample of Poorvi's data:
"election_results":{
        "Alabama":{
                "contests":{
                        "presidential":{
                                "winners":1,
                                "candidates":[
                                        "Biden",
                                        "Trump"
                                ],
                                "results":[849624,1441170],
                                "ballots_cast":2323282,
                                "state_id":1,
                                "margin":-0.2582274967
                        }
                },
                "round_sizes_Minerva_EoR":[114,213],
                "round_sizes_Minerva_EoR_scaled":[116,217],
                "round_sizes_factor":1.868421053,
                "stop_prob_Minerva":0.9181868455,
                "stop_prob_EoR":0.9104180435
        },
        "Alaska":{
"""
"""
Sample of round size format:
{
    "Alabama": {
        "Minerva_pv_scaled": 94,
        "Athena_pv_scaled": 94
    },
    "Alaska": {
        "Minerva_pv_scaled": 295,
        "Athena_pv_scaled": 295
    },
    "Arizona": {
""" 

new_sample_sizes = {}

with open('poorvi_2020.json', 'r') as fd:
    poorvi_election_results = json.load(fd)['election_results']
    total_ballots = 0
    for state in poorvi_election_results:
        poorvi_state = poorvi_election_results[state]['contests']['presidential']
        total_ballots += poorvi_state['ballots_cast']
    new_election = {
            "name:": "2020 Presidential",
            "total_ballots:": total_ballots,
            "contests": {}
        }
    for state in poorvi_election_results:
        poorvi_state = poorvi_election_results[state]['contests']['presidential']
        if poorvi_state['margin'] > 0:
            reported_winner = 'Biden'
        else:
            reported_winner = 'Trump'
        new_election['contests'][state] = {
            "contest_ballots": poorvi_state['ballots_cast'],
            "tally": {
                "Biden": poorvi_state['results'][0],
                "Trump": poorvi_state['results'][1]
            },
            "num_winners": 1,
            "reported_winners": [ reported_winner ],
            "contest_type": "PLURALITY"
        }
        new_sample_sizes[state] = {}
        new_sample_sizes[state]['Minerva_pv_scaled:'] = [116,217]
    with open('2020_presidential.json', 'w') as outfile:
        json.dump(new_election, outfile, indent=2)
    with open('2020_presidential_sample_sizes.json', 'w') as outfile:
        json.dump(new_sample_sizes, outfile, indent=2)

