########################
## Written by pederbg ##
########################

import time
from sentinelsat.sentinel import SentinelAPI, read_geojson, geojson_to_wkt
import zipfile
import os, sys, subprocess, shutil
from osgeo import ogr
from osgeo import osr
import urllib2
import xml.etree.ElementTree as ET
import cv2
import math

GDALHOME='/usr/bin'

##------------------------------------------------------------------------------
def getS1Data(geojson):
    # connect to the API
    # api = SentinelAPI('PederBG', 'Copernicus', 'https://scihub.copernicus.eu/dhus') # For areas outside Norway
    api = SentinelAPI('PederBG', 'Copernicus',
                      'https://colhub.met.no/#/home')  # Use this if the area of interest is within Norway

    # search by polygon, time, and SciHub query keywords
    footprint = geojson_to_wkt(read_geojson(geojson))
    date = time.strftime("%Y%m%d")
    yestdate = str(int(date)-1)

    products = api.query(footprint,
                         ("20180107", date),
                         platformname='Sentinel-1',
                         producttype='GRD',
                         sensoroperationalmode='IW'
                         )

    if len(products) == 0:
        print("No files found at date: " + date)
        quit()
    print("Found", len(products), "Sentinel-1 images.")

    products_df = api.to_dataframe(products)
    for i in range(len(products_df)):
        print( "Name:", api.get_product_odata(products_df.index[i])["title"], "size:", \
         str(int(api.get_product_odata(products_df.index[i])["size"]) / 1000000), "MB" )

    # FINDING SMALLEST FILE
    smallestFile = None
    #tempSize = 9999999999
    tempSize = 1
    for i in range(0, len(products)):
        if (api.get_product_odata(products_df.index[i])["size"] > tempSize):
            smallestFile = products_df.index[i]
            tempSize = api.get_product_odata(products_df.index[i])["size"]
    # ----------------------------------------------------------------

    # SETTING MAX SIZE AND GETTING PRODUCT INFO
    maxSize = 2 * 1000000000  # Set the max size for files to download (in bytes)
    if (tempSize < maxSize):
        s1File = smallestFile
        api.download(s1File)
        s1Name = api.get_product_odata(s1File)["title"]
        s1Date = api.get_product_odata(s1File)["date"].strftime("%d-%m-%Y_%H-%M") # ":" cause error in windowsOS and with KML links
        s1Link = api.get_product_odata(s1File)["url"]
        print("Downloaded " + s1Name + ", Size: " + str(tempSize) + " bytes.")
        print("----------------___>", s1Link)
    else:
        print("No file small enough to download")
        quit()

    # UNZIPPING DOWNLOADED FILE
    print("Unzipping product")

    zip_ref = zipfile.ZipFile(s1Name + '.zip')
    zip_ref.extractall()
    zip_ref.close()

    return [s1File, s1Name, s1Date, s1Link]
##------------------------------------------------------------------------------

##------------------------------------------------------------------------------
def mkGraticule(stepsize = 1, area = "13 68 33 78"):
    #cmd = GDALHOME + "/mkgraticule.py -s " +str(stepsize) + " -range " + area + " tmp/graticule.shp"
    cmd = "python mkgrat.py -s " +str(stepsize) + " -range " + area + " tmp/graticule.shp"
    print(cmd)
    retcode = subprocess.call(cmd, shell=True)

def addGraticule(working, graticule="/graticule.shp"):
    cmd = GDALHOME + "/gdal_rasterize -burn 255 tmp" + graticule + " " + working
    print(cmd)
    retcode = subprocess.call(cmd, shell=True)
##------------------------------------------------------------------------------

##------------------------------------------------------------------------------
def cleaner(target_file = "tmp"):
    try:
        if (os.path.isfile(target_file)):
            os.remove(target_file)
        else:
            shutil.rmtree(target_file)
    except OSError:
        print("No file named", target_file)
##------------------------------------------------------------------------------

