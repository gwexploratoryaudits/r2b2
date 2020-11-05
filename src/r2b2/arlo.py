"""API to be used in ARLO intefrace, matching Filip's Athena library."""
from r2b2.election import Election
from r2b2.minerva import Minerva

from r2b2.tests.util import election_from_dict
from r2b2.tests.util import parse_election


class Status():
    def __init__(self):
        self.risks = []
        self.min_kmins = []


class Audit():

    minerva: Minerva
    alpha: float
    election: Election
    contest: str
    status: dict

    def __init__(self, audit_type: str, alpha: float):

        if audit_type != 'minerva':
            raise ValueError('Audit type must be minerva.')
        if alpha <= 0.0 or alpha > 1.0:
            raise ValueError('Audit risk limit but be between 0 and 1')

        self.election = None
        self.contest = None
        self.minerva = None
        self.alpha = alpha
        self.status = {}

    def add_election(self, election):
        """Set election in Audit.

        Args:
            election: Election data. Can be dict with election information or JSON file.
        """
        if self.election is not None:
            raise Exception('Election is already set.')
        
        if type(election) is dict:
            self.election = election_from_dict(election)
        elif type(election) is str:
            self.election = parse_election(election)
        else:
            raise TypeError('election must be a dict of election info or filename.')

    def load_contest(self, contest: str):
        """Set contest (from election) in Audit and create underlying Minerva audit.

        Args:
            contest: Name of contest form election to use in Audit.
        """
        if self.election is None:
            raise Exception('Cannot load contest before election is added.')
        if self.contest is not None:
            raise Exception('Contest is already loaded.')
        self.contest = contest
        self.minerva = Minerva(self.alpha, 1.0, self.election.contests[self.contest])
        self.status[contest] = Status()

    def find_next_round_size(self):
        # TODO
        pass

    def set_observations(self, new_ballots, new_valid_ballots, round_observation):
        """Set audit observations, essentially execute a round of the minerva audit.

        Args:
            new_ballots: Not used in this implementation.
            new_valid_ballots (int): Not used in this implementation.
            round_observation: Array of number of ballots sampled for each candidate in the round.
        """
        if self.election is None:
            raise Exception('Must add election before setting observations.')
        if self.contest is None:
            raise Exception('Must load contest before setting observations.')
        if self.minerva is None:
            raise Exception('No underlying Minerva audit object.')
        if len(round_observation) != 2:
            raise Exception('Round observation must have length 2')

        # Set cumulative valid round size
        if len(self.minerva.rounds) == 0:
            round_size = sum(round_observation)
            sample_winner_ballots = round_observation[0]
        else:
            round_size = sum(round_observation) + self.minerva.rounds[-1]
            sample_winner_ballots = self.minerva.sample_winner_ballots[-1] + round_observation[0]
        # Run minerva round
        self.minerva.execute_round(round_size, sample_winner_ballots)

        # Update status from minerva audit
        self.status[self.contest].risks = self.minerva.pvalue_schedule
        self.status[self.contest].min_kmins = self.minerva.min_winner_ballots
