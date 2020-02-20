from typing import List

from audit import Audit


class BayesianRLA(Audit):
    """Baysian Risk-Limiting Audit implementation.

    TODO: insert description

    Attributes
        alpha (float): Risk limit. Alpha represents the chance, that gien and incorrect called
            election, the audit will fail to force a full recount.
        max_to_draw (int): The maximum total number of ballots auditors are willing to draw
            during the course of the audit.
        rounds (List[int]): The round sizes to use during the audit.
    """

    rounds: List[int]

    def __init__(self, alpha, max_to_draw, contest, rounds):
        """Initialize a Byasian RLA."""

        super().__init__(alpha, 0, max_to_draw, False, contest)
        self.rounds = rounds

    def compute_risk(self, sample: int, current_round: int):
        """Compute the risk level given current round size and votes for winner in sample

        TODO: insert description

        Args
            sample (int): Votes found for reported winner in current round size.
            current_round(int): Current round size.
        """
        # TODO: Implement.
        pass

    def lookup_table(self):
        """Generate a lookup table of stopping values for each round."""

        # TODO: Implement.
        pass
