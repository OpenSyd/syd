import setuptools

with open("readme.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="syd",
    version="0.0.1",
    author="David Sarrut",
    author_email="david.sarrut@creatis.insa-lyon.fr",
    description="SYD - Dosimetry for Molecular Radiation Therapy",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://gitlab.in2p3.fr/dsarrut/syd",
    package_dir={ 'syd': 'syd',
                  'syd_test': 'syd_test'},
    packages=['syd', 'syd_test'],
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ),
    python_requires='>=3.6',
    install_requires=[
        'dataset',
        'pydicom',
        'tqdm',
        'colored',
        'itk>=5',
        'python-box'
      ],
    scripts=[
        'bin/syd_create',
        'bin/syd_info',
        'bin/syd_find',
        'bin/syd_delete',
        'bin/syd_update',
        'bin/syd_dicom_info',
        'bin/syd_insert_dicom',
        'bin/syd_insert_image_from_dicom',
        'bin/syd_stitch_image',
        'bin/syd_geometrical_mean',
        'bin/syd_faf_calibration']
)
