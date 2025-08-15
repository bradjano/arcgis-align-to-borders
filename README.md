# Align Polygons to Borders (ArcGIS)
This is a custom ArcGIS geoprocessing tool designed to align administrative boundary polygons. The tool:

1. Aligns the geometry of lower-level administrative boundaries (target dataset) with the geometry of higher-level boundaries (border dataset),
2. Handles single polygon (e.g., single national border) and multipolygon (e.g., first-level administrative borders) inputs as the border dataset, and
3. Optimizes processing based on the inputs.

More documentation will be added to describe the tool in more detail and how it can be used.
## Future enhancements
- Add an option to opt-out of admin name inheritance
- Add a secondary approach for filling polygon gaps for users without the Spatial Analyst extension
- Add pre-run validation in toolbox properties to prevent errors
- Enhance documentation
- Explore an open source alterative for non-ArcGIS users
