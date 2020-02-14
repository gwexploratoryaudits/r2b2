from typing import List

from r2b2.audit import Audit


class BayesianRLA(Audit):
    """Baysian Risk-Limiting Audit implementation.

    TODO: insert description

    Attributes
        alpha (float): Risk limit. Alpha represents the chance, that gien and incorrect called
            election, the audit will fail to force a full recount.
        max_to_draw (int): The maximum total number of ballots auditors are willing to draw
            during the course of the audit.
        rounds ()
    """
    # TODO: How should the election/contest information be incorporated?

    rounds: List[int]

    def __init__(self, alpha, max_to_draw, rounds):
        """Initialize a Byasian RLA."""

        super().__init__(alpha)
        self.max_to_draw = max_to_draw
        self.rounds = rounds
        self.replacement = False
        self.beta = 0

    def compute_risk(self, sample: int, current_roud: int):
        """Compute the risk level given current round size and votes for winner in sample

        TODO: insert description

        Args
            sample (int): Votes found for reported winner in current round size.
            current_round(int): Current round size.
        """
        # TODO: Implement.
        pass
