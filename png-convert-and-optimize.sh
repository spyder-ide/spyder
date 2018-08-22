#!/bin/bash
#
# Small script to use ImageMagick on all png files to make sure the png
# format is correct, and to avoid lipng warnings like:
# libpng warning: iCCP: known incorrect sRGB profile
# For more information, see PR 2216:
# https://github.com/spyder-ide/spyder/pull/2216
# and this soluation is based on:
# https://stackoverflow.com/questions/22745076/libpng-warning-iccp-known-incorrect-srgb-profile
# https://tex.stackexchange.com/questions/125612/warning-pdflatex-libpng-warning-iccp-known-incorrect-srgb-profile
#
# make sure to run this from the top level spyder repo dir in order to catch
# all the png files
echo "Searching recursively for all png files in:" `pwd`
# fix all png files in the current directory (and sub-dirs) using ImageMagick:
find . -type f -name "*.png" -exec convert {} -strip {} \;

# optimize all images, can hold a 20-30% size reduction on avarage, no loss of
# image quality
find . -type f -name "*.png" -exec optipng -o7 {} \;

