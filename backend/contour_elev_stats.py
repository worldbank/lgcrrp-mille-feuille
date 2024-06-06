# DETERMINE WHETHER TO RUN THIS SCRIPT ##############
import yaml

# load menu
with open("../mnt/city-directories/01-user-input/menu.yml", 'r') as f:
    menu = yaml.safe_load(f)

if menu['raster_processing'] and menu['elevation']:
    print('run contour')
    
    # SET UP ##############################################

    from os.path import exists
    from pathlib import Path

    # load city inputs files, to be updated for each city scan
    with open("../mnt/city-directories/01-user-input/city_inputs.yml", 'r') as f:
        city_inputs = yaml.safe_load(f)

    city_name_l = city_inputs['city_name'].replace(' ', '_').lower()

    # load global inputs, such as data sources that generally remain the same across scans
    with open("global_inputs.yml", 'r') as f:
        global_inputs = yaml.safe_load(f)

    # Define output folder ---------
    output_folder = Path('../mnt/city-directories/02-process-output')

    # Check if elevation raster exists ------------
    if not exists(output_folder / f'{city_name_l}_elevation.tif'):
        print('cannot generate contour lines or elevantion stats because elevation raster does not exist')
        exit()
    
    import os
    import math
    import csv
    import geopandas as gpd
    import numpy as np
    import rasterio
    from osgeo import osr, ogr, gdal


    # CONTOUR ##############################################
    print('generate contour lines')

    try:
        # Open the elevation raster
        rasterDs = gdal.Open(str(output_folder / f'{city_name_l}_elevation.tif'))
        rasterBand = rasterDs.GetRasterBand(1)
        proj = osr.SpatialReference(wkt=rasterDs.GetProjection())

        # Get elevation data as a numpy array
        elevArray = rasterBand.ReadAsArray()

        # Define no-data value
        demNan = -9999

        # Get min and max elevation values
        demMax = elevArray.max()
        demMin = elevArray[elevArray != demNan].min()
        demDiff = demMax - demMin

        # Determine contour intervals
        contourInt = 1
        if demDiff > 250:
            contourInt = math.ceil(demDiff / 500) * 10
        elif demDiff > 100:
            contourInt = 5
        elif demDiff > 50:
            contourInt = 2
        
        contourMin = math.floor(demMin / contourInt) * contourInt
        contourMax = math.ceil(demMax / contourInt) * contourInt

        # Create contour shapefile
        contourPath = str(output_folder / f'{city_name_l}_contour.shp')
        contourDs = ogr.GetDriverByName("ESRI Shapefile").CreateDataSource(contourPath)
        contourShp = contourDs.CreateLayer('contour', proj)

        # Define fields for ID and elevation
        fieldDef = ogr.FieldDefn("ID", ogr.OFTInteger)
        contourShp.CreateField(fieldDef)
        fieldDef = ogr.FieldDefn("elev", ogr.OFTReal)
        contourShp.CreateField(fieldDef)

        # Generate contours
        for level in range(contourMin, contourMax + contourInt, contourInt):
            gdal.ContourGenerate(rasterBand, level, level, [], 1, demNan, contourShp, 0, 1)

        # Clean up
        contourDs.Destroy()
    except:
        print('generate contour lines failed')
    

    # ELEVATION STATS ##############################################
    print('calculate elevation stats')

    try:
        # Calculate equal interval bin edges
        num_bins = 5
        bin_edges = np.linspace(demMin, demMax, num_bins + 1)
        
        # TODO: use max_elev and min_elev to determine rounding
        # Round bin edges to the nearest 1
        bin_edges = np.round(bin_edges, 0)
        
        # Calculate histogram
        hist, _ = np.histogram(elevArray, bins = bin_edges)
        
        # Write bins and hist to a CSV file
        with open(output_folder / f'{city_name_l}_elevation.csv', 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Bin', 'Count'])
            for i, count in enumerate(hist):
                bin_range = f"{int(bin_edges[i])}-{int(bin_edges[i+1])}"
                writer.writerow([bin_range, count])
    except:
        print('calculate elevation stats failed')