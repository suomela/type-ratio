#!/bin/bash

set -e

pipenv run yapf -ip *.py
clang-format -i --style=file src/*.cc
