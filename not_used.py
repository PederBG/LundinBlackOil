#!/bin/sh
''''cd /home/lundinbl/public_html/peder/ && exec /home/lundinbl/Python27_v2/Python-2.7.13/python  -- "$0" # '''

import sys
sys.path.append("/home/lundinbl/.local/lib/python2.7/site-packages/snappy")
sys.path.append("/home/lundinbl/.local/lib/python2.7/site-packages/jpy")

import time
import os
from sentinelsat.sentinel import SentinelAPI, read_geojson, geojson_to_wkt
import zipfile
import snappy
from snappy import ProductIO, GPF, ProgressMonitor, PixelGeoCoding, PixelPos, GeoPos
import urllib2
import xml.etree.ElementTree as ET
import cv2
import math
import shutil
# ----------------------------------------------------------------

# WRITING TO LOG FILE
class Tee(object):
    def __init__(self, *streams):
        self.streams = streams

    def write(self, obj):
        for s in self.streams:
            s.write(obj)
            s.flush()

    def flush(self):
        for s in self.streams:
            s.flush()

logFile = open('sentinelDownload.log', 'w')
tee = Tee(sys.stdout, logFile)
sys.stdout = tee
sys.stderr = tee
# ----------------------------------------------------------------
# deletes the used files (only works on linux OS)
def removeUsedFiles():
    os.remove(smallestName + '.zip')
    os.remove('temp.dim')
    os.remove('temp2.dim')
    os.remove('temp3.dim')
    
    shutil.rmtree(smallestName + '.SAFE')
    shutil.rmtree('temp.data')
    shutil.rmtree('temp2.data')
    shutil.rmtree('temp3.data')
# shutil.rmtree('kmzfiles/' + dirName) # KMZ file generating on hold...
# ----------------------------------------------------------------

# connect to the API
# api = SentinelAPI('PederBG', 'Copernicus', 'https://scihub.copernicus.eu/dhus') # For areas outside Norway
api = SentinelAPI('PederBG', 'Copernicus',
                  'https://colhub.met.no/#/home')  # Use this if the area of interest is within Norway

# search by polygon, time, and SciHub query keywords
footprint = geojson_to_wkt(read_geojson('smallBarentsSea.geojson'))
date = time.strftime("%Y%m%d")

products = api.query(footprint,
                     date,
                     platformname='Sentinel-1',
                     producttype='GRD',
                     sensoroperationalmode='IW'
                     )

if len(products) == 0:
    print("No files found at date: " + date)
    quit()
for i in range(len(products)):
    print(products[products.keys()[i]])

products_df = api.to_dataframe(products)

# FINDING SMALLEST FILE
smallestFile = None
tempSize = 9999999999
for i in range(0, len(products)):
    if (api.get_product_odata(products_df.index[i])["size"] < tempSize):
        smallestFile = products_df.index[i]
        tempSize = api.get_product_odata(products_df.index[i])["size"]
# ----------------------------------------------------------------

# SETTING MAX SIZE AND GETTING PRODUCT INFO
maxSize = 500000000  # Set the max size for files to download (in bytes)
if (tempSize < maxSize):
    api.download(smallestFile)
    smallestName = api.get_product_odata(smallestFile)["title"]
    smallestDate = api.get_product_odata(smallestFile)["date"].strftime("%d-%m-%Y_%H-%M") # ":" cause error in windowsOS and with KML links
    smallestLink = api.get_product_odata(smallestFile)["url"]
    print("Downloading " + smallestName + ", Size: " + str(tempSize) + " bytes.")
else:
    print("No file small enough to download")
    quit()
    
fileName = 'sentinel-image(a)_' + smallestDate
cleanFileName = 'sentinel-image(C)_' + smallestDate
saveName = 'sentinel_images/' + fileName + '.png'  # file name
cleanSaveName = 'sentinel_images_clean/' + cleanFileName + '.png' 
# ----------------------------------------------------------------


# UNZIPPING DOWNLOADED FILE
print("Unzipping product")

zip_ref = zipfile.ZipFile(smallestName + '.zip')
zip_ref.extractall()
zip_ref.close()
# -------------------------------------------------------------------------------------------

###################### SNAP PROCESSING ##########################

HashMap = snappy.jpy.get_type('java.util.HashMap')

# Get file:
product = ProductIO.readProduct(smallestName + '.SAFE/manifest.safe')
print("Processing...")
print(product)

# CALIBRATION
print("Calibrating product...")
params0 = HashMap()
params0.put('outputSigmaBand', True)
params0.put('sourceBands', 'Amplitude_' + 'VV')
params0.put('selectedPolarisations', 'VV')
params0.put('outputImageScaleInDb', False)

calib = GPF.createProduct("Calibration", params0, product)
# ----------------------------------------------------------------

# MAKING SUBSET (TODO?: Change to SubsetOp() )
print("Making subset...")
WKTReader = snappy.jpy.get_type('com.vividsolutions.jts.io.WKTReader')
wkt = geojson_to_wkt(read_geojson('veryBigBarentsSea.geojson'))  # Lundin landing site in Barents Sea
geom = WKTReader().read(wkt)

