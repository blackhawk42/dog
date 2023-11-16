import re
import datetime
import json
from dataclasses import dataclass
from typing import Callable, List, Optional, Set, Union

class ParsingException(Exception):
    pass

@dataclass
class Player:
    id: int
    name: str
    currentPlace: int
    totalPlaces: int

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Player) and other.id == self.id
    
    def __hash__(self) -> int:
        return hash(id)

@dataclass
class LogEntry:
    raw: str
    datetime: datetime.datetime

@dataclass
class PlayerStats(LogEntry):
    players: Set[Player]

PLAYER_STATS_REGEX = re.compile(r"(?P<dt>\S+) player stats: (?P<json>.+)")
def parsePlayerStats(line: str) -> PlayerStats:
    m = PLAYER_STATS_REGEX.match(line)

    if m is None:
        raise ParsingException()

    dt = datetime.datetime.fromisoformat(m['dt'])
    playerStatsJson = json.loads(m['json'])

    playerStats = map(lambda st: Player(st['id'], st['name'], st['current_place'], st['total_places']), playerStatsJson)
    playerStats = set(playerStats)

    return PlayerStats(
        line,
        dt,
        playerStats,
    )

@dataclass
class Roll(LogEntry):
    playerID: int
    roll: int

ROLL_REGEX = re.compile(r"(?P<dt>\S+) die roll by .+\((?P<player_id>\d+)\): (?P<roll>\d+)")
def parseRoll(line: str) -> Roll:
    m = ROLL_REGEX.match(line)
    if m is None:
        raise ParsingException()

    return Roll(
        line,
        datetime.datetime.fromisoformat(m['dt']),
        int(m['player_id']),
        int(m['roll'])
    )

@dataclass
class Move(LogEntry):
    playerID: int
    step: int
    placeID: int
    message: Optional[str]

MOVE_REGEX = re.compile(r"(?P<dt>\S+) .+\((?P<player_id>\d+)\) moved (?P<step>-?\d+) to place (?P<place_id>\d+)(, message: (?P<message>.+))?")
def parseMove(line: str) -> Move:
    m = MOVE_REGEX.match(line)
    if m is None:
        raise ParsingException()
    
    return Move(
        line,
        datetime.datetime.fromisoformat(m['dt']),
        int(m['player_id']),
        int(m['step']),
        int(m['place_id']),
        m['message']
    )

@dataclass
class Winner(LogEntry):
    playerID: int

WINNER_REGEX = re.compile(r"(?P<dt>\S+) winner: .+\((?P<player_id>\d+)\)")
def parseWinner(line: str):
    m = WINNER_REGEX.match(line)
    if m is None:
        raise ParsingException()
    
    return Winner(
        line,
        datetime.datetime.fromisoformat(m['dt']),
        int(m['player_id'])
    )

@dataclass
class NoWinner(LogEntry):
    datetime: datetime.datetime

NO_WINNER_REGEX = re.compile(r"(?P<dt>\S+) everyone lost")
def parseNoWinner(line: str) -> NoWinner:
    m = NO_WINNER_REGEX.match(line)
    if m is None:
        raise ParsingException()
    
    return NoWinner(
        line,
        datetime.datetime.fromisoformat(m['dt']),
    )


@dataclass
class Losers(LogEntry):
    playersID: Optional[Set[int]]

LOSERS_REGEX = re.compile(r"(?P<dt>\S+) losers:(?P<losers>.+)?")
LOSERS_ID_REGEX = re.compile(r".*\((?P<player_id>\d+)\)$")
def parseLosers(line: str):
    m = LOSERS_REGEX.match(line)
    if m is None:
        raise ParsingException()
    
    dt = datetime.datetime.fromisoformat(m['dt'])
    losersRaw = m['losers']

    losersIds = None
    if losersRaw is not None:
        losersRaw = losersRaw.split(', ')
        losersIds = set()
        for l in losersRaw:
            mLoser = LOSERS_ID_REGEX.match(l)
            if mLoser is None:
                raise ParsingException()
            
            losersIds.add(int(mLoser['player_id']))

    return Losers(
        line,
        dt,
        losersIds,
    )


@dataclass
class TotalTurns(LogEntry):
    turns: int

TOTAL_TURNS_REGEX = re.compile(r"(?P<dt>\S+) total turns: (?P<turns>\d+)")
def parseTotalTurns(line: str) -> TotalTurns:
    m = TOTAL_TURNS_REGEX.match(line)
    if m is None:
        raise ParsingException()
    
    return TotalTurns(
        line,
        datetime.datetime.fromisoformat(m['dt']),
        int(m['turns']),
    )

@dataclass
class Seed(LogEntry):
    seed: int

