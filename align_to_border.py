'''
@author: Bradley Janocha
@collab: N/A
updated: 2025-08-12

Align To Border

'''

import arcpy


# Function to extend the polygons
def extendToBorder(l, gaps, subpolys, border, dissolve_field): # Ingests both polygons,gap file, unique ID field, and border name
    border_buff = r"memory\%s_buff" % l.replace(" ", "_") # Generate name for temp border buff
    arcpy.analysis.PairwiseBuffer(border, border_buff, "20 Kilometers") # Buffer by 20 km to ensure extent beyond the border
    arcpy.env.extent = border_buff # Set processing extent to the buffered border
    arcpy.env.cellSize = 0.005 # Set the cell size of the envrionment
    rast_name = r"memory\%s_rast" % l.replace(" ", "_") # Generate name for temp raster
    arcpy.conversion.FeatureToRaster(subpolys, "OBJECTID", rast_name) # Convert features to raster to extend
    extended_raster = arcpy.sa.DistanceAllocation(rast_name) # Conduct distance allocation to extend polygons as rasters
    extend_name = r"memory\%s_extended" % l.replace(" ", "_") # Generate name for extedned polygon
    arcpy.conversion.RasterToPolygon(extended_raster, extend_name)  # Convert back to polygons
    clipped_name = r"memory\%s_clipped" % l.replace(" ", "_") # Output name for temp clip file
    arcpy.analysis.PairwiseClip(extend_name, gaps, clipped_name) # Clip the poly extensions to the complex gaps
    arcpy.management.JoinField(clipped_name, "gridcode", subpolys, "OBJECTID", dissolve_field) # Add merge field to poly extensions
    return clipped_name # Return the gap fills


# Function to fill the gaps (slivers) between polygons
def fillGaps(l, gaps, subpolys, border, dissolve_field): # Ingests both polygons,gap file, unique ID field, and border name
    gap_join = r"memory/%s_gap_join" % l.replace(" ", "_") # Generate name for spatial join
    arcpy.management.DeleteField(gaps, dissolve_field) # Drop field to simplify the merge
    arcpy.analysis.SpatialJoin(gaps, subpolys, gap_join) # Join the gaps with subpolys to populate the names
    simple_gaps = r"memory/%s_gap_simple" % l.replace(" ", "_")# Name for gaps w/ 1 adjacent poly
    complex_gaps = r"memory/%s_gap_complex" % l.replace(" ", "_")# Name for gaps w/ 2+ adjacent polys
    arcpy.management.MakeFeatureLayer(gap_join, simple_gaps, "Join_Count = 1") # Select gaps w/ 1 adjacent poly for an easy merge
    arcpy.management.MakeFeatureLayer(gap_join, complex_gaps, "Join_Count > 1") # Select gaps w/ 2+ adjacent polys
    dissolve_name = r"memory/%s_dissolve" % l.replace(" ", "_") # Generate dissolve name
    poly_extended = extendToBorder(l, complex_gaps, subpolys, border, dissolve_field) # Convert to raster and extend
    combo_name = r"memory/%s_combo" % l.replace(" ", "_") # Output name for temp merge file
    arcpy.management.Merge([subpolys, simple_gaps, poly_extended], combo_name) # Merge the gaps and polygons to align
    arcpy.management.Dissolve(combo_name, dissolve_name, dissolve_field) # Dissolve the gaps into the polygons based on unique ID
    border_clip_name = r"memory/%s_border_clip" % l.replace(" ", "_") # Output name for temp clipped file
    arcpy.analysis.Clip(dissolve_name, border, border_clip_name) # Clip to the boundary to prevent overlap of surrounded units
    arcpy.AddMessage("Processing complete for %s." % l)
    return border_clip_name # Return the aligned polys


