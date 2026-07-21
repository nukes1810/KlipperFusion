# sentient_first_layer.py
# Sentient Project - https://github.com/nukes1810/sentient
#
# Automatic first layer Z offset calibration using Cartographer bed mesh.
# Prints a small calibration square, scans it, calculates actual layer
# height, adjusts Z offset, and saves per-filament offsets automatically.
#
# Usage in printer.cfg:
#   [sentient_first_layer]
#   calibration_x: 30        # X position for calibration square
#   calibration_y: 30        # Y position for calibration square
#   calibration_size: 40     # Size of calibration square in mm
#   calibration_speed: 1200  # Print speed for calibration square mm/min
#   scan_speed: 300          # Scan speed mm/min
#   iterations: 3            # Number of calibration iterations
#   tolerance: 0.01          # Acceptable error in mm
#
# Gcode commands exposed:
#   SENTIENT_CALIBRATE_Z FILAMENT=ASA   - full calibration for filament
#   SENTIENT_SCAN_LAYER                 - scan current surface
#   SENTIENT_SET_FILAMENT_OFFSET FILAMENT=ASA OFFSET=-0.365
#   SENTIENT_GET_FILAMENT_OFFSET FILAMENT=ASA
#   SENTIENT_APPLY_FILAMENT_OFFSET FILAMENT=ASA
#   SENTIENT_STATUS                     - show all saved offsets

import logging
import math

# Target squish heights per filament type
# These are the ACTUAL layer heights we want after squish
# Lower = more squish = better adhesion
FILAMENT_TARGETS = {
    'PLA':  0.18,
    'PETG': 0.19,
    'ASA':  0.17,
    'ABS':  0.17,
    'TPU':  0.19,
    'PA':   0.17,
    'PC':   0.17,
    'default': 0.18,
}

