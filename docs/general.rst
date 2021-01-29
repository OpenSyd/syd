Getting Started
!!!!!!!!!!!!!!!


Installation Guide
==================

First clone the git folder with::

    git clone --recursive or git submodule update --init

Once the git folder is setup run the command::

    pip install -e .

You can run the tests to check the installation is ok::

    python -m unittest syd_test -v
 
From here, you can write python script using syd by using the module::

    import syd
    
    
