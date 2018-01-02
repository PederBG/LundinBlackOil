#!/usr/bin/python

###############################
## Written by Frode Dinessen ##
## Edits by pederbg          ##
###############################

import os, sys, subprocess
import string, math, time
from datetime import datetime, date
from datetime import timedelta
import numpy
from scipy import interpolate
from scipy import ndimage

import scipy

from osgeo import gdal
from osgeo import ogr
from osgeo import osr
from osgeo.gdalconst import *
import osgeo.gdal_array as gdal_array
import struct

import glob
from xml.dom.minidom import parse
import xml.dom.minidom
import matplotlib.pyplot as plt

TMPDIR = '/home/pederbg/LundinBlackOil/tmp'
GDALHOME='/usr/bin'


def getfilename(indir):
    dir = '%s/measurement/*.tiff' % (indir)
    print(dir)
    files = glob.glob(dir)
    for file in files:
        if '-vv-' in file:
            fileVV = file
        if '-vh-' in file:
            fileVH = file

    if os.path.isfile(fileVV) == False:
        fileVV = ''
    if os.path.isfile(fileVH) == False:
        fileVH = ''

    return (fileVV,fileVH)


# Check for Date Line (180E/180W)
def s1dateline( filename ):
    dlflg = 0
    firstgcp = 1
    inds = gdal.Open( filename )

    gcps = inds.GetGCPs()
    inds = None
    print(gcps)
    for gcp in gcps:
        if firstgcp == 1:
            minlon = gcp.GCPX
            maxlon = gcp.GCPX
            minlat = gcp.GCPY
            maxlat = gcp.GCPY
            firstgcp = 0
        else:
            if gcp.GCPX > maxlon:
                maxlon = gcp.GCPX
            if gcp.GCPX < minlon:
                minlon = gcp.GCPX
            if gcp.GCPY > maxlat:
                maxlat = gcp.GCPY
            if gcp.GCPY < minlat:
                minlat = gcp.GCPY

    if minlon < -90 and maxlon > 90:
        dlflg = 1
    print minlon,maxlon
    inds = None

    return [ dlflg, gcps, minlon, maxlon, minlat, maxlat ]

def s1applygcp( infiles, working, nbands, gcps ):

    for band in range(nbands):
        cmd = "/usr/bin/gdal_translate -of GTiff -ot Float32 -co \"COMPRESS=LZW\" " + \
            "-a_srs \"+proj=longlat +ellps=WGS84\" "
        for gcp in gcps:
            gcplon = gcp.GCPX
#            if gcplon < 0:
#                gcplon = gcplon + 360.0
            cmd = cmd + "-gcp " + \
                ("%f " % gcp.GCPPixel) + ("%f " % gcp.GCPLine) + \
                ("%f " % gcplon) + ("%f " % gcp.GCPY) + ("%f " % gcp.GCPZ)

        cmd = cmd + infiles[band] + " " + working[band]
        retcode = subprocess.call(cmd, shell=True)
        if retcode < 0:
            print 'Error in warping file %s' % infiles[band]
            sys.exit(-1)

    return 1


def getCalXML(indir):
    dir = '%s/annotation/calibration/calibration*.xml' % (indir)
    files = glob.glob(dir)
    for file in files:
        if '-vv-' in file:
            fileVV = file
        if '-vh-' in file:
            fileVH = file

    if os.path.isfile(fileVV) == False:
        fileVV = ''
    if os.path.isfile(fileVV) == False:
        fileVV = ''

    return (fileVV,fileVH)


def getXML(indir):
    dir = '%s/annotation/s1?-iw-grd*.xml' % (indir)
    files = glob.glob(dir)
    for file in files:
        if '-vv-' in file:
            fileVV = file
        if '-vh-' in file:
            fileVH = file

    if os.path.isfile(fileVV) == False:
        fileVV = ''
    if os.path.isfile(fileVH) == False:
        fileVH = ''

    return (fileVV,fileVH)

def getNoiseXML(indir):
    dir = '%s/annotation/calibration/noise*.xml' % (indir)
    files = glob.glob(dir)
    for file in files:
        if '-vv-' in file:
            fileVV = file
        if '-vh-' in file:
            fileVH = file

    if os.path.isfile(fileVV) == False:
        fileVV = ''
    if os.path.isfile(fileVV) == False:
        fileVV = ''

    return (fileVV,fileVH)

