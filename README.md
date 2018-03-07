# Addresslabels
Quick Python script to create simple PDF with addresses to print on label sheets. Depends on reportlab.

Just run addresslabels.py after configuring it in `config` to get a PDF document like shown in the image below.

![sample.pdf](doc/sample.png)

## Features
* supports custom fonts to embed into the PDF file, as long as you provide the `.afm` anf `.pfb` files for them in the designated fontdir
* supports any pagesize and unit that reportlab supports
* supports multipage PDF output
* horizontally centres every line and does good effort to vertically align the complete label as well
