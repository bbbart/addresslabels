#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Generate PDF to print on address sticker sheets."""

import configparser
import csv
from collections import namedtuple
from pathlib import Path

from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas

BASEDIR = Path(__file__).parent

CONFIG = configparser.ConfigParser(inline_comment_prefixes='#')
CONFIG.read((BASEDIR / 'config', BASEDIR / 'config.local'))

Label = namedtuple(
    'Label',
    ('name',
     'address',
     'postalcode',
     'city',
     'country'))


class FontFileNotFound(Exception):
    """Exception to raise when given font file cannot be found."""
    pass


class CanvasWithFontState(canvas.Canvas):

    """Reportlab canvas which stores it currently active font face and size."""

    Font = namedtuple('Font', ('face', 'size'))

    def __init__(self, filename, pagesize):
        """Initialize a new canvas."""
        self._currentfont = self.Font('Courier', 12)
        super().__init__(filename, pagesize=pagesize)

    def set_current_font(self, fontface, fontsize):
        """Set and store the given font to the canvas."""
        self.setFont(fontface, fontsize)
        self._currentfont = self.Font(fontface, fontsize)

    @property
    def currentfont(self):
        """Return the currently set font of this canvas."""
        return self._currentfont


class LineWriter:

    """Convenience class to hold repetitive methods for advanced line writing to
    reportlab canvases.
    """

    def __init__(self, acanvas, maxwidth):
        """Initialize a new LineWriter."""
        self.canvas = acanvas
        self.maxwidth = maxwidth

    @property
    def baselineskip(self):
        """Get the baselineskip."""
        return self.canvas._leading

    def numlines(self, text):
        """Get the number of lines this text would take to print."""
        return len(simpleSplit(
            text, *self.canvas.currentfont, self.maxwidth))

    def textheight(self, text):
        """Get the height the given text would consume to be printed."""
        return self.baselineskip * self.numlines(text)

    def writetext(self, pos_x, pos_y, text):
        """Print text centred at pos_x, pos_y on the given canvas. If text is wider
        than maxwidth, it is wrapped on multiple lines.

        Returns the number of lines written.
        """
        textlines = simpleSplit(
            text,
            *self.canvas.currentfont,
            self.maxwidth)
        for line in textlines:
            self.canvas.drawCentredString(pos_x, pos_y, line)
            pos_y -= self.baselineskip

        return len(textlines)


def baselineskip(acanvas):
    """Calculate the baselineskip."""
    return acanvas._leading * \
        CONFIG['addresslabels'].getfloat('extralinespacing')


def loadcsv(csvfile):
    """Load addresses from the csv file into a List of Labels."""
    labels = []
    with open(csvfile, 'r', newline='') as addressfile:
        addressreader = csv.reader(addressfile)
        for row in addressreader:
            labels.append(
                Label(
                    name=row[0].strip(),
                    address=row[1].strip(),
                    postalcode=row[2].strip(),
                    city=row[3].strip(),
                    country=row[4].strip()))

    return labels


