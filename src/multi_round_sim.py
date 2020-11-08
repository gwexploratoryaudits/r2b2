#!/usr/bin/env python
"""
Simulate Filip's minerva round strategy.

[Based on evolving simulation code, half-way thru converting it to json output.
Sorry for the mess and invalid syntax in the json!]

General plan:

Simulate random audits, with random round sizes.

Eventually:

* Do these steps for risk limits of 20%, 10%, 5%, 1%, 0.1% or whatever
* "Mostly small" means drawn from a probibility distribution which is weighted towards small values, like a gamma with k=2, theta=2
* For each trial audit:
 * pick random totals for each candidate from 0 to 10,000,000 mostly small, throw out winning margins larger than e.g 0.5% for performance, practicality
 * set a conservative cumulative max_samplesize, e.g. 10% of ballot count, or 6 ASN, or ??
 * for each round
   * pick random round size from 0 to 100000 mostly small, but capped so as not to exceed max_samplesize
   * pick random candidate totals based on binomial for a tie
   * If stopping condition met, increment failure count and break loop
   * if total sample >= max_samplesize:
     * declare full hand count done, increment success count and break loop
  * Log parameters and result


* Analyze results to confirm that the fraction of failures is less than the risk limit in each case


* [some day?] random number of candidates from 2 to 20 mostly small, and test full multi-candidate audits
"""

import sys
import os
import random
from typing import Any
import time
import itertools
import json
import logging
from scipy.stats import binom, gamma
from collections import Counter
from athena.audit import Audit  # type: ignore
import numpy as np
import traceback

# Parameters
SPROB = 0.9
MIN_ROUND_SIZE = 25

def vars_to_dict(*args):
    ""
    return dict(((k, eval(k)) for k in args))

def compute_multi_round_r2b2(contest_dict, rounds, observations, risk_limit=0.1, max_fraction=0.5):
    """Compute multi-round risk level via r2b2 module, returning p_value"""

    contest = r2b2contest.Contest(**contest_dict)
    if contest.contest_ballots % 2 != 0:
        raise Exception("Number of contest ballots must be a multiple of two")

    half_ballots = contest.contest_ballots // 2
    tied_contest = Contest(contest.contest_ballots, {'A': half_ballots, 'B': half_ballots}, 1, ['A'], ContestType.PLURALITY)

    sprob_reported = Sprob(rounds, observations, contest)
    sprob_tied = Sprob(rounds, observations, tied_contest)
    tsprobs = sprob_tied.compute_sprobs()
    rsprobs = sprob_reported.compute_sprobs()
    # print(f"{tsprobs=}\n{rsprobs=}")
    ratios = [tsprobs[i] /rsprobs[i]  for i in range(len(rounds))]
    print(f"{ratios=}")
    return min(ratios)


def make_election(risk_limit, p_w: float, p_r: float) -> Any:
    """
    Transform fractional shares to an athena Election object.

    Inputs:
        risk_limit      - the risk-limit for this audit
        p_w             - the fraction of vote share for the winner
        p_r             - the fraction of vote share for the loser / runner-up
    """

    # calculate the undiluted "two-way" share of votes for the winner
    p_wr = p_w + p_r
    p_w2 = p_w / p_wr

    contest_ballots = 100000
    winner = int(contest_ballots * p_w2)
    loser = contest_ballots - winner

    contest = {
        "contest_ballots": contest_ballots,
        "tally": {"A": winner, "LOSER": loser},
        "num_winners": 1,
        "reported_winners": ["A"],
        "contest_type": "PLURALITY",
    }

    contest_name = "ArloContest"
    election = {
        "name": "ArloElection",
        "total_ballots": contest_ballots,
        "contests": {contest_name: contest},
    }

    audit = Audit("minerva", risk_limit)
    audit.add_election(election)
    audit.load_contest(contest_name)

    return audit


# TODO:
# def next_if_missed_by_one(audit, sprob):
#        "Return next round size for given stopping probability assuming audit missed kmin by just one in last round"
# extract from below


