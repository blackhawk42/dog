from __future__ import annotations
import random
import argparse
import sys
import logging
import datetime
import json
from pathlib import Path
from dataclasses import dataclass
from typing import Callable, Optional, List, Set, Union, Tuple, Iterable, Dict

@dataclass
class Player:
    id: int
    name: str
    game: Game
    currentPlace: int
    totalPlaces: int
    turnsToSkip: int

    def move(self, step: int):
        if step > 0:
            # Deal with overflows
            if self.currentPlace + step >= len(self.game.places):
                step = (len(self.game.places) - 1) - self.currentPlace
            
            self.currentPlace += step
            self.totalPlaces += step

        elif step < 0:
            # Deal with underflows. Remember step is negative
            if self.currentPlace + step < 0:
                step = self.currentPlace
            
            self.currentPlace += step
            self.totalPlaces += (-step)

        # Unnecessary, but explicitely state that 0 does nothing
        else:
            pass

        # Logging
        currentPlace = self.getCurrentPlace()
        logMessage = f'{self.name} ({self.id}) moved {step} to place {currentPlace.id}'
        if currentPlace.message is not None:
            logMessage = f'{logMessage}, message: {currentPlace.message}'
        logging.info(logMessage)
    
    def getCurrentPlace(self) -> Place:
        return self.game.places[self.currentPlace]
    
    def showPlayer(self) -> str:
        return f'{self.name} ({self.id})'
    
    def stats(self) -> Dict:
        stats = {
            'id': self.id,
            'name': self.name,
            'current_place': self.currentPlace,
            'total_places': self.totalPlaces,
        }

        return stats

    def __eq__(self, another: object) -> bool:
        return isinstance(another, Player) and another.id == self.id
    
    def __hash__(self) -> int:
        return hash(self.id)

'''
players that were moved if any, or a single player for a winner
'''
EffectResult = Union[List[Player], Player]

'''
(players moved if any, was the effect triggered at all?)
'''
PersistentEffectResult = Tuple[List[Player], bool]

'''
f(place) -> EffectResult
'''
EffectFunc = Callable[['Place', Player], EffectResult]

'''
f(place, player testing effect, roll of the testing player)
'''
PersistentEffectFunc = Callable[['Place', Player, int], PersistentEffectResult]

@dataclass
class Place:
    id: int
    game: Game
    effect: Optional[EffectFunc]
    persistentEffect: Optional[PersistentEffectFunc]
    message: Optional[str]

    def getPlayersInPlace(self) -> List[Player]:
        return [p for p in self.game.players if p.getCurrentPlace() == self]
    
    def hasEffect(self) -> bool:
        return self.effect is not None
    
    def hasPersistentEffect(self) -> bool:
        return self.persistentEffect is not None
    
    def executeEffect(self, player: Player) -> EffectResult:
        if self.effect is None:
            raise AttributeError(f'this place (id: {self.id}) has no effect')

        return self.effect(self, player)
    
    def executePersistentEffect(self, player: Player, roll: int) -> PersistentEffectResult:
        if self.persistentEffect is None:
            raise AttributeError(f'this place (id: {self.id}) has no persistent effect')
        
        return self.persistentEffect(self, player, roll)


    def __eq__(self, another: object) -> bool:
        return isinstance(another, Place) and another.id == self.id
    
    def __hash__(self) -> int:
        return hash(self.id)

