'''
Katamari - proof of concept
           finds the weakest piece on the horizon
           waits until we have enough strength to capture it
           pathfinds backwards to find enough pieces, then sets them rolling

Problems - doesn't take into account production
           only one target at a time is being addressed

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

from hlt import *
from networking import *

Piece = namedtuple('Piece', ['loc', 'site'])

myID, gameMap = getInit()
sendInit('katamari')

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

def adjacent_pieces(gmap, location):
    for direction in CARDINALS:
        loc = gmap.one_over(location, direction)
        site = gmap.getSite(loc)
        assert site, 'I am so confused'
        yield Piece(loc, site)

def my_adjacent_pieces(gmap, location):
    for piece in adjacent_pieces(gmap, location):
        if p_my_piece(piece):
            yield piece

def lowest_strength(pieces):
    return min(pieces, key=lambda piece: piece.site.strength, default=None)

def adjacent_unowned_lowest_strength(gmap, location):
    'the location next to this piece with the lowest strength'
    not_mine = filter(p_my_piece, adjacent_pieces(gmap, location))
    return lowest_strength(not_mine)

def get_direction(gmap, first, second):
    'given two adjacent locations returns direction from first to second'
    for direction in CARDINALS:
        loc = gmap.one_over(first, direction)
        if loc.x == second.x and loc.y == second.y:
            return direction
    assert False, 'second is not adjacent to first'

def is_perimeter(gmap, location):
    'a piece I own adjacent to a piece I do not own'
    if not p_mine(gmap.getSite(location)):
        return False
    for item in filter(p_my_piece, adjacent_pieces(gmap, location)):
        return True
    return False

def is_border(gmap, location):
    'a piece I do not own, adjacent to a piece I own'
    if p_mine(gmap.getSite(location)):
            return False
    for item in filter(lambda piece: p_mine(piece.site),
                       adjacent_pieces(gmap, location)):
        return True
    return False

def all_pieces(gmap):
    for y in range(gmap.height):
        for x in range(gmap.width):
            location = Location(x, y)
            site = gmap.getSite(location)
            yield Piece(location, site)

def find_move(gmap, used_pieces):
    def p_valid_border(piece):
        if p_my_piece(piece):
            return False
        mine = filter(p_my_piece, adjacent_pieces(gmap, piece.loc))
        for item in filter(lambda p: p.loc not in used_pieces, mine):
            return True
        return False

    border_pieces = filter(p_valid_border, all_pieces(gmap))
    target = min(border_pieces, key=lambda piece: piece.site.strength, default=None)

    if not target:
        return (None, None)

    unexplored = PriorityQueue()
    visited = set()

    unexplored.put((target.site.strength, target, set()))
    visited.add(target.loc)

    while not unexplored.empty():
        (remaining, candidate, path_locations) = unexplored.get()

        for piece in my_adjacent_pieces(gmap, candidate.loc):
            if piece.loc in used_pieces:
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
    moves, used_locations = [], set()
    (new_move, new_locations) = find_move(gmap, used_locations)
    while new_move:
        used_locations |= new_locations
        moves.append(new_move)
        (new_move, new_locations) = find_move(gmap, used_locations)

    return moves

while True:
    gameMap = getFrame()
    moves = moves_for(gameMap)
    sendFrame(moves)
