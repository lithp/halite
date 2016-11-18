'''
Katamari - proof of concept
           finds the weakest piece on the horizon
           waits until we have enough strength to capture it
           pathfinds backwards to find enough pieces, then sets them rolling

Problems - doesn't take production into account
           during combat all the squares next to the enemy count as 0 so we move the
             minium of pieces into them, when we should move many pieces into them

eventual goal:

Stingray - finds the lowest cost tunnel to the enemy and uses it

Does a floodfill starting at the enemy (much like A*) and marks each piece by
how many strength away from the enemy it is. All pieces move downhill along that
gradient (to find a target) (respecting the Katamari strategy)

2 1 2 3 4 5
1 x 1 2 o 6
2 1 2 3 4 5

Altenratively:

Uses A* to route to any part of the enemy from any point on the perimeter.
Once we've made contact with the enemy send everything you have down it.
'''

from queue import PriorityQueue
from collections import namedtuple
import functools

from hlt import *
from networking import *

Piece = namedtuple('Piece', ['loc', 'site'])

myID, gameMap = getInit()
sendInit('katamari')

def p_mine(site):
    return site.owner == myID

def p_my_piece(piece):
    return p_mine(piece.site)

def adjacent_pieces(gmap, location):
    for direction in CARDINALS:
        loc = gmap.one_over(location, direction)
        site = gmap.getSite(loc)
        yield Piece(loc, site)

def my_adjacent_pieces(gmap, location):
    return filter(p_my_piece, adjacent_pieces(gmap, location))

def get_direction(gmap, first, second):
    'given two adjacent locations returns direction from first to second'
    for direction in CARDINALS:
        loc = gmap.one_over(first, direction)
        if loc.x == second.x and loc.y == second.y:
            return direction
    assert False, 'second is not adjacent to first'

def piece_is_border(gmap, piece):
    if p_my_piece(piece):
        return False
    return bool(my_adjacent_pieces(gmap, piece.loc))

def all_pieces(gmap):
    for y in range(gmap.height):
        for x in range(gmap.width):
            location = Location(x, y)
            site = gmap.getSite(location)
            yield Piece(location, site)

def find_move(gmap, target, used_locations):
    unexplored = PriorityQueue()
    visited = set()

    unexplored.put((target.site.strength, target, set()))
    visited.add(target.loc)

    # TODO: I think removing visited and only using path_locations makes sense?
    while not unexplored.empty():
        (remaining, candidate, path_locations) = unexplored.get()

        for piece in my_adjacent_pieces(gmap, candidate.loc):
            if piece.loc in used_locations:
                continue
            if piece.loc in visited:
                continue

            new_path_locations = path_locations.union([piece.loc])

            if piece.site.strength > remaining:
                direction = get_direction(gmap, piece.loc, candidate.loc)
                return (Move(piece.loc, direction), new_path_locations)

            unexplored.put((remaining - piece.site.strength, piece, new_path_locations))
            visited.add(piece.loc)

    return (None, None) # we don't have enough strength so wait until we do

def moves_for(gmap):
    # Build a list of all border pieces and sort them by strength
    # for each border:
    #  attempt to find the strength to attack it, receiving (move, used_locations)

    borders = filter(functools.partial(piece_is_border, gmap), all_pieces(gmap))
    borders = sorted(borders, key=lambda p: p.site.strength)
    moves, used_locations = [], set()

    for border in borders:
        (move, consumed) = find_move(gmap, border, used_locations)
        if move:
            moves.append(move)
            used_locations |= consumed

    return moves

while True:
    gameMap = getFrame()
    moves = moves_for(gameMap)
    sendFrame(moves)