def genLUT2 (working, xmlFile, xmlFileBeam, outfile):
    # This routie support interpolation on an irregular grid where
    # number of pixels may vary for each line of calibration values.
    # Had to make this update of the genLUT because ESA suddenly changed
    # pixel length for different lines.
    # This updated version looks to be mutch slover in interpolation.
    vectorList = ''
    vector = ''
    lut = ''

    if xmlFile.find('calibration-s1') >=0:
        vectorList = 'calibrationVectorList'
        vector = 'calibrationVector'
        lut = 'sigmaNought'

    if xmlFile.find('noise-s1') >=0:
        vectorList = 'noiseVectorList'
        vector = 'noiseVector'
        lut = 'noiseLut'

    if len(vectorList) == 0:
        print 'Could not find a valid LUT in xmlfile %s' % (xmlfile)
        sys.exit()

    inds = gdal.Open( working )
    transform = inds.GetGeoTransform()
    projstr = inds.GetProjection()
    gcps = inds.GetGCPs()
    ulx = transform[0]
    xres = transform[1]
    uly = transform[3]
    yres = transform[5]
    xsize = inds.RasterXSize
    ysize = inds.RasterYSize

    inds = None
    print xmlFile
    DOMTree = xml.dom.minidom.parse(xmlFile)
    collection = DOMTree.documentElement
    List = collection.getElementsByTagName(vectorList)
    count = int(List[0].getAttribute("count"))
    vectors = List[0].getElementsByTagName(vector)
    pix=[]
    line=[]
    valList=[]

    for vec in vectors:
        pixVals = numpy.asarray(vec.getElementsByTagName('pixel')[0].
                                childNodes[0].data.split(),dtype=int)

        lineVal = int(vec.getElementsByTagName('line')[0].childNodes[0].data)

#        line.append(int(vec.getElementsByTagName('line')[0].childNodes[0].data))
        lutValues = numpy.asarray(vec.getElementsByTagName(lut)[0].
                                  childNodes[0].data.split(),dtype=float)

        for val in pixVals:
            pix.append( val )
            line.append( lineVal )

        for val in lutValues:
            valList.append( val )

    print 'Start interpolating'
    print xsize,ysize

    valList = numpy.array(valList)
    points = numpy.array([line,pix]).transpose()
    grid_y, grid_x = numpy.mgrid[0:ysize:1, 0:xsize:1]
    grid_z0 = interpolate.griddata(points, valList, (grid_y, grid_x), method='nearest')

    print 'write cal file %s' % (outfile)
    driver = gdal.GetDriverByName( 'GTiff' )
    createopts=[ "COMPRESS=LZW", "BIGTIFF=YES"]
    outds = driver.Create(outfile, xsize, ysize, 1, \
                              GDT_Float32 )
    if outds is None:
        print 'Could not create %s' % (outfile)
        sys.exit()
    outds.SetGeoTransform( transform )
    outds.SetProjection( projstr )
    outband = outds.GetRasterBand(1)
    outband.WriteArray(grid_z0)

    # Close the dataset
    outds = None

def genLUT (working, xmlFile,outfile):
    # This routie support interpolation on a regular grid where
    # calibration values are available for a fixed number of pixels for all lines.
    vectorList = ''
    vector = ''
    lut = ''

    if xmlFile.find('calibration-s1') >=0:
        vectorList = 'calibrationVectorList'
        vector = 'calibrationVector'
        lut = 'sigmaNought'

    if xmlFile.find('noise-s1') >=0:
        vectorList = 'noiseVectorList'
        vector = 'noiseVector'
        lut = 'noiseLut'

    if len(vectorList) == 0:
        print 'Could not find a valid LUT in xmlfile %s' % (xmlfile)
        sys.exit()

    inds = gdal.Open( working )
    transform = inds.GetGeoTransform()
    projstr = inds.GetProjection()
    gcps = inds.GetGCPs()
    ulx = transform[0]
    xres = transform[1]
    uly = transform[3]
    yres = transform[5]
    xsize = inds.RasterXSize
    ysize = inds.RasterYSize

    inds = None
    print xmlFile
    DOMTree = xml.dom.minidom.parse(xmlFile)
    collection = DOMTree.documentElement
    List = collection.getElementsByTagName(vectorList)
    count = int(List[0].getAttribute("count"))
    vectors = List[0].getElementsByTagName(vector)
    pix=[]
    line=[]
    valList=[]

    for vec in vectors:
        if len(line) == 0:
            pix = numpy.asarray(vec.getElementsByTagName('pixel')[0].
                                childNodes[0].data.split(),dtype=int)

        line.append(int(vec.getElementsByTagName('line')[0].childNodes[0].data))
        lutValues = numpy.asarray(vec.getElementsByTagName(lut)[0].
                                  childNodes[0].data.split(),dtype=float)
        if len(lutValues) == len(pix):
            lastLut = lutValues.copy()
            for val in lutValues:
                valList.append( val )

        if len(lutValues) != len(pix):
            for val in lastLut:
                valList.append( val )


    print 'Start interpolating'
    #tck = interpolate.interp2d(pix,line,valList,kind='cubic')
    vararr = numpy.asarray(valList).reshape(len(line),len(pix))
    tck = interpolate.RectBivariateSpline(line,pix,vararr)
    print 'OK'

    x = range(0,xsize)
    y = range(0,ysize)

    lutOut= tck(y,x)
    print lutOut.shape
    print ysize,xsize
    #plt.imshow(lutOut)
    #plt.show()

    print 'write cal file %s' % (outfile)
    driver = gdal.GetDriverByName( 'GTiff' )
    createopts=[ "COMPRESS=LZW", "BIGTIFF=YES"]
    outds = driver.Create(outfile, xsize, ysize, 1, \
                              GDT_Float32 )
    if outds is None:
        print 'Could not create %s' % (outfile)
        sys.exit()
    outds.SetGeoTransform( transform )
    outds.SetProjection( projstr )
    outband = outds.GetRasterBand(1)
    outband.WriteArray(lutOut)

    # Close the dataset
    outds = None

