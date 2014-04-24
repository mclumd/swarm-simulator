# swarm.viz - the graphical visualization module

import math
import numpy
import pygame

def visualize(world, screen_size, fps):
    pygame.init()

    screen = pygame.display.set_mode(screen_size, 0, 32)
    scale = (float(screen_size[0]) / world.size[0],
             float(screen_size[1]) / world.size[1])
    clock = pygame.time.Clock()
    arrow = pygame.image.load("assets/arrow.png").convert_alpha()
    arrow_baked = bake_rotations(arrow, 0.06, math.pi / 2, 128)
    draw(screen, world, arrow_baked, scale)
    frame_time = 1000.0 / fps
    wait_time = frame_time
    running = True

    while running:
        wait_time -= clock.tick(100)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        if wait_time <= 0:
            wait_time = frame_time
            update(world)
            draw(screen, world, arrow_baked, scale)

    pygame.quit()

def update(world):
    """
    Change to world.update so world can pass in neighbors.
    """
    world.update()

def draw(screen, world, baked, scale):
    screen.fill(0xffffffff)

    for agent in world.agents:
        angle = math.atan2(agent.vel[1], agent.vel[0])
        image = rotation(baked, angle)
        x = agent.pos[0] * scale[0] - image.get_width() / 2
        y = screen.get_height() - (agent.pos[1] * scale[1] + image.get_height() / 2)
        screen.blit(image, (x, y))

    pygame.display.flip()

def bake_rotations(image, scale, a0, steps):
    baked = []
    step_size = 2 * math.pi / steps

    for step in xrange(steps):
        a = step * step_size - a0
        degrees = a * 180.0 / math.pi
        baked.append(pygame.transform.rotozoom(image, degrees, scale))

    return baked

def rotation(baked, a):
    steps = len(baked)
    step_size = 2 * math.pi / steps
    a = a % (2 * math.pi)
    i = int(round(a / step_size) % steps)

    return baked[i]
