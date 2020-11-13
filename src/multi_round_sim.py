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
import string
import os
import random
from numpy.random import Generator, PCG64
from typing import Any
import time
import itertools
import json
import logging
from scipy.stats import binom, multinomial, gamma, uniform
from collections import Counter
from athena.audit import Audit  # type: ignore
import numpy as np
import traceback

# Parameters
SPROB = 0.7
MIN_ROUND_SIZE = 100
MINERVA_MULTIPLE = 1.5

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


def make_audit(risk_limit, tally, num_winners=1, winners=["A"]) -> Any:
    """
    Transform tally to an athena Election object.

    Inputs:
        risk_limit      - the risk-limit for this audit
        tally:      {c1: votes, c2: votes, ...}
    """

    contest_ballots = sum(tally.values())
    votes = {key: tally[key] for key in tally if key != "_undervote_"}

    contest = {
        "contest_ballots": contest_ballots,
        "tally": tally,
        "num_winners": num_winners,
        "reported_winners": winners,
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


def next_round(audit, probs, max_samplesize):
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

        with Timer() as t:
            round_size = audit.find_next_round_size([SPROB])["future_round_sizes"][0]
        print(f"Round size for {SPROB:.0%} SPROB = {round_size}, cpu={round(t.interval, 5)}")
        round_size = max(MIN_ROUND_SIZE, int(gamma.rvs(a=2, scale=2) * round_size/2) * 2 ** len(audit.round_schedule))

        sampled = 0
        if len(audit.round_schedule) > 0:
            sampled = audit.round_schedule[-1]

        #print(f"{round_size=}, {sampled=}, {max_samplesize=}")
        round_size = min(round_size, max_samplesize - sampled)

    else:
        round_num = len(audit.round_schedule)
        round_size = int(audit.round_schedule[0] * MINERVA_MULTIPLE ** round_num)


    # a = binom.rvs(round_size, 0.505)
    sample = list(multinomial.rvs(round_size, probs))
    #print(sample)

    audit.set_observations(round_size, round_size, sample)

    risk = audit.status[audit.active_contest].risks[-1]
    return {"relevant_sample_size": round_size, "sample": sample, "p_value": risk}


def future_round_kmin():
        # FIXME: add arguments, make this available to next_round()
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
        except ValueError as e:
              print(f"obsolete code{e}")
        except Exception:
          print(f" traceback for {delta_rounds=}, {votes_per_round=}")
          traceback.print_exc(file=sys.stdout)
          # import pdb; pdb.set_trace()


def run_audit(audit, probs, max_samplesize):
    "Run a Minerva RLA to completion and return the p_value"

    for i in itertools.count(start=1):
        with Timer() as t:
          try:
            results = next_round(audit, probs, max_samplesize)
          except ValueError as e:
              print(f"Cannot audit: {e}")
              return float('nan'), audit
          except Exception:
            traceback.print_exc(file=sys.stdout)
            import pdb; pdb.set_trace()
            print(" Unknown traceback")
            return float('nan'), audit
        results.update({"round": i, "cpu": round(t.interval, 5)})
        risk = results["p_value"]
        print(" ", results)
        #print(" ", json.dumps(results), ",")
        if risk <= risk_limit:
            return risk, audit
        if audit.round_schedule[-1] >= max_samplesize  or  float('inf') > risk > 100.0:
            print("Bailing audit due to exceeding max-samplesize or big risk")
            return risk, audit


class Timer:
    def __enter__(self):
        self.start = time.process_time()  # or perhaps time.perf_counter here and below for clock time if using threads
        return self

    def __exit__(self, *args):
        self.end = time.process_time()
        self.interval = self.end - self.start


# https://www.nytimes.com/interactive/2020/11/03/us/elections/results-georgia-senate.html 2020-11-10T22:52:45+0000 
# tally = {"Perdue": 2457909, "Ossoff": 2369925, "Hazel": 114802, "Writein": 265}
# https://www.nytimes.com/interactive/2020/11/03/us/elections/results-georgia-senate-special.html
ga_special_tally = {"Warnock": 1613896, "Loeffler": 1270718, "Collins": 978667, "Jackson": 323518, "Lieberman": 135745,
                 "Tamara Johnson-Shealey": 106552,
                 "Jamesia James": 94201,
                 "Derrick Grayson": 51513,
                 "Joy Slade": 44849,
                 "Annette Jackson": 44231,
		 "Kandiss Taylor": 40266,
                 "Wayne Johnson": 36114,
                 "Brian Slowinski": 35354,
                 "Richard Winfield": 28617,
                 "Ed Tarver": 26311,
                 "Allen Buckley": 17922,
                 "John Fortuin": 15269,
                 "Al Bartell": 14614,
                 "Valencia Stovall": 13280,
                 "Michael Greene": 13253,
                 "Write-ins": 132
        }

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

    os.system("pip show athena; echo; cd ~/bayes/r2b2; git log --pretty=oneline -n 1; echo; git status -vv")
    # treat RuntimeWarning overflows as errors
    import warnings
    warnings.filterwarnings('error', category=RuntimeWarning)

    # TODO: simulate random # candidates, random # winners, uniform random votes per candidate, sort votes, pick random round size around 70% stopping prob?

    vote_scale = 100
    univotes = uniform(0, vote_scale)
    trials = 100000 # But easy to stop at any time and get final summary report via interrupt
    risks = []
    results = []

    print("[")

    # Pick starting point at random, but override via $RANDSEED
    epoch = random.randint(0, 100000)
    epoch = int(os.environ.get("RANDSEED", epoch))

    for seq in range(trials):
        seed = (epoch, seq)

        # See reproducable seeding - Stack Overflow https://stackoverflow.com/questions/16016959/scipy-stats-seed
        # TODO: Is it all reproducable if some other module uses binom and varies in its use?
        random_gen = Generator(PCG64(seed))
        binom.random_state = random_gen
        gamma.random_state = random_gen
        univotes.random_state = random_gen
        multinomial.random_state = random_gen
        random.seed(seq/epoch)

        risk_limit = random.choice([0.2, 0.1, 0.1, 0.1, 0.05, 0.01])

        num_candidates = max(2, min(5, 2 + int(gamma.rvs(a=3, scale=0.6))))
        num_winners = max(1, min(num_candidates-1, int(gamma.rvs(a=3, scale=0.6))))

        # Find a set of votes with a big enough margin
        while True:
            votes = np.array([int(univotes.rvs()) for _ in range(num_candidates)])
            votes = np.sort(votes)[::-1]
            print(f'{votes=}, {num_winners=}')
            if sum(votes) == 0:
                # Avoid divide by zero == RuntimeWarning: invalid value encountered in long_scalars
                continue
            margin = (votes[num_winners-1] - votes[num_winners]) / sum(votes)
            if margin >= 0.005:
                break

        #tally = {"A": 320, "B": 300, "C": 200, "D": 180}
        tally = {cand: votes for cand, votes in zip(string.ascii_uppercase, votes)}
        audit = make_audit(risk_limit, tally, num_winners=num_winners, winners=string.ascii_uppercase[:num_winners])

        max_samplesize = 1000000   # FIXME: higher?

        # print(f'{seed=}, {risk_limit=}, {num_candidates=}, {num_winners=}, tally={tally}')

        c = audit.election.contests['ArloContest']

        probs = np.array(list(audit.election.contests['ArloContest'].tally.values()))
        probs = probs / sum(probs)
        # Pick an actual tally which is close to the original, rejecting those with different outcomes
        while True:
            try:
                truetally = multinomial.rvs(200, probs)
            except Exception as e:
                print(f"Exception for multinomial of {probs=} {e}")
            num_winners = audit.election.contests[audit.active_contest].num_winner
            #print(f"{truetally[:num_winners]=} {truetally[num_winners:]=}")
            if min(truetally[:num_winners]) > max(truetally[num_winners:]):
                break
            #print(f'\n\nfailed truetally: {truetally=}\n')
            # if all(truetally[win] > truetally[lose] for win in range(num_winners) for lose in range(num_winners+1, len(probs)):
        trueprobs = truetally / sum(truetally)

        print(f'\n{seed=}, {risk_limit=}, {margin=:.2%}, {num_candidates=}, {num_winners=}, ballots={audit.election.total_ballots}, tally={c.tally}, winners={c.reported_winners}, {trueprobs=}')

        #  "num_winners": {c.num_winners},

        risk, res = run_audit(audit, probs, max_samplesize)
        risks.append(risk)
        results.append(res)
        # print(f"{repr(res)=}, {type(res)=}")
        print(f"Summary: {(res.round_schedule, res.observations['ArloContest'], risk, risk <= risk_limit)}")
        # print("}")
        if killer.kill_now:
            print("Received interrupt - stopping")
            break

    audits = len(risks)
    # FIXME: The athena module frequently produces a risk level of 0.0 for large multi-round audits
    passed = len([r for r in risks if r <= risk_limit])

    print(f"{passed / audits:.2%} ({passed}/{audits}) of the audits passed:")
    print(f"Round size counter: {sorted(Counter([len(r.round_schedule) for r in results]).items())}")
    np.set_printoptions(suppress=True, linewidth=95)

    # FIXME: need to truncate / round down to preserve thresholds
    # And need to actually print all the values if there are more than default of threshold=1000.
    #print(f"Risks:\n{np.around(np.array(sorted(risks)), decimals=2)}")

    print("]")
