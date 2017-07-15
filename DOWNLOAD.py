#!/bin/sh
''''cd /home/lundinbl/public_html/peder/ && exec /home/lundinbl/Python27_v2/Python-2.7.13/python  -- "$0" # '''
import time
import os
import sys
sys.path.append("/home/lundinbl/.local/lib/python2.7/site-packages/snappy")
sys.path.append("/home/lundinbl/.local/lib/python2.7/site-packages/jpy")

class Tee(object):
    def __init__(self, *streams):
        self.streams = streams
    def write(self, obj):
        for s in self.streams:
            s.write(obj)
            s.flush()
    def flush(self) :
        for s in self.streams:
            s.flush()

logFile = open('sentinelDownload.log', 'w')

tee = Tee(sys.stdout, logFile)

sys.stdout = tee
sys.stderr = tee


# connect to the API
from sentinelsat.sentinel import SentinelAPI, read_geojson, geojson_to_wkt

# api = SentinelAPI('PederBG', 'Copernicus', 'https://scihub.copernicus.eu/dhus')
api = SentinelAPI('PederBG', 'Copernicus','https://colhub.met.no/#/home')  # Use this if the area of interest is within Norway

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
    print("No files found")
    quit()
for i in range(len(products)):
    print(products[products.keys()[i]])

products_df = api.to_dataframe(products)

smallestFile = None
tempSize = 9999999999
for i in range(0, len(products)):
    if (api.get_product_odata(products_df.index[i])["size"] < tempSize):
        smallestFile = products_df.index[i]
        tempSize = api.get_product_odata(products_df.index[i])["size"]

maxSize = 300000000  # Set the max size for files to download (in bytes)
if (tempSize < maxSize):
    api.download(smallestFile)
    smallestName = api.get_product_odata(smallestFile)["title"]
    smallestDate = api.get_product_odata(smallestFile)["date"].strftime("%d-%m-%Y_%H:%M")

    print("Downloading " + smallestName + ", Size: " + str(tempSize) + " bytes.")
else:
    print("No file small enough to download")

### Unzipping downloaded file
print("Unzipping product")
import zipfile
zip_ref = zipfile.ZipFile(smallestName + '.zip')
zip_ref.extractall()
zip_ref.close()

# --------------------------------------------------------------------------------- #
###################### SNAP PROCESSING ##########################

import snappy
from snappy import ProductIO
from snappy import GPF
from snappy import ProgressMonitor

HashMap = snappy.jpy.get_type('java.util.HashMap')

# Get file:
product = ProductIO.readProduct(smallestName + '.SAFE/manifest.safe')
print("Processing...")
print(product)


### CALIBRATION
print("Calibrating product...")
params0 = HashMap()
params0.put('outputSigmaBand', True)
params0.put('sourceBands', 'Amplitude_' + 'VV')
params0.put('selectedPolarisations', 'VV')
params0.put('outputImageScaleInDb', False)

calib = GPF.createProduct("Calibration", params0, product)

### MAKING SUBSET
print("Making subset...")
WKTReader = snappy.jpy.get_type('com.vividsolutions.jts.io.WKTReader')
wkt = geojson_to_wkt(read_geojson('barentsSea.geojson'))  # Lundin landing site in Barents Sea
geom = WKTReader().read(wkt)

subsettings = HashMap()
subsettings.put('geoRegion', geom)
subsettings.put('outputImageScaleInDb', False)

target_0 = GPF.createProduct("Subset", subsettings, calib)
ProductIO.writeProduct(target_0, "temp", 'BEAM-DIMAP')

# Reading in new product
productSUB = ProductIO.readProduct('temp.dim')

### SPECKLE FILTER
print("Speckle filtering...")
params1 = HashMap()
params1.put('sourceBands', 'Sigma0_' + 'VV')
target_1 = GPF.createProduct('Speckle-Filter', params1, productSUB)
ProductIO.writeProduct(target_1, "temp2", 'BEAM-DIMAP')

# Reading in new product
productFILT = ProductIO.readProduct('temp2.dim')

### TERRAIN CORRECTION
print("Range Doppler Terrain Correction...")
params2 = HashMap()
params2.put('demName', 'ACE30')
params2.put('nodataValueAtSea', False)
target_2 = GPF.createProduct('Terrain-Correction', params2, productFILT )
ProductIO.writeProduct(target_1, "temp3", 'BEAM-DIMAP')

# Reading in new product
productTER = ProductIO.readProduct('temp3.dim')

### MAKING IMAGE
print("Generating image...")
JPY = snappy.jpy
imageIO = JPY.get_type('javax.imageio.ImageIO')
File = JPY.get_type('java.io.File')

