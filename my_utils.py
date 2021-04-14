# -*- coding:utf-8 -*-

import numpy as np
import matplotlib
from matplotlib import colors as mcolors
from matplotlib.collections import LineCollection, PolyCollection, CircleCollection
from six.moves import xrange, zip
from matplotlib.patches import Circle, Wedge, Polygon, Ellipse
from matplotlib.collections import PatchCollection


def candlestick2_ohlc(ax, opens, highs, lows, closes, width=4,
                      colorup='k', colordown='r',
                      alpha=0.75):

    delta = width / 2.
    barVerts = [((i, open),
                 (i, close),
                 (i + width, close),
                 (i + width, open))
                for i, open, close in zip(xrange(len(opens)), opens, closes)
                if open != -1 and close != -1]

    rangeSegments = [((i + delta, low), (i + delta, high))
                     for i, low, high in zip(xrange(len(lows)), lows, highs)
                     if low != -1]

    colorup = mcolors.to_rgba(colorup, alpha)
    colordown = mcolors.to_rgba(colordown, alpha)
    colord = {True: colorup, False: colordown}
    colors = [colord[open < close]
              for open, close in zip(opens, closes)
              if open != -1 and close != -1]

    useAA = 0,  # use tuple here
    lw = 0.5,   # and here
    rangeCollection = LineCollection(rangeSegments,
                                     colors=colors,
                                     linewidths=lw,
                                     antialiaseds=useAA,
                                     )

    barCollection = PolyCollection(barVerts,
                                   facecolors=colors,
                                   edgecolors=colors,
                                   antialiaseds=useAA,
                                   linewidths=lw,
                                   )

    minx, maxx = 0, len(rangeSegments)
    miny = min([low for low in lows if low != -1])
    maxy = max([high for high in highs if high != -1])

    corners = (minx, miny), (maxx, maxy)
    ax.update_datalim(corners)
    ax.autoscale_view()

    # add these last
    ax.add_collection(rangeCollection)
    ax.add_collection(barCollection)
    return rangeCollection, barCollection

def draw_input(ax, opens, highs, lows, closes, width=4,
                      color='b', alpha=0.75):

    delta = width / 2.
    barVerts = [((i, open),
                 (i, close),
                 (i + width, close),
                 (i + width, open))
                for i, open, close in zip(xrange(len(opens)), opens, closes)
                if open > 0 and close > 0]

    rangeSegments = [((i + delta, low), (i + delta, high))
                     for i, low, high in zip(xrange(len(lows)), lows, highs)
                     if low > 0]

    use_color = mcolors.to_rgba(color, alpha)
    colors = [use_color
              for open, close in zip(opens, closes)
              if open > 0 and close > 0]

    useAA = 0,  # use tuple here
    lw = 0.5,   # and here
    rangeCollection = LineCollection(rangeSegments,
                                     colors=colors,
                                     linewidths=lw,
                                     antialiaseds=useAA,
                                     )

    barCollection = PolyCollection(barVerts,
                                   facecolors=colors,
                                   edgecolors=colors,
                                   antialiaseds=useAA,
                                   linewidths=lw,
                                   )

    minx, maxx = 0, len(rangeSegments)
    miny = min([low for low in lows if low != -1])
    maxy = max([high for high in highs if high != -1])

    corners = (minx, miny), (maxx, maxy)
    ax.update_datalim(corners)
    ax.autoscale_view()

    # add these last
    ax.add_collection(rangeCollection)
    ax.add_collection(barCollection)
    return rangeCollection, barCollection

def draw_op(ax, buy, sell, width=4):
    delta = width / 2.

    use_color = mcolors.to_rgba('b', 1)
    r = mcolors.to_rgba('r', 1)
    g = mcolors.to_rgba('g', 1)

    useAA = 0,  # use tuple here
    lw = 0.5,   # and here
    patches = []
    for idx, price in buy.iteritems():
        patches.append(Circle((idx, price), 0.05, color=use_color))

    for idx, (price, is_up) in sell.iteritems():
        patches.append(Circle((idx, price), 0.1, color=r if is_up else g))

    p = PatchCollection(patches)
    ax.add_collection(p)


