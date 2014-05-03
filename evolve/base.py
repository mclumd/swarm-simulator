# evolve.base
# Basic evolutionary proceedure for the Swarm Simulation
#
# Author:   Philip Kim <philip.y.kim@gmail.com>
# Created:  Sat Apr 26 18:06:44 2014 -0400
#
# Copyright (C) 2014 Bengfort.com
# For license information, see LICENSE.txt
#
# ID: base.py [8dac23a] philip.y.kim@gmail.com $

"""
Basic evolutionary proceedure for the Swarm Simulation
"""

##########################################################################
## Imports
##########################################################################

import json
import copy
import random
from utils import relpath
from swarm.params import *

##########################################################################
## Module Constants
##########################################################################

POPSIZE      = 50
MAXGENS      = 999
TOURNEY_SIZE = 3
P_MUT        = 0.2
MUT_WEIGHT   = 0.2
MUT_RADIUS   = 20
MUT_ALPHA    = 20
CONF_DIR     = relpath(__file__, "../fixtures/")

##########################################################################
## Evolver
##########################################################################

def parse_fitness(path):
    with open(path, 'r') as fit:
        result = json.load(fit)
    return int(result['result']['fitness'])

def stats_path(generation, dirpath=CONF_DIR):
    basename = "%s.stats" % str(generation).zfill(Evolver.gen_len)
    return os.path.join(dirpath, basename)

def individual_paths(generation, individual, dirpath=CONF_DIR):
    basename = "%s_%s" % (str(generation).zfill(Evolver.gen_len), str(individual).zfill(Evolver.n_len))
    confname = basename + ".yaml"
    fitname  = basename + ".fit"
    return os.path.join(dirpath, confname), os.path.join(dirpath, fitname)

class Evolver(object):
    """
    Evolves a population using tournament selection.
    """

    # The expected file name is '{generation}_{id}.yaml' for the configuration
    # and '{generation}_{id}.fitness', with leading zeros.
    gen_len = len(str(POPSIZE - 1))
    n_len = len(str(POPSIZE - 1))

    @classmethod
    def random_pop(klass, dir_path = CONF_DIR):
        for i in range(POPSIZE):
            config = AllyParameters()
            for state in [config.spreading, config.seeking, config.caravan, config.guarding]:
                for k, v in state.components.iteritems():
                    v.weight = round(random.random(), 3)
                    v.radius = random.randrange(50, 400)
                    v.alpha = random.randrange(30, 360)
            config.dump_file(dir_path + "/%s_%s.yaml" % ("0".zfill(Evolver.gen_len), str(i).zfill(Evolver.n_len)))

    @classmethod
    def random_fit(klass, dir_path = CONF_DIR):
        for i in range(POPSIZE):
            path = dir_path + "/%s_%s.fit" % ("0".zfill(Evolver.gen_len), str(i).zfill(Evolver.n_len))
            file = open(path, 'w')
            file.write(str(random.randrange(0, 300)))
            file.close()

    @classmethod
    def evolve(klass, generation, dir_path = CONF_DIR):
        curr_gen = [] # an array of (config, fitness) tuples

        for i in range(POPSIZE):
            path = dir_path + "/%s_%s" % (str(generation).zfill(Evolver.gen_len), str(i).zfill(Evolver.n_len))
            config = AllyParameters.load_file(path + ".yaml")
            fitness = parse_fitness(path+".fit")
            curr_gen.append((config, fitness))

        curr_gen = sorted(curr_gen, key=lambda x: x[1], reverse = True)

        stats_file = open(dir_path + "/%s.stats" % (str(generation).zfill(Evolver.gen_len),), 'w')
        stats_file.write("Best fitness: %d\n" % curr_gen[0][1])
        stats_file.write("Median fitness: %d\n" % curr_gen[POPSIZE / 2][1])
        stats_file.close()

        # Elitism: always carry forward the best of the previous generation
        next_gen = [curr_gen[0]]

        # Reproduce by tournament selection
        while len(next_gen)< POPSIZE:
            tourney = [random.choice(curr_gen) for i in range(TOURNEY_SIZE)];
            tourney = sorted(tourney, key=lambda x: x[1], reverse = True)
            next_gen.append(copy.deepcopy(tourney[0]))

        # Mutate (the elite carry-forward is exempt)
        for i in range(1, POPSIZE):
            config = next_gen[i][0]

            if (random.random() < P_MUT):
                config.home_guard_threshold = min(5, max(0, config.home_guard_threshold + (1 if random.random() < 0.5 else -1)))

            if (random.random() < P_MUT):
                config.depo_guard_threshold = min(5, max(0, config.depo_guard_threshold + (1 if random.random() < 0.5 else -1)))

            for state in [config.spreading, config.seeking, config.caravan, config.guarding]:
                for k, v in state.components.iteritems():
                    if (random.random() < P_MUT):
                        v.weight = min(1.0, max(0.0, round(v.weight - MUT_WEIGHT + (2.0 * random.random() * MUT_WEIGHT), 3)))
                    if (random.random() < P_MUT):
                        v.radius = min(500, max(0, v.radius - MUT_RADIUS + random.randrange(0, 2 * MUT_RADIUS + 1)))
                    if (random.random() < P_MUT):
                        v.alpha = min(359, max(0, v.alpha - MUT_ALPHA + random.randrange(0, 2 * MUT_ALPHA + 1)))

        # Dump
        generation += 1
        for i in range(POPSIZE):
            path = dir_path + "/%s_%s.yaml" % (str(generation).zfill(Evolver.gen_len), str(i).zfill(Evolver.n_len))
            next_gen[i][0].dump_file(path)

if __name__ == '__main__':
    #Evolver.random_pop()
    Evolver.random_fit()
    #Evolver.evolve(1)
    print ""