p = productTER
band = p.getBand('Sigma0_VV')
image = band.createColorIndexedImage(ProgressMonitor.NULL)
date = time.strftime("%d%m%Y_%H%M%S")  # dd/mm/yyyy format
dateHourMin = time.strftime("%H:%M")
name = File('temp.png')
print("...")
imageIO.write(image, 'PNG', name)
print("Image created")


################### MAKING WIND ARROW ####################
# CONNECT TO YR.NO
print("Connecting to yr.no...")
import urllib2
response = urllib2.urlopen('https://www.yr.no/place/Norway/Hav/Goliat_observation_site/varsel.xml')
html = response.read()  # Observations from Goliat platform

import xml.etree.ElementTree as ET
tree = ET.ElementTree(ET.fromstring(html))
root = tree.getroot()

try:
    obsSpeed = float(root[6][0][3].get('mps'))
    obsDeg = float(root[6][0][2].get('deg'))
    obsName = root[6][0].get('name')
    obsDir = root[6][0][2].get('name')
    obsTime = root[6][0][2].get('time')
except Exception:
    print ("Goliat Platform weather observations, not available, using Fruholmen")
    obsSpeed = float(root[6][0][3].get('mps'))
    obsDeg = float(root[6][0][2].get('deg'))
    obsName = root[6][0].get('name')
    obsDir = root[6][0][2].get('name')
    obsTime = root[6][0][2].get('time')

print("Wind: ", obsSpeed, " mps, direction: ", obsDeg, "degrees.")


################### WRITING ON THE IMAGE ###################
#TODO (bruke logaritmisk skala eller noe...)?
print("Writing weather to image...")
import cv2
import math
img = cv2.imread('temp.png')  # reading in generated image
obsDeg = - math.radians(obsDeg)  # negative radians to turn arrow the correct way

imgHeight = img.shape[0]
imgWidth = img.shape[1]
print("Image height: ", imgHeight, ", image width: ", imgWidth)

# COMPUTING IMAGE HEIGHT AND WIDTH TO SCALE TEXT/ARROW
if (imgHeight > imgWidth):
    p = imgHeight / 600
else:
    p = (img.shape[0] + img.shape[1]) / 1500
print("Computed P-ratio: ", p)

# LINE LENGTH CONTROL
lineSpeed = obsSpeed
lineSize = 2
if (lineSpeed > 28):
    lineSize = 4
    lineSpeed = lineSpeed / 8
elif (lineSpeed > 12):
    lineSize = 3
    lineSpeed = lineSpeed/3

startX = 50
startY = 100
x = 10*(lineSpeed * math.sin(obsDeg)) + startX
y = 10*(lineSpeed * math.cos(obsDeg)) + startY

print("x: ", x, ", y: ", y)

# MORE LINE LENGTH CONTROL
if (x < 0):
    startX += -(x - 10*p)
    x += -(x - 10)
if (y < 0):
    startY += -(y - 10*p)
    y += -(y - 10)

print("startX: ", startX, ", startY: ", startY)
print("X: ", x, ", Y: ", y)


draw = cv2.arrowedLine(img, (int(startX)*p, int(startY)*p), (int(x)*p,int(y)*p), (0,0,255), lineSize*p)
font = cv2.FONT_HERSHEY_COMPLEX
cv2.putText(img,('Wind data from ' + obsName + ' observation site'),(10*p,20*p), font, 0.35*p,(0,0,255),p)
cv2.putText(img,(str(obsSpeed)+" mps, from "+obsDir+". Observation time: "+obsTime+"."),(10*p,40*p),font,0.3*p,(0,0,255),p)

cv2.imwrite('sentinel_images/sentinel_image_autonomousAtHour-' + dateHourMin + '__' + smallestDate + '.png', img)
print("Wind vector created!")

#################### DELETING USED FILES AND MAKING ZIP-FILE #################### (only works on linux OS)
# deletes the used files
os.remove(smallestName + '.zip')
os.remove('temp.dim')
os.remove('temp.png')
os.remove('temp2.dim')
os.remove('temp3.dim')


import shutil
shutil.rmtree(smallestName + '.SAFE')
shutil.rmtree('temp.data')
shutil.rmtree('temp2.data')
shutil.rmtree('temp3.data')



# Comressing directory to enable download
zf = zipfile.ZipFile("sentinel_images.zip", "w")
for dirname, subdirs, files in os.walk("sentinel_images"):
    zf.write(dirname)
    for filename in files:
        zf.write(os.path.join(dirname, filename))
zf.close()

print("Process finished !")

logFile.close()
