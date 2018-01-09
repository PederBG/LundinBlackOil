# LundinBlackOil
This project uses real-time SAR (synthetic aperture radar) satellite images from the Copernicus programme to monitor possible oil slicks in a specific area on the Norwegian continental shelf. It contains the complete native-javascript based web application and the python script using the ESA developed SNAP module to prosess raw SAFE-format Sentinel-1 data.

<p>Note: This project is meant to run on a linux server with a high RAM size. The code in DOWNLOAD.py also has a high number of module dependencies, making it hard to reproduce. Simply forking the repository will not work.

<p>Also note that the image prosessing done by the SNAP module is having some
issues with memory usage handling.
Since the DOWNLOAD script isn't that well written, it is likely to be changed in the next major update. The plan is also to
use GDAL for image prosessing instead of SNAP, removing everything that is dependent on the SNAP module.