subsettings = HashMap()
subsettings.put('geoRegion', geom)
subsettings.put('outputImageScaleInDb', False)

target_0 = GPF.createProduct("Subset", subsettings, calib)
ProductIO.writeProduct(target_0, "temp", 'BEAM-DIMAP')

# Reading in new product
productSUB = ProductIO.readProduct('temp.dim')
# ----------------------------------------------------------------

# SPECKLE FILTER
print("Speckle filtering...")
params1 = HashMap()
params1.put('sourceBands', 'Sigma0_' + 'VV')
target_1 = GPF.createProduct('Speckle-Filter', params1, productSUB)
ProductIO.writeProduct(target_1, "temp2", 'BEAM-DIMAP')

# Reading in new product
productFILT = ProductIO.readProduct('temp2.dim')
# ----------------------------------------------------------------

# TERRAIN CORRECTION TODO: Change to Ellipsoid Correction GG/RD (?)
print("Range Doppler Terrain Correction...")
params2 = HashMap()
params2.put('demName', 'ACE30')
params2.put('nodataValueAtSea', False)
params2.put('saveLatLon', True)
target_2 = GPF.createProduct('Terrain-Correction', params2, productFILT)
ProductIO.writeProduct(target_2, "temp3", 'BEAM-DIMAP')

# Reading in new product
productTER = ProductIO.readProduct('temp3.dim')
# ----------------------------------------------------------------

# MAKING IMAGE
print("Generating image...")
JPY = snappy.jpy
imageIO = JPY.get_type('javax.imageio.ImageIO')
File = JPY.get_type('java.io.File')

p = productTER
band = p.getBand('Sigma0_VV')

# Here the Java HeapSpace error will occur
try:
    first_image = band.createColorIndexedImage(ProgressMonitor.NULL)
except RuntimeError:
    removeUsedFiles()
    print("Error: Java Heap Space")
    quit()
    
name = File('temp.png')
print("...")
imageIO.write(first_image, 'PNG', name)

print("Image created")
# -------------------------------------------------------------------------------------------

################### GETTING WIND INFORMATION ####################
# CONNECT TO YR.NO
print("Connecting to yr.no...")

GRID = '72.2922222_21.8055556'  # LANDING SITE GRID (center of square)
splitGrid = GRID.split('_')
response = urllib2.urlopen('https://www.yr.no/place/Hav/' + GRID + '/varsel.xml')
html = response.read()  # Observations from Goliat platform
# ----------------------------------------------------------------

# PARSING XML
tree = ET.ElementTree(ET.fromstring(html))
root = tree.getroot()

obsSpeed = float(root[5][0][0][3].get('mps'))
obsDeg = float(root[5][0][0][2].get('deg'))
obsName = root[0][3].get('geobaseid')
obsDir = root[5][0][0][2].get('name')

print("Wind: ", obsSpeed, " mps, direction: ", obsDeg, "degrees.")
# -------------------------------------------------------------------------------------------

################### WRITING ON THE IMAGE ###################
# TODO -> FIX BAD/COMPLICATED CODE HERE: (use logarithmic scale?)

# READING IN GENERATED IMAGE
print("Writing weather info to image...")
img = cv2.imread('temp.png')
obsDeg = - math.radians(obsDeg)  # negative radians to turn arrow the correct way

imgHeight = img.shape[0]
imgWidth = img.shape[1]
print("Image height: ", imgHeight, ", image width: ", imgWidth)
# ----------------------------------------------------------------

# COMPUTING IMAGE HEIGHT AND WIDTH TO SCALE TEXT/ARROW
if (imgHeight > imgWidth):
    p = imgHeight / 750
    lineSpeed = obsSpeed/1.5
else:
    p = (img.shape[0] + img.shape[1]) / 1500
    lineSpeed = obsSpeed

print("Computed P-ratio: ", p)
# ----------------------------------------------------------------

# LINE LENGTH CONTROL
lineSize = 2
if (lineSpeed > 25):
    lineSize = 4
    lineSpeed = lineSpeed / 8
elif (lineSpeed > 10):
    lineSize = 3
    lineSpeed = lineSpeed / 3

startX = 50
startY = 100
x = 10 * (lineSpeed * math.sin(obsDeg)) + startX
y = 10 * (lineSpeed * math.cos(obsDeg)) + startY

print("x: ", x, ", y: ", y)
# ----------------------------------------------------------------

# MORE LINE LENGTH CONTROL
if (x < 0):
    startX += -(x - 10 * p)
    x += -(x - 10)
if (y < 0):
    startY += -(y - 10 * p)
    y += -(y - 10)

print("startX: ", startX, ", startY: ", startY)
print("X: ", x, ", Y: ", y)
# ----------------------------------------------------------------

# DRAWING ON IMAGE
draw = cv2.arrowedLine(img, (int(startX) * p, int(startY) * p), (int(x) * p, int(y) * p), (0, 0, 255), lineSize * p)
font = cv2.FONT_HERSHEY_COMPLEX
cv2.putText(img, ('Wind data from grid: ' + splitGrid[0] + 'N, ' + splitGrid[1] + 'E'), (10 * p, 20 * p), font, 0.3 * p,
            (0, 0, 255), p)
