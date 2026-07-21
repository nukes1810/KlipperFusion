# sentient_first_layer.py v3
# Sentient Project - https://github.com/nukes1810/sentient
#
# v3 fixes:
#   - Store nozzle temp and reheat before printing calibration square
#   - Nozzle was cooling during 35 second bed scan causing shutdown
#   - Tighter infill spacing (0.45mm) for solid calibration square
#   - Better error messages throughout

import logging
import math

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

        self.cal_x = config.getfloat('calibration_x', 30.0)
        self.cal_y = config.getfloat('calibration_y', 30.0)
        self.cal_size = config.getfloat('calibration_size', 40.0)
        self.cal_speed = config.getfloat('calibration_speed', 1200.0)
        self.iterations = config.getint('iterations', 3)
        self.tolerance = config.getfloat('tolerance', 0.01)
        self.layer_height = config.getfloat('layer_height', 0.20)

        self.baseline_avg = None
        self.saved_offsets = {}
        self.current_filament = 'PLA'
        self.calibrating = False
        self._nozzle_temp = None  # stored nozzle temp for reheating

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
            desc="Save current bed mesh as baseline"
        )

        self.printer.register_event_handler(
            'klippy:connect', self._handle_connect
        )
        self.logger.info("sentient_first_layer v3 loaded")

    def _handle_connect(self):
        try:
            save_variables = self.printer.lookup_object('save_variables')
            svv = save_variables.allVariables()
            for key, value in svv.items():
                if key.startswith('sentient_z_offset_'):
                    filament = key.replace('sentient_z_offset_', '').upper()
                    self.saved_offsets[filament] = float(value)
                    self.logger.info(
                        "Loaded offset %s: %.3f" % (filament, float(value))
                    )
        except Exception as e:
            self.logger.warning("Could not load saved offsets: %s" % str(e))

    def _save_offset(self, filament, offset):
        filament = filament.upper()
        self.saved_offsets[filament] = offset
        try:
            save_variables = self.printer.lookup_object('save_variables')
            key = 'sentient_z_offset_%s' % filament.lower()
            save_variables.cmd_SAVE_VARIABLE(
                self.gcode.create_gcode_command(
                    'SAVE_VARIABLE', 'SAVE_VARIABLE',
                    {'VARIABLE': key, 'VALUE': '%.4f' % offset}
                )
            )
        except Exception as e:
            self.logger.warning("Could not save offset: %s" % str(e))

    def _get_mesh_average(self):
        """Get average Z from current bed mesh using Klipper API"""
        try:
            bed_mesh = self.printer.lookup_object('bed_mesh')
            status = bed_mesh.get_status(None)
            matrix = status.get('probed_matrix', None)
            if not matrix or matrix == [[]] or len(matrix) == 0:
                self.logger.warning("Mesh matrix is empty")
                return None
            total = 0.0
            count = 0
            for row in matrix:
                for val in row:
                    total += val
                    count += 1
            if count == 0:
                return None
            avg = total / count
            self.logger.info(
                "Mesh average: %.4f from %d points" % (avg, count)
            )
            return avg
        except Exception as e:
            self.logger.warning("Could not read mesh: %s" % str(e))
            return None

    def _run_gcode(self, gcode_str):
        self.gcode.run_script_from_command(gcode_str)

    def _get_current_z_offset(self):
        try:
            gcode_move = self.printer.lookup_object('gcode_move')
            return gcode_move.get_status(None)['homing_origin'][2]
        except Exception:
            return 0.0

    def _apply_z_offset(self, offset):
        self._run_gcode("SET_GCODE_OFFSET Z=%.4f MOVE=1" % offset)

    def _reheat_nozzle(self, gcmd):
        """Reheat nozzle to stored temp — called after bed scan"""
        if self._nozzle_temp is not None:
            gcmd.respond_info(
                "Reheating nozzle to %.0f°C after bed scan..." % self._nozzle_temp
            )
            self._run_gcode("M109 S%.0f" % self._nozzle_temp)
        else:
            # No stored temp — get current target
            try:
                extruder = self.printer.lookup_object('extruder')
                current_target = extruder.get_heater().get_status(None)['target']
                if current_target < 150:
                    gcmd.respond_info(
                        "Warning: Nozzle target is %.0f°C — too cold to extrude.\n"
                        "Waiting for nozzle to reach 150°C minimum..." % current_target
                    )
                    self._run_gcode("M109 S150")
            except Exception as e:
                self.logger.warning("Could not check nozzle temp: %s" % str(e))

    def cmd_SENTIENT_CALIBRATE_Z(self, gcmd):
        filament = gcmd.get('FILAMENT', 'PLA').upper()
        bed_temp = gcmd.get_float('BED_TEMP', None)
        nozzle_temp = gcmd.get_float('NOZZLE_TEMP', None)
        iterations = gcmd.get_int('ITERATIONS', self.iterations)
        target = FILAMENT_TARGETS.get(filament, FILAMENT_TARGETS['default'])

        # Store nozzle temp for reheating after scans
        self._nozzle_temp = nozzle_temp

        gcmd.respond_info(
            "=== sentient Z Offset Calibration ===\n"
            "Filament:      %s\n"
            "Target height: %.2fmm\n"
            "Iterations:    %d\n"
            "Tolerance:     ±%.3fmm" % (filament, target, iterations, self.tolerance)
        )

        self.calibrating = True
        self.current_filament = filament

        if bed_temp is not None:
            gcmd.respond_info("Heating bed to %.0f°C..." % bed_temp)
            self._run_gcode("M190 S%.0f" % bed_temp)
        if nozzle_temp is not None:
            gcmd.respond_info("Heating nozzle to %.0f°C..." % nozzle_temp)
            self._run_gcode("M109 S%.0f" % nozzle_temp)

        gcmd.respond_info("Homing and leveling...")
        self._run_gcode("G28")
        self._run_gcode("Z_TILT_ADJUST")

        # Baseline scan — bare bed
        gcmd.respond_info("Scanning bare bed baseline...")
        self._run_gcode("BED_MESH_CALIBRATE")
        self.baseline_avg = self._get_mesh_average()

        if self.baseline_avg is not None:
            gcmd.respond_info("Baseline average: %.4fmm" % self.baseline_avg)
        else:
            gcmd.respond_info(
                "Warning: Could not read baseline mesh.\n"
                "Check BED_MESH_CALIBRATE is working correctly."
            )

        # CRITICAL: Reheat nozzle after bed scan — scan takes 35s and nozzle cools
        self._reheat_nozzle(gcmd)

        best_offset = self._get_current_z_offset()

        for i in range(iterations):
            gcmd.respond_info("--- Iteration %d of %d ---" % (i + 1, iterations))

            gcmd.respond_info("Printing calibration square...")
            self._print_calibration_square()

            gcmd.respond_info("Waiting for layer to stabilize (5s)...")
            self._run_gcode("G4 P5000")

            gcmd.respond_info("Scanning first layer...")
            self._run_gcode("BED_MESH_CALIBRATE")

            # CRITICAL: Reheat nozzle after each scan
            self._reheat_nozzle(gcmd)

            layer_avg = self._get_mesh_average()

            if layer_avg is not None and self.baseline_avg is not None:
                actual_height = layer_avg - self.baseline_avg
                error = actual_height - target

                gcmd.respond_info(
                    "Actual layer height: %.3fmm\n"
                    "Target:             %.3fmm\n"
                    "Error:              %+.3fmm" % (actual_height, target, error)
                )

                if abs(error) <= self.tolerance:
                    gcmd.respond_info("Within tolerance! Z offset is perfect.")
                    break
                else:
                    correction = error * -1.0
                    new_offset = best_offset + correction
                    gcmd.respond_info(
                        "Applying correction: %+.3fmm → new Z offset: %.4f" % (
                            correction, new_offset
                        )
                    )
                    self._apply_z_offset(new_offset)
                    best_offset = new_offset
            else:
                gcmd.respond_info(
                    "Could not calculate layer height.\n"
                    "Baseline: %s  Layer scan: %s" % (
                        "OK" if self.baseline_avg is not None else "MISSING",
                        "OK" if layer_avg is not None else "MISSING"
                    )
                )

            if i < iterations - 1:
                gcmd.respond_info("Clearing calibration area...")
                self._clear_calibration_area()

        final_offset = self._get_current_z_offset()
        self._save_offset(filament, final_offset)

        gcmd.respond_info(
            "=== Calibration Complete ===\n"
            "Filament: %s\n"
            "Z Offset: %.4f\n"
            "Saved automatically. Applied on every future %s print." % (
                filament, final_offset, filament
            )
        )
        self.calibrating = False

    def _print_calibration_square(self):
        """Print a solid filled calibration square"""
        x = self.cal_x
        y = self.cal_y
        size = self.cal_size
        speed = self.cal_speed
        lh = self.layer_height
        e_per_mm = 0.04
        extrusion = 0.0

        self._run_gcode("G90")
        self._run_gcode("G1 X%.2f Y%.2f F6000" % (x, y))
        self._run_gcode("G1 Z%.3f F300" % lh)
        self._run_gcode("G92 E0")

        # Outer perimeter
        moves = [
            (x + size, y),
            (x + size, y + size),
            (x, y + size),
            (x, y),
        ]
        cx, cy = x, y
        for tx, ty in moves:
            dx = tx - cx
            dy = ty - cy
            dist = math.sqrt(dx*dx + dy*dy)
            extrusion += dist * e_per_mm
            self._run_gcode(
                "G1 X%.2f Y%.2f E%.4f F%.0f" % (tx, ty, extrusion, speed)
            )
            cx, cy = tx, ty

        # Solid infill — 0.45mm line spacing for solid square
        line_spacing = 0.45
        current_y = y + line_spacing
        direction = 1
        while current_y < y + size - line_spacing:
            if direction == 1:
                self._run_gcode("G1 X%.2f Y%.2f F6000" % (x, current_y))
                extrusion += size * e_per_mm
                self._run_gcode(
                    "G1 X%.2f Y%.2f E%.4f F%.0f" % (
                        x + size, current_y, extrusion, speed
                    )
                )
            else:
                self._run_gcode("G1 X%.2f Y%.2f F6000" % (x + size, current_y))
                extrusion += size * e_per_mm
                self._run_gcode(
                    "G1 X%.2f Y%.2f E%.4f F%.0f" % (
                        x, current_y, extrusion, speed
                    )
                )
            current_y += line_spacing
            direction *= -1

        self._run_gcode("G92 E0")
        self._run_gcode("G1 Z5 F3000")

    def _clear_calibration_area(self):
        self._run_gcode("G1 Z20 F3000")
        self._run_gcode(
            "G1 X%.2f Y%.2f F6000" % (
                self.cal_x + self.cal_size + 20,
                self.cal_y
            )
        )
        self._run_gcode("G4 P2000")

    def cmd_SENTIENT_SCAN_LAYER(self, gcmd):
        gcmd.respond_info("Scanning surface...")
        self._run_gcode("BED_MESH_CALIBRATE")
        mesh_avg = self._get_mesh_average()
        if mesh_avg is not None:
            if self.baseline_avg is not None:
                actual_height = mesh_avg - self.baseline_avg
                gcmd.respond_info(
                    "Surface scan:\n"
                    "Mesh average:  %.4fmm\n"
                    "Baseline:      %.4fmm\n"
                    "Layer height:  %.4fmm" % (
                        mesh_avg, self.baseline_avg, actual_height
                    )
                )
            else:
                gcmd.respond_info(
                    "Surface scan: %.4fmm\n"
                    "(Run SENTIENT_SAVE_BASELINE on bare bed first)" % mesh_avg
                )
        else:
            gcmd.respond_info("Could not read mesh. Check Cartographer.")

    def cmd_SENTIENT_SAVE_BASELINE(self, gcmd):
        gcmd.respond_info("Scanning baseline...")
        self._run_gcode("BED_MESH_CALIBRATE")
        avg = self._get_mesh_average()
        if avg is not None:
            self.baseline_avg = avg
            gcmd.respond_info("Baseline saved: %.4fmm" % avg)
        else:
            gcmd.respond_info("No mesh data. Run BED_MESH_CALIBRATE first.")

    def cmd_SENTIENT_SET_FILAMENT_OFFSET(self, gcmd):
        filament = gcmd.get('FILAMENT', 'PLA').upper()
        offset = gcmd.get_float('OFFSET', 0.0)
        self._save_offset(filament, offset)
        gcmd.respond_info("Set Z offset for %s: %.4f" % (filament, offset))

    def cmd_SENTIENT_GET_FILAMENT_OFFSET(self, gcmd):
        filament = gcmd.get('FILAMENT', 'PLA').upper()
        if filament in self.saved_offsets:
            gcmd.respond_info(
                "Z offset for %s: %.4f" % (filament, self.saved_offsets[filament])
            )
        else:
            gcmd.respond_info(
                "No saved offset for %s.\n"
                "Run SENTIENT_CALIBRATE_Z FILAMENT=%s" % (filament, filament)
            )

    def cmd_SENTIENT_APPLY_FILAMENT_OFFSET(self, gcmd):
        filament = gcmd.get('FILAMENT', 'PLA').upper()
        if filament in self.saved_offsets:
            offset = self.saved_offsets[filament]
            self._apply_z_offset(offset)
            gcmd.respond_info(
                "Applied Z offset for %s: %.4f" % (filament, offset)
            )
        else:
            gcmd.respond_info(
                "No saved offset for %s.\n"
                "Run SENTIENT_CALIBRATE_Z FILAMENT=%s first.\n"
                "Using current Z offset." % (filament, filament)
            )

    def cmd_SENTIENT_STATUS(self, gcmd):
        if not self.saved_offsets:
            gcmd.respond_info(
                "No filament offsets saved yet.\n"
                "Run SENTIENT_CALIBRATE_Z FILAMENT=<type> to calibrate."
            )
            return
        lines = ["=== sentient Filament Z Offsets ==="]
        for filament, offset in sorted(self.saved_offsets.items()):
            target = FILAMENT_TARGETS.get(
                filament, FILAMENT_TARGETS['default']
            )
            lines.append(
                "%-8s offset: %+.4f  (target: %.2fmm squish)" % (
                    filament, offset, target
                )
            )
        lines.append("====================================")
        lines.append("Active: %s" % self.current_filament)
        lines.append("Current Z offset: %.4f" % self._get_current_z_offset())
        gcmd.respond_info('\n'.join(lines))

    def get_status(self, eventtime):
        return {
            'calibrating': self.calibrating,
            'current_filament': self.current_filament,
            'saved_offsets': dict(self.saved_offsets),
            'baseline_avg': self.baseline_avg,
        }


def load_config(config):
    return SentientFirstLayer(config)
