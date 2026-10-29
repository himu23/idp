# Example sheets (NOT field data)

Made-up numbers that only show the format of each sheet and let the analysis scripts be tested before the
visit. Every row is marked EXAMPLE. Never copy them into the report as results.

    python ../analysis/discharge_velocity_area.py cross_section.csv float_velocity.csv water_surface_slope.csv
    python ../analysis/manning_cowan.py manning_cowan.csv
    python ../analysis/bridge_clearance.py bridge_inspection.csv 5000
    python ../analysis/soil_gradation.py sieve_analysis.csv atterberg.csv
