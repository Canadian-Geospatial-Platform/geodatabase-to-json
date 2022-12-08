# -------------------------------------------------------------------------------
# Name:         GeoDatabase to single polygon coverage
# Purpose:      The purpose of this tool is to download a geodatabase contained
#               in a zipfile, unzip it, for each feature class: points, lines
#               and polygons, create a polygon representation and append it to
#               a shapefile that holds all polygons coverages.  From there the
#               tool will merge all polygons together and then performa multi-
#               part to single part to ensure that each polygon is seperate and
#               no multi-part features exist. This is a small part of a greater
#               tool that will search through a spatial catalogue and make
#               polygon features representing the spatial coverage of each
#               dataset or service in the catalogue.  This is used to provide
#               a library of geometry for search and discovery purposes on
#               GEO.CA
#
# Author:       Sean
#
# Created:      30-04-2021
# Copyright:    (c) seagles 2021
# Licence:      Open Data License
# -------------------------------------------------------------------------------

from urllib.request import urlopen
from contextlib import closing
import requests
import zipfile
import arcpy
import os
import sys


# module to download zip files
# senderle from Stackoverflow.com March 8, 2020
def download_url(url, save_path):
    with closing(urlopen(url)) as dl_file:
        with open(save_path, 'wb') as out_file:
            out_file.write(dl_file.read())


# module for listing all feature classes within a given geodatabase
def listFcsInGDB(gdb):
    arcpy.env.workspace = gdb
    print("Processing ", arcpy.env.workspace)

    fcs = []
    for fds in arcpy.ListDatasets('', 'feature') + ['']:
        for fc in arcpy.ListFeatureClasses('', '', fds):
            # yield os.path.join(fds, fc)
            fcs.append(os.path.join(fds, fc))
    return fcs


def polygonTransform(FeatureClass):
    # set polygons which will be used to dissolve and create multipart
    # polygons in a single shapefile
    #
    dissolved = FeatureClass + "_dissolved"
    singlepart = FeatureClass + "_finished"

    # add field "merge"
    #
    arcpy.AddField_management(
        in_table=FeatureClass,
        field_name="MERGE",
        field_type="TEXT",
        field_precision="",
        field_scale="",
        field_length="5",
        field_alias="",
        field_is_nullable="NULLABLE",
        field_is_required="NON_REQUIRED",
        field_domain="")

    print("Field Added")

    # calculate the merge field to value 1, so that every polygon is
    # a value of 1
    arcpy.CalculateField_management(
        in_table=FeatureClass,
        field="MERGE",
        expression="1",
        expression_type="PYTHON3",
        code_block="")

    print("Field Calculated")

    # dissolve based on the value 1 in 'merge' field
    #
    arcpy.Dissolve_management(
        in_features=FeatureClass,
        out_feature_class=dissolved,
        dissolve_field="MERGE",
        statistics_fields="",
        multi_part="MULTI_PART",
        unsplit_lines="DISSOLVE_LINES")

    print("Features Dissolved")

    # similar to the explode tool, take all of the multipart polygons
    # and create single part polygons that are separate when not
    # attached to another polygon
    #
    arcpy.MultipartToSinglepart_management(
        in_features=dissolved,
        out_feature_class=singlepart)

    print("Multi part to single part explosion")

    # Append the result into the shapefile that has all appended
    # polygons
    #
    arcpy.Append_management(
        inputs=singlepart,
        target=ShapefileAll,
        schema_type="NO_TEST",
        field_mapping="", subtype="")


def pointTransform(FeatureClass):
    # name buffer and singlepart polygons to be created
    #
    buffer = FeatureClass + "_buffer"
    singlepart = FeatureClass + "_finished"

    # perform a buffer in the existing points which is one multipart
    # feature
    #
    arcpy.Buffer_analysis(
        in_features=FeatureClass,
        out_feature_class=buffer,
        buffer_distance_or_field="5 Kilometers",
        line_side="FULL", line_end_type="ROUND",
        dissolve_option="ALL", dissolve_field="",
        method="PLANAR")

    print("Buffer created for points - " + buffer)

    # take the multipart polygon created by the dissolve and explode
    # all of the polygons into singlepart features
    #
    arcpy.MultipartToSinglepart_management(
        in_features=buffer,
        out_feature_class=singlepart)

    print("Multi part to single part explosion")

    # append the finalized polygons into one master shapefile
    #
    arcpy.Append_management(
        inputs=singlepart,
        target=ShapefileAll,
        schema_type="NO_TEST",
        field_mapping="",
        subtype="")


