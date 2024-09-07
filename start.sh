#!/bin/bash

# Mount the Cloud Storage bucket
gcsfuse --implicit-dirs -o allow_other gcs-1:web-bucket-ui /mnt/disks/persistent-storage/open-webui-data

# Start the Open WebUI application
/app/entrypoint.sh