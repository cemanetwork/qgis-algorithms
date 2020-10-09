# -*- coding: utf-8 -*-

"""
Name        : Extract shoreline
Description : Extracts shoreline from satellite images.
Version     : 0.1.0
Date        : 2020-10-9
Reference   : -
"""

from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterRasterLayer
from qgis.core import QgsProcessingParameterBand
from qgis.core import QgsProcessingParameterBoolean
from qgis.core import QgsProcessingParameterEnum
from qgis.core import QgsProcessingParameterFeatureSink
from qgis.core import QgsProcessingParameterExtent
from qgis.core import QgsProcessingParameterCrs
from qgis.core import QgsProcessingParameterDistance
from qgis.core import QgsExpression
import processing


class ExtractShoreline4(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer('raster_layer', 'Raster layer'))
        self.addParameter(QgsProcessingParameterBand('blue_band', 'Blue band', parentLayerParameterName='raster_layer', allowMultiple=False, defaultValue=1))
        self.addParameter(QgsProcessingParameterBand('green_band', 'Green band', parentLayerParameterName='raster_layer', allowMultiple=False, defaultValue=2))
        self.addParameter(QgsProcessingParameterBand('nir_band', 'NIR band', parentLayerParameterName='raster_layer', allowMultiple=False, defaultValue=4))
        self.addParameter(QgsProcessingParameterBand('swir1_band', 'SWIR1 band', parentLayerParameterName='raster_layer', allowMultiple=False, defaultValue=5))
        self.addParameter(QgsProcessingParameterBand('swir2_band', 'SWIR2 band', parentLayerParameterName='raster_layer', allowMultiple=False, defaultValue=6))
        self.addParameter(QgsProcessingParameterEnum('index', 'Index', options=['NDWI','MNDWI','AWEI','NIR','WI1','WI2'], allowMultiple=False, defaultValue=5))
        self.addParameter(QgsProcessingParameterDistance('simplification_tol', 'Simplification tolerance', optional=True, parentParameterName='raster_layer', minValue=0))
        self.addParameter(QgsProcessingParameterExtent('extent', 'Extent', optional=True))
        self.addParameter(QgsProcessingParameterFeatureSink('shoreline', 'Shoreline', type=QgsProcessing.TypeVectorLine, createByDefault=True))

    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        feedback = QgsProcessingMultiStepFeedback(9, model_feedback)
        results = {}
        outputs = {}

        if parameters['simplification_tol'] is None:
            raster_layer = self.parameterAsRasterLayer(parameters, 'raster_layer', context)
            dx = raster_layer.rasterUnitsPerPixelX()
            dy = raster_layer.rasterUnitsPerPixelY()
            if dx != dy:
                raise QgsProcessingException('Raster pixels are not square! Please provide a simplification tolerance.')
            tol = dx
        else:
            tol = parameters['simplification_tol']

        if parameters['extent'] is None:
            # Pass input raster layer
            calc_input = parameters['raster_layer']
            raster_layer = self.parameterAsRasterLayer(parameters, 'raster_layer', context)
            ext = raster_layer.extent()
            xmin = ext.xMinimum()
            xmax = ext.xMaximum()
            ymin = ext.yMinimum()
            ymax = ext.yMaximum()
            crs_str = raster_layer.crs().authid()
            extract_extent = '{},{},{},{} [{}]'.format(xmin + 0.001, xmax - 0.001, ymin + 0.001, ymax - 0.001, crs_str)
        else:
            # Clip raster by extent
            alg_params = {
                'DATA_TYPE': 0,
                'EXTRA': '',
                'INPUT': parameters['raster_layer'],
                'NODATA': None,
                'OPTIONS': '',
                'PROJWIN': parameters['extent'],
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
            }
            outputs['clip_raster_by_extent'] = processing.run('gdal:cliprasterbyextent', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
            calc_input = outputs['clip_raster_by_extent']['OUTPUT']
            coord_str, crs_str = parameters['extent'].split()
            xmin, xmax, ymin, ymax = (float(x) for x in coord_str.split(','))
            extract_extent = '{},{},{},{} {}'.format(xmin + 0.001, xmax - 0.001, ymin + 0.001, ymax - 0.001, crs_str)

        feedback.setCurrentStep(1)
        if feedback.isCanceled():
            return {}

        if parameters['index'] == 0:
            band_a = parameters['green_band']
            band_b = parameters['nir_band']
            band_c = None
            band_d = None
            formula = QgsExpression('\'(A - B) / (A + B)\'').evaluate()
            i = 'NDWI'
        elif parameters['index'] == 1:
            band_a = parameters['green_band']
            band_b = parameters['swir1_band']
            band_c = None
            band_d = None
            formula = QgsExpression('\'(A - B) / (A + B)\'').evaluate()
            i = 'MNDWI'
        elif parameters['index'] == 2:
            band_a = parameters['green_band']
            band_b = parameters['swir1_band']
            band_c = parameters['nir_band']
            band_d = parameters['swir2_band']
            formula = QgsExpression('\'4 * (A - B) - (0.25 * C + 2.75 * D)\'').evaluate()
            i = 'AWEI'
        elif parameters['index'] == 3:
            band_a = parameters['nir_band']
            band_b = None
            band_c = None
            band_d = None
            formula = QgsExpression('\'A\'').evaluate()
            i = 'NIR'
        elif parameters['index'] == 4:
            band_a = parameters['green_band']
            band_b = parameters['swir2_band']
            band_c = None
            band_d = None
            formula = QgsExpression('\'(A - B) / (A + B)\'').evaluate()
            i = 'WI1'
        elif parameters['index'] == 5:
            band_a = parameters['blue_band']
            band_b = parameters['swir2_band']
            band_c = None
            band_d = None
            formula = QgsExpression('\'(A - B) / (A + B)\'').evaluate()
            i = 'WI2'
        feedback.pushInfo('Computing {} ...'.format(i))

        # Raster calculator 
        alg_params = {
            'BAND_A': band_a,
            'BAND_B': band_b,
            'BAND_C': band_c,
            'BAND_D': band_d,
            'BAND_E': None,
            'BAND_F': None,
            'EXTRA': '',
            'FORMULA': formula,
            'INPUT_A': calc_input,
            'INPUT_B': calc_input,
            'INPUT_C': calc_input,
            'INPUT_D': calc_input,
            'INPUT_E': None,
            'INPUT_F': None,
            'NO_DATA': None,
            'OPTIONS': '',
            'RTYPE': 5,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['raster_calculator'] = processing.run('gdal:rastercalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(2)
        if feedback.isCanceled():
            return {}

        # Otsu's binarization
        alg_params = {
            'BAND': 1,
            'FILL': True,
            'INPUT': outputs['raster_calculator']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['otsu_binarization'] = processing.run('script:otsubinarization', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(3)
        if feedback.isCanceled():
            return {}

        # Morphological filter
        alg_params = {
            'INPUT': outputs['otsu_binarization']['OUTPUT'],
            'METHOD': 2,
            'MODE': 0,
            'RADIUS': 1,
            'RESULT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['morphological_filter'] = processing.run('saga:morphologicalfilter', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(4)
        if feedback.isCanceled():
            return {}

        # Polygonize (raster to vector)
        alg_params = {
            'BAND': 1,
            'EIGHT_CONNECTEDNESS': True,
            'EXTRA': '',
            'FIELD': 'DN',
            'INPUT': outputs['morphological_filter']['RESULT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['polygonize'] = processing.run('gdal:polygonize', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(5)
        if feedback.isCanceled():
            return {}

        # Extract by attribute
        alg_params = {
            'FIELD': 'DN',
            'INPUT': outputs['polygonize']['OUTPUT'],
            'OPERATOR': 0,
            'VALUE': '1',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['extract_by_attribute'] = processing.run('native:extractbyattribute', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(6)
        if feedback.isCanceled():
            return {}

        # Polygons to lines
        alg_params = {
            'INPUT': outputs['extract_by_attribute']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['polygons_to_lines'] = processing.run('native:polygonstolines', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(7)
        if feedback.isCanceled():
            return {}

        # Extract/clip by extent
        alg_params = {
            'CLIP': True,
            'EXTENT': extract_extent,
            'INPUT': outputs['polygons_to_lines']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['extract_by_extent'] = processing.run('native:extractbyextent', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(8)
        if feedback.isCanceled():
            return {}

        # Simplify
        parameters['shoreline'].destinationName = 'Shoreline'
        alg_params = {
            'INPUT': outputs['extract_by_extent']['OUTPUT'],
            'METHOD': 0,
            'TOLERANCE': tol,
            'OUTPUT': parameters['shoreline']
        }
        outputs['simplify_geometries'] = processing.run('native:simplifygeometries', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['shoreline'] = outputs['simplify_geometries']['OUTPUT']
        return results

    def name(self):
        return 'extractshoreline'

    def displayName(self):
        return 'Extract shoreline'

    def group(self):
        return 'CEMAN'

    def groupId(self):
        return 'ceman'

    def shortHelpString(self):
        return """<html><body><h2>Algorithm description</h2>
<p>This algorithm extracts the shoreline from a raster layer given a water index and the required bands for that water index. The water index is computed, and the raster is binarized using Otsu’s threshold. An opening morphological filter is applied to reduce noise. The water&#8209;land interface is extracted as a vector line layer, and it is simplified using the Douglas&#8209;Peucker method for the provided tolerance.
</p>
<h2>Input parameters</h2>
<h3>Raster layer</h3>
<p>A multi-band raster layer (usually a Landsat image or similar satellite product) with the required bands for the selected water index.</p>
<h3>Blue band</h3>
<p>Blue band.</p>
<h3>Green band</h3>
<p>Green band.</p>
<h3>NIR band</h3>
<p>Near Infrared (NIR) band.</p>
<h3>SWIR1 band</h3>
<p>Short-wave Infrared (SWIR) 1.</p>
<h3>SWIR2 band</h3>
<p>Short-wave Infrared (SWIR) 2.</p>
<h3>Index</h3>
<p>A suitable water index. WI2 is recommended.</p>
<h3>Extent</h3>
<p>Provide an extent if you want to extract the shoreline for a region in the raster. By default, the shoreline is extracted for the entire raster extension.</p>
<h3>Simplification tolerance</h3>
<p>Distance value used for the Douglas&#8209;Peucker method implemented in QGIS. By default, if the raster pixels are square, the pixel size is used. Use 0 for no simplification.</p>
<h2>Outputs</h2>
<h3>Shoreline</h3>
<p>Vector line layer with the shoreline extracted from the raster layer.</p>
<br></body></html>"""

    def createInstance(self):
        return ExtractShoreline4()
