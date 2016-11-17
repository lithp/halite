'''
Amoeba - pieces on the perimeter attack the highest production piece they can
       - pieces on the interior wait it out

Lance - pieces on the interior move to the closest perimeter

Thermal Lance - don't move into any location which would cause you to cap

Ideas:
- Special-case combat somehow, optimize damage done / damage taken?
- Special-case small colonies and optimize expansion / production

TODO:
- The overcap map is too easy to forget to set, build some kind of infra around it

Maybe:
- The overcap map is currently quite greedy, is it sometimes preferable for a piece
  which wasn't seen first to move instead?

Problems:
- pieces spend a lot of time oscilating when attempting to get to the perim
  This could be an artifact of being on the boundary of the kd-tree?
  Soln: maybe when deciding which way to move, and filtering out capped ones,
        you also filter out the direction which doesn't face the perim
- Capping only checks internal pieces, pieces on the perimeter don't check for capping
  I implemented this but it only improved game performance a little. It wasn't worth
  the extra code
'''

from collections import namedtuple, defaultdict
import random
import kdtree
import cProfile, pstats

from hlt import *
from networking import *

Piece = namedtuple('Piece', ['loc', 'site'])

myID, gameMap = getInit()
sendInit('thermal-lance')

def p_mine(site):
    return site.owner == myID

def p_my_piece(piece):
    return p_mine(piece.site)

def group_by_pred(pred, iterable):
    'takes an iterable and returns two lists, the True and False lists'
    true, false = [], []
    for item in iterable:
        if pred(item):
            true.append(item)
        else:
            false.append(item)
    return true, false

def adjacent_sites(gmap, location):
    for direction in CARDINALS:
        loc = gmap.one_over(location, direction)
        site = gmap.getSite(loc)
        assert site, 'I am so confused'
        yield Piece(loc, site)

def lowest_strength(pieces):
    return min(pieces, key=lambda piece: piece.site.strength, default=None)

def adjacent_unowned_lowest_strength(gmap, location):
    'the location next to this piece with the lowest strength'
    not_mine = filter(lambda piece: not p_mine(piece.site),
                      adjacent_sites(gmap, location))
    return lowest_strength(not_mine)

def get_direction(gmap, first, second):
    'given two adjacent locations returns direction from first to second'
    for direction in CARDINALS:
        loc = gmap.one_over(first, direction)
        if loc.x == second.x and loc.y == second.y:
            return direction
    assert False, 'second is not adjacent to first'

def is_perimeter(gmap, location):
    # if there are any adjacent nodes which are not mine, I'm perimeter
    for item in filter(lambda piece: not p_mine(piece.site),
                       adjacent_sites(gmap, location)):
        return True
    return False

def all_pieces(gmap):
    for y in range(gmap.height):
        for x in range(gmap.width):
            location = Location(x, y)
            site = gmap.getSite(location)
            yield Piece(location, site)

def moves_for(gmap):
    moves = []
    perimeter_tree = kdtree.create(dimensions=2)
    perimeter_nodes = []
    internal_nodes = []

    # 1) partition all our pieces

    my_pieces = filter(lambda piece: p_mine(piece.site), all_pieces(gmap))

    p_perim = lambda piece: is_perimeter(gmap, piece.loc)
    perimeter_nodes, internal_nodes = group_by_pred(p_perim, my_pieces)

    for piece in perimeter_nodes:
        perimeter_tree.add((piece.loc.x, piece.loc.y))
    perimeter_tree.rebalance()

    # 2) move perimeter_nodes

    for (location, site) in perimeter_nodes:
        target = adjacent_unowned_lowest_strength(gmap, location)
        assert target

        if target.site.strength > site.strength:
            # we're too weak to attack, wait it out
            continue

        direction = get_direction(gmap, location, target.loc)
        moves.append(Move(location, direction))

    # refuse to move enough strength into a location to cause overcapping
    overcap_map = defaultdict(int)

    # 3) move internal pieces

    stays, highs = group_by_pred(lambda piece: gmap.getSite(piece.loc).strength < 50,
                                 internal_nodes)

    for (location, site) in stays:
        overcap_map[location] += site.strength

    for (location, site) in highs:
        closest_perim = perimeter_tree.search_nn((location.x, location.y))[0]
        perim_loc = Location(closest_perim.data[0], closest_perim.data[1])

        def p_overcap(neighbor):
            # This still allows some amount of capping, the idea is that two squares
            # which are both at 255 won't move into each other, but if we don't allow
            # any overcapping at all the big pieces get trapped
            moved_strength = overcap_map[neighbor.loc]
            return site.strength + moved_strength <= 300
        allowed = filter(p_overcap, adjacent_sites(gmap, location))

        distance_to = lambda neighbor: gmap.getDistance(perim_loc, neighbor.loc)
        closest_neighbor = min(allowed, key=distance_to, default=None)

        if not closest_neighbor:
            # we shouldn't move, make sure nobody crashes into us
            overcap_map[location] += site.strength
            continue

        direction = get_direction(gmap, location, closest_neighbor.loc)
        moves.append(Move(location, direction))
        overcap_map[closest_neighbor.loc] += site.strength

    return moves

turn = 0
while True:
    gameMap = getFrame()

    #if turn == 100:
    #    profile = cProfile.Profile()

    #if turn >= 100 and turn <= 199:
    #    profile.enable()

    moves = moves_for(gameMap)

    #if turn >= 100 and turn <= 199:
    #    profile.disable()

    #if turn == 199:
    #    profile.create_stats()

    #    stats = pstats.Stats(profile)
    #    stats.dump_stats('thermal.profile')

    sendFrame(moves)
    turn += 1
