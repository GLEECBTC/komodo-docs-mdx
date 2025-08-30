#!/bin/bash

docker compose up -d
python generate_postman.py --all
python ./kdf_responses_manager.py --update-files
docker compose down