class SentientFirstLayer:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.config = config
        self.gcode = self.printer.lookup_object('gcode')
        self.logger = logging.getLogger('sentient_first_layer')

        # Configuration
        self.cal_x = config.getfloat('calibration_x', 30.0)
        self.cal_y = config.getfloat('calibration_y', 30.0)
        self.cal_size = config.getfloat('calibration_size', 40.0)
        self.cal_speed = config.getfloat('calibration_speed', 1200.0)
        self.scan_speed = config.getfloat('scan_speed', 300.0)
        self.iterations = config.getint('iterations', 3)
        self.tolerance = config.getfloat('tolerance', 0.01)
        self.layer_height = config.getfloat('layer_height', 0.20)

        # State
        self.baseline_mesh = None
        self.saved_offsets = {}
        self.current_filament = 'PLA'
        self.calibrating = False

        # Register gcode commands
        self.gcode.register_command(
            'SENTIENT_CALIBRATE_Z',
            self.cmd_SENTIENT_CALIBRATE_Z,
            desc="Calibrate Z offset for a specific filament"
        )
        self.gcode.register_command(
            'SENTIENT_SCAN_LAYER',
            self.cmd_SENTIENT_SCAN_LAYER,
            desc="Scan current surface and report height"
        )
        self.gcode.register_command(
            'SENTIENT_SET_FILAMENT_OFFSET',
            self.cmd_SENTIENT_SET_FILAMENT_OFFSET,
            desc="Manually set Z offset for a filament"
        )
        self.gcode.register_command(
            'SENTIENT_GET_FILAMENT_OFFSET',
            self.cmd_SENTIENT_GET_FILAMENT_OFFSET,
            desc="Get saved Z offset for a filament"
        )
        self.gcode.register_command(
            'SENTIENT_APPLY_FILAMENT_OFFSET',
            self.cmd_SENTIENT_APPLY_FILAMENT_OFFSET,
            desc="Apply saved Z offset for a filament"
        )
        self.gcode.register_command(
            'SENTIENT_STATUS',
            self.cmd_SENTIENT_STATUS,
            desc="Show all saved filament Z offsets"
        )
        self.gcode.register_command(
            'SENTIENT_SAVE_BASELINE',
            self.cmd_SENTIENT_SAVE_BASELINE,
            desc="Save current bed mesh as baseline for comparison"
        )

        # Load saved offsets from save_variables if available
        self.printer.register_event_handler(
            'klippy:connect', self._handle_connect
        )

        self.logger.info("sentient_first_layer loaded")

    def _handle_connect(self):
        """Load saved offsets from persistent storage on connect"""
        try:
            save_variables = self.printer.lookup_object('save_variables')
            svv = save_variables.allVariables()
            for key, value in svv.items():
                if key.startswith('sentient_z_offset_'):
                    filament = key.replace('sentient_z_offset_', '').upper()
                    self.saved_offsets[filament] = float(value)
                    self.logger.info(
                        "Loaded offset for %s: %.3f" % (filament, float(value))
                    )
        except Exception as e:
            self.logger.warning("Could not load saved offsets: %s" % str(e))

    def _save_offset(self, filament, offset):
        """Save a filament Z offset to persistent storage"""
        filament = filament.upper()
        self.saved_offsets[filament] = offset
        try:
            save_variables = self.printer.lookup_object('save_variables')
            key = 'sentient_z_offset_%s' % filament.lower()
            save_variables.cmd_SAVE_VARIABLE(
                self.gcode.create_gcode_command(
                    'SAVE_VARIABLE',
                    'SAVE_VARIABLE',
                    {'VARIABLE': key, 'VALUE': '%.4f' % offset}
                )
            )
            self.logger.info(
                "Saved Z offset for %s: %.3f" % (filament, offset)
            )
        except Exception as e:
            self.logger.warning("Could not save offset: %s" % str(e))

    def _get_bed_mesh(self):
        """Get current bed mesh object"""
        try:
            return self.printer.lookup_object('bed_mesh')
        except Exception:
            return None

    def _get_mesh_average(self, mesh_obj):
        """Calculate average height from bed mesh data"""
        try:
            if mesh_obj is None:
                return None
            mesh = mesh_obj.get_mesh()
            if mesh is None:
                return None
            # Get the mesh matrix
            z_matrix = mesh.get_z_matrix()
            if not z_matrix:
                return None
            total = 0.0
            count = 0
            for row in z_matrix:
                for val in row:
                    total += val
                    count += 1
            if count == 0:
                return None
            return total / count
        except Exception as e:
            self.logger.warning("Could not get mesh average: %s" % str(e))
            return None

    def _get_toolhead_position(self):
        """Get current toolhead position"""
        toolhead = self.printer.lookup_object('toolhead')
        return toolhead.get_position()

    def _run_gcode(self, gcode_str):
        """Run a gcode string"""
        self.gcode.run_script_from_command(gcode_str)

    def _get_current_z_offset(self):
        """Get current Z gcode offset"""
        try:
            gcode_move = self.printer.lookup_object('gcode_move')
            return gcode_move.get_status(None)['homing_origin'][2]
        except Exception:
            return 0.0

    def _apply_z_offset(self, offset):
        """Apply a Z gcode offset"""
        self._run_gcode("SET_GCODE_OFFSET Z=%.4f MOVE=1" % offset)

    def cmd_SENTIENT_CALIBRATE_Z(self, gcmd):
        """Full automatic Z offset calibration for a filament"""
        filament = gcmd.get('FILAMENT', 'PLA').upper()
        bed_temp = gcmd.get_float('BED_TEMP', None)
        nozzle_temp = gcmd.get_float('NOZZLE_TEMP', None)
        iterations = gcmd.get_int('ITERATIONS', self.iterations)

        target = FILAMENT_TARGETS.get(filament, FILAMENT_TARGETS['default'])

        gcmd.respond_info(
            "=== sentient Z Offset Calibration ===\n"
            "Filament:      %s\n"
            "Target height: %.2fmm\n"
            "Iterations:    %d\n"
            "Tolerance:     ±%.3fmm" % (
                filament, target, iterations, self.tolerance
            )
        )

        self.calibrating = True
        self.current_filament = filament

        # Heat up if temps provided
        if bed_temp is not None:
            gcmd.respond_info("Heating bed to %.0f°C..." % bed_temp)
            self._run_gcode("M190 S%.0f" % bed_temp)
        if nozzle_temp is not None:
            gcmd.respond_info("Heating nozzle to %.0f°C..." % nozzle_temp)
            self._run_gcode("M109 S%.0f" % nozzle_temp)

        # Home and prepare
        gcmd.respond_info("Homing and leveling...")
        self._run_gcode("G28")
        self._run_gcode("Z_TILT_ADJUST")

        # Save baseline mesh (bare bed)
        gcmd.respond_info("Scanning bare bed baseline...")
        self._run_gcode("BED_MESH_CALIBRATE")

        bed_mesh = self._get_bed_mesh()
        baseline_avg = self._get_mesh_average(bed_mesh)
        if baseline_avg is not None:
            self.baseline_mesh = baseline_avg
            gcmd.respond_info(
                "Baseline average height: %.4fmm" % baseline_avg
            )
        else:
            gcmd.respond_info(
                "Warning: Could not read baseline mesh. "
                "Proceeding with visual calibration only."
            )

        # Calibration iterations
        best_offset = self._get_current_z_offset()

        for i in range(iterations):
            gcmd.respond_info(
                "--- Iteration %d of %d ---" % (i + 1, iterations)
            )

            # Print calibration square
            gcmd.respond_info("Printing calibration square...")
            self._print_calibration_square()

            # Wait for layer to partially cool and stabilize
            gcmd.respond_info("Waiting for layer to stabilize (5s)...")
            self._run_gcode("G4 P5000")

            # Scan the printed layer
            gcmd.respond_info("Scanning first layer...")
            self._run_gcode("BED_MESH_CALIBRATE")

            bed_mesh = self._get_bed_mesh()
            layer_avg = self._get_mesh_average(bed_mesh)

            if layer_avg is not None and self.baseline_mesh is not None:
                actual_height = layer_avg - self.baseline_mesh
                error = actual_height - target
                gcmd.respond_info(
                    "Actual layer height: %.3fmm\n"
                    "Target:             %.3fmm\n"
                    "Error:              %+.3fmm" % (
                        actual_height, target, error
                    )
                )

                if abs(error) <= self.tolerance:
                    gcmd.respond_info(
                        "✓ Within tolerance! Z offset is perfect."
                    )
                    break
                else:
                    # Calculate correction
                    # If layer is too thick (positive error) = nozzle too far = lower Z offset
                    # If layer is too thin (negative error) = nozzle too close = raise Z offset
                    correction = error * -1.0
                    new_offset = best_offset + correction
                    gcmd.respond_info(
                        "Applying correction: %+.3fmm\n"
                        "New Z offset: %.3f" % (correction, new_offset)
                    )
                    self._apply_z_offset(new_offset)
                    best_offset = new_offset
            else:
                gcmd.respond_info(
                    "Could not read mesh data. "
                    "Check Cartographer connection and try again."
                )

            # Clear calibration area for next iteration
            if i < iterations - 1:
                gcmd.respond_info("Clearing calibration area...")
                self._clear_calibration_area()

        # Save the final offset
        final_offset = self._get_current_z_offset()
        self._save_offset(filament, final_offset)

        gcmd.respond_info(
            "=== Calibration Complete ===\n"
            "Filament: %s\n"
            "Z Offset: %.4f\n"
            "Saved to filament profile automatically.\n"
            "This offset will be applied automatically on future prints." % (
                filament, final_offset
            )
        )

        self.calibrating = False

    def _print_calibration_square(self):
        """Print a small filled calibration square"""
        x = self.cal_x
        y = self.cal_y
        size = self.cal_size
        speed = self.cal_speed
        lh = self.layer_height

        # Move to start position
        self._run_gcode("G90")
        self._run_gcode("G1 X%.2f Y%.2f F6000" % (x, y))
        self._run_gcode("G1 Z%.3f F300" % lh)
        self._run_gcode("G92 E0")

        # Outer perimeter
        e_per_mm = 0.04  # approximate extrusion per mm for 0.4mm nozzle
        extrusion = 0.0

        moves = [
            (x + size, y),
            (x + size, y + size),
            (x, y + size),
            (x, y),
        ]

        for tx, ty in moves:
            dx = tx - x
            dy = ty - y
            dist = math.sqrt(dx*dx + dy*dy)
            extrusion += dist * e_per_mm
            self._run_gcode(
                "G1 X%.2f Y%.2f E%.4f F%.0f" % (tx, ty, extrusion, speed)
            )
            x, y = tx, ty

        # Reset x,y to start
        x = self.cal_x
        y = self.cal_y

        # Fill with parallel lines (every 3mm)
        line_spacing = 3.0
        current_y = y + line_spacing
        direction = 1

        while current_y < y + size - line_spacing:
            if direction == 1:
                # Left to right
                self._run_gcode("G1 X%.2f Y%.2f F6000" % (x, current_y))
                extrusion += size * e_per_mm
                self._run_gcode(
                    "G1 X%.2f Y%.2f E%.4f F%.0f" % (
                        x + size, current_y, extrusion, speed
                    )
                )
            else:
                # Right to left
                self._run_gcode(
                    "G1 X%.2f Y%.2f F6000" % (x + size, current_y)
                )
                extrusion += size * e_per_mm
                self._run_gcode(
                    "G1 X%.2f Y%.2f E%.4f F%.0f" % (
                        x, current_y, extrusion, speed
                    )
                )
            current_y += line_spacing
            direction *= -1

        # Lift and reset
        self._run_gcode("G92 E0")
        self._run_gcode("G1 Z5 F3000")

    def _clear_calibration_area(self):
        """Move away from calibration area (user removes material)"""
        # Park toolhead away from calibration area
        self._run_gcode("G1 Z20 F3000")
        self._run_gcode(
            "G1 X%.2f Y%.2f F6000" % (
                self.cal_x + self.cal_size + 20,
                self.cal_y
            )
        )
        # In a real implementation this would pause for user to clean
        # For now just wait 2 seconds
        self._run_gcode("G4 P2000")

    def cmd_SENTIENT_SCAN_LAYER(self, gcmd):
        """Scan current surface and report height vs baseline"""
        gcmd.respond_info("Scanning surface...")
        self._run_gcode("BED_MESH_CALIBRATE")

        bed_mesh = self._get_bed_mesh()
        mesh_avg = self._get_mesh_average(bed_mesh)

        if mesh_avg is not None:
            if self.baseline_mesh is not None:
                actual_height = mesh_avg - self.baseline_mesh
                gcmd.respond_info(
                    "Surface scan results:\n"
                    "Mesh average:    %.4fmm\n"
                    "Baseline:        %.4fmm\n"
                    "Layer height:    %.4fmm" % (
                        mesh_avg, self.baseline_mesh, actual_height
                    )
                )
            else:
                gcmd.respond_info(
                    "Surface scan: %.4fmm\n"
                    "(No baseline saved - run SENTIENT_SAVE_BASELINE first)" %
                    mesh_avg
                )
        else:
            gcmd.respond_info(
                "Could not read mesh data. Check Cartographer connection."
            )

    def cmd_SENTIENT_SAVE_BASELINE(self, gcmd):
        """Save current mesh as baseline"""
        bed_mesh = self._get_bed_mesh()
        avg = self._get_mesh_average(bed_mesh)
        if avg is not None:
            self.baseline_mesh = avg
            gcmd.respond_info(
                "Baseline saved: %.4fmm average height" % avg
            )
        else:
            gcmd.respond_info(
                "No mesh data available. Run BED_MESH_CALIBRATE first."
            )

    def cmd_SENTIENT_SET_FILAMENT_OFFSET(self, gcmd):
        """Manually set and save a filament Z offset"""
        filament = gcmd.get('FILAMENT', 'PLA').upper()
        offset = gcmd.get_float('OFFSET', 0.0)
        self._save_offset(filament, offset)
        gcmd.respond_info(
            "Set Z offset for %s: %.4f" % (filament, offset)
        )

    def cmd_SENTIENT_GET_FILAMENT_OFFSET(self, gcmd):
        """Get saved Z offset for a filament"""
        filament = gcmd.get('FILAMENT', 'PLA').upper()
        if filament in self.saved_offsets:
            gcmd.respond_info(
                "Z offset for %s: %.4f" % (filament, self.saved_offsets[filament])
            )
        else:
            gcmd.respond_info(
                "No saved offset for %s. Run SENTIENT_CALIBRATE_Z FILAMENT=%s first." % (
                    filament, filament
                )
            )

    def cmd_SENTIENT_APPLY_FILAMENT_OFFSET(self, gcmd):
        """Apply saved Z offset for a filament"""
        filament = gcmd.get('FILAMENT', 'PLA').upper()
        if filament in self.saved_offsets:
            offset = self.saved_offsets[filament]
            self._apply_z_offset(offset)
            gcmd.respond_info(
                "Applied Z offset for %s: %.4f" % (filament, offset)
            )
        else:
            gcmd.respond_info(
                "No saved offset for %s. "
                "Run SENTIENT_CALIBRATE_Z FILAMENT=%s first." % (
                    filament, filament
                )
            )

    def cmd_SENTIENT_STATUS(self, gcmd):
        """Show all saved filament Z offsets"""
        if not self.saved_offsets:
            gcmd.respond_info(
                "No filament offsets saved yet.\n"
                "Run SENTIENT_CALIBRATE_Z FILAMENT=<type> to calibrate."
            )
            return

        lines = ["=== sentient Filament Z Offsets ==="]
        for filament, offset in sorted(self.saved_offsets.items()):
            target = FILAMENT_TARGETS.get(filament, FILAMENT_TARGETS['default'])
            lines.append(
                "%-8s offset: %+.4f  (target squish: %.2fmm)" % (
                    filament, offset, target
                )
            )
        lines.append("====================================")
        lines.append(
            "Active filament: %s" % self.current_filament
        )
        lines.append(
            "Current Z offset: %.4f" % self._get_current_z_offset()
        )
        gcmd.respond_info('\n'.join(lines))

    def get_status(self, eventtime):
        """Return status for Mainsail/dashboard"""
        return {
            'calibrating': self.calibrating,
            'current_filament': self.current_filament,
            'saved_offsets': dict(self.saved_offsets),
            'baseline_mesh': self.baseline_mesh,
        }


def load_config(config):
    return SentientFirstLayer(config)
