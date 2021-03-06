# sarsim.world
# Contains the mechanics and behavior of the world
#
# Author:   Benjamin Bengfort <bengfort@cs.umd.edu>
# Created:  Tue Apr 08 12:15:08 2014 -0400
#
# Copyright (C) 2014 UMD Metacognitive Lab
# For license information, see LICENSE.txt
#
# ID: world.py [] bengfort@cs.umd.edu $

"""
Contains the mechanics and behavior of the world
"""

##########################################################################
## Imports
##########################################################################

from particle import *
from vectors import Vector
from params import *
from distribute import circular_distribute, linear_distribute

##########################################################################
## Helper functions
##########################################################################

def initialize_particles(**kwargs):
    """
    Initialize N particles in a circular distribution around a center
    point, where N=number. Keyword arguments include a radius from the
    center, an identifier pattern and other keyword arguments that would
    instantiate a particle.
    """

    # Initialize variables needed to do initialization
    klass  = kwargs.get('type', Particle)
    number = kwargs.get('number', world_parameters.get('team_size'))
    center = kwargs.get('center', (750,750))
    radius = kwargs.get('radius', 100)
    team   = kwargs.get('team', 'ally')
    maxvel = kwargs.get('maximum_velocity', world_parameters.get('maximum_velocity'))
    home   = kwargs.get('home', None)
    params = kwargs.get('params', world_parameters)

    # Generate coordinates and particles
    coords = zip(*circular_distribute(num=number, center=center, r=radius))
    for idx, coord in enumerate(coords):
        position = Vector.arrp(*coord)
        velocity = Vector.rand(maxvel) if maxvel > 0 else Vector.zero()
        name     = team + "%02i" % (idx+1)
        yield klass(position, velocity, name, team=team, home=home, params=params)

def initialize_resources(**kwargs):
    """
    Initialize N particles in a linear distribution along a line with a
    slope and an intercept. N=number. Keyword arguments include the slope,
    the intercept, and the length of the line to distribute along.
    """

    # Initialize variables needed to do initialization
    klass  = kwargs.get('type', ResourceParticle)
    number = kwargs.get('number', world_parameters.get('deposits')) + 2  # Add two to skip corners
    length = kwargs.get('length', 3000)
    slope  = kwargs.get('slope', -1)
    yint   = kwargs.get('yint', 3000)

    coords = zip(*linear_distribute(number, length, slope, yint))
    for idx, coord in enumerate(coords):
        if coord[0] in (0.0, length): continue  # Skip corners
        yield klass(Vector.arrp(*coord), identifier="mineral%2i" % (idx+1))

##########################################################################
## The world environment for a simulation
##########################################################################

class World(object):
    """
    Performs the mechanics of simulating the world
    """

    @staticmethod
    def create_ally_home():
        """
        Constructs the ALLY_HOME on a per-simulation basis.
        """
        return ResourceParticle(Vector.arrp(750,750), identifier="ally_home", stash_size=0)

    @staticmethod
    def create_enemy_home():
        """
        Constructs the ENEMY_HOME on a per-simulation basis.
        """
        return ResourceParticle(Vector.arrp(2250,2250), identifier="enemy_home", stash_size=0)

    def __init__(self, **kwargs):
        # Helper function for accessing kwargs and parameters
        setting = lambda name: kwargs.pop(name, world_parameters.get(name))

        # Initialize parameters from settings
        world_size = setting('world_size')
        self.size = (world_size, world_size)
        self.iterations = setting('maximum_time')
        self.deposits = setting('deposits')
        self.time = 0

        # Create the home particles
        self.ally_home  = self.create_ally_home()
        self.enemy_home = self.create_enemy_home()

        # Create an empty agents list
        self.agents = []

        # Initialize the allies
        ally_parameters = AllyParameters.load_file(setting('ally_conf_path'))
        if 'agents' in kwargs:
            self.add_agents(kwargs.pop('agents'))
        else:
            self.add_agents(initialize_particles(params=ally_parameters, home=self.ally_home))
            self.add_agents(initialize_particles(team="enemy", center=(2250,2250), home=self.enemy_home))

        # Initialize the bases
        self.add_agent(self.ally_home)
        self.add_agent(self.enemy_home)

        # Initialize resources
        self.add_agents(initialize_resources())
        self.resources = [agent for agent in self.agents if agent.idx.startswith('mineral')]

    def add_agent(self, agent):
        agent.world = self
        self.agents.append(agent)

    def add_agents(self, agents):
        for agent in agents:
            self.add_agent(agent)

    def update(self):
        for agent in self.agents:
            agent.update()
        for agent in self.agents:
            agent.blit()
        self.time += 1

    def status(self):
        """
        Reports the number of resources in the bases and resource depots
        at the given timestamp. (Ordered tuple).
        """
        bases = (self.ally_home.stash, self.enemy_home.stash)
        depot = tuple(depot.stash for depot in self.resources)
        return bases + depot
