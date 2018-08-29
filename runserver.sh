#!/bin/bash
docker build -t hebrew-reader .
docker stop hebrew-reader
docker rm hebrew-reader
docker run -d --restart=always --name hebrew-reader -p 19419:19419 hebrew-reader