@dataclass
class Game:
    rng: random.Random
    currentPlayerOffset: int
    currentTurn: int
    totalPlayers: Set[Player]
    players: List[Player]
    places: List[Place]
    totalTurns: int

    def _nextPlayerOffset(self) -> int:
        return (self.currentPlayerOffset + 1) % len(self.players)
    
    def _lastPlayerOffset(self) -> int:
        return (self.currentPlayerOffset - 1) % len(self.players)
    
    def _advanceCurrentPlayer(self):
        self.currentPlayerOffset = self._nextPlayerOffset()
    
    def _rewindCurrentPlayer(self):
        self.currentPlayerOffset = self._lastPlayerOffset()

    def losePlayer(self, player: Player):
        # If the current player is the one we are losing, we make it as if we
        # are still in the last player's turn, and we can pop the next player
        if player == self.players[self.currentPlayerOffset]:
            self._rewindCurrentPlayer()
            self.players.pop(self._nextPlayerOffset())
        # Otherwise, we just linear search, and fix currentPlayerOffset if we need
        # to
        else:
            deletedOffset = self.players.index(player)
            # We need to fix if the current player is after the deleted one. Last
            # branch already dealt with the "current player == deleted player"
            # case
            if self.currentPlayerOffset > deletedOffset:
                self._rewindCurrentPlayer()

            self.players.pop(deletedOffset)

    def getPlayers(self) -> List[Player]:
        return [p for p in self.players]
    
    def getCurrentTurnPlayer(self):
        return self.players[self.currentPlayerOffset]
    
    def getCurrentPersistentEffectPlaces(self) -> List[Place]:
        return [p.getCurrentPlace() for p in self.players if p.getCurrentPlace().hasPersistentEffect()]

    def everyoneLost(self) -> bool:
        return len(self.players) == 0

    def coin(self, player: Player) -> bool:
        flip = bool(self.rng.getrandbits(1))
        logging.info(f'coin flip by {player.showPlayer()}: {flip}')
        return flip

    def d6(self, player: Player) -> int:
        roll = self.rng.randint(1, 6)
        logging.info(f'die roll by {player.showPlayer()}: {roll}')
        return roll
    
    def doTurn(self) -> Union[Player, bool, None]:
        '''
        If there's a winner, return it. If everyone lost, return False. If game
        continues, return None.
        '''

        self.totalTurns += 1
        logging.info(f'turn {self.totalTurns}')

        currentPlayer = self.getCurrentTurnPlayer()

        # Deal with skipping turns
        if currentPlayer.turnsToSkip > 0:
            currentPlayer.turnsToSkip -= 1
            self._advanceCurrentPlayer()
            return None
        
        roll = self.d6(currentPlayer)

        # To start with, let's assume only the first player will move
        # (activating an effect) and no persistent effect was activated
        movedPlayers = {currentPlayer}
        persistentEffectActivated = False

        # We check if we've activated some persistent effect. This can
        # only be done by the current player, when they roll their dice, but
        # before actually moving
        currentPersistentEffectsPlaces = self.getCurrentPersistentEffectPlaces()
        for place in currentPersistentEffectsPlaces:
            possibleMovedPlayers, persistentEffectActivated = place.executePersistentEffect(currentPlayer, roll)
            # If a persistent effect activated, many may have moved (and activated
            # effects), and we may not have moved at all. We let the function tell
            # us who moved
            if persistentEffectActivated:
                movedPlayers = set(possibleMovedPlayers)
                # It seems it's not possible for more than one persistent event
                # to activate at once, so we don't check others
                break
        
        if not persistentEffectActivated:
            currentPlayer.move(roll)

        # The main loop:
        # If there are moved players, go through them and activate their effects.
        # Each effect may yield more moves. We register those moved players.
        # We'll exit the loop when the number of players registered is 0
        while len(movedPlayers) != 0:
            newMovedPlayers = set()
            for mp in movedPlayers:
                place = mp.getCurrentPlace()
                moved = []
                if place.hasEffect():
                    moved = place.executeEffect(mp)
                    # If a winner was detected, we just return it here
                    if isinstance(moved, Player):
                        return moved
                    
                    for p in moved:
                        newMovedPlayers.add(p)
            movedPlayers = newMovedPlayers
        
        # Finally, check if there was no movement because everyone lost
        if self.everyoneLost():
            return False
        
        self._advanceCurrentPlayer()
        return None

