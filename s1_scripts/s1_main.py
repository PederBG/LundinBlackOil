#!/usr/bin/python

########################
## Written by pederbg ##
########################

import os, sys, subprocess, shutil
import numpy as np
import math
from osgeo import gdal
from osgeo.gdalconst import *

#from datetime import datetime
from glob import glob
import datetime
import time
import s1_lib
import s1_functions as s1_func
import s1_drawGrids as s1_draw

print('## Get newest Sentinel-1 data')
[s1File, s1Name, s1Date, s1Link] = s1_func.getS1Data("../smallBarentsSea.geojson")

TMPDIR = '/home/lundinbl/public_html/peder/s1_scripts/tmp'
subprocess.call('mkdir tmp', shell=True)

GDALHOME='/home/lundinbl/gdal/bin'
PROJSTR = '+proj=stere +lat_0=90.0 +lat_ts=90.0 +lon_0=0.0 +R=6371000'

#infile = '/home/pederbg/Downloads/S1A_IW_GRDM_1SDV_20171219T051117_20171219T051149_019767_0219DF_F8E8.SAFE'
infile = s1Name + ".SAFE"

workingVV = TMPDIR + "/workingVV.tif"
workingVH = TMPDIR + "/workingVH.tif"
working = [workingVV,workingVH]

calibratedVV = TMPDIR + "/calibratedVV.tif"
calibratedVH = TMPDIR + "/calibratedVH.tif"
calibrated = [calibratedVV,calibratedVH]

warpVVfname = TMPDIR+"/warpedVV.tif"
warpVHfname = TMPDIR+"/warpedVH.tif"
warpfname = [warpVVfname,warpVHfname]

calVVfname = TMPDIR+"/calVV.tif"
calVHfname = TMPDIR+"/calVH.tif"
calfname = [calVVfname,calVHfname]

noiseVVfname = TMPDIR+"/noiseVV.tif"
noiseVHfname = TMPDIR+"/noiseVH.tif"
noisefname = [noiseVVfname,noiseVHfname]

imageVV = "testVV.jpg"
imageVH = "testVH.jpg"
imagenames = [imageVV, imageVH]

#----------------------------------------------------------------

(fileVV,fileVH) = s1_lib.getfilename(infile)
infiles = [fileVV,fileVH]
nbands = 2
[dateline, gcps, minlon, maxlon, minlat, maxlat] = s1_lib.s1dateline( fileVV )
print("")
print("minlon:", minlon, "maxlon:", maxlon, "minlat:", minlat, "maxlat:", maxlat)
print("")

print('## Apply gcps')
s1_lib.s1applygcp( infiles, working, nbands, gcps )

print('## Find Noise xml files for band VV and VH')
(xmlNoiseFileVV,xmlNoiseFileVH) = s1_lib.getNoiseXML(infile)
xmlNoiseFile = [xmlNoiseFileVV,xmlNoiseFileVH]

print('## Find Calibration xml files for band VV and VH')
(xmlCalFileVV,xmlCalFileVH) = s1_lib.getCalXML(infile)
xmlCalFile = [xmlCalFileVV,xmlCalFileVH]

print('## Find xmlfile with scene inforamtion')
(xmlFileVV,xmlFileVH) = s1_lib.getXML(infile)
xmlFile = [xmlFileVV,xmlFileVH]

print('## Generate LUT (2) files for noise')
s1_lib.genLUT2(working[0], xmlNoiseFile[0], xmlFile[0] ,noisefname[0])
s1_lib.genLUT2(working[1], xmlNoiseFile[1], xmlFile[1], noisefname[1])

print('## Generate LUT files for s0 calibration')
s1_lib.genLUT(working[0], xmlCalFile[0], calfname[0])
s1_lib.genLUT(working[1], xmlCalFile[1], calfname[1])

print('## Remove Noise and Calibrate data to db')
log10=0
s1_lib.calibrate2d(working[0], calfname[0], noisefname[0], calibrated[0],log10)
s1_lib.calibrate2d(working[1], calfname[1], noisefname[1], calibrated[1],log10)

print('Warping to polarstereographic projection')
for i in range(nbands):
    s1_lib.s1warp(calibrated[i],warpfname[i],PROJSTR)
    if ((os.path.isfile(warpfname[i]) == False)):
        print 'Error warping file'
        sys.exit()

print('## Add graticule overlay')
s1_func.mkGraticule()
for i in range(nbands):
    s1_func.addGraticule(warpfname[i])


print('## Generate JPEG from warped tif-file')
for i in range(nbands):
    s1_lib.s1image(warpfname[i], imagenames[i])

print('## Add reference coordinates to graticule overlay')
[pixels, coordinates] = s1_draw.getGeoInfo()
for i in range(nbands):
    s1_draw.drawCords(pixels, coordinates, imagenames[i], imagenames[i])

print('## Add wind information from yr.no')
s1_func.addWindArrow(imageVV, imageVH)

print('## Make KML-file')
s1_func.generateKML("test.kml", minlon, maxlon, minlat, maxlat)

print('## Removed used files')
s1_func.cleaner()
s1_func.cleaner("testVV.jpg.aux.xml")
s1_func.cleaner("testVH.jpg.aux.xml")
