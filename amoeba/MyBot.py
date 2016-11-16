'''
Amoeba - pieces on the permiter attack the highest production piece they can
       - pieces on the interior wait it out
'''

import logging

from hlt import *
from networking import *

logging.basicConfig(filename='amoeba.log')
log = logging.getLogger()
log.setLevel(logging.DEBUG)

myID, gameMap = getInit()
sendInit('amoeba')

def adjacent_sites(gameMap, location):
    for direction in CARDINALS:
        loc = gameMap.getLocation(location, direction)
        site = gameMap.getSite(loc)
        assert site
        yield (loc, gameMap.getSite(loc))

def mine(site):
    return site.owner == myID

def adjacent_unowned_lowest_strength(gameMap, location):
    'the location next to this piece with the lowest strength'
    minimum = 300
    result = None
    for loc, site in adjacent_sites(gameMap, location):
        if mine(site):
            continue
        if site.strength < minimum:
            minimum = site.strength
            result = (loc, site)
    return result

def get_direction(gameMap, first, second):
    'given two adjacent locations returns direction from first to second'
    for direction in CARDINALS:
        loc = gameMap.getLocation(location, direction)
        if loc.x == second.x and loc.y == second.y:
            return direction
    assert False, 'second is not adjacent to first'

while True:
    moves = []
    gameMap = getFrame()

    for y in range(gameMap.height):
        line = []
        for x in range(gameMap.width):
            location = Location(x, y)
            site = gameMap.getSite(location)
            if not mine(site):
                continue

            target = adjacent_unowned_lowest_strength(gameMap, location)
            if not target or target[1].strength > site.strength:
                continue

            direction = get_direction(gameMap, location, target[0])
            moves.append(Move(location, direction))

    sendFrame(moves)
