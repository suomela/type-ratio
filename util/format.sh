#!/bin/bash

set -e

yapf -ip *.py
clang-format -i --style=file src/*.cc