def newGame(
        seed: int,
        playerNames: Iterable[str],
        board: Iterable[Tuple[Optional[EffectFunc], Optional[PersistentEffectFunc], Optional[str]]],
    ) -> Game:
    game = Game(
        random.Random(seed),
        currentPlayerOffset=0,
        currentTurn=0,
        totalPlayers=None, # type: ignore
        players=None, # type: ignore
        places=None, # type: ignore
        totalTurns=0
    )

    players = []
    for id, name in enumerate(playerNames):
        player = Player(
            id=id,
            name=name,
            game=game,
            currentPlace=0,
            totalPlaces=0,
            turnsToSkip=0,
        )
        players.append(player)
    
    game.players = players
    game.totalPlayers = set(players)
    places = []
    for (id, (effect, persistentEffect, msg)) in enumerate(board):
        place = Place(
            id=id,
            game=game,
            effect=effect,
            persistentEffect=persistentEffect,
            message=msg
        )
        places.append(place)

    game.places = places

    return game

# Places effects

def ifAnyoneRollsNFactory(n: int) -> PersistentEffectFunc:
    '''
    Create persistent effect functions in the form: "if anyone rolls n, everyone
    goes back n spaces". They're very common.
    '''

    def f(place: Place, testingPlayer: Player, roll: int) -> PersistentEffectResult:
        if roll == n:
            players = place.game.getPlayers()
            for p in players:
                p.move(-n)
            return players, True
        else:
            return [], False
    
    return f


def effect_4(place: Place, player: Player) -> EffectResult:
    player.move(-2)

    return [player]

effect_6_persistent = ifAnyoneRollsNFactory(2)

def effect_9(place: Place, player: Player) -> EffectResult:
    '''
    Randomly decide if we feel like it
    '''

    if place.game.coin(player):
        player.move(place.game.d6(player))
        return [player]
    else:
        return []

def effect_13(place: Place, player: Player) -> EffectResult:
    player.turnsToSkip += 1
    
    return []

def effect_15_persistent(place: Place, playerTesting: Player, roll: int) -> PersistentEffectResult:
    if roll == 1:
        players = place.getPlayersInPlace()
        for p in players:
            p.move(1)
        return players, True
    else:
        return [], False

effect_16_persistent = ifAnyoneRollsNFactory(3)

def effect_18(game: Game, player: Player) -> EffectResult:
    player.move(2)

    return [player]

def effect_20_persistent(place: Place, player: Player, roll: int) -> PersistentEffectResult:
    if player.getCurrentPlace() == place:
        player.move(-roll)
        return [player], True
    else:
        return [], False

def effect_23(place: Place, player: Player) -> EffectResult:
    player.move(2)

    return [player]

def effect_25(game: Game, player: Player) -> EffectResult:
    player.move(-5)

    return [player]

effect_28_persistent = ifAnyoneRollsNFactory(5)

def effect_31(place: Place, player: Player) -> EffectResult:
    '''
    Randomly determine if it tickles our fancy.
    '''

    if place.game.coin(player):
        player.move(-2)
        return [player]
    else:
        return []

def effect_33(place: Place, player: Player) -> EffectResult:
    rolls = (place.game.d6(player) == 6, place.game.d6(player) == 6, place.game.d6(player) == 6)
    if all(rolls):
        players = [p for p in place.game.players if p != player]
        for p in players:
            p.move(-18)

        return players
    else:
        return []

effect_35_persistent = ifAnyoneRollsNFactory(4)

effect_37_persistent = ifAnyoneRollsNFactory(6)

def effect_40(place: Place, player: Player) -> EffectResult:
    if place.game.d6(player) % 2 == 0:
        place.game.losePlayer(player)
        return []

    else:
        return []

def effect_44(place: Place, player: Player) -> EffectResult:
    player.move(2)
    return [player]

def effect_45(place: Place, player: Player) -> EffectResult:
    player.move(2)
    return [player]

def effect_46(place: Place, player: Player) -> EffectResult:
    player.move(-1)
    return [player]

def effect_47(place: Place, player: Player) -> EffectResult:
    player.move(-4)
    return [player]