def main():
    """Generate PDF to print on address sticker sheets."""

    unit = getattr(
        __import__(
            'reportlab.lib.units',
            fromlist=[
                CONFIG['addresslabels']['unit']]),
        CONFIG['addresslabels']['unit'])

    dimensions = {}
    for dimension in CONFIG['dimensions']:
        dimensions[dimension] = CONFIG['dimensions'].getfloat(
            dimension, 0) * unit

    pagesize = getattr(
        __import__(
            'reportlab.lib.pagesizes',
            fromlist=[
                CONFIG['addresslabels']['pagesize']]),
        CONFIG['addresslabels']['pagesize'])

    labels = loadcsv(CONFIG['addresslabels']['csvfile'])

    canv = CanvasWithFontState(
        CONFIG['addresslabels']['pdffile'],
        pagesize=pagesize)
    canv.setTitle('Address labels')
    canv.setAuthor('Bart Van Loon')
    canv.setSubject('Just some addresses in boxes...')
    canv.setKeywords(
        ('address',
         'addresses',
         'label',
         'labels',
         'sticker',
         'stickers'))

    linewriter = LineWriter(
        canv,
        dimensions['width_label'] -
        dimensions['pad_label'])

    x_label = dimensions['margin_page_left']
    y_label = pagesize[1] - \
        (dimensions['margin_page_top'] + dimensions['height_label'])
    for label in labels:
        if CONFIG['addresslabels'].getboolean('drawborders'):
            canv.rect(
                x_label,
                y_label,
                dimensions['width_label'],
                dimensions['height_label'])

        # calculating the height of the label for vertical positioning
        textheight = 0
        canv.set_current_font(
            CONFIG['fonts']['fontname_name'],
            CONFIG['fonts'].getint('fontsize_name'))
        textheight += linewriter.textheight(label.name)
        textheight += baselineskip(canv)
        canv.set_current_font(
            CONFIG['fonts']['fontname_address'],
            CONFIG['fonts'].getint('fontsize_address'))
        textheight += linewriter.textheight(label.address)
        textheight += baselineskip(canv)
        textheight += linewriter.textheight(f'{label.postalcode} {label.city}')
        if label.country:
            textheight += baselineskip(canv)
            textheight += linewriter.textheight(label.country)

        canv.set_current_font(
            CONFIG['fonts']['fontname_name'],
            CONFIG['fonts'].getint('fontsize_name'))

        x_name = x_label + dimensions['width_label'] / 2
        y_name = y_label + dimensions['height_label'] / \
            2 + textheight / 2 - canv._leading
        numlines = linewriter.writetext(x_name, y_name, label.name)

        canv.set_current_font(
            CONFIG['fonts']['fontname_address'],
            CONFIG['fonts'].getint('fontsize_address'))

        x_address = x_name
        y_address = y_name - numlines * canv._leading - baselineskip(canv)
        numlines = linewriter.writetext(x_address, y_address, label.address)

        y_address -= numlines * canv._leading + baselineskip(canv)
        numlines = linewriter.writetext(
            x_address,
            y_address,
            f'{label.postalcode} {label.city}')

        if label.country:
            y_address -= numlines * canv._leading + baselineskip(canv)
            numlines = linewriter.writetext(
                x_address, y_address, label.country)

        x_label += dimensions['width_label'] + dimensions['margin_label_right']
        if x_label > pagesize[0] - dimensions['width_label']:
            x_label = dimensions['margin_page_left']
            y_label -= dimensions['height_label'] + \
                dimensions['margin_label_top']
            if y_label < 0:
                y_label = pagesize[1] - \
                    dimensions['margin_page_top'] - dimensions['height_label']
                canv.showPage()
                canv.set_current_font(*canv.currentfont)

    canv.showPage()
    canv.save()


def installfont(fontname):
    """Registers a typeface and font based on the given name."""
    fontdir_afm = Path(CONFIG['fonts']['fontdir_afm'])
    fontdir_pfb = Path(CONFIG['fonts']['fontdir_pfb'])
    fontfile_stem = fontname.lower()
    afm = (fontdir_afm / fontfile_stem).with_suffix('.afm')
    pfb = (fontdir_pfb / fontfile_stem).with_suffix('.pfb')

    try:
        pdfmetrics.registerTypeFace(pdfmetrics.EmbeddedType1Face(afm, pfb))
        pdfmetrics.registerFont(
            pdfmetrics.Font(
                fontname,
                fontname,
                'WinAnsiEncoding'))
    except AssertionError:
        raise FontFileNotFound(f'Cannot install font {fontname}. '
                               'Does its .afm and .pfb files exist?')


if __name__ == '__main__':
    availablefonts = canvas.Canvas('/dev/null').getAvailableFonts()
    for font in (CONFIG['fonts']['fontname_name'],
                 CONFIG['fonts']['fontname_address']):
        if font not in availablefonts:
            installfont(font)

    main()
