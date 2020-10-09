# -*- coding: utf-8 -*-

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (QgsProcessingException,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterRasterLayer,
                       QgsProcessingParameterBand,
                       QgsProcessingParameterBoolean,
                       QgsProcessingParameterRasterDestination)
from osgeo import gdal
from osgeo.gdalconst import GA_ReadOnly
from scipy.ndimage import binary_fill_holes
from skimage.filters import threshold_otsu

class OtsuBinarizationAlgorithm(QgsProcessingAlgorithm):
    INPUT = 'INPUT'
    BAND = 'BAND'
    FILL = 'FILL'
    OUTPUT = 'OUTPUT'

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return OtsuBinarizationAlgorithm()

    def name(self):
        return 'otsubinarization'

    def displayName(self):
        return self.tr('Otsu\'s binarization')

    def group(self):
        return self.tr('CEMAN')

    def groupId(self):
        return 'ceman'

    def shortHelpString(self):
        return self.tr("Binarize grayscale raster by Otsu\'s thresholding")

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer(self.INPUT, self.tr('Input Raster Layer')))
        self.addParameter(QgsProcessingParameterBand(self.BAND, self.tr('Band Number'), 1, self.INPUT))
        self.addParameter(QgsProcessingParameterBoolean(self.FILL, self.tr('Fill holes')))
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT, self.tr('Binarized')))

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsRasterLayer(parameters, self.INPUT, context)
        if source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
            
        band = self.parameterAsInt(parameters, self.BAND, context)
        fill = self.parameterAsBool(parameters, self.FILL, context)
        
        output_raster = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)
        
        # create output raster dataset
        inputDs = gdal.Open(unicode(source.source()), GA_ReadOnly)
        inputBand = inputDs.GetRasterBand(band)
        if inputBand is None:
            raise QgsProcessingException('Cannot open raster band {}'.format(band))
        
        nodata = -9999

        driver = gdal.GetDriverByName('GTiff')
        outputDs = driver.Create(output_raster, inputDs.RasterXSize, inputDs.RasterYSize, 1, gdal.GDT_Int32)
        outputDs.SetProjection(inputDs.GetProjection())
        outputDs.SetGeoTransform(inputDs.GetGeoTransform())
        outputBand = outputDs.GetRasterBand(1)
        outputBand.SetNoDataValue(nodata)

        # binarize
        arr = inputBand.ReadAsArray()
        th = threshold_otsu(arr)
        feedback.pushInfo('Threshold is {}'.format(th))
        feedback.setProgress(50)
        if fill:
            outputBand.WriteArray(binary_fill_holes(arr < th))
        else:
            outputBand.WriteArray(arr < th)

        outputDs.FlushCache()
        outputDs = None
        inputDs = None
        feedback.setProgress(100)

        return {self.OUTPUT: output_raster}