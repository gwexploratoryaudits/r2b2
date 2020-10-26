#!/usr/bin/env python

"""
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

from typing import Any
import time
import itertools
import json
from scipy.stats import binom
from collections import Counter
from athena.audit import Audit  # type: ignore
import numpy as np

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


def random_round(audit, max_samplesize):
    "Run another round of random size and sample results on the given audit and return the p_value"

    # Increase round sizes geometrically.  TODO: randomize via gamma or the like
    round_size = 50 * 4 ** len(audit.round_schedule)

    sampled = 0
    if len(audit.round_schedule) > 0:
        sampled = audit.round_schedule[-1]

    round_size = min(round_size, max_samplesize - sampled)

    a = binom.rvs(round_size, 0.5)
    audit.set_observations(round_size, round_size, [a, round_size - a])

    risk = audit.status[audit.active_contest].risks[-1]
    return {"relevant_sample_size": round_size, "winner_ballots": a, "p_value": risk}


def run_audit(audit, max_samplesize):
    "Run a Minerva RLA to completion and return the p_value"

    for i in itertools.count(start=1):
        with Timer() as t:
            results = random_round(audit, max_samplesize)
        results.update({"round": i, "cpu": round(t.interval, 5)})
        risk = results["p_value"]
        print(" ", json.dumps(results), ",")
        if risk <= risk_limit:
            return risk, audit
        if audit.round_schedule[-1] >= max_samplesize:
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


"""
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
        "contest_type": "PLURALITY",
"""

if __name__ == "__main__":
    killer = GracefulKiller()

    risk_limit = 0.1
    trials = 2 # 100000
    risks = []
    results = []

    risk_limit = 0.1
    
    print("[")

    for i in range(trials):
        p_w = 0.55
        p_l = 0.45
        audit = make_election(risk_limit, p_w, p_l)

        max_samplesize = 2000   # FIXME: higher?

        c = audit.election.contests['ArloContest']

        print(f'''
    "audit": {{
          "seq": {i},
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
        #print(f"Summary: {(res.round_schedule, res.observations['ArloContest'][0])}\n")
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
    # And need to actually print all the values.
    print(f"Risks:\n{np.around(np.array(sorted(risks)), decimals=2)}")
    print("]")
