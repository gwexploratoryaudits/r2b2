## Minerva Multiround Simulations
These simulations have a maximum of 5 rounds of a Minerva audit in which
the first round size is computed to have a 90% probability of stopping
and subsequent rounds are found by multiplying previous round size by 1.5.
There are 10^6 (one million) simulations for each statewide contest with a 
margin above 5% in the 2020 Presidential contest.

### Absolute
The absolute plots consider the probability that an audit stopped.
(So number of audits stopped in a given round divided by the total 
number of audits at the very beginning of the simulation: 10^6 in this case.)

### Conditional
The conditional plots consider the probability that an audit stopped
given that it had already made it through to the current round.

### Ratio
There are also plots of the Minerva ratio for each round which we claim is less
than .1. 