def effect_48(place: Place, player: Player) -> EffectResult:
    otherRolls = [place.game.d6(p) for p in place.game.players if p != player]
    myRoll = place.game.d6(player)
    for otherRoll in otherRolls:
        if myRoll <= otherRoll:
            player.move(-20)
            return [player]
    
    return player

# The data for the board proper

BLANK = (None, None, None)
BOARD = [
    BLANK,
    BLANK,
    (None, None, 'pretty good'),
    BLANK,
    (effect_4, None, 'Go back 2 spaces'),
    BLANK,
    (None, effect_6_persistent, 'If anyone rolls a 2, everyone goes back two spaces'),
    (None, None, 'dog_0'),
    (None, None, 'woof'),
    (effect_9, None, 'Roll again but only if you feel like it'),
    BLANK,
    (None, None, 'sometimes I eat cheese'),
    BLANK,
    (effect_13, None, None),
    BLANK,
    (None, effect_15_persistent, 'If anyone rolls a 1, go forward 1 space'),
    (None, effect_16_persistent, 'If anyone rolls a 3, everyone goes back three spaces'),
    (None, None, 'dog_1'),
    (effect_18, None, 'Go forward two spaces'),
    (None, None, 'neat'),
    (None, effect_20_persistent, 'When you roll to move, go back that many spaces'),
    BLANK,
    (None, None, 'dog_2'),
    (effect_23, None, 'Go forward two spaces'),
    BLANK,
    (effect_25, None, 'Go back five spaces'),
    BLANK,
    (None, None, 'yes'),
    (None, effect_28_persistent, 'If anyone rolls a 5, everyone goes back five spaces'),
    (None, None, 'dog_3'),
    BLANK,
    (effect_31, None, 'Go back two spaces if it tickles your fancy'),
    BLANK,
    (effect_33, None, 'Roll three times. If you roll three 6s, everyone else moves back 18 spaces. PRAISE SATAN'),
    (None, None, 'sometimes'),
    (None, effect_35_persistent, 'If anyone rolls a 4, everyone moves back 4 spaces'),
    BLANK,
    (None, effect_37_persistent, 'If anyone rolls a 6, everyone moves back six spaces'),
    (None, None, 'dog_4'),
    BLANK,
    (effect_40, None, 'Roll a die. If you roll an even number, you lose'),
    BLANK,
    BLANK,
    (None, None, 'no :('),
    (effect_44, None, 'Go forward 2 spaces'),
    (effect_45, None, 'Go forward 2 spaces'),
    (effect_46, None, 'Go back 1 spaces'),
    (effect_47, None, 'Go back 4 spaces'),
    (effect_48, None, 'On your turn, everyone rolls a die. If you have the highest number, you win. If you tie for the highest or someone\'s roll beats yours, go back twenty spaces')
]

if __name__ == '__main__':
    argParser = argparse.ArgumentParser(description='Simulate that fuckin\' dog game')
    argParser.add_argument('players', nargs='+', help='names of the players')
    argParser.add_argument('-s', '--seed', type=int, default=random.randrange(sys.maxsize), help='random seed, as an integer; by default a random value, probably time-based')
    args = argParser.parse_args()

    logging.basicConfig(
        format='%(asctime)s %(message)s',
        level=logging.INFO,
        stream=sys.stdout,
    )
    logging.Formatter.formatTime = logging.Formatter.formatTime = (lambda self, record, datefmt=None: datetime.datetime.fromtimestamp(record.created).astimezone().isoformat(sep="T",timespec="milliseconds"))

    logging.info(f'seed: {args.seed}')
    game = newGame(args.seed, args.players, BOARD)

    while True:
        result = game.doTurn()
        if isinstance(result, Player):
            logging.info(f'winner: {result.showPlayer()}')
            break
        elif isinstance(result, bool) and result == False:
            logging.info('everyone lost')
            break
    
    logging.info(f'total turns: {game.totalTurns}')
    stats = [p.stats() for p in game.totalPlayers]
    logging.info(f'player stats: {json.dumps(stats)}')