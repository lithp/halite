'''
Amoeba - pieces on the permiter attack the highest production piece they can
       - pieces on the interior wait it out

Lance - pieces on the interior move to the closest perimeter if it wouldn't cap
'''

import logging
from collections import namedtuple
import random
import kdtree

from hlt import *
from networking import *

Tup = namedtuple('Tup', ['loc', 'site'])

logging.basicConfig(filename='amoeba.log')
log = logging.getLogger()
log.setLevel(logging.DEBUG)

myID, gameMap = getInit()
sendInit('lance')

def angle_to_direction(angle):
    pi = math.pi

    if angle >= (pi/4) and angle < (3*pi/4):
        return NORTH

    if angle >= (3*pi/4) or angle < (-3*pi/4):
        return WEST

    if angle < (pi/4) and angle >= (-pi*4):
        return EAST

    if angle < (-pi*4) and angle >= (-3*pi/4):
        return SOUTH

    assert False, 'this should not happen'

def adjacent_sites(gameMap, location):
    for direction in CARDINALS:
        loc = gameMap.getLocation(location, direction)
        site = gameMap.getSite(loc)
        assert site
        yield Tup(loc, gameMap.getSite(loc))

def mine(site):
    return site.owner == myID

def lowest_strength(tups):
    return min(tups, key=lambda tup: tup.site.strength, default=None)

def adjacent_unowned_lowest_strength(gameMap, location):
    'the location next to this piece with the lowest strength'
    minimum = 300
    result = None
    not_mine = filter(lambda tup: not mine(tup.site),
                      adjacent_sites(gameMap, location))
    return lowest_strength(not_mine)

def get_direction(gameMap, first, second):
    'given two adjacent locations returns direction from first to second'
    for direction in CARDINALS:
        loc = gameMap.getLocation(location, direction)
        if loc.x == second.x and loc.y == second.y:
            return direction
    assert False, 'second is not adjacent to first'

def is_perimeter(gameMap, location):
    # if there are any adjacent nodes which are not mine, I'm perimeter
    for item in filter(lambda tup: not mine(tup.site),
            adjacent_sites(gameMap, location)):
        return True
    return False

while True:
    moves = []
    gameMap = getFrame()

    perimeter_tree = kdtree.create(dimensions=2)
    perimeter_nodes = []

    internal_nodes = []

    # first collect all the nodes
    for y in range(gameMap.height):
        for x in range(gameMap.width):
            location = Location(x, y)
            site = gameMap.getSite(location)
            if not mine(site):
                continue

            if is_perimeter(gameMap, location):
                perimeter_tree.add((x, y))
                perimeter_nodes.append(location)
            else:
                internal_nodes.append(location)

    perimeter_tree.rebalance()

    # now move them!
    for location in perimeter_nodes:
        site = gameMap.getSite(location)
        target = adjacent_unowned_lowest_strength(gameMap, location)

        if not target:
            continue

        if target[1].strength > site.strength:
            # we're too weak to attack, wait it out
            continue

        direction = get_direction(gameMap, location, target[0])
        moves.append(Move(location, direction))

    for location in internal_nodes:
        site = gameMap.getSite(location)
        if site.strength < 50:
            continue

        closest_perim = perimeter_tree.search_nn((location.x, location.y))[0]
        perim_loc = Location(closest_perim.data[0], closest_perim.data[1])

        distance_to = lambda neighbor: gameMap.getDistance(perim_loc, neighbor.loc)
        min_neighbor = min(adjacent_sites(gameMap, location), key=distance_to)

        direction = get_direction(gameMap, location, min_neighbor.loc)
        #next_spot = gameMap.getLocation(location, direction)
        moves.append(Move(location, direction))

    sendFrame(moves)

'''
        # debug the current state!
        log.debug('Current board:')
        log.debug('--------------')

        for y in range(gameMap.height):
            line = []
            for x in range(gameMap.width):
                loc = Location(x, y)
                site = gameMap.getSite(loc)
                if loc.x == location.x and loc.y == location.y:
                    line.append('Q')
                elif min_neighbor.loc.x == loc.x and min_neighbor.loc.y == loc.y:
                    line.append('M')
#                elif next_spot.x == loc.x and next_spot.y == loc.y:
#                    line.append('N')
                elif perim_loc.x == loc.x and perim_loc.y == loc.y:
                    line.append('Z')
                elif site.owner == myID:
                    line.append('x')
                else:
                    line.append('_')
            log.debug(' '.join(line))

        log.debug('direction: %s', direction)

        assert False
'''
