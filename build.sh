#!/bin/bash

set -e

mkdir -p release
cd release
cmake .. -DCMAKE_BUILD_TYPE=Release
cmake --build .
