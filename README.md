TypeRatio: comparing competing suffixes
=======================================

This repository contains source code connected to the following articles:

- Paula Rodríguez-Puente, Tanja Säily and Jukka Suomela (2022). "New methods for analysing diachronic suffix competition across registers: How *-ity* gained ground on *-ness* in Early Modern English." *International Journal of Corpus Linguistics.* https://doi.org/10.1075/ijcl.22014.rod

- Tanja Säily, Martin Hilpert and Jukka Suomela (to appear). "New approaches to investigating change in derivational productivity: Gender and internal factors in the development of -ity and -ness, 1600–1800." Patricia Ronan, Theresa Neumaier, Lisa Westermayer, Andreas Weilinghoff & Sarah Buschfeld (eds.), *Crossing boundaries through corpora: Innovative approaches to corpus linguistics* (Studies in Corpus Linguistics). Amsterdam: John Benjamins.

News
----

For a new version of this tool, see https://github.com/suomela/types3

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

Acknowledgments
---------------

The author wishes to acknowledge CSC – IT Center for Science, Finland, for computational resources.
