# LundinBlackOil
This project uses real-time SAR (synthetic aperture radar) satellite images from the Copernicus programme to monitor possible oil slicks in a specific area on the Norwegian continental shelf. It contains the complete native-javascript based web application as well as python scripts used to process raw Sentinel-1 imagery. Generated images are used as training data for machine learning, as of now implemented with SVM (Support Vector Machines). This is another part of the project and therefore not available in this repository.

The image processing has been through a major update and is no longer using the ESA developed SNAP module. It is now instead using the modules GDAL and SciFy/NumPy. All code used in the back end cron job is now placed in s1_scripts.

Note: This project is meant to run on a linux server with a high RAM size. The code in s1_scripts also has a high number of module dependencies, making it hard to reproduce. Simply forking the repository will not work.

Also note that while image processing works fine on smaller Sentinel-1 files, is it likely to run into problems if the raw data is too big. SAFE-files exceeding about 800 MB will probably cause errors since the program runs out of memory during 2-D interpolation.

##### Important dependencies:
 - OSGeo/GDAL - Geospatial Data Abstraction Library: https://pypi.python.org/pypi/GDAL
 - Scify / Numpy: https://www.scipy.org/install.html / https://pypi.python.org/pypi/numpy
 - sentinelsat: https://github.com/sentinelsat/sentinelsat
 - opencv-python (cv2): https://pypi.python.org/pypi/opencv-python
 - Pillow: https://pypi.python.org/pypi/Pillow/2.2.1
 
 ##### Run main script as cron job (Linux CentOS):
 ```
 source ~/.bash_profile &&
 source ~/.bashrccd &&
 /path/to/repo/s1_scripts/ &&
 python s1_main.py
 ```
