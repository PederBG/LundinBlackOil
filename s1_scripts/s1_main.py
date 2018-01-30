#!/usr/bin/python

########################
## Written by pederbg ##
########################

import os, sys, subprocess, shutil
from shutil import copyfile as cp
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

TMPDIR = '/home/lundinbl/public_html/peder/s1_scripts/tmp'

GDALHOME='/home/lundinbl/gdal/bin'
PROJSTR = '+proj=stere +lat_0=90.0 +lat_ts=90.0 +lon_0=0.0 +R=6371000'
GRID = '72.2922222_21.8055556'  # LANDING SITE GRID (center of square)
MAXWIND = 12 # If the wind speed is higher image will not be generated
MAX_FILE_DOWNLOADS = 4  # The maximum amount of files to download and process
MIN_LAT = 70.8

print('## Check if wind is low enough to run image')
#s1_func.getAverageWind(GRID) TODO
windSpeed = s1_func.getWindInfo(GRID, simple=True)[0]
if windSpeed > MAXWIND:
    print("Image is not usable for oil detection. Too much wind in the area.")
    quit()

print('## Get newest Sentinel-1 data')
s1Files = s1_func.getS1Data("../smallBarentsSea.geojson", 200000000)

s1Files = s1Files[:MAX_FILE_DOWNLOADS]

print('## Starting main loop:')
print('########################################################################')
for numb in range(len(s1Files)):
    print('## Downloading file', numb + 1, "of", len(s1Files))
    [s1File, s1Name, s1Date, s1Link] = s1_func.downloadS1Data( s1Files[numb] )
    infile = s1Name + ".SAFE"

    subprocess.call('mkdir tmp', shell=True)

    workingVV = TMPDIR + "/workingVV.tif"
    workingVH = TMPDIR + "/workingVH.tif"
    working = [workingVV,workingVH]

    calibratedVV = TMPDIR + "/calibratedVV.tif"
    calibratedVH = TMPDIR + "/calibratedVH.tif"
    calibrated = [calibratedVV,calibratedVH]

    calVVfname = TMPDIR+"/calVV.tif"
    calVHfname = TMPDIR+"/calVH.tif"
    calfname = [calVVfname,calVHfname]

    noiseVVfname = TMPDIR+"/noiseVV.tif"
    noiseVHfname = TMPDIR+"/noiseVH.tif"
    noisefname = [noiseVVfname,noiseVHfname]

    warpVVfname = TMPDIR+"/warpedVV.tif"
    warpVHfname = TMPDIR+"/warpedVH.tif"
    warpfname = [warpVVfname, warpVHfname]

    warpVVfname_clear = TMPDIR+"/warpedVV_c.tif"
    warpVHfname_clear = TMPDIR+"/warpedVH_c.tif"
    warpfname_clear = [warpVVfname_clear,warpVHfname_clear]

    justNameVV = "sentinel-imageVV_" + s1Date + ".jpg"
    justNameVH = "sentinel-imageVH_" + s1Date + ".jpg"
    justNames = [justNameVV, justNameVH]

    imageVV = "/home/lundinbl/public_html/peder/sentinel_images/" + justNameVV
    imageVH = "/home/lundinbl/public_html/peder/sentinel_images/" + justNameVH
    imagenames = [imageVV, imageVH]

    justNameVV_clear = "sentinel-imageVV_" + s1Date + "_c.jpg"
    justNameVH_clear = "sentinel-imageVH_" + s1Date + "_c.jpg"
    justNames_clear = [justNameVV_clear, justNameVH_clear]

    imageVV_clear = "/home/lundinbl/public_html/peder/sentinel_images_clear/" + justNameVV_clear
    imageVH_clear = "/home/lundinbl/public_html/peder/sentinel_images_clear/"     + justNameVH_clear
    imagenames_clear = [imageVV_clear, imageVH_clear]

    justNameVV_thumb = "sentinel-imageVV_" + s1Date + "_t.jpg"
    justNameVH_thumb = "sentinel-imageVH_" + s1Date + "_t.jpg"
    justNames_thumb = [justNameVV_thumb, justNameVH_thumb]

    imageVV_thumb = "/home/lundinbl/public_html/peder/sentinel_images/" + justNameVV_thumb
    imageVH_thumb = "/home/lundinbl/public_html/peder/sentinel_images/"     + justNameVH_thumb
    imagenames_thumb = [imageVV_thumb, imageVH_thumb]


    kmlNameVV = "sentinel-imageVV_" + s1Date + ".kml"
    kmlNameVH = "sentinel-imageVH_" + s1Date + ".kml"
    kmlNames = [kmlNameVV, kmlNameVH]

    linksFile = "/home/lundinbl/public_html/peder/product_download_links.txt"

    #----------------------------------------------------------------

    (fileVV,fileVH) = s1_lib.getfilename(infile)
    infiles = [fileVV,fileVH]
    nbands = 2
    [dateline, gcps, minlon, maxlon, minlat, maxlat] = s1_lib.s1dateline( fileVV )
    print("")
    print("minlon:", minlon, "maxlon:", maxlon, "minlat:", minlat, "maxlat:", maxlat)
    print("")

    # TODO: CALIBRATION DOES NOT WORK IF IMAGE CONTAINS LAND
    # TODO: GET A BETTER SOLUTION
    if minlat > MIN_LAT:

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

        print('## Copy the clear image before adding grid overlay')
        for i in range(nbands):
            cp( warpfname[i], warpfname_clear[i])

        print('## Add graticule overlay')
        s1_func.mkGraticule()
        for i in range(nbands):
            s1_func.addGraticule(warpfname[i])


        print('## Generate JPEG from warped tif-file')
        for i in range(nbands):
            s1_lib.s1image(warpfname[i], imagenames[i])
            s1_lib.s1image(warpfname_clear[i], imagenames_clear[i])

        print('## Add reference coordinates to graticule overlay')
        [pixels, coordinates] = s1_draw.getGeoInfo()
        for i in range(nbands):
            s1_draw.drawCords(pixels, coordinates, imagenames[i], imagenames[i])

        print('## Add wind information from yr.no')
        s1_func.addWindArrow([imageVV, imageVH], GRID)

        print('## Make KML-file')
        for i in range(nbands):
            s1_func.generateKML(kmlNames[i], justNames_clear[i], maxlat, minlat, maxlon, minlon)

        print('## Make thumbnail image')
        for i in range(nbands):
            s1_func.makeThumbnail(imagenames_clear[i], imagenames_thumb[i])

        print('## Append to download links file')
        for i in range(nbands):
            s1_func.genDownloadLinks(s1Link, linksFile, justNames[i])
    else:
        print("Image too far south and may contain landmass. Not added.")

    print('## Removed used files')
    s1_func.cleaner()
    s1_func.cleaner(infile)
    s1_func.cleaner(s1Name + ".zip")
    for i in range(nbands):
        s1_func.cleaner(imagenames[i] + ".aux.xml")
        s1_func.cleaner(imagenames_clear[i] + ".aux.xml")

print('#######################################################################')
print('## Main loop finnished')

print('## Update zipfile used for direct download')
s1_func.makeZipFile()
