"""
Compute the actual value that is meant by ASN, as presented
in BRAVO.
function Average_Ballots = ASN(margin, alpha)
    % 
    % Average_Ballots = ASN(margin, alpha)
    % outputs ASN as described in BRAVO paper, eqn(5)
    % ----------
    % Input: 
    %   margin:         fractional margin
    %   alpha:          fractional risk limit
    % ----------
    % Output: 
    % Average_Ballots:  ASN value
    % ----------

    p_w = (1+margin)/2;
    p_l = (1-margin)/2;
    z_w = log(1+margin);
    z_l = log(1-margin);

    Average_Ballots = (log(1/alpha)+ (z_w/2))/((p_w*z_w) + (p_l*z_l))
"""


import math
def ASN(margin, alpha=.1):
    p_w = (1+margin)/2
    p_l = (1-margin)/2
    z_w = math.log(1+margin)
    z_l = math.log(1-margin)
    asn = (math.log(1/alpha)+ (z_w/2))/((p_w*z_w) + (p_l*z_l))
    return asn

texas_margin = 0.05661442473559064
missouri_margin = 0.15671641288802896
massachusetts_margin = 0.3423109908029629

print('Texas:',ASN(texas_margin))
print('Missouri:',ASN(missouri_margin))
print('Massachusetts:',ASN(massachusetts_margin))


