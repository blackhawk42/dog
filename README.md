# dog simulation

Tools to simulate [that fucki'n dog game for Tabletop Simulator](https://steamcommunity.com/sharedfiles/filedetails/?id=381108254)

# dog.py

`dog.py` simulates an entire game. Example:

```shell
py dog.py -o doglog.txt player1 player2 player3
```

# dogimg.py

`dogimg.py` creates an animated GIF from the log of a simulation, using the
[Pillow](https://python-pillow.org/) library and `dogparser.py`. Warning: it may use lots of memory,
and the GIFs will be large (70-100 MB is not unheard of). Example:

```shell
py dogimg.py doglog.txt
```

# dogparser.py

`dogparser.py` is a parsing library to convert a simulation log into something
more manageable. The most important function is the `parseGame()` funtion, which
just takes the entire string of a log.

# Licencing

All code is under MIT (see the `LICENCE` file in this root directory). But other
assets may be under another licence. If so, I'll include the licence in the
`licences` folder. See the `assets` folder. All assets are made/derived by me
unless stated otherwise.
