import logging

from hlt import *
from networking import *

logging.basicConfig(filename='whatever.log')
log = logging.getLogger()
log.setLevel(logging.DEBUG)

myID, gameMap = getInit()
sendInit('prod-logger')

gameMap = getFrame()

log.debug('Production Values')
log.debug('-----------------')

for y in range(gameMap.height):
    line = []
    for x in range(gameMap.width):
        location = Location(x, y)
        site = gameMap.getSite(location)
        line.append(str(site.production).rjust(2))
    log.debug(','.join(line))

log.debug('Strength Values')
log.debug('-----------------')

for y in range(gameMap.height):
    line = []
    for x in range(gameMap.width):
        location = Location(x, y)
        site = gameMap.getSite(location)
        line.append(str(site.strength).rjust(3))
    log.debug(','.join(line))
