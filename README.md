# CEMAN’s QGIS Algorithms

Collection of custom QGIS processing algorithms, scripts, and models.

* Extract shoreline (depends on Otsu’s binarization)
* Otsu’s binarization (depends on Python packages _SciPy_ and _scikit-image_)

You can install packages in QGIS’ own Python by following the instructions in [this article](https://landscapearchaeology.org/2018/installing-python-packages-in-qgis-3-for-windows/). The command in step 3 would be:

```
python -m pip install scipy scikit-image
```

In order to install the algorithms, download this repository and add the scripts to the QGIS processing toolbox: _Add Script to Toolbox..._

![QGIS Scripts menu.](add-script.png)

You are free to use these algorithms for your projects. Also, remember to use the batch processing interface in QGIS if you have to process large amounts of data.