# Function to check for gaps (slivers) between the polygons
def checkForGaps(l, subpolys, border, dissolve_field): # Ingests border name, both polygons, and the unique ID field
    union_file = r"memory/%s_union" % l.replace(" ", "_") # Create filename for temporary union file
    union_poly = arcpy.analysis.Union([subpolys, border], union_file, join_attributes="ALL", gaps="NO_GAPS") # Run union tool to identify gaps
    query = "%s = ''" % dissolve_field # Query to identify gaps
    arcpy.management.MakeFeatureLayer(union_poly,"gaps", query) # Select where the subpoly field name is empty
    gap_file = r"memory/%s_gaps" % l.replace(" ", "_") # Output name for temp gap file
    arcpy.management.MultipartToSinglepart("gaps", gap_file) # Explode multipart gap polygon
    gap_count = arcpy.management.GetCount(gap_file) # Count the gaps
    if gap_count == 0: # If no gaps, don't try and fill them
        arcpy.AddWarning("No gaps were found in %s." % l) # Warn the user since this is rare
        return subpolys # Return without running any gaps
    else: # If there are gaps, fill them
        filled = fillGaps(l, gap_file, subpolys, border, dissolve_field) # Run the fill function to fill the gaps
        return filled # Return the resulting polygon


# Function to list the border names
def listFieldValues(fc, field): # Ingests the border feature class and field name
    cursor = arcpy.da.SearchCursor(fc, [field]) # Create search cursor for passed field
    field_values = [] # Init empty list to store field values
    for row in cursor: # Loop through the cursor
        field_values.append(row[0]) # Append the first item in the current field
    return field_values # Return the list of border names


# Function to populate the matching field with aligned border names
def alignMatchNames(b, b_field, a, a_field, dissolve_field): # Ingests both polygons and field name parameters
    ab_join = r"memory/ab_join" # Output name for temp join
    arcpy.analysis.SpatialJoin(a, b, ab_join, match_option="LARGEST_OVERLAP") # Join the border to the polygons to align based on largest overlap
    calc_query = "!%s!" % b_field # Format the border field for the calculate field operation
    arcpy.management.CalculateField(ab_join, a_field, calc_query) # Replace match field with boundary's values
    all_a_fields = [] # Make a list of all original field names
    for f in arcpy.ListFields(a): # Loop through the field names
        all_a_fields.append(f.name) # Append the field names to the list
    for f in arcpy.ListFields(ab_join): # Loop through current fields
        if f.name in all_a_fields: # If the fieldname is in original list, pass
            pass
        else: # Otherwise delete the field
            arcpy.management.DeleteField(ab_join, f.name) # Remove extra fields from join
    return ab_join # Return the adjusted feature class


