#!/usr/bin/python 

print "Content-type: text/html\n\n" 

import time
import os
# connect to the API
from sentinelsat.sentinel import SentinelAPI, read_geojson, geojson_to_wkt

# api = SentinelAPI('PederBG', 'Copernicus', 'https://scihub.copernicus.eu/dhus')
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

maxSize = 500000000  # Set the max size for files to download (in bytes)
if (tempSize < maxSize):
    api.download(smallestFile)
    smallestName = api.get_product_odata(smallestFile)["title"]
    smallestDate = api.get_product_odata(smallestFile)["date"].strftime("%Y-%m-%d_%H:%M")

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
parameters = HashMap()
parameters.put('outputSigmaBand', True)
parameters.put('sourceBands', 'Amplitude_' + 'VV')
parameters.put('selectedPolarisations', 'VV')
parameters.put('outputImageScaleInDb', False)

calib = GPF.createProduct("Calibration", parameters, product)

### MAKING SUBSET
print("Making subset...")
WKTReader = snappy.jpy.get_type('com.vividsolutions.jts.io.WKTReader')
#wkt = "POLYGON((21.005859375 71.97218900592375, 21.97265625 71.97218900592375, 21.97265625 72.24221647071744," \
 #     " 21.005859375 72.24221647071744, 21.005859375 71.97218900592375))" # Lundin landing site in Barents Sea

wkt = "POLYGON((20.77514648437 71.9066233794298, 22.230834960937 71.9066233794298, 22.230834960937 72.3199564831422," \
     " 20.77514648437 72.3199564831422, 20.77514648437 71.9066233794298))" # Lundin landing site in Barents Sea
geom = WKTReader().read(wkt)

subsettings = HashMap()
subsettings.put('geoRegion', geom)
subsettings.put('outputImageScaleInDb', False)

target_1 = GPF.createProduct("Subset", subsettings, calib)
ProductIO.writeProduct(target_1, "temp", 'BEAM-DIMAP')

# Reading in new product
productSUB = ProductIO.readProduct('temp.dim')

### SPECKLE FILTER
print("Speckle filtering...")
params2 = HashMap()
params2.put('sourceBands', 'Sigma0_' + 'VV')
target_0 = GPF.createProduct('Speckle-Filter', params2, productSUB)


### MAKING IMAGE
print("Generating image...")
JPY = snappy.jpy
imageIO = JPY.get_type('javax.imageio.ImageIO')
File = JPY.get_type('java.io.File')

p = target_0
band = p.getBand('Sigma0_VV')
image = band.createColorIndexedImage(ProgressMonitor.NULL)
date = time.strftime("%d%m%Y_%H%M%S")  # dd/mm/yyyy format
name = File('sentinel_images/sentinel_image_' + smallestDate + '.png')
imageIO.write(image, 'PNG', name)
print("Image created")

# deletes the used files
os.remove(smallestName + '.zip')
os.remove('temp.dim')
import shutil
shutil.rmtree(smallestName + '.SAFE')
shutil.rmtree('temp.data')


# Comressing directory to enable download
zf = zipfile.ZipFile("sentinel_images.zip", "w")
for dirname, subdirs, files in os.walk("sentinel_images"):
    zf.write(dirname)
    for filename in files:
        zf.write(os.path.join(dirname, filename))
zf.close()
