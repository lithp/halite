import random
import math
import copy

STILL = 0
NORTH = 1
EAST = 2
SOUTH = 3
WEST = 4

DIRECTIONS = [a for a in range(0, 5)]
CARDINALS = [a for a in range(1, 5)]

ATTACK = 0
STOP_ATTACK = 1

class Location:
    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y

    def __key(self):
        return (self.x, self.y)

    def __eq__(self, obj):
        return self.__key() == obj.__key()

    def __repr__(self):
        return "<Location {}, {}>".format(self.x, self.y)

    def __hash__(self):
        return hash(self.__key())


class Site:
    def __init__(self, owner=0, strength=0, production=0):
        self.owner = owner
        self.strength = strength
        self.production = production

    def __repr__(self):
        return "<Site o:{}, s:{}, p:{}>".format(self.owner, self.strength, self.production)


class Move:
    def __init__(self, loc=0, direction=0):
        self.loc = loc
        self.direction = direction

    def __repr__(self):
        direction_strings = {
            0: "STILL",
            1: "NORTH",
            2: "EAST",
            3: "SOUTH",
            4: "WEST"
        }

        return "<Move l:({}, {}) d:{}>".format(self.loc.x, self.loc.y, direction_strings[self.direction])


class GameMap:
    def __init__(self, width = 0, height = 0, numberOfPlayers = 0):
        self.width = width
        self.height = height
        self.contents = []

        for y in range(0, self.height):
            row = []
            for x in range(0, self.width):
                row.append(Site(0, 0, 0))
            self.contents.append(row)

    def inBounds(self, l):
        return l.x >= 0 and l.x < self.width and l.y >= 0 and l.y < self.height

    def getDistance(self, l1, l2):
        dx = abs(l1.x - l2.x)
        dy = abs(l1.y - l2.y)
        if dx > self.width / 2:
            dx = self.width - dx
        if dy > self.height / 2:
            dy = self.height - dy
        return dx + dy

    def getAngle(self, l1, l2):
        dx = l2.x - l1.x
        dy = l2.y - l1.y

        if dx > self.width - dx:
            dx -= self.width
        elif -dx > self.width + dx:
            dx += self.width

        if dy > self.height - dy:
            dy -= self.height
        elif -dy > self.height + dy:
            dy += self.height
        return math.atan2(dy, dx)

    def one_over(self, loc, direction):
        if direction == STILL:
            # TODO: Is the copy important? Locations should be immutable...
            return Location(loc.x, loc.y)
        if direction == NORTH:
            return Location(loc.x, (loc.y - 1) % self.height)
        if direction == SOUTH:
            return Location(loc.x, (loc.y + 1) % self.height)
        if direction == EAST:
            return Location((loc.x + 1) % self.width, loc.y)
        if direction == WEST:
            return Location((loc.x - 1) % self.width, loc.y)
        assert False

    def getLocation(self, loc, direction):
        l = copy.deepcopy(loc)
        if direction != STILL:
            if direction == NORTH:
                if l.y == 0:
                    l.y = self.height - 1
                else:
                    l.y -= 1
            elif direction == EAST:
                if l.x == self.width - 1:
                    l.x = 0
                else:
                    l.x += 1
            elif direction == SOUTH:
                if l.y == self.height - 1:
                    l.y = 0
                else:
                    l.y += 1
            elif direction == WEST:
                if l.x == 0:
                    l.x = self.width - 1
                else:
                    l.x -= 1
        return l

    def getSite(self, l, direction = STILL):
        l = self.one_over(l, direction)
        return self.contents[l.y][l.x]
