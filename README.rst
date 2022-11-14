########
InsarViz
########

InsarViz is a project dedicated to the visualisation of InSar data. 

The full documentation is available here: 

https://deformvis.gricad-pages.univ-grenoble-alpes.fr/insarviz



Installation
************

First, download the source code, typically using git:

.. code-block :: bash

    git clone git@gricad-gitlab.univ-grenoble-alpes.fr:deformvis/insarviz.git


We recommend you install the Insarviz tool in a virtual environment. If you have installed the `Anaconda distribution <https://www.anaconda.com/products/individual>`_, navigate to within the top-level insarviz folder and create a conda environment with the required dependencies using :

.. code-block :: bash

 conda env create -f environment.yaml


And activate it:

.. code-block :: bash

 conda activate insarviz-env


Without Anaconda, create an virtual environment, activate it and install the required packages using the following commands:

.. code-block :: bash

 python3 -m venv venv
 source venv/bin/activate
 pip install -r requirements.txt

Finally, install the Insarviz module. If you do **not** want to modify the source code, follow the **Regular installation** instructions. If you would like to be able to **modify the code**, follow the **Developper install instructions**.

* **Regular installation**

Installing Insarviz in a virtual environment, or system-wide, is just a one-line command:

.. code-block :: bash

        pip install .

* **Developper install instructions** 

If you intend to change the source code, you should install the tool in a *editable* mode:

.. code-block :: bash

        pip install -e . 

Check your installation
----------------------

You can check your installation by doing:

.. code-block :: bash

        ts_viz --help

This should print the help message. If not, your install failed.

Running InsarViz
----------------

Simply run InsarViz from the following command line:

.. code-block :: bash

        ts_viz 

Debug
-----
If you get errors mentioning rasterio, try:

.. code-block :: bash

        python3
        >> import rasterio

If this fails with an error mentioning that rasterio cannot find the libgdal.so.XX, you
should try either changing the version of rasterio (in the requirements.txt file) or the 
gdal version you are using. 

InsarViz has rasterio (https://rasterio.readthedocs.io) as dependency. Rasterio depends upon
the gdal library and assumes gdal is already installed. We recommend using version 1.2.10
of rasterio which is compatible with gdal 3.4.1 (on linux, use the command gdalinfo --version
to figure out which version of gdal you have).


Contact
-------
If you need help or have ideas for further developments, you can contact:
insarviz-sos@univ-grenoble-alpes.fr