cv2.putText(img, (str(obsSpeed) + " mps, from " + obsDir), (10 * p, 40 * p), font, 0.3 * p, (0, 0, 255), p)

cv2.imwrite(saveName, img)
imageIO.write(first_image, 'PNG', File(cleanSaveName))
print("Wind vector created and added to image!")
# -------------------------------------------------------------------------------------------

################### MAKING KMZ AND KML FILES ####################
print ("Making KML/KMZ files...")


band_lat = target_2.getBand('latitude')
band_long = target_2.getBand('longitude')

group = PixelGeoCoding(band_lat, band_long, None, 5)  # TODO: Check last parameter (is 5 optimal?)

imHeight = band_lat.getRasterHeight()
imWidth = band_lat.getRasterWidth()

boundNorth = group.getGeoPos(PixelPos(imWidth, 0), GeoPos()).getLat()
boundWest = group.getGeoPos(PixelPos(0, imHeight), GeoPos()).getLon()
boundEast = group.getGeoPos(PixelPos(imWidth, imHeight), GeoPos()).getLon()
boundSouth = group.getGeoPos(PixelPos(imWidth, imHeight), GeoPos()).getLat()

print boundNorth, boundWest, boundEast, boundSouth


# TODO: KMZ generating on hold since I dont know how to show them directly
dirName = fileName
"""
os.makedirs('kmzfiles/' + dirName)
kmz_saveName = 'kmzfiles/' + dirName + '/' + fileName + '.png'
cv2.imwrite(kmz_saveName, img)
print "Writing KML file..."  # TODO: Make legend (bar that shows backscatter color scale)
txt_file = open('kmzfiles/' + dirName + "/doc.kml", "w")
txt_file.write(
    '<?xml version="1.0" encoding="UTF-8"?>' + "\n" +
    '<kml xmlns="http://earth.google.com/kml/2.0">' + "\n" +
    '<Document>' + "\n" +
    '  <name>' + fileName + '</name>' + "\n" +
    '  <description>' + "\n" +
    'TODO</description>' + "\n" +
    '  <GroundOverlay>' + "\n" +
    '    <name>Raster data</name>' + "\n" +
    '      <LatLonBox>' + "\n" +
    '      <north>' + str(boundNorth) + '</north>' + "\n" +
    '      <south>' + str(boundSouth) + '</south>' + "\n" +
    '      <east>' + str(boundEast) + '</east>' + "\n" +
    '      <west>' + str(boundWest) + '</west>' + "\n" +
    '    </LatLonBox>' + "\n" +
    '    <Icon>' + "\n" +
    '      <href>' + fileName + '.png</href>' + "\n" +
    '    </Icon>' + "\n" +
    '  </GroundOverlay>' + "\n" +
    '</Document>' + "\n" +
    '</kml>'
)
txt_file.close()
zf = zipfile.ZipFile('kmzfiles/' + dirName + ".zip", "w")
for dirname, subdirs, files in os.walk('kmzfiles/' + dirName):
    zf.write(dirname)
    for filename in files:
        zf.write(os.path.join(dirname, filename))
zf.close()
"""

# MAKING KML TO OVERLAY IN MAP.HTML
print("Making KML to overlay in Map.html...")

txt_file = open('kmlfiles/' + fileName + ".kml", "w")
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
    '      <href>http://lundinblackoil.com/peder/sentinel_images/' + fileName + '(R).png</href>' + "\n" +
    '    </Icon>' + "\n" +
    '  </GroundOverlay>' + "\n" +
    '</Document>' + "\n" +
    '</kml>'
)
txt_file.close()

# -------------------------------------------------------------------------------------------

################# RESIZE AND MAKEING THUMBNAIL ################
resizeInput = cv2.imread(saveName)
height, width = img.shape[:2]
resized = cv2.resize(resizeInput, (int(0.05 * width), int(0.05 * height)), interpolation=cv2.INTER_CUBIC)
cv2.imwrite("sentinel_images/" + fileName + "(R).png", resized)
print("Thumbnail image created!")
# -------------------------------------------------------------------------------------------

################# ADDING PRODUCT DOWNLOAD LINK TO TEXT-FILE ################
print("Appending to download_links txt-file...")
txt_file = open("product_download_links.txt", "a")
txt_file.write(saveName + ' ' + str(smallestLink) + "\n")
txt_file.close()
# -------------------------------------------------------------------------------------------

#################### DELETING USED FILES AND MAKING ZIP-FILE####################
removeUsedFiles()
os.remove('temp.png')
# ------------------------------------------------------------------------------

# COMPRESSING TO ENABLE DIRECT DOWNLOAD
zf = zipfile.ZipFile("sentinel_images.zip", "w")
for dirname, subdirs, files in os.walk("sentinel_images"):
    zf.write(dirname)
    for filename in files:
        zf.write(os.path.join(dirname, filename))
zf.close()

print("Process finished !")

logFile.close()