# Primary function that will call the other functions
def alignToBorder(b, ml, b_field, a, a_field, dissolve_field, out): # Ingests all parameters from the user

    # Begin by clipping the file to remove any overlaps
    clip_file = r"memory/clip_file" # Output name for temp clipped file
    arcpy.analysis.Clip(a, b, clip_file) # Clip polygons to align to the border feature class

    # Single level border alignment
    if ml == 'false': # If the input has a single border to align to
        
        aligned = checkForGaps("NoLvl", clip_file, b, dissolve_field) # Check for and address gaps after clip
        arcpy.management.CopyFeatures(aligned, "TEMPFILE") # Copy the returned features to modify the attribute table
        a_table = r"memory/a_table" # Output name for temp align polys table
        arcpy.conversion.ExportTable(a, a_table) # Create table for align polys to be used later for attribute regen
        arcpy.management.DeleteField(a, dissolve_field, "KEEP_FIELDS") # Delete all unecessary fields to simplify attribute cleanup

    # Multi-border alignment
    else: # If it's a multi-border polygon
        
        arcpy.AddMessage("Aligning polygons to multiple borders...")
        shape_list = [] # Initialize empty list for the aligned subpolygon subsets

        # Reassign border names in the polygon to align
        b_copy = r"memory/b_copy" # Output name for temp border copy
        arcpy.management.CopyFeatures(b, b_copy) # Copy border features to mod attribute table (simplifies cleanup later)
        calc_query = "!%s!" % b_field # Format the border field for the calculate field operation
        arcpy.management.AddField(b_copy, "MATCHFIELD", "TEXT") # Add a new field with diff name to make it easier to remove
        arcpy.management.CalculateField(b_copy, "MATCHFIELD", calc_query) # Fill field with border names
        arcpy.management.DeleteField(b_copy, "MATCHFIELD", "KEEP_FIELDS") # Delete all other fields to simplify cleanup
        a_prepared = alignMatchNames(b_copy, "MATCHFIELD", clip_file, a_field, dissolve_field) # Pull border names into the polygon to align (reassign to align)

        # Prep table to regen attributes in poly to align
        a_table = r"memory/a_table" # Output name for temp align polys table
        arcpy.conversion.ExportTable(a_prepared, a_table) # Create table for align polys to be used later for attribute regen
        arcpy.management.DeleteField(a_prepared, [a_field, dissolve_field], "KEEP_FIELDS") # Delete unecessary fields

        # Loop through the borders and align
        lvl_names = listFieldValues(b, b_field) # Create a list of border values
        for l in lvl_names: # Loop through the list of borders
            
            # Prep border
            border_name = r"memory/%s_border" % l.replace(" ", "_") # Temp file for the queried border poly
            border_query = "MATCHFIELD = '%s'" % l # Query for border selection
            arcpy.management.MakeFeatureLayer(b_copy, border_name, border_query) # Extract border to its own feature class
            
            # Prep subpolys
            subpoly_name = "%s_subpolys" % l.replace(" ", "_") # Temp file for the queried polygons to align
            subpoly_query = "%s = '%s'" %(a_field, l) # Query for subpolygon selection
            arcpy.management.MakeFeatureLayer(a_prepared, subpoly_name, subpoly_query) # Select subpolygons to align
            aligned = checkForGaps(l, subpoly_name, border_name, dissolve_field) # Check for and address gaps after clip
            shape_list.append(aligned) # Append the aligned shape to the list (for later merge)
            arcpy.env.extent = b # Reset processing extent

        arcpy.management.Merge(shape_list, "TEMPFILE") # Merge the aligned subploygon subsets

    # Regen the original fields in the polygons to align (but with new match field vals)
    arcpy.management.AlterField("TEMPFILE", dissolve_field, "TEMPFIELD", "TEMPFIELD") # Rename unique ID field to simplify join and later removal
    join_file = arcpy.management.AddJoin("TEMPFILE", "TEMPFIELD", a_table, dissolve_field) # Join with original data
    arcpy.management.CopyFeatures(join_file, out) # Generate the output file
    arcpy.management.DeleteField(out, ["TEMPFILE_TEMPFIELD", "a_table_OBJECTID", "a_table_Shape_Leng"]) # Remove duplicate fields from join
    arcpy.management.Delete("TEMPFILE") # Delete the temporary feature class
    
    
if __name__ == "__main__":

    # Set parameters
    arcpy.CheckOutExtension("Spatial") # Check out spatial analyst
    arcpy.env.workspace = arcpy.GetParameterAsText(0) # GDB or folder where files are stored
    arcpy.env.overwriteOutput = True
    border_poly = arcpy.GetParameterAsText(1) # Polygon to which the underlying polgyons will be aligned
    multi_border = arcpy.GetParameterAsText(2) # Boolean indicating if there are multiple borders to align to (e.g. regions or states)
    border_names = arcpy.GetParameterAsText(3) # Field containing names when aligning to multiple borders
    align_poly = arcpy.GetParameterAsText(4) # Polygon that will be aligned to the border polygon
    align_names = arcpy.GetParameterAsText(5) # Field where the new, aligned border names will be stored
    dissolve_field = arcpy.GetParameterAsText(6) # This is the unique ID field used to dissolve the polygons and gaps
    out_name = arcpy.GetParameterAsText(7) # This is the name of the output file
        
    # Run the tool and close out
    arcpy.management.ClearWorkspaceCache() # Clear the cache of any temp files before the run
    alignToBorder(border_poly, multi_border, border_names, align_poly, align_names, dissolve_field, out_name) # Initiate main function
    arcpy.management.ClearWorkspaceCache() # Clear the cache of any temp files after the run
    arcpy.CheckInExtension("Spatial") # Check in spatial analyst
    
