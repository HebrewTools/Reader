#!/bin/bash
set -e
docker build -t hebrew-reader .
docker stop hebrew-reader || true
docker rm hebrew-reader || true
docker run -d --restart=always --name hebrew-reader -p 19419:19419 hebrew-reader
