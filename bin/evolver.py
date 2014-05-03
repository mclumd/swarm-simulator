#!/usr/bin/env python
# evolver
# Command line utilities for our evolutionary process
#
# Author:   Benjamin Bengfort <benjamin@bengfort.com>
# Created:  Sat May 03 08:42:42 2014 -0400
#
# Copyright (C) 2014 Bengfort.com
# For license information, see LICENSE.txt
#
# ID: evolver.py [] benjamin@bengfort.com $

"""
Command line utilities for our evolutionary process
"""

##########################################################################
## Imports
##########################################################################

import os
import sys
import time
import json
import argparse

from evolve import Evolver
from evolve.tasks import runsim
from evolve import CONF_DIR, POPSIZE, MAXGENS
from evolve import individual_paths, stats_path

##########################################################################
## Command Line Variables
##########################################################################

DESCRIPTION = "Command line functions for evolving the swarm"
EPILOG      = "(C) Copyright University of Maryland 2014"
VERSION     = "1.0"

##########################################################################
## Commands
##########################################################################

def initpop(args):
    """
    Initialize the population
    """
    Evolver.random_pop(args.dirname[0])
    return "Population with %i individuals generated in %s" % (POPSIZE, args.dirname[0])

def evolve(args):
    """
    One step execution of a single evolution on a population
    """
    Evolver.evolve(args.generation[0], args.dirname)
    return "Generation %i with %i individuals created in %s" % (args.generation[0]+1, POPSIZE, args.dirname)

def run(args):
    """
    Run evolution including simulation tasks with celery for a number of
    generations, keeping the best simulations around.
    """

    def doneyet(population):
        """
        Checks if tasks are completed, and if so, writes them to disk.
        """
        done = True
        for individual in population:
            if not individual['result']:
                task = individual['task']
                if task.ready():
                    individual['result'].update(task.result)
                    with open(individual['fit_path'], 'w') as fit:
                        json.dump(individual, fit, indent=4)
                else:
                    done = False
        return done

    ## Check if there is a population in the specified directory
    check = os.path.join(args.dirname, '00_00.yaml')
    if not os.path.exists(check):
        return "First individual not found at '%s' have you initialized the population?" % check

    for generation in xrange(args.generations):
        individuals = []
        for idx in xrange(POPSIZE):
            conf, fit = individual_paths(generation, idx, args.dirname)
            individuals.append({
                'conf_path': conf,
                'fit_path':  fit,
                'result':    {},
                'task':      runsim.delay(os.path.abspath(conf)),
            })

        # Wait for simulations to complete
        while not doneyet(individuals):
            time.sleep(args.wait)
        Evolver.evolve(generation, args.dirname)

##########################################################################
## Main method
##########################################################################

def main(*argv):

    # Construct the argument parser
    parser = argparse.ArgumentParser(description=DESCRIPTION, epilog=EPILOG, version=VERSION)
    subparsers = parser.add_subparsers(title='commands', description='Administrative commands for evolver.')

    # Initialize population command
    initpop_parser = subparsers.add_parser('initpop', help='Initialize a random population in a directory.')
    initpop_parser.add_argument('dirname', nargs=1, type=str, help='Directory to init the population of configuration files.')
    initpop_parser.set_defaults(func=initpop)

    # Evolve command
    evolve_parser = subparsers.add_parser('evolve', help='Execute selection and mutation for a generation.')
    evolve_parser.add_argument('-d', '--dirname', type=str, default=CONF_DIR, help='Directory with the population and fitness files.')
    evolve_parser.add_argument('generation', type=int, nargs=1, help='The generation from which to evolve the next (by timestep).')
    evolve_parser.set_defaults(func=evolve)

    # Run command
    run_parser = subparsers.add_parser('run', help='Run async evolution for some number of generations.')
    run_parser.add_argument('-g', '--generations', type=int, default=MAXGENS, help='Number of generations to run the simulation for.')
    run_parser.add_argument('-d', '--dirname', type=str, default=CONF_DIR, help='Directory with the population and fitness files.')
    run_parser.add_argument('-w', '--wait', metavar='SECS', type=int, default=20, help='Seconds to wait before checking status of simulations.')
    run_parser.set_defaults(func=run)

    # Handle input from the command line
    args = parser.parse_args()            # Parse the arguments
    msg = args.func(args)             # Call the default function
    parser.exit(0, msg+"\n")          # Exit clearnly with message

if __name__ == '__main__':
    main(*sys.argv)