#!/usr/bin/env python3

import dataset
import syd

# -----------------------------------------------------------------------------
def create_radionuclide_table(db):
    '''
    Create the radionuclide table
    '''

    # create default tables
    q = 'CREATE TABLE Radionuclide (\
    id INTEGER PRIMARY KEY NOT NULL,\
    name TEXT NOT NULL,\
    element TEXT NOT NULL,\
    atomic_number INTEGER NOT NULL,\
    mass_number INTEGER NOT NULL,\
    metastable INTEGER NOT NULL,\
    half_life_in_hours REAL NULL,\
    max_beta_minus_energy_in_kev REAL)'
    result = db.query(q)

    # insert default elements
    # later -> get from website
    r = [

        { 'name': 'C-11', 'element': 'Carbon', 'atomic_number': 6.0,
          'mass_number': 11.0, 'metastable': False, 'half_life_in_hours': 0.34,
          'max_beta_minus_energy_in_kev': 0.0 },
        { 'name': 'O-15', 'element': 'Oxygen', 'atomic_number': 8.0,
          'mass_number': 15.0, 'metastable': False, 'half_life_in_hours': 0.03,
          'max_beta_minus_energy_in_kev': 0.0 },
        { 'name': 'F-18', 'element': 'Fluorine', 'atomic_number': 9.0,
          'mass_number': 18.0, 'metastable': False, 'half_life_in_hours': 1.83,
          'max_beta_minus_energy_in_kev': 0.0 },
        { 'name': 'P-32', 'element': 'Phosphorus', 'atomic_number': 15.0,
          'mass_number': 32.0, 'metastable': False, 'half_life_in_hours': 342.81,
          'max_beta_minus_energy_in_kev': 1710.66 },
        { 'name': 'P-33', 'element': 'Phosphorus', 'atomic_number': 15.0,
          'mass_number': 33.0, 'metastable': False, 'half_life_in_hours': 609.19,
          'max_beta_minus_energy_in_kev': 248.5 },
        { 'name': 'Cu-64', 'element': 'Copper', 'atomic_number': 29.0,
          'mass_number': 64.0, 'metastable': False, 'half_life_in_hours': 12.7,
          'max_beta_minus_energy_in_kev': 579.4 },
        { 'name': 'Cu-67', 'element': 'Copper', 'atomic_number': 29.0,
          'mass_number': 67.0, 'metastable': False, 'half_life_in_hours': 63.84,
          'max_beta_minus_energy_in_kev': 0.0 },
        { 'name': 'Ga-68', 'element': 'Gallium', 'atomic_number': 31.0,
          'mass_number': 68.0, 'metastable': False, 'half_life_in_hours': 1.13,
          'max_beta_minus_energy_in_kev': 0.0 },
        { 'name': 'Sr-89', 'element': 'Strontium', 'atomic_number': 38.0,
          'mass_number': 89.0, 'metastable': False, 'half_life_in_hours': 1213.67,
          'max_beta_minus_energy_in_kev': 1495.1 },
        { 'name': 'Y-90', 'element': 'Yttrium', 'atomic_number': 39.0,
          'mass_number': 90.0, 'metastable': False, 'half_life_in_hours': 64.0417,
          'max_beta_minus_energy_in_kev': 2278.7 },
        { 'name': 'Zr-89', 'element': 'Zirconium', 'atomic_number': 40.0,
          'mass_number': 89.0, 'metastable': False, 'half_life_in_hours': 78.42,
          'max_beta_minus_energy_in_kev': 0.0 },
        { 'name': 'Tc-99m', 'element': 'Technetium', 'atomic_number': 43.0,
          'mass_number': 99.0, 'metastable': True, 'half_life_in_hours': 6.01,
          'max_beta_minus_energy_in_kev': 436.2 },
        { 'name': 'Rh-103m', 'element': 'Rhodium', 'atomic_number': 45.0,
          'mass_number': 103.0, 'metastable': True, 'half_life_in_hours': 0.94,
          'max_beta_minus_energy_in_kev': 0.0 },
        { 'name': 'In-111', 'element': 'Indium', 'atomic_number': 49.0,
          'mass_number': 111.0, 'metastable': False, 'half_life_in_hours': 67.32,
          'max_beta_minus_energy_in_kev': 0.0 },
        { 'name': 'Sn-117m', 'element': 'Tin', 'atomic_number': 50.0,
          'mass_number': 117.0, 'metastable': True, 'half_life_in_hours': 326.39,
          'max_beta_minus_energy_in_kev': 0.0 },
        { 'name': 'I-123', 'element': 'Iodine', 'atomic_number': 53.0,
          'mass_number': 123.0, 'metastable': False, 'half_life_in_hours': 13.22,
          'max_beta_minus_energy_in_kev': 0.0 },
        { 'name': 'I-124', 'element': 'Iodine', 'atomic_number': 53.0,
          'mass_number': 124.0, 'metastable': False, 'half_life_in_hours': 100.22,
          'max_beta_minus_energy_in_kev': 0.0 },
        { 'name': 'I-125', 'element': 'Iodine', 'atomic_number': 53.0,
          'mass_number': 125.0, 'metastable': False, 'half_life_in_hours': 1425.31,
          'max_beta_minus_energy_in_kev': 0.0 },
        { 'name': 'I-131', 'element': 'Iodine', 'atomic_number': 53.0,
          'mass_number': 131.0, 'metastable': False, 'half_life_in_hours': 192.56,
          'max_beta_minus_energy_in_kev': 970.8 },
        { 'name': 'Sm-153', 'element': 'Samarium', 'atomic_number': 62.0,
          'mass_number': 153.0, 'metastable': False, 'half_life_in_hours': 46.29,
          'max_beta_minus_energy_in_kev': 807.6 },
        { 'name': 'Ho-166', 'element': 'Holmium', 'atomic_number': 67.0,
          'mass_number': 166.0, 'metastable': False, 'half_life_in_hours': 26.79,
          'max_beta_minus_energy_in_kev': 1854.5 },
        { 'name': 'Er-169', 'element': 'Erbium', 'atomic_number': 6.0,
          'mass_number': 8.0, 'metastable': False, 'half_life_in_hours': 225.11,
          'max_beta_minus_energy_in_kev': 353.0 },
        { 'name': 'Lu-177', 'element': 'Lutetium', 'atomic_number': 71.0,
          'mass_number': 177.0, 'metastable': False, 'half_life_in_hours': 159.53,
          'max_beta_minus_energy_in_kev': 498.3 },
        { 'name': 'Re-186', 'element': 'Rhenium', 'atomic_number': 75.0,
          'mass_number': 186.0, 'metastable': False, 'half_life_in_hours': 89.25,
          'max_beta_minus_energy_in_kev': 1069.5 },
        { 'name': 'Re-188', 'element': 'Rhenium', 'atomic_number': 75.0,
          'mass_number': 188.0, 'metastable': False, 'half_life_in_hours': 17.0,
          'max_beta_minus_energy_in_kev': 2120.4 },
        { 'name': 'Tl-201', 'element': 'Thallium', 'atomic_number': 81.0,
          'mass_number': 201.0, 'metastable': False, 'half_life_in_hours': 73.01,
          'max_beta_minus_energy_in_kev': 0.0 },
        { 'name': 'Pb-212', 'element': 'Lead', 'atomic_number': 82.0,
          'mass_number': 212.0, 'metastable': False, 'half_life_in_hours': 10.64,
          'max_beta_minus_energy_in_kev': 569.9 },
        { 'name': 'Bi-212', 'element': 'Bismuth', 'atomic_number': 83.0,
          'mass_number': 212.0, 'metastable': False, 'half_life_in_hours': 1.01,
          'max_beta_minus_energy_in_kev': 2252.1 },
        { 'name': 'Bi-213', 'element': 'Bismuth', 'atomic_number': 83.0,
          'mass_number': 213.0, 'metastable': False, 'half_life_in_hours': 0.76,
          'max_beta_minus_energy_in_kev': 1423.0 },
        { 'name': 'At-211', 'element': 'Astatine', 'atomic_number': 85.0,
          'mass_number': 211.0, 'metastable': False, 'half_life_in_hours': 7.22,
          'max_beta_minus_energy_in_kev': 0.0 },
        { 'name': 'Ra-223', 'element': 'Radium', 'atomic_number': 88.0,
          'mass_number': 223.0, 'metastable': False, 'half_life_in_hours': 274.33,
          'max_beta_minus_energy_in_kev': 0.0 },
        { 'name': 'Ac-225', 'element': 'Actinium', 'atomic_number': 89.0,
          'mass_number': 225.0, 'metastable': False, 'half_life_in_hours': 240.0,
          'max_beta_minus_energy_in_kev': 0.0 },
        { 'name': 'Th-227', 'element': 'Thorium', 'atomic_number': 90.0,
          'mass_number': 227.0, 'metastable': False, 'half_life_in_hours': 449.23,
          'max_beta_minus_energy_in_kev': 0.0 }]

    syd.insert(db['Radionuclide'], r)