def next_round(audit, max_samplesize):
    """Run another round on the given audit and return the p_value

    TODO: generalize. Replace max_samplesize with a more general context object to this method,
    and make each of these round size approaches into
    a generator which is part of the context object.

    Current approach: choose next round size assuming sample results hit kmin-1.
    Pick random sample results.

    Other approaches:
    approach 1: Increase round sizes geometrically.
    round_size = 4000 * 2 ** len(audit.round_schedule)

    fixed approaches:
    margin 10%, 90% at each round: round_size = [710, 1850, 3250, 5110, 10000, 20000, 40000, 80000][len(audit.round_schedule)]
    margin 10%, 33% at each round: round_size = [199,336,481,632,796,975,1180,1380,1582,1800,2100,2400,2700,3000,3500,5000, 10000, 20000, 40000, 80000][len(audit.round_schedule)]

    Strategic approach:
    Employ filip's strategy, choosing 2nd round size based on 1st observation
    if len(audit.round_schedule) == 0:
        round_size = 20
    elif len(audit.round_schedule) == 1:
        if audit.observations['ArloContest'][0][0] in [12, 13]:
            round_size = 30
        else:
            round_size = 60
    else:
        round_size = 30 * 3 ** len(audit.round_schedule)
    """

    if len(audit.round_schedule) == 0:
        # Random round size, min 1, average of 100 in first round, approximately doubling every round, via gamma function.
        # TODO: is there a suitable discrete distribution like gamma, or one better?
        # TODO: see if we can eliminate need to require at least MIN_ROUND_SIZE
        #   due to kmin being larger than round size, thus proposing negative values for votes.
        #   File "/home/neal/Envs/arlo/lib/python3.8/site-packages/athena/athena.py", line 384, in find_next_round_size
        #   prob_table_prev[observations_i] = 1.0
        #  IndexError: list assignment index out of range

        round_size = max(MIN_ROUND_SIZE, int(gamma.rvs(a=2, scale=2) * 50) * 2 ** len(audit.round_schedule))

        sampled = 0
        if len(audit.round_schedule) > 0:
            sampled = audit.round_schedule[-1]

        round_size = min(round_size, max_samplesize - sampled)

    else:
        # Extract kmin for current audit
        contest = audit.active_contest
        c = audit.election.contests[contest]
        kmin = audit.status[audit.active_contest].min_kmins[0]
        print(f"{kmin=}")
        #logging.warning(f"{kmin=}")

        # Create a play_audit object with the same election parameters, for estimations
        risk_limit = audit.alpha
        p_w = c.tally['A']
        p_l = c.tally['LOSER']
        play_audit = make_election(risk_limit, p_w, p_l)

        # We'll estimate the next round size optimistically as if kmin-1 votes have been seen.
        # Figure out how many votes to put in each round, filling them in starting with the last round,
        # since we can't succeed too early.
        votes_to_go = kmin - 1
        delta_rounds = np.diff(audit.round_schedule, prepend=[0])
        votes_per_round = []
        for round_size in np.flip(delta_rounds):
             votes = min(votes_to_go, round_size)
             votes_to_go -= votes 
             votes_per_round.append(votes)

        # put the rounds back in the right order
        votes_per_round = votes_per_round[::-1]

        # Replay the audit rounds, with winner votes adding up to kmin-1
        for play_round_size, play_round_votes in zip(delta_rounds, votes_per_round):
            play_audit.set_observations(play_round_size, play_round_size, [play_round_votes, play_round_size - play_round_votes])
            # logging.warning(f"{play_audit.status[contest].risks[-1]=}")

        try:
          round_size = play_audit.find_next_round_size([SPROB])['future_round_sizes'][0]
        except Exception:
          print(f" traceback for {delta_rounds=}, {votes_per_round=}")
          traceback.print_exc(file=sys.stdout)
          import pdb; pdb.set_trace()

    a = binom.rvs(round_size, 0.5)

    audit.set_observations(round_size, round_size, [a, round_size - a])

    risk = audit.status[audit.active_contest].risks[-1]
    return {"relevant_sample_size": round_size, "winner_ballots": a, "p_value": risk}


def run_audit(audit, max_samplesize):
    "Run a Minerva RLA to completion and return the p_value"

    for i in itertools.count(start=1):
        with Timer() as t:
          try:
            results = next_round(audit, max_samplesize)
          except Exception:
            traceback.print_exc()
            import pdb; pdb.set_trace()
            print(" traceback for ", json.dumps(results), ",")
            return float('nan'), audit
        results.update({"round": i, "cpu": round(t.interval, 5)})
        risk = results["p_value"]
        print(" ", json.dumps(results), ",")
        if risk <= risk_limit:
            return risk, audit
        if audit.round_schedule[-1] >= max_samplesize  or  risk > 100.0:
            return risk, audit  # FIXME: refactor?


class Timer:
    def __enter__(self):
        self.start = time.process_time()  # or perhaps time.perf_counter here and below for clock time if using threads
        return self

    def __exit__(self, *args):
        self.end = time.process_time()
        self.interval = self.end - self.start


class GracefulKiller:
  kill_now = False
  def __init__(self):
    import signal

    signal.signal(signal.SIGINT, self.exit_gracefully)
    signal.signal(signal.SIGTERM, self.exit_gracefully)

  def exit_gracefully(self,signum, frame):
    self.kill_now = True


if __name__ == "__main__":
    #logging.basicConfig(level=logging.WARNING)
    logging.basicConfig(level=logging.ERROR)

    killer = GracefulKiller()

    risk_limit = 0.1
    trials = 100000 # 100000 # 100000
    risks = []
    results = []

    risk_limit = 0.1
    
    print("[")

    # Pick starting point at random, but override via $RANDSEED
    epoch = random.seed(0, 100000)
    epoch = os.environ.get("RANDSEED", epoch)
    for seq in range(trials):
        p_w = 0.55
        p_l = 0.45
        audit = make_election(risk_limit, p_w, p_l)

        max_samplesize = 100000   # FIXME: higher?

        c = audit.election.contests['ArloContest']

        seed = f"{epoch},{seq}"
        random.seed(seed)
        print(f'''
    "audit": {{
          "seq": {seed},
          "contest_ballots": {audit.election.total_ballots},
          "tally": {c.tally},
          "reported_winners": {c.reported_winners},
          "rounds": {{
        ''')

        #  "num_winners": {c.num_winners},

        risk, res = run_audit(audit, max_samplesize)
        risks.append(risk)
        results.append(res)
        # print(f"{repr(res)=}, {type(res)=}")
        print(f"Summary: {(res.round_schedule, res.observations['ArloContest'][0], risk)}\n")
        print("}")
        if killer.kill_now:
            print("Received interrupt - stopping")
            break

    audits = len(risks)
    # FIXME: The athena module frequently produces a risk level of 0.0 for large multi-round audits
    passed = len([r for r in risks if r > 0.0 and r <= risk_limit])

    print(f"{passed / audits:.2%} ({passed}/{audits}) of the audits passed: (excluding 'zero' risks)")
    print(f"{risk_limit=:.1%}")
    print(f"Round size counter: {sorted(Counter([len(r.round_schedule) for r in results]).items())}")
    np.set_printoptions(suppress=True, linewidth=95)

    # FIXME: need to truncate / round down to preserve thresholds
    # And need to actually print all the values if there are more than default of threshold=1000.
    #print(f"Risks:\n{np.around(np.array(sorted(risks)), decimals=2)}")

    print("]")
