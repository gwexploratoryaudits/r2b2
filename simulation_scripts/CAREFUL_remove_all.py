"""
Removing all trials/simulations from my local db in order to restart easily
the 90% sims.
"""

from pymongo import MongoClient

print("Connecting")
db = MongoClient(host='localhost', port=27017, username='', password='')['r2b2']
print("Connection Established")
print("Removing all trials")
print(db.trials.delete_many({}))
print("Removing all simulations")
print(db.simulations.delete_many({}))
print("Done")
