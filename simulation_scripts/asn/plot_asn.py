import json
import math
import matplotlib.pyplot as plt

with open('asn.json', 'r') as datafile:
    data = json.load(datafile)

margins = data['margins']
minerva_asns = data['minerva_asns']

def bravo_asn(margin, alpha=.05):
    p_w = (1+margin)/2
    p_l = (1-margin)/2
    z_w = math.log10(1+margin)
    z_l = math.log10(1-margin)

    asn = (math.log10(1/alpha) + (z_w/2)) / ((p_w*z_w) + (p_l*z_l))

    return asn

bravo_asns = []

for margin in margins:
    bravo_asns.append(bravo_asn(margin))

# Plot the ASNs for the various margins 
# (both Minerva ASN and normal Bravo ASN)
fig = plt.figure()
ax = fig.add_subplot(111)
ax.scatter(margins, 
           minerva_asns, 
           s=len(margins),
           c='b', 
           marker='x', 
           label='Experimental Minerva ASN')
ax.scatter(margins, 
           bravo_asns, 
           s=len(margins),
           c='r', 
           marker='o', 
           label='Analytical Bravo ASN')
title = 'ASN for Bravo and 90% Minerva'
plt.title(title)
plt.ylabel('Average Sample Number (ASN)')
plt.xlabel('Margin')
plt.grid()
plt.legend(loc='upper right')
plt.show()