def polylineTransform(FeatureClass):
    # create a name for the buffer and singlepart polygons to be created
    #
    buffer = FeatureClass + "_buffer"
    dissolved = FeatureClass + "_dissolved"
    singlepart = FeatureClass + "_finished"

    # run buffer on the feature class to create a polygon feature class
    #
    arcpy.Buffer_analysis(
        in_features=FeatureClass,
        out_feature_class=buffer,
        buffer_distance_or_field="5000 Meters",
        line_side="FULL", line_end_type="ROUND",
        dissolve_option="NONE", dissolve_field="",
        method="PLANAR")

    print("Buffer created for points - " + buffer)

    # add a field called "merge"
    #
    arcpy.AddField_management(
        in_table=buffer,
        field_name="MERGE",
        field_type="TEXT",
        field_precision="",
        field_scale="",
        field_length="5",
        field_alias="",
        field_is_nullable="NULLABLE",
        field_is_required="NON_REQUIRED",
        field_domain="")

    # calculate the merge field to value 1
    #
    arcpy.CalculateField_management(
        in_table=buffer,
        field="MERGE",
        expression="1",
        expression_type="PYTHON3",
        code_block="")

    print("Field Calculated")

    # dissolve the polygons based on the merge value of 1 creating one
    # multipart polygon
    #
    arcpy.Dissolve_management(
        in_features=buffer,
        out_feature_class=dissolved,
        dissolve_field="MERGE",
        statistics_fields="",
        multi_part="MULTI_PART",
        unsplit_lines="DISSOLVE_LINES")

    print("Features Dissolved")

    # similar to the explode tool, take the multipart polygon that was
    # created and make it into singlepart seperate polygons
    #
    arcpy.MultipartToSinglepart_management(
        in_features=dissolved,
        out_feature_class=singlepart)

    print("Multi part to single part explosion")

    # append the new polyons into the shapefile which contains all
    # polygons
    #
    arcpy.Append_management(
        inputs=singlepart,
        target=ShapefileAll,
        schema_type="NO_TEST",
        field_mapping="",
        subtype="")


def prepJSON(Shapefile):
    Shapefile = ShapefileAll
    print(Shapefile)
    dissolve = folder + "\\" + ShapefileBaseName + "_dissolve.shp"
    print(dissolve)
    singlepart = folder + "\\" + ShapefileBaseName + "_singlepart.shp"
    print(singlepart)
    # now work on the master shapefile
    # add a field called "merge"
    #
    arcpy.AddField_management(
        in_table=ShapefileAll,
        field_name="MERGE",
        field_type="TEXT",
        field_precision="",
        field_scale="",
        field_length="5",
        field_alias="",
        field_is_nullable="NULLABLE",
        field_is_required="NON_REQUIRED",
        field_domain="")

    print("Field Added")

    # calculate the merge field to value 1
    #
    arcpy.CalculateField_management(
        in_table=ShapefileAll,
        field="MERGE",
        expression="1",
        expression_type="PYTHON3",
        code_block="")

    print("Field Calculated")

    # dissolve the polygons based on the merge value of 1 creating one
    # multipart polygon
    #
    arcpy.Dissolve_management(
        in_features=ShapefileAll,
        out_feature_class=dissolve,
        dissolve_field="MERGE",
        statistics_fields="",
        multi_part="MULTI_PART",
        unsplit_lines="DISSOLVE_LINES")

    print("Features Dissolved")

    # take the dissolved polygon and explode the single polygon into singlepart
    # polygons
    #
    singlepart = "C:/TEMP/MAP_Selection_Finished.shp"
    arcpy.MultipartToSinglepart_management(
        in_features=ShapefileAll,
        out_feature_class=singlepart)

    print("Multi part to single part explosion")

    # Add a field to count vertices "vertices"
    #
    arcpy.AddField_management(
        in_table=singlepart,
        field_name="VERTICES",
        field_type="FLOAT",
        field_precision="255",
        field_scale="0",
        field_length="",
        field_alias="",
        field_is_nullable="NULLABLE",
        field_is_required="NON_REQUIRED", field_domain="")

    print("Added field VERTICES")

    # Calculate the vertices field with a count of vertices in that polygon
    #
    arcpy.CalculateField_management(
        singlepart,
        "VERTICES",
        "!Shape!.pointCount-!Shape!.partCount",
        "PYTHON")

    print("Calculate the amount of vertices in VERTICES field")

    # print the count of all polygons found within the master shapefile
    #
    PolygonCounter = 0
    with arcpy.da.SearchCursor(singlepart, "MERGE") as cursor:
        for row in cursor:
            PolygonCounter = PolygonCounter + 1
    print("There are " + str(PolygonCounter) + " polygons")
    del row, cursor, PolygonCounter

    # create an ESRI GeoJSON for the master shapefile to be used to load into
    # GeoCore
    #
    arcpy.FeaturesToJSON_conversion(
        in_features=singlepart,
        out_json_file="C:/TEMP/IPN_FeaturesToJSON.json",
        format_json="FORMATTED",
        include_z_values="NO_Z_VALUES",
        include_m_values="NO_M_VALUES",
        geoJSON="GEOJSON")

    print("ESRI JSON created")
    '''
    arcpy.Delete_management(gdb)
    print("Deleted Geodatabase")
    arcpy.Delete_management(save_path)
    print("Deleted zip file")
    arcpy.Delete_management(dissolve)
    print("Deleted dissolved polygon shapefile")
    arcpy.Delete_management(singlepart)
    print("Deleted singlepart polygon shapefile")
    arcpy.Delete_management(ShapefileAll)
    print("Deleted master shapefile")
    '''

