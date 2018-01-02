########################
## Written by pederbg ##
########################

import time
from sentinelsat.sentinel import SentinelAPI, read_geojson, geojson_to_wkt
import zipfile
import os, sys, subprocess, shutil

GDALHOME='/usr/bin'


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
                         (yestdate, date),
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

def mkGraticule(stepsize = 1, area = "13 68 33 78"):
    cmd = GDALHOME + "/mkgraticule.py -s " +str(stepsize) + " -range " + area + " tmp/graticule.shp"
    print(cmd)
    retcode = subprocess.call(cmd, shell=True)

def addGraticule(working, graticule="/graticule.shp"):
    cmd = GDALHOME + "/gdal_rasterize -burn 255 tmp" + graticule + " " + working
    print(cmd)
    retcode = subprocess.call(cmd, shell=True)
