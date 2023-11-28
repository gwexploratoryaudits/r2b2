""" 
Generates some plots for Oliver's thesis for a toy example audit to develop
intuition for the Minerva audit.. 
"""
import matplotlib.pyplot as plt
import numpy as np
import statistics
import math
from scipy.stats import binom
plt.rcParams['mathtext.fontset'] = 'stix'
plt.rcParams['font.family'] = 'STIXGeneral'
plt.rcParams['text.usetex'] = True

from r2b2.simulator import DBInterface
from r2b2.simulator import histogram
from r2b2.tests.util import parse_election
from r2b2.contest import Contest
from r2b2.contest import ContestType
import json

# audit-specific items:
all_audit_specific_items = {}
audits = []
audit_labels = {}

marker = 'o'
color = 'b'
linestyle = '-'
audit_label = r'\textsc{Providence}'
font = {'size'   : 17}
plt.rc('font', **font)
ks = np.linspace(0, 100, 101)
N = 1000
p0 = .5
p1 = .7
p_alt = binom.pmf(ks, 100, p1)
p_null = binom.pmf(ks, 100, p0)
print(ks)
print(p_alt)
print(p_null)
plt.plot(ks, p_alt, linestyle='-', color='g')
plt.plot(ks, p_null, linestyle='-', color='r')
plt.xlabel('Winner votes')
plt.ylabel('Probability')
plt.tight_layout()
plt.show()