def calibrate2d(working, calFile, noiseFile, calibrated,log10):

    inds = gdal.Open( working )
    transform = inds.GetGeoTransform()
    projstr = inds.GetProjection()
    gcps = inds.GetGCPs()
    ulx = transform[0]
    xres = transform[1]
    uly = transform[3]
    yres = transform[5]
    xsize = inds.RasterXSize
    ysize = inds.RasterYSize
    print xsize,ysize
    data= (inds.GetRasterBand(1).ReadAsArray()).astype('float64')
    inds = None

    noiseds = gdal.Open(noiseFile )
    nxsize = noiseds.RasterXSize
    nysize = noiseds.RasterYSize
    print nxsize,nysize
    noise = (noiseds.GetRasterBand(1).ReadAsArray()).astype('float64')
    noiseds = None

    calds = gdal.Open(calFile )
    nxsize = calds.RasterXSize
    nysize = calds.RasterYSize
    print nxsize,nysize
    cal = (calds.GetRasterBand(1).ReadAsArray()).astype('float64')
    calds = None

    s0grid = ((numpy.abs(numpy.power(data,2)-noise))/numpy.power(cal,2))
    s0grid[s0grid<0.00001]=0.00001 #limits S0 to -50db

    #teller = numpy.abs(numpy.power(data,2)-noise)
    #i = numpy.where(teller==0)
    #teller[i]=1
    #teller[:,0:100]=1
    #teller[:,-100:]=1

    if log10==1:
        #s0grid = 10*numpy.log10(teller/numpy.power(cal,2))
        s0grid = 10*numpy.log10(s0grid)
#    else:
#        s0grid = teller/numpy.power(cal,2)

    calibrated_tmp = calibrated+"_tmp"
    driver = gdal.GetDriverByName( 'GTiff' )
    createopts=[ "COMPRESS=LZW", "BIGTIFF=YES"]
    outds = driver.Create(calibrated_tmp, xsize, ysize, 1, \
                              GDT_Float32, createopts  )
    if outds is None:
        print 'Could not create ', calibrated
        sys.exit()

    outds.SetGeoTransform( transform )
    outds.SetProjection( projstr )
    outband = outds.GetRasterBand(1)
    outband.WriteArray(s0grid)

    # Close the dataset
    outds = None

    # Apply GCPs
    cmd = GDALHOME+"/gdal_translate -of GTiff -co \"COMPRESS=LZW\" " + \
        "-a_srs \"+proj=longlat +ellps=WGS84\" "
    # if debug == 0:

    for gcp in gcps:
        gcplon = gcp.GCPX
        cmd = cmd + "-gcp " + \
            ("%f " % gcp.GCPPixel) + ("%f " % gcp.GCPLine) + \
            ("%f " % gcplon) + ("%f " % gcp.GCPY) + ("%f " % gcp.GCPZ)
    cmd = cmd + calibrated_tmp + " " + calibrated
    # print cmd
    try:
        retcode = subprocess.call(cmd, shell=True)
        if retcode < 0:
            print >>sys.stderr, "Child was terminated by signal", -retcode
        # else:
        #     print >>sys.stderr, "Child returned", retcode
    except OSError, e:
        print >>sys.stderr, "Execution failed:", e

    # Remove temporary file
    os.remove( calibrated_tmp )


def s1warp(working,warpfname,projstr):

    cmd = GDALHOME + "/gdalwarp -of GTiff " + \
        "-t_srs \"+proj=stere +lat_0=90 +lat_ts=90 +lon_0=0 +R=6371000\" "
    cmd = cmd + "-tr 40 40 "
    cmd = cmd + "-order 3 -dstnodata 255 "
    cmd = cmd + working + " " + warpfname
    print("--------------------")
    print cmd
    print("--------------------")
    retcode = subprocess.call(cmd, shell=True)
      # TODO: shell=True -> vulnerable to shell injection
    if retcode < 0:
        print "Error: Warped was terminated by signal", -retcode
        sys.exit(-1)

def s1image(working, imagename):
    cmd = GDALHOME + "/gdal_translate -of JPEG " + \
        "-scale " + working + " " + imagename
    retcode = subprocess.call(cmd, shell=True)
    if retcode < 0:
        print "Error: Image generating was terminated by signal", -retcode
        sys.exit(-1)
