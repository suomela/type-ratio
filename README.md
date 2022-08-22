TypeRatio: comparing competing suffixes
=======================================

This repository contains source code connected to the following article:

- Rodríguez-Puente, Paula, Tanja Säily and Jukka Suomela. "New methods for analysing diachronic suffix competition across registers: How *-ity* gained ground on *-ness* in Early Modern English". *International Journal of Corpus Linguistics.* https://doi.org/10.1075/ijcl.22014.rod


Building
--------

    ./build.sh


Testing
-------

This should run a number of tests and eventually output "All tests passed":

    ./test.py


Usage
-----

Please see https://github.com/suomela/suffix-competition-code for an example of how to use this code.


Requirements
------------

If you use Ubuntu 20.04, installing the following packages should be enough:

    apt-get install -y cmake g++ git python3 python3-jinja2 python3-matplotlib

You can use the Docker image [suomela/type-ratio](https://hub.docker.com/r/suomela/type-ratio), which is an Ubuntu image with all the right packages installed. There is also a [Dockerfile](docker/Dockerfile) you can use to create your own Docker image.


Author
------

Jukka Suomela, https://jukkasuomela.fi/
