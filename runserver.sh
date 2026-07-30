#!/bin/bash
set -e
docker pull camilstaps/hebrew-reader:server
docker stop hebrew-reader || true
docker rm hebrew-reader || true
docker run -d --restart=always --name hebrew-reader -p 19419:19419 camilstaps/hebrew-reader:server
