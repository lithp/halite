'''
Amoeba - pieces on the permiter attack the highest production piece they can
       - pieces on the interior wait it out

Lance - pieces on the interior move to the closest perimeter

Thermal Lance - small improvements
                don't move into any location which would cause you to cap

Ideas:
- Special-case combat somehow, optimize damage done / damage taken?
- Special-case small colonies and optimize expansion / production
'''

import logging
from collections import namedtuple, defaultdict
import random
import kdtree

from hlt import *
from networking import *

Tup = namedtuple('Tup', ['loc', 'site'])

logging.basicConfig(filename='amoeba.log')
log = logging.getLogger()
log.setLevel(logging.DEBUG)

myID, gameMap = getInit()
sendInit('thermal-lance')

def group_by_pred(pred, iterable):
    'takes an iterable and returns two lists, the True and False lists'
    true, false = [], []
    for item in iterable:
        if pred(item):
            true.append(item)
        else:
            false.append(item)
    return true, false

def adjacent_sites(gameMap, location):
    for direction in CARDINALS:
        loc = gameMap.getLocation(location, direction)
        site = gameMap.getSite(loc)
        assert site, 'I am so confused'
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
        loc = gameMap.getLocation(first, direction)
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

    # keep track of where you'll move every piece and refuse to move enough strength
    # into the same spot if it causes overcapping
    overcap_map = defaultdict(int)
    # TODO: there has to be a cleaner way to do this, it's too easy to forget to update
    # the overcap_map after making a decision
    # MAYBE: the overcap is currently very greedy, the first piece to want to move gets
    # priority. Are there situations where a later piece might be more important?

    stays, highs = group_by_pred(lambda loc: gameMap.getSite(loc).strength < 50,
                                 internal_nodes)

    for location in stays:
        site = gameMap.getSite(location)
        overcap_map[(location.x, location.y)] += site.strength

    for location in highs:
        site = gameMap.getSite(location)

        closest_perim = perimeter_tree.search_nn((location.x, location.y))[0]
        perim_loc = Location(closest_perim.data[0], closest_perim.data[1])

        def p_overcap(neighbor):
            # This still allows some amount of capping, the idea is that two squares
            # which are both at 255 won't move into each other, but if we don't allow
            # any overcapping at all the big pieces get trapped
            moved_strength = overcap_map[(neighbor.loc.x, neighbor.loc.y)]
            return site.strength + moved_strength <= 300
        allowed = filter(p_overcap, adjacent_sites(gameMap, location))

        distance_to = lambda neighbor: gameMap.getDistance(perim_loc, neighbor.loc)
        min_neighbor = min(allowed, key=distance_to, default=None)

        # to stop oscillating, we should also never move away from the perim?
        # (the max_neighbor should be filtered out)

        if not min_neighbor:
            # we shouldn't move, make sure nobody crashes into us
            overcap_map[(location.x, location.y)] += site.strength
            continue

        direction = get_direction(gameMap, location, min_neighbor.loc)
        moves.append(Move(location, direction))

        next_spot = gameMap.getLocation(location, direction)
        overcap_map[(next_spot.x, next_spot.y)] += site.strength

    sendFrame(moves)
