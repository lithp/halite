'''
Katamari - proof of concept
           finds the weakest piece on the horizon
           waits until we have enough strength to capture it
           pathfinds backwards to find enough pieces, then sets them rolling

Damacy   - does the same but instead of looking for lowest strength, looks for the
           cheapest path to the enemy

           don't treat pieces next to the enemy as strength 0, sum the strength of the
           enemy pieces next to them
           (this had almost no effect, and made the performance on small boards worse)

Point Defense Drone - once it makes contact with the enemy it routes all pieces towards
                      that point of contact, avoiding capping as much as possible

                      starting at the point of contact we do a breadth-first search,
                      keeping track of where each piece will move (to prevent capping).
                      If it isn't able to move it waits

                      at each point we find the unvisited neighbors and attempt to pull 
                      them towards us

Problems:
    - platooning appears to be important even during battles
    - routing all your strength appears to be more important than battles
      (for big maps, your interior still caps and it's a massive waste)
    - (also, only thinks about one battle at a time)

Problem for combat:
- First we plan a move for the piece next to the enemy.
- After we've planned the move, the best path to the enemy is now "taken", so pieces
  which should keep going down that path are now forced to take a different route, even
  though they conflict in space but not space-time

- After we've planned the capture of a piece we don't target it again until the next turn
  More importantly, we don't target the pieces beyond it until it has been captured

How about:
1. Once you've finished routing a piece throw its adjacent pieces back into the queue
   If they come next, then route to it but without using any of the used pieces
    This requires drawing strength from further back, you can start platoons "in the
    past"?

How would you maximize the strength which is sent to a specific square?
1 From all the contact points with the enemy flood-fill your own territory to detemine
  which pieces will serve which point of contact

  Do a breadth-first search to pull pieces toward you
  a. Gather strength and try to get 255 at your target
  b. once you've done that, try again, but instead of marking a spot "used"
     mark (moves in the future, location) tuples used
  c. if any pieces assigned to target are trapped, have them wait
     (don't waste strength on expanding while there's a fight!)

erden appears to send a piece every three turns, and pieces hop on the train as it moves

A devastating loss:
./halite -s 2248200476 -d "10 10" "python3 damacy/MyBot.py" "python3 thermal-lance/MyBot.py"
1480800096-2248200476.hlt
This bot does quite badly at close quarters
'''

import math
from queue import PriorityQueue, Queue
from collections import namedtuple, defaultdict
import functools

from hlt import *
from networking import *

Piece = namedtuple('Piece', ['loc', 'site'])

myID, gameMap = getInit()
sendInit('point-defense-drone')

def p_mine(site):
    return site.owner == myID

def p_my_piece(piece):
    return p_mine(piece.site)

def p_enemy(piece):
    return piece.site.owner != myID and piece.site.owner != 0

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

def cost_to_enemy_map(gmap):
    '''
    returns a dict[loc] -> cost, where cost is the cheapest path
    (by strength) from this cell to any enemy cell.
    '''
    enemies = [enemy.loc for enemy in all_pieces(gmap) if p_enemy(enemy)]

    # flood-fill, starting from any of the enemies, until there are no more nodes
    horizon = PriorityQueue()
    visited = set()

    # defaultdict because lower down we stop routing once we see any of our own pieces.
    # doing so means that any enclaves are never considered which causes issues later on.
    cost_to_enemy = defaultdict(lambda: math.inf)

    for enemy in enemies:
        cost_to_enemy[enemy] = 0
        visited.add(enemy)
        horizon.put((0, enemy)) # All enemy cells are considered equally valuable

    while not horizon.empty():
        (curr_cost, enemy) = horizon.get()

        for neighbor in adjacent_pieces(gmap, enemy):
            if neighbor.loc in visited:
                continue
            visited.add(neighbor.loc)

            # TODO: Maybe you don't want this check?
            if p_my_piece(neighbor):
                continue

            new_cost = curr_cost + neighbor.site.strength
            cost_to_enemy[neighbor.loc] = new_cost
            horizon.put((new_cost, neighbor.loc))

    return cost_to_enemy

def assign_to_battle(gmap, target, used_locations):
    'Takes every piece within a radius of 10 and moves them towards the target'
    visited = set() # the set of nodes we have already considered
    unexplored = Queue() # the neighbors of visited nodes
    moves = []
    assigned = set()

    # prevent capping by keeping track of how much strength is sent to each node
    assigned_strength = defaultdict(int) # map from loc->strength

    unexplored.put((target, 0))
    visited.add(target.loc)

    while not unexplored.empty():
        (current, depth) = unexplored.get()

        if current.loc not in assigned:
            # none of my neighbors with a lower depth wanted me, so I will stay
            assigned_strength[current.loc] += current.site.strength
            assigned.add(current.loc)

        for neighbor in my_adjacent_pieces(gmap, current.loc):
            if neighbor.loc in visited:
                continue
            visited.add(neighbor.loc)

            if neighbor.site.strength + assigned_strength[current.loc] < 255:
                # pull the neighbor to this cell
                direction = get_direction(gmap, neighbor.loc, current.loc)
                moves.append(Move(neighbor.loc, direction))
                assigned.add(neighbor.loc)
                assigned_strength[current.loc] += neighbor.site.strength

            if (depth + 1) <= 10:
                unexplored.put((neighbor, depth + 1))

    return moves, assigned


def find_move(gmap, target, used_locations):
    unexplored = PriorityQueue()
    visited = set()

    is_enemy = False
    enemy_strength = 0
    for neighbor in adjacent_pieces(gmap, target.loc):
        if p_enemy(neighbor):
            enemy_strength += neighbor.site.strength
            is_enemy = True

    unexplored.put((enemy_strength + target.site.strength, target, set()))
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

    #if is_enemy:
        # normally we would return, not having found enough strength, but if it's an
        # enemy we push through anyway
    #    pass

    return (None, None) # we don't have enough strength so wait until we do

def moves_for(gmap):

    # 1. first look for points of conflict
    def is_conflicted(piece):
        if not piece.site.strength == 0:
            return False
        next_to_mine = False
        next_to_enemy = False
        for piece in adjacent_pieces(gmap, piece.loc):
            owner = piece.site.owner
            next_to_mine |= (owner == myID)
            next_to_enemy |= (owner != myID and owner != 0)
        return next_to_mine and next_to_enemy
    battles = filter(is_conflicted, all_pieces(gmap))

    try:
        first_battle = next(battles)
    except StopIteration:
        moves, used_locations = [], set()
    else:
        (moves, used_locations) = assign_to_battle(gmap, first_battle, set())

    cost_map = cost_to_enemy_map(gmap)

    borders = filter(functools.partial(piece_is_border, gmap), all_pieces(gmap))
    borders = sorted(borders, key=lambda p: cost_map[p.loc])

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