SEED_REGEX = re.compile(r"(?P<dt>\S+) seed: (?P<seed>\d+)")
def parseSeed(line: str) -> Seed:
    m = SEED_REGEX.match(line)
    if m is None:
        raise ParsingException()
    
    return Seed(
        line,
        datetime.datetime.fromisoformat(m['dt']),
        int(m['seed']),
    )

@dataclass
class TurnNo(LogEntry):
    turnNo: int

TURN_NO_REGEX = re.compile(r"(?P<dt>\S+) turn (?P<turn_no>\d+)")
def parseTurnNo(line: str) -> TurnNo:
    m = TURN_NO_REGEX.match(line)
    if m is None:
        raise ParsingException()
    
    return TurnNo(
        line,
        datetime.datetime.fromisoformat(m['dt']),
        int(m['turn_no']),
    )

@dataclass
class CoinFlip(LogEntry):
    playerID: int
    flip: bool

COIN_FLIP_REGEX = re.compile(r"(?P<dt>\S+) coin flip by .+\((?P<player_id>\d+)\): (?P<flip>True|False)")
def parseCoinFlip(line: str) -> CoinFlip:
    m = COIN_FLIP_REGEX.match(line)
    if m is None:
        raise ParsingException()
    
    return CoinFlip(
        line,
        datetime.datetime.fromisoformat(m['dt']),
        int(m['player_id']),
        m['flip'] == True,
    )

@dataclass
class PlayerLost(LogEntry):
    playerID: int

PLAYER_LOST_REGEX = re.compile(r"(?P<dt>\S+) .+\((?P<player_id>\d+)\) has lost")
def parsePlayerLost(line: str) -> PlayerLost:
    m = PLAYER_LOST_REGEX.match(line)
    if m is None:
        raise ParsingException()
    
    return PlayerLost(
        line,
        datetime.datetime.fromisoformat(m['dt']),
        int(m['player_id'])
    )

Message = Union[Move, TurnNo, CoinFlip, Roll, PlayerLost]

@dataclass
class Game:
    seed: Seed
    playersStats: PlayerStats
    totalTurns: TotalTurns
    winner: Union[Winner, NoWinner]
    losers: Losers
    messages: List[Message]

ParsedEntry = Union[
    Seed,
    PlayerStats,
    TotalTurns,
    Winner,
    NoWinner,
    Losers,
    Move,
    TurnNo,
    Roll,
    CoinFlip,
    PlayerLost,
]

PARSERS: List[Callable[[str], ParsedEntry]] = [
    parseRoll,
    parseMove,
    parseTurnNo,
    parseCoinFlip,
    parsePlayerLost,
    parseSeed,
    parseWinner,
    parseNoWinner,
    parseTotalTurns,
    parseLosers,
    parsePlayerStats,
]


def parseGame(text: str) -> Game:
    lines = text.splitlines()
    lines = map(lambda l: l.strip(), lines)
    lines = filter(lambda l: l != '', lines)

    game = Game(
        None, # type: ignore
        None, # type: ignore
        None, # type: ignore
        None, # type: ignore
        None, # type: ignore
        []
    )

    for (lineno, line) in enumerate(lines, 1):
        result = None
        for p in PARSERS:
            try:
                result = p(line)
            except ParsingException:
                continue
            except Exception as e:
                raise ParsingException(f'unkown error "{e}" in line {lineno}: {line}')
            
        if result is None:
            raise ParsingException(f'line {lineno} could not be parsed: {line}')
        
        if isinstance(result, Roll):
            game.messages.append(result)
        elif isinstance(result, Move):
            game.messages.append(result)
        elif isinstance(result, TurnNo):
            game.messages.append(result)
        elif isinstance(result, CoinFlip):
            game.messages.append(result)
        elif isinstance(result, PlayerLost):
            game.messages.append(result)
        elif isinstance(result, Seed):
            game.seed = result
        elif isinstance(result, Winner):
            game.winner = result
        elif isinstance(result, NoWinner):
            game.winner = result
        elif isinstance(result, TotalTurns):
            game.totalTurns = result
        elif isinstance(result, Losers):
            game.losers = result
        elif isinstance(result, PlayerStats):
            game.playersStats = result
        else:
            raise ParsingException(f'unrecognised data structure {result} in line {lineno}: {line}')
    

    if game.seed is None:
        raise ParsingException('game attribute "seed" is empty')
    if game.playersStats is None:
        raise ParsingException('game attribute "playersStats" is empty')
    if game.totalTurns is None:
        raise ParsingException('game attribute "totalTurns" is empty')
    if game.winner is None:
        raise ParsingException('game attribute "winner" is empty')
    if game.losers is None:
        raise ParsingException('game attribute "losers" is empty')
    if game.messages is None:
        raise ParsingException('game attribute "movesTurnsRolls" is empty')


    return game