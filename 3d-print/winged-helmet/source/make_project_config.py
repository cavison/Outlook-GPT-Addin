#!/usr/bin/env python
# Build Metadata/project_settings.config for the AD5X: the full Flashforge AD5X 0.4 / 0.20mm Standard @FF AD5X /
# Flashforge PLA Basic @FF AD5X presets exactly as Orca ships them (inheritance resolved), three filaments
# (navy / white / gold), and per-plate prime-tower spots. Orca then opens the file as a project: all plates load.
import json, glob, os, sys
PROF = os.environ.get('ORCA_FF_PROFILES', 'orca_profiles/Flashforge')     # bundled copy of OrcaSlicer's Flashforge profiles
META = {'type', 'name', 'inherits', 'from', 'instantiation', 'setting_id', 'renamed_from', 'description', 'version', 'filament_id', 'is_custom_defined'}
idx = {}
for f in glob.glob(PROF + '/*/*.json'):
    d = json.load(open(f)); idx[d['name']] = d
def resolved(name):
    chain = []
    n = name
    while n:
        d = idx[n]; chain.append(d); n = d.get('inherits')
    out = {}
    for d in reversed(chain):
        for k, v in d.items():
            if k not in META: out[k] = v
    return out
PRINTER, PROCESS, FILAMENT = 'Flashforge AD5X 0.4 nozzle', '0.20mm Standard @FF AD5X', 'Flashforge PLA Basic @FF AD5X'
def build(n_plates, colours, tower_xy):
    m, p, f = resolved(PRINTER), resolved(PROCESS), resolved(FILAMENT)
    cfg = {}
    cfg.update(m); cfg.update(p)
    nf = len(colours)
    for k, v in f.items():
        cfg[k] = (v * nf) if isinstance(v, list) else v           # one entry per filament
    for k in ('compatible_printers', 'compatible_prints', 'compatible_printers_condition', 'compatible_prints_condition'): cfg.pop(k, None)
    cfg.update({
        'name': 'project_settings', 'from': 'project', 'version': '2.3.0.0',
        'printer_settings_id': PRINTER, 'print_settings_id': PROCESS, 'filament_settings_id': [FILAMENT] * nf,
        'filament_colour': colours, 'filament_map': ['1'] * nf,
        # values below equal the system presets; listing one key per preset makes Orca take every other value
        # straight from the user's own installed AD5X presets
        'different_settings_to_system': ['enable_prime_tower'] + ['filament_type'] * nf + ['printer_model'],
        'wipe_tower_x': [str(tower_xy[0])] * n_plates, 'wipe_tower_y': [str(tower_xy[1])] * n_plates,
        'flush_multiplier': '1',
        'curr_bed_type': 'Textured PEI Plate',            # the AD5X's standard sheet; change it in Orca if you use another
    })
    # purge volumes (mm3) between the three colours, from -> to; dark into light needs the most
    FL = {('navy', 'white'): 560, ('navy', 'gold'): 420, ('white', 'navy'): 180, ('white', 'gold'): 260,
          ('gold', 'navy'): 200, ('gold', 'white'): 380}
    names = ['navy', 'white', 'gold']
    cfg['flush_volumes_matrix'] = [str(0 if a == b else FL[(a, b)]) for a in names for b in names]
    cfg['flush_volumes_vector'] = ['140'] * (2 * nf)
    return cfg
if __name__ == '__main__':
    c = build(20, ['#1E2A52', '#ECECE4', '#F2C12E'], (15, 193))
    print(len(c), 'keys'); print({k: c[k] for k in ('printable_area', 'printable_height', 'enable_prime_tower', 'prime_tower_width', 'nozzle_temperature', 'filament_type', 'sparse_infill_density', 'wall_loops', 'curr_bed_type', 'default_bed_type') if k in c})
