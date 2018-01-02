########################
## Written by pederbg ##
########################

from osgeo import gdal
import osr
from PIL import Image, ImageDraw, ImageFont

inp = []
for i in range(10):
    for j in range(10):
        inp.append( (18+i, 65+j) )

dataset = gdal.Open("tmp/warpedVV.tif")
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

def getPixfromCor(cor):
    ct = osr.CoordinateTransformation(srsLatLong,srs)
    temp = ct.TransformPoint(cor[0], cor[1])
    print(temp)

    point = (temp[0], temp[1])

    col = int((point[0] - xOrigin) / pixelWidth)
    row = int((yOrigin - point[1] ) / pixelHeight)

    return (col, row)

#----------------------------------------------------------------
res = []
for elem in inp:
    res.append(getPixfromCor(elem))

print(res)

def drawCords(cords, raw_cords):
    im = Image.open("testVV.jpg")

    rgbim = Image.new("RGB", im.size)
    rgbim.paste(im)

    pix = rgbim.load()

    d = ImageDraw.Draw(rgbim)
    font = ImageFont.load("pilfonts/timI14.pil")
    color = (255,255,255)

    for i in range(len(cords)):
        d.text((cords[i][0]+8,cords[i][1]), str(raw_cords[i][1])+"N, " + \
         str(raw_cords[i][0])+"E", color, font)

    rgbim.save('foo.jpg')

drawCords(res, inp)
