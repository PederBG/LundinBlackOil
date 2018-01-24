########################
## Written by pederbg ##
########################

from osgeo import gdal
import osr
from PIL import Image, ImageDraw, ImageFont

def getPixfromCor(cor, srsLatLong, srs, xOrigin, yOrigin, pixelWidth, pixelHeight):
    ct = osr.CoordinateTransformation(srsLatLong,srs)
    temp = ct.TransformPoint(cor[0], cor[1])

    point = (temp[0], temp[1])

    col = int((point[0] - xOrigin) / pixelWidth)
    row = int((yOrigin - point[1] ) / pixelHeight)

    return (col, row)

def getGeoInfo(target_file = "tmp/warpedVV.tif"):
    coordinates = []
    for i in range(15):
        for j in range(10):
            coordinates.append( (17+i, 65+j) )

    dataset = gdal.Open(target_file)
    band = dataset.GetRasterBand(1)

    srs = osr.SpatialReference()
    srs.ImportFromWkt(dataset.GetProjection())
    srsLatLong = srs.CloneGeogCS()

    transform = dataset.GetGeoTransform()
    print("transform:", transform)

    xOrigin = transform[0]
    yOrigin = transform[3]
    pixelWidth = transform[1]
    pixelHeight = -transform[5]

    cols = dataset.RasterXSize
    rows = dataset.RasterYSize
    print (cols, rows)
    data = band.ReadAsArray(0, 0, cols, rows)

    #Get min/max coordinates
    toLatLong = osr.CoordinateTransformation(srs, srsLatLong)

    minXY = toLatLong.TransformPoint(xOrigin, yOrigin)
    print("minXY:", minXY)
    maxXY = toLatLong.TransformPoint((xOrigin + cols*pixelWidth), (yOrigin + rows*pixelHeight))
    print("maxXY:", maxXY)

    pixels = []
    for elem in coordinates:
        pixels.append(getPixfromCor(elem, srsLatLong, srs, xOrigin, yOrigin, pixelWidth, pixelHeight))

    return [pixels, coordinates]


def drawCords(pixPos, raw_cords, target_img, save_name):
    im = Image.open(target_img)

    rgbim = Image.new("RGB", im.size)
    rgbim.paste(im)

    pix = rgbim.load()

    d = ImageDraw.Draw(rgbim)
    font = ImageFont.load("pilfonts/timI14.pil")
    color = (255,255,255)

    for i in range(len(pixPos)):
        d.text((pixPos[i][0]+8,pixPos[i][1]), str(raw_cords[i][1])+"N, " + \
         str(raw_cords[i][0])+"E", color, font)

    rgbim.save(save_name)
