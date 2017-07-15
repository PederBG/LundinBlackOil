#!/usr/bin/python 
import time
from sentinelsat.sentinel import SentinelAPI, read_geojson, geojson_to_wkt
import zipfile
import os
import shutil


import snappy
from snappy import ProductIO
from snappy import GPF
from snappy import ProgressMonitor

date = 20170112
while date < 20170131:
    print("-----------------> Date: " + str(date))
    # connect to the API
    #api = SentinelAPI('PederBG', 'Copernicus', 'https://scihub.copernicus.eu/dhus')
    api = SentinelAPI('PederBG', 'Copernicus', 'https://colhub.met.no/#/home')  # Use this if the area of interest is within Norway

    # search by polygon, time, and SciHub query keywords
    footprint = geojson_to_wkt(read_geojson('barentsSea.geojson'))
    dateInt = date - 1
    print(dateInt, date)

    products = api.query(footprint,
                         str(dateInt), str(date),
                         platformname = 'Sentinel-1',
                         producttype = 'GRD',
                         sensoroperationalmode = 'IW'
                         )
    if len(products) == 0:
        print("No files found")
        date += 1
    else:
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
            print("Downloading " + smallestName + ", Size: " + str(tempSize) + " bytes.")

            ### Unzipping downloaded file
            print("Unzipping product")
            zip_ref = zipfile.ZipFile(smallestName + '.zip')
            zip_ref.extractall()
            zip_ref.close()

            # --------------------------------------------------------------------------------- #
            ###################### SNAP PROCESSING ##########################

            HashMap = snappy.jpy.get_type('java.util.HashMap')

            # Get file:
            product = ProductIO.readProduct(smallestName + '.SAFE/manifest.safe')
            # product = ProductIO.readProduct("S1A_IW_GRDH_1SDV_20170623T153459_20170623T153524_017163_01C9E7_C2E1"+ '.SAFE/manifest.safe')

            print("Processing...")
            print(product)

            ### CALIBRATION
            print("Calibrating product...")
            parameters = HashMap()
            parameters.put('outputSigmaBand', True)
            parameters.put('sourceBands', 'Amplitude_' + 'VV')
            parameters.put('selectedPolarisations', 'VV')
            parameters.put('outputImageScaleInDb', False)

            target_0 = GPF.createProduct("Calibration", parameters, product)

            ### SPECKLE FILTER
            print("Speckle filtering...")
            params2 = HashMap()
            params2.put('sourceBands', 'Sigma0_' + 'VV')

            target_2 = GPF.createProduct('Speckle-Filter', params2, target_0)

            ### MAKING IMAGE
            print("Generating image...")
            JPY = snappy.jpy
            imageIO = JPY.get_type('javax.imageio.ImageIO')
            File = JPY.get_type('java.io.File')
            p = target_2
            band = p.getBand('Sigma0_VV')
            image = band.createColorIndexedImage(ProgressMonitor.NULL)
            name = File('sentinel_images/sentinel_image-' + str(date) + '.png')
            imageIO.write(image, 'PNG', name)

            # deletes the used files
            os.remove(smallestName + '.zip')
            shutil.rmtree(smallestName + '.SAFE')

            print("Image created")

            date += 1
        else:
            print("No files under under the set max download size.")
            date += 1