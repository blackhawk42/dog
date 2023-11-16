from __future__ import annotations
import argparse
import inspect
import io
import dogparser
from dataclasses import dataclass
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, Iterable, List, Optional, Set, Tuple

# Constants

CURRENT_FILE_PATH = Path(inspect.getfile(inspect.currentframe())) # type: ignore
ASSETS_PATH = CURRENT_FILE_PATH.parent / 'assets'

BOARD_TEMPLATE = ASSETS_PATH / 'board_dogimg.png'
FONT_PATH = ASSETS_PATH / 'LiberationMono-Regular.ttf'

TURN_COORDS = (980, 80)
PLAYERS_BOARD_COORDS = (870, 130)
MESSAGES_COORDS = (43, 895)
BOARD_COORDS = [
    (48, 33),
    (154, 28),
    (259, 28),
    (385, 25),
    (525, 27),
    (636, 34),
    (762, 31),
    (796, 148),
    (793, 289),
    (787, 408),
    (789, 526),
    (795, 640),
    (790, 730),
    (792, 808),
    (684, 808),
    (559, 805),
    (400, 808),
    (264, 817),
    (150, 814),
    (45, 816),
    (43, 733),
    (46, 655),
    (42, 589),
    (42, 507),
    (40, 406),
    (40, 315),
    (34, 213),
    (34, 121),
    (133, 121),
    (298, 121),
    (430, 130),
    (550, 138),
    (651, 144),
    (658, 267),
    (651, 399),
    (654, 514),
    (651, 634),
    (504, 673),
    (348, 673),
    (193, 676),
    (184, 573),
    (190, 480),
    (184, 382),
    (160, 264),
    (240, 240),
    (367, 244),
    (493, 234),
    (522, 318),
    (415, 441),
]

# Classes

class Player:
    def __init__(self, id: int, name: str, startingPlace: Place, board: List[Place]) -> None:
        self.id = id
        self.name = name
        self.currentPlace = startingPlace
        self.lost = False
        self.showName = f'{self.id} .- {self.name}'
        self.board = board

    def losePlayer(self):
        self.lost = True
        self.showName = strikethrough(self.showName)
    
    def showPlayer(self) -> str:
        return self.showName

    def setPlace(self, placeId: int):
        self.currentPlace = self.board[placeId]
    
    def getPlace(self) -> Place:
        return self.currentPlace

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Player) and self.id == other.id
    
    def __hash__(self) -> int:
        return hash(self.id)
    

@dataclass
class Place:
    id: int
    center: Tuple[int, int]
    font: ImageFont.FreeTypeFont

    def draw(self, text: str, drawer: ImageDraw.ImageDraw):
        left, top, right, bottom = drawer.textbbox(self.center, text, align='center', anchor='ms', font=self.font)
        drawer.rectangle((left-5, top-5, right+5, bottom+5), fill='white')
        drawer.text(self.center, text, align='center', anchor='ms', fill='black', font=self.font)
    
    def __eq__(self, other: object) -> bool:
        return isinstance(other, Place) and self.id == other.id
    
    def __hash__(self) -> int:
        return hash(self.id)

@dataclass
class TurnDrawer:
    curretTurn: int
    font: ImageFont.FreeTypeFont
    turnCoords: Tuple[int, int]

    def draw(self, drawer: ImageDraw.ImageDraw):
        drawer.text(self.turnCoords, f'Turn {self.curretTurn}', align='center', anchor='ms', fill='black', font=self.font)

@dataclass
class MessageDrawer:
    messageCoords: Tuple[int, int]
    font: ImageFont.FreeTypeFont

    def draw(self, message: str, drawer: ImageDraw.ImageDraw):
        drawer.multiline_text(self.messageCoords, message, align='left', anchor='la', fill='black', font=self.font)


class PlayersBoardDrawer:
    def __init__(self, players: Iterable[Player], playersStartCoords: Tuple[int, int], font: ImageFont.FreeTypeFont, spacing=1.2) -> None:
        self.playersStartCoords = playersStartCoords
        self.font = font
        self.spacing = font.size*spacing

        self.players = [p for p in players]
        self.players.sort(key=lambda p: p.id)
    
    def draw(self, drawer: ImageDraw.ImageDraw):
        coords = self.playersStartCoords
        for p in self.players:
            drawer.text(coords, f'{p.showPlayer()}', align='left', anchor='la', fill='black', font=self.font)
            coords = (coords[0], coords[1] + self.spacing)

