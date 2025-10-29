# OpenROAD Place & Route Makefile
# Requires OpenROAD installation

.PHONY: all clean reports

# Default target
all: reports

# Create reports directory
reports:
	mkdir -p reports

# Run place & route
sta: reports
	openroad -exit sta.tcl

# Generate timing and area reports
reports: sta
	@echo "Place & Route completed"
	@echo "Reports available in reports/ directory"

# Clean generated files
clean:
	rm -rf reports/
	rm -f *.def *.v *.log
	rm -f final.def final.v

# Help target
help:
	@echo "Available targets:"
	@echo "  all     - Run place & route and generate reports"
	@echo "  sta     - Run static timing analysis"
	@echo "  reports - Generate timing and area reports"
	@echo "  clean   - Remove generated files"
	@echo "  help    - Show this help message"

