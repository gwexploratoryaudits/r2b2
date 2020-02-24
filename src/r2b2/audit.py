from abc import ABC
from abc import abstractmethod

from r2b2.contest import Contest


class Audit(ABC):
    """Abstract Base Class to define a general Audit object type.

    The Audit class will be an abstract base class which defines the general structure and properties
    of a risk-limiting audit. Individual RLAs should be subclasses of the Audit class.

    Attributes:
        alpha (float): Risk limit.  Alpha represents the chance that given an incorrectly called
            election, the audit will fail to go to a full recount.
        beta (float): the worst case chance of causing an unnecessary full recount. For many RLAs,
            beta will simply be set to 0 and will not appear to be a parameter.
        max_to_draw (integer): The maximum total number of ballots auditors are willing to draw
            during the course of the audit.
        replacement (bool): Indicates if the audit sampling should be done with (true) or without
            (false) replacement.
        contest (Contest): Contest on which to run the audit.
    """

    alpha: float
    beta: float
    max_to_draw: int
    replacement: bool
    contest: Contest

    def __init__(self, alpha: float, beta: float, max_to_draw: int,
                 replacement: bool, contest: Contest):
        """Create an instance of an Audit.

        Note:
            This should only be called when initializing a subclass as the Audit class is an
            abstract class.
        """
        self.alpha = alpha
        self.beta = beta
        self.max_to_draw = max_to_draw
        self.replacement = replacement
        self.contest = contest

    @abstractmethod
    def compute_risk(self):
        """Compute the current risk level of the audit.

        Returns:
            Current risk-level of the audit as a float.
        """

        pass

    @abstractmethod
    def compute_sample_size(self):
        """Compute the next sample size to draw."""

        pass
