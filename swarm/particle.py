# sarsim.particle
# A Particle class for local behaviors
#
# Author:   Benjamin Bengfort <benjamin@bengfort.com>
# Created:  Tue Apr 15 10:50:20 2014 -0400
#
# Copyright (C) 2014 Bengfort.com
# For license information, see LICENSE.txt
#
# ID: particle.py [] benjamin@bengfort.com $

"""
A Particle class for local behaviors
"""

##########################################################################
## Imports
##########################################################################

import numpy as np
from params import parameters
from exceptions import *
from vectors import Vector

##########################################################################
## Module Constants
##########################################################################

## Possible states
SPREADING = "spreading"
SEEKING   = "seeking"
CARAVAN   = "caravan"
GUARDING  = "guarding"

## Maximum Velocity
VMAX      = parameters.get('maximum_velocity')

##########################################################################
## Particle Object
##########################################################################

class Particle(object):

    def __init__(self, position, velocity, identifier=None, **kwargs):
        """
        Initialize a particle by assigning a position and velocity to it.
        Optional parameters include assigning an idx value (a unique way
        to identify the particle) and the world it belongs to, so that it
        can be bound to discover its own neighborhood.
        """
        self.pos   = Vector.arr(position)           # Init vectors here?
        self.vel   = Vector.arr(velocity)           # Init vectors here?
        self.idx   = identifier
        self.world = kwargs.get('world', None)      # Initialize in world
        self.state = kwargs.get('state', SPREADING) # Set initial state...
        self.team  = kwargs.get('team', 'ally')     # Set the team

        # Hidden variables to reduce computation

    def __repr__(self):
        type_name  = self.__class__.__name__
        identifier = self.idx or "anonymous"
        if self.world:
            return "<bound %s %s of %r>" % (type_name, identifier, self.world)
        return "<unbound %s %s>" % (type_name, identifier)

    ##////////////////////////////////////////////////////////////////////
    ## Particle Methods
    ##////////////////////////////////////////////////////////////////////

    def update(self):
        """
        Called to update the particle at a new timestep.
        """
        self.update_velocity()
        self.update_position()

    def update_position(self):
        newpos = self.pos + self.newvel
        x = newpos.x % self.world.size[0]
        y = newpos.y % self.world.size[1]
        self.newpos = Vector.arrp(x,y)

    def update_velocity(self):
        """
        Instead of starting with velocity zero as in the ARod paper, we
        implement 'intertia' by using the old velocity.
        """
        vectors = []    # Tuples of vector components and their priority
        for component, parameters in self.components.items():
            # Get the method by name and compute
            if hasattr(self, component):
                velocity = getattr(self, component)
                vectors.append((component, velocity(), parameters))
            else:
                raise Exception("No method on %r, '%s'" % (self, component))

        # Sort the vectors by priority
        vectors = sorted(vectors, key=lambda vp: vp[2].priority)
        #print [(comp, (vec * param.weight).length) for comp,vec,param in vectors]

        newvel  = Vector.arrp(self.vel.x, self.vel.y)
        for comp, vec, params in vectors:
            wvec = newvel + (params.weight * vec)
            if wvec.length > VMAX:
                continue
            newvel = wvec

        self.newvel = newvel

    ##////////////////////////////////////////////////////////////////////
    ## Helper Functions
    ##////////////////////////////////////////////////////////////////////

    @property
    def components(self):
        """
        Get movement behaviors components based on state
        """
        _behavior = parameters.get(self.state)
        if _behavior is None:
            raise ImproperlyConfigured("No movement behaviors for state '%s'." % self.state)
        return _behavior.components

    def is_bound(self):
        """
        Returns the bound state of the particle.
        """
        if not self.world: return False
        return True

    def neighbors(self, radius, alpha):
        """
        Finds the neighbors given a radius and an alpha

        Is there a better way than running through all the agents and
        checking if they are within our neighborhood, for every single
        velocity component we check?!

        TODO: Store neighborhood until blit
        """

        if not self.is_bound():
            raise Exception("Can only find neighbors for bound particles.")

        for agent in self.world.agents:
            if agent is self: continue        # We're not in our own neighborhood

            distance = np.linalg.norm(self.pos-agent.pos)
            if distance > radius: continue    # Outside of our own vision radius

            # compute heading to other
            delta = agent.pos - self.pos
            angle = self.vel.angle(delta)
            alpha = alpha / 2
            if angle > alpha:
                continue

            yield agent                       # The agent is a neighbor!

    def find_nearest(self, radius, alpha, team="any"):
        """
        Finds the nearest point from the neighbors
        """
        nearest  = None
        distance = None
        for neighbor in self.neighbors(radius, alpha):

            if team != 'any' and neighbor.team != team:
                continue

            d = np.linalg.norm(self.pos - neighbor.pos)
            if distance is None or d < distance:
                distance = d
                nearest  = neighbor
        return nearest

    def blit(self):
        """
        Swap new pos/vel for old ones.
        """
        self.pos = self.newpos
        self.vel = self.newvel

    ##////////////////////////////////////////////////////////////////////
    ## Movement Behavior Velocity Components
    ##////////////////////////////////////////////////////////////////////

    def cohesion(self):
        """
        Reports coehesion velocity from an array of neighbors
        """
        r = self.components['cohesion'].radius
        a = self.components['cohesion'].alpha
        neighbors = list(self.neighbors(r,a))

        if not neighbors:
            return Vector.zero()

        center = np.average(list(n.pos for n in neighbors), axis=0)
        delta  = center - self.pos

        scale  = (delta.length / r) ** 2
        vmaxrt = VMAX * delta.unit
        return vmaxrt * scale

    def alignment(self):
        """
        Reports the alignment velocity from an array of neighbors
        """
        r = self.components['alignment'].radius
        a = self.components['alignment'].alpha
        neighbors = list(self.neighbors(r,a))

        if not neighbors:
            return Vector.zero()

        center = np.average(list(n.pos for n in neighbors), axis=0)
        deltap = center - self.pos
        scale  = (deltap.length / r) ** 2

        avgvel = np.average(list(n.vel for n in neighbors), axis=0)
        #deltav = avgvel - self.vel     # Why are we subtracting the average velocity from ours? Makes no sense.
        deltav = Vector.arr(avgvel)
        vmaxrt = VMAX * deltav.unit

        return vmaxrt #* scale

    def avoidance(self):
        """
        Reports the avoidance velocity from an array of neighbors

        Target should be the closest enemy agent. See the following:
        nearest, _ = self.find_nearest(neighbors)

        Changed the formula to (r-dp.length /r)**2
        """
        r = self.components['avoidance'].radius
        a = self.components['avoidance'].alpha
        target = self.find_nearest(r, a, 'enemy')

        if not target:
            return Vector.zero()

        delta  = target.pos - self.pos
        scale  = ((r - delta.length) / r) ** 2
        vmaxrt = VMAX * (delta / delta.length)

        return -1 * vmaxrt * scale

    def separation(self):
        """
        Reports the separation velocity from an array of neighbors

        Changed the formula to (r-dp.length /r)**2
        """
        r = self.components['separation'].radius
        a = self.components['separation'].alpha
        neighbors = list(self.neighbors(r,a))

        if not neighbors:
            return Vector.zero()

        center = np.average(list(n.pos for n in neighbors), axis=0)
        delta  = center - self.pos

        scale  = ((r - delta.length) / r) ** 2
        vmaxrt = VMAX * delta.unit

        return -1 * vmaxrt * scale

    def seeking(self):
        """
        Reports the seeking velocity to a target.

        How do we store a target?
        """
        if not hasattr(self, 'target'):
            raise Exception("In Seeking, the particle must have a target")

        direction = self.target.pos - self.pos
        return VMAX * (direction / direction.length)

    def clearance(self):
        """
        Reports the clearance velocity orthoganol to current velocity
        """
        r = self.components['clearance'].radius
        a = self.components['clearance'].alpha
        neighbors = list(self.neighbors(r,a))
        if neighbors:
            return VMAX * self.vel.orthogonal
        return Vector.zero()

    def homing(self):
        """
        Reports the homing velocity component to move the agent to a point
        """
        if not hasattr(self, 'target'):
            raise Exception("In Homing, the particle must have a target")

        direction = self.target.pos - self.pos
        return VMAX * (direction / direction.length)

if __name__ == '__main__':

    from params import parameters
    from world import SimulatedWorld

    debug = parameters.get('debug', True)
    world = SimulatedWorld()

    def update(iterations=1):

        def inner_update():
            for agent in world.agents:
                agent.update()
                print "%s at %s going %s" % (agent.idx, str(agent.pos), str(agent.vel))

        print "Initial state:"
        for agent in world.agents:
            print "%s at %s going %s" % (agent.idx, str(agent.pos), str(agent.vel))

        for i in xrange(1, iterations+1):
            print
            print "Iteration #%i" % i
            inner_update()

    update()