if __name__ == '__main__':

    # set the url that needs to be downloaded
    #
    url = 'http://ftp.maps.canada.ca/pub/statcan_statcan/Census_Recensement/census_subdivisions_2016/census_subdivisions_2016_en.gdb.zip'
    # url = 'https://ftp.maps.canada.ca/pub/nrcan_rncan/Aboriginal-languages_Langue-autochtone/indigenous_place_names_2019/indigenous_place_names.gdb.zip'

    # set the path to save the zip file (needs to be dynamic later)
    #
    save_path = r"C:\TEMP\download.zip"

    # download the url to the save path
    #
    download_url(url, save_path)
    print("zip file downloaded to: " + save_path)
    # set folder for extraction
    #
    folder = r"C:\TEMP"
    # unzip the zipfile to the folder location
    with zipfile.ZipFile(save_path, 'r') as zip_ref:
        zip_ref.extractall(folder)
    print("Zip file folder extracted to: " + folder)

    # set the geodatabasee (this needs to be dynamic in future)
    #
    # gdb = "C:\TEMP\indigenous_place_names.gdb"
    gdb = r"C:\TEMP\census_subdivisions_2016_en.gdb"
    # set the shapefile up for creation where all polygons will be appended
    # also create the polygon
    ShapefileName = "IPN.shp"
    ShapefileBaseName = "IPN"
    ShapefileAll = folder + "\\" + ShapefileName
    arcpy.CreateFeatureclass_management(
        out_path=folder,
        out_name=ShapefileName,
        geometry_type="POLYGON",
        template="",
        has_m="DISABLED",
        has_z="DISABLED",
        spatial_reference="GEOGCS['GCS_WGS_1984',DATUM['D_WGS_1984',SPHEROID['WGS_1984',6378137.0,298.257223563]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]];-400 -400 1000000000;-100000 10000;-100000 10000;8.98315284119522E-09;0.001;0.001;IsHighPrecision", config_keyword="", spatial_grid_1="0", spatial_grid_2="0", spatial_grid_3="0")

    print("Shapefile created to hold all finished polygons: " + ShapefileName)

    # list all feature classes within the geodatabase
    #
    fcs = listFcsInGDB(gdb)

    # Cycle through all feature classes in the geodatabase
    #
    print("Cycle through feature classes in geodatabase")
    for fc in fcs:
        # set feature class location and name
        #
        FeatureClass = gdb + "\\" + fc
        print("Feature class: " + FeatureClass)

        # Describe a feature class
        #
        desc = arcpy.Describe(FeatureClass)

        # Get the shape type (Polygon, Polyline) of the feature class
        #
        fcType = desc.shapeType

        print(fcType)
        # If the type is polygon run through these instructions
        #
        if fcType == "Polygon":
            polygonTransform(FeatureClass)

        # run these instructions if type is point
        #
        elif fcType == "Point":
            pointTransform(FeatureClass)

        # run these instructions if type is polyline
        #
        elif fcType == "Polyline":
            polylineTransform(FeatureClass)

    prepJSON(ShapefileAll)

sys.exit()
