#!/usr/bin/env bash

export FASTAPI_HOST=$FASTAPI_HOST
export FASTAPI_PORT=$FASTAPI_PORT

set -o errexit      # make your script exit when a command fails.
set -o nounset      # exit when your script tries to use undeclared variables.

case "$1" in
  serve)
    uvicorn src.main:app --host $FASTAPI_HOST --port $FASTAPI_PORT --reload
    ;;
  jupyter)
    jupyter notebook src/jupyter_notebooks --ip 0.0.0.0 --port 8888 --allow-root --no-browser --NotebookApp.token= --NotebookApp.password=
    ;;
  *)
    exec "$@"
esac