# OpenROAD Static Timing Analysis script
# Place & route and timing analysis for ISP-AI pipeline

# Read design
read_verilog ../synth/netlist.v

# Set top module
link_design axi4s_rgb_dw_pw_top

# Initialize floorplan
initialize_floorplan -die_area "0 0 1000 1000" -core_area "50 50 950 950"

# Place macros and standard cells
place_pins -random
global_placement -skip_initial_place
detailed_placement

# Routing
global_route
detailed_route

# Generate reports
report_checks -path_delay min_max -format full_clock_expanded
report_checks -path_delay min_max -format full_clock_expanded > reports/timing.rpt
report_design_area > reports/area.rpt

# Write final design
write_def final.def
write_verilog final.v

puts "Place & Route completed successfully"
puts "Reports generated in reports/ directory"