##------------------------------------------------------------------------------
def getWindInfo(GRID):
    # CONNECT TO YR.NO
    print("Connecting to yr.no...")

    response = urllib2.urlopen('https://www.yr.no/place/Hav/' + GRID + '/varsel.xml')
    html = response.read()
    # ----------------------------------------------------------------

    # PARSING XML
    tree = ET.ElementTree(ET.fromstring(html))
    root = tree.getroot()

    obsSpeed = float(root[5][0][0][3].get('mps'))
    obsDeg = float(root[5][0][0][2].get('deg'))
    obsName = root[0][3].get('geobaseid')
    obsDir = root[5][0][0][2].get('name')

    print("Wind: ", obsSpeed, " mps, direction: ", obsDeg, "degrees.")
    return [obsSpeed, obsDeg, obsDir]
    # ----------------------------------------------------------------
def addWindArrow(*imNames):
    GRID = '72.2922222_21.8055556'  # LANDING SITE GRID (center of square)
    splitGrid = GRID.split('_')
    [obsSpeed, obsDeg, obsDir] = getWindInfo(GRID)
    first = True
    for imName in imNames:
        img = cv2.imread(imName)
        if first:
            first = False
            obsDeg = - math.radians(obsDeg)
            imgHeight = img.shape[0]
            imgWidth = img.shape[1]
            print("Image height: ", imgHeight, ", image width: ", imgWidth)

            # COMPUTING IMAGE HEIGHT AND WIDTH TO SCALE TEXT/ARROW
            if (imgHeight > imgWidth):
                p = imgHeight / 750
                lineSpeed = obsSpeed/3
            else:
                p = (img.shape[0] + img.shape[1]) / 1500
                lineSpeed = obsSpeed/2

            print("Computed P-ratio: ", p)

            startX = 50
            startY = 100
            x = 10 * (lineSpeed * math.sin(obsDeg)) + startX
            y = 10 * (lineSpeed * math.cos(obsDeg)) + startY

            print("x: ", x, ", y: ", y)
        # DRAWING ON IMAGE
        draw = cv2.arrowedLine(img, (int(startX) * p, int(startY) * p), (int(x) * p, int(y) * p), (0, 0, 255), p)
        font = cv2.FONT_HERSHEY_COMPLEX
        cv2.putText(img, ('Wind data from grid: ' + splitGrid[0] + 'N, ' + splitGrid[1] + 'E'), (10 * p, 20 * p), font, 0.3 * p,
                    (0, 0, 255), p)
        cv2.putText(img, (str(obsSpeed) + " mps, from " + obsDir), (10 * p, 40 * p), font, 0.3 * p, (0, 0, 255), p)

        cv2.imwrite(imName, img)
        print("Wind vector created and added to image named", imName + ".")
##------------------------------------------------------------------------------

##------------------------------------------------------------------------------
def generateKML(fileName, boundNorth, boundSouth, boundEast, boundWest):

    print("Making KML to overlay in Map.html...")

    txt_file = open('../kmlfiles/' + fileName + ".kml", "w")
    txt_file.write(
        '<?xml version="1.0" encoding="UTF-8"?>' + "\n" +
        '<kml xmlns="http://earth.google.com/kml/2.0">' + "\n" +
        '<Document>' + "\n" +
        '  <name>' + fileName + '</name>' + "\n" +
        '  <description>' + "\n" +
        'TODOC</description>' + "\n" +
        '  <GroundOverlay>' + "\n" +
        '    <name>Raster data</name>' + "\n" +
        '      <LatLonBox>' + "\n" +
        '      <north>' + str(boundNorth) + '</north>' + "\n" +
        '      <south>' + str(boundSouth) + '</south>' + "\n" +
        '      <east>' + str(boundEast) + '</east>' + "\n" +
        '      <west>' + str(boundWest) + '</west>' + "\n" +
        '    </LatLonBox>' + "\n" +
        '    <Icon>' + "\n" +
        '      <href>http://lundinblackoil.com/peder/sentinel_images/' + fileName + "\n" +
        '    </Icon>' + "\n" +
        '  </GroundOverlay>' + "\n" +
        '</Document>' + "\n" +
        '</kml>'
    )
    txt_file.close()
##------------------------------------------------------------------------------
