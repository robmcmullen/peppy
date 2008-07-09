.. _hsi:

******************************
Hyperspectral Image Major Mode
******************************

What is Hyperspectral Imagery?
==============================

Commonly used in remote sensing applications, hyperspectral images have many
more "colors" than just red, green, and blue.  Typically, the images are
structured in layers called "bands", where each band represents a specific
wavelength of light.  You can think of them as a stack of grayscale images,
one on top of the other, where each image in the stack is looking at the same
field of view, but at a different wavelength of light.

Because each pixel at the same row and column in the band refers to the same
spot on the ground, each pixel can be associated with a spectrum.  Because
there can be hundreds of bands in an image, the spectrum can be quite high
resolution.  Because of the large number of samples in the spectrum, the
spectrum can be used to identify the material(s) in the pixel.

The Federation of American Scientists has a `good tutorial <href="http://www.fas.org/irp/imint/docs/rst/index.html>`_
about remote sensing, and it includes sections about hyperspectral imagery.


Hyperspectral Image Data
------------------------

Hyperspectral images are very large, typically on the order of hundreds of
megabytes for a standard scene.  Most data comes from either government or
commercial sensors mounted on either aircraft or spacecraft.  NASA's `AVIRIS
sensor <http://aviris.jpl.nasa.gov/>`_ is very well known in the field of
earth remote sensing.

There are many different image formats for hyperspectral images, but they
fall in two general categories: raw and compressed.  peppy doesn't support
compressed formats directly; you must use GDAL to load compressed images like
copressed NITF, ECW, jpeg2000, etc.

Raw Formats
^^^^^^^^^^^

A common raw image format is the ENVI format, which consists of two files: a
data file in a raw format, and a header file that describes the type of data.

ENVI format is currently the only type of format supported in peppy without
extra libraries.

Compressed Formats and GDAL
^^^^^^^^^^^^^^^^^^^^^^^^^^^

`GDAL <http://www.gdal.org/>`_ is a C++ library with a python binding
that supports many different file formats through one API.  Note that peppy
only supports the ngpython bindings of GDAL, available by default starting
with GDAL 1.5.

In addition, the libecw2 library from `ERMapper
<href="http://www.ermapper.com/">`_ can be used to support stand-alone
JPEG2000 images and JPEG2000 images embedded in other formats like NITF.


Sample Images
-------------

ENVI
  Free data from `AVIRIS <http://aviris.jpl.nasa.gov/html/aviris.freedata.html>`_
GDAL (with libecw2)
  jpeg2000: `MicroImages JPEG2000 image gallery <http://www.microimages.com/gallery/jp2/>`_

  ECW: `McElhanney sample images <http://www.mcelhanney.com/products/prod_swo_samples.html>`_






Hyperspectral Images in Peppy
=============================

The HSI mode in peppy provides simple capability to view hyperspectral images,
navigate through the available bands, and show various profile and spectrum
plots.

Because of the extremely large size of hypespectral images, peppy is capable
of viewing images much larger than can reside in physical memory.  It uses the
technique of memory mapping to accomplish this.



Starting HSI Mode
=================


Changing View Parameters
========================


Using Profile Plots
===================


