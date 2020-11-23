Developper
==========

.. contents:: Table of Contents
   :depth: 15
   :local:

Test
----

To run unit tests. ::
    python -m unittest syd_test -v

DataBase Structure
------------------

- A Patient table containing the patient information and various id
- An Injection table, related to the patient table and containing all information about the injection of a radioisotope. This table uses the Radionuclide table that contains radionuclide properties and which is already pre-filled.
- An Acquisition table related to an injection, corresponding to the acquisition of some data with an imaging system. Dicom images and listmode data will refer to an acquisition. This table makes possible chronological display of all acquisitions related to an injection.
- A Listmode table containing the listmode data and associated files (see the table File below).
- A DicomStudy table containing all the Dicom studies for one patient
- A DicomSerie table containing series for one study and linked to one Acquisition. An Acquisition is linked to all the associated DicomSeries and listmode data.
- A DicomFile table containing details about the dicom file.
- An Image table that groups all images that will be created. Usually stored as .mhd/.raw files.
- A File table that store path for all the files included in the database

View
----

In **syd_find**, the resulting table of elements is printed with a panda dataframe. The elements are extracted from
 the database via either the raw elements in the table or via a view. The views are defined in the FormatView table
  and created with **syd_clear_view --default** or database creations. Additional view can be created with the
   **syd_insert_view** command.