# Helper functions

def strikethrough(s: str) -> str:
    return '\u0336'.join(s) + '\u0336'

def drawPlayers(players: Iterable[Player], drawer: ImageDraw.ImageDraw):
    placesPlayers: Dict[Place, Set[Player]] = {}
    for p in players:
        place = p.getPlace()
        try:
            placesPlayers[place].add(p)
        except KeyError:
            placesPlayers[place] = set((p,))
    
    for p in placesPlayers:
        text = ', '.join([str(player.id) for player in placesPlayers[p]])
        p.draw(text, drawer)

def drawEvrything(
        players: Iterable[Player],
        turnDrawer: TurnDrawer,
        messageDrawer: MessageDrawer,
        playersBoardDrawer: PlayersBoardDrawer,
        message: Optional[str],
        drawer: ImageDraw.ImageDraw,
    ):

    if message is not None:
        messageDrawer.draw(message, drawer)

    drawPlayers(players, drawer)
    turnDrawer.draw(drawer)
    playersBoardDrawer.draw(drawer)

# Main

if __name__ == '__main__':
    argParser = argparse.ArgumentParser('convert the logs of a dog session into images')
    argParser.add_argument('doglog', type=Path, help='log of a dog seesion')
    argParser.add_argument('-o', '--output', type=Path, default=None, help='output gif; by default name of the doglog with suffix changed to ".gif"')
    argParser.add_argument('-f', '--framrate', type=int, default=1000, help='duration of a frame, in miliseconds')
    args = argParser.parse_args()

    if args.output is None:
        args.output = args.doglog.with_suffix('.gif')

    with args.doglog.open('r', encoding='utf-8') as fi:
        game = dogparser.parseGame(fi.read())

    # Font handling
    fontData = io.BytesIO(FONT_PATH.read_bytes())
    PLACE_FONT = ImageFont.truetype(fontData, 16)
    fontData.seek(0)
    TURN_FONT = ImageFont.truetype(fontData, 40)
    fontData.seek(0)
    PLAYERS_BOARD_FONT = ImageFont.truetype(fontData, 16)
    fontData.seek(0)
    MESSAGES_FONT = ImageFont.truetype(fontData, 20)

    # Set up objects and drawers
    boardPlaces = list(
        map(lambda id_coords: Place(id_coords[0], id_coords[1], PLACE_FONT), enumerate(BOARD_COORDS))
    )

    players = list(
        map(lambda p: Player(p.id, p.name, boardPlaces[0], boardPlaces), game.playersStats.players)
    )
    players.sort(key=lambda p: p.id)

    turnDrawer = TurnDrawer(1, TURN_FONT, TURN_COORDS)
    messageDrawer = MessageDrawer(MESSAGES_COORDS, MESSAGES_FONT)
    playersBoardDrawer = PlayersBoardDrawer(players, PLAYERS_BOARD_COORDS, PLAYERS_BOARD_FONT)

    frames: List[Image.Image] = []

    # Load initial template
    templateIm = Image.open(BOARD_TEMPLATE)
    templateIm.load()

    # Starting position and frame
    currentIm = templateIm.copy()
    drawer = ImageDraw.Draw(currentIm)

    drawEvrything(players, turnDrawer, messageDrawer, playersBoardDrawer, game.seed.raw, drawer)

    frames.append(currentIm)

    # All other messages
    for message in game.messages:
        if isinstance(message, dogparser.Move):
            players[message.playerID].setPlace(message.placeID)
        elif isinstance(message, dogparser.TurnNo):
            turnDrawer.curretTurn = message.turnNo
        elif isinstance(message, dogparser.PlayerLost):
            players[message.playerID].losePlayer()
        
        currentIm = templateIm.copy()
        drawer = ImageDraw.Draw(currentIm)
        drawEvrything(players, turnDrawer, messageDrawer, playersBoardDrawer, message.raw, drawer)

        frames.append(currentIm)
    
    # final frame
    currentIm = templateIm.copy()
    finalMessage = f'{game.winner.raw}\n{game.losers.raw}\n{game.totalTurns.raw}'
    drawer = ImageDraw.Draw(currentIm)
    drawEvrything(players, turnDrawer, messageDrawer, playersBoardDrawer, finalMessage, drawer)
    frames.append(currentIm)

    # Final GIF
    frames[0].save(
        args.output,
        format='GIF',
        loop=0,
        save_all=True,
        append_images=frames[1:],
        duration=args.framrate,
    )