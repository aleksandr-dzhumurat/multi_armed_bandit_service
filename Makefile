CURRENT_DIR = $(shell pwd)
PROJECT_NAME = bandit
PORT = 8080
include .env
export

prepare-dirs:
	mkdir -p ${CURRENT_DIR}/data || true && \
	mkdir -p ${CURRENT_DIR}/data/service_data || true && \
	mkdir -p ${CURRENT_DIR}/data/mongo_data || true

build-network:
	docker network create service_network -d bridge || true

build-frontend:
	docker build -f Dockerfile.streamlit -t ${PROJECT_NAME}:frontend .

build: build-network prepare-dirs build-frontend
	docker build -t ${PROJECT_NAME}:dev .

stop-service:
	docker rm -f ${PROJECT_NAME}_container || true

stop-mongo:
	docker rm -f ${PROJECT_NAME}_mongo_container || true

stop-frontend:
	docker rm -f ${PROJECT_NAME}_frontend || true

stop: stop-frontend stop-mongo stop-service

run-mongo: stop-mongo
	docker run -d \
		-v "${CURRENT_DIR}/data/mongo_data:/data/db" \
		--name ${PROJECT_NAME}_mongo_container \
		--network service_network \
		-p 27018:27017 \
		mongo:6.0.5

prepare-data:
	tar -xzvf data/service_data.tar.gz -C data/service_data || true

stop-jupyter:
	docker rm -f ${PROJECT_NAME}_jupyter || true

stop-all: stop stop-jupyter

run-jupyter: stop-jupyter build-network
	docker run -d --rm \
	    --env-file ${CURRENT_DIR}/.env \
	    -p ${JYPYTER_PORT}:${JYPYTER_PORT} \
	    -v "${CURRENT_DIR}/src:/srv/src" \
	    -v "${CURRENT_DIR}/data:/srv/data" \
		--network service_network \
	    --name ${PROJECT_NAME}_jupyter \
	    ${PROJECT_NAME}:dev jupyter

run-debug:
	docker run -it --rm \
	    --env-file ${CURRENT_DIR}/.env \
	    -v "${CURRENT_DIR}/src:/srv/src" \
	    -v "${CURRENT_DIR}/data:/srv/data" \
	    --name ${PROJECT_NAME}_container \
	    ${PROJECT_NAME}:dev bash

run-frontend: build-network
	docker run -d --rm \
	    --env-file ${CURRENT_DIR}/.env \
	    -p ${STREAMLIT_PORT}:${STREAMLIT_PORT} \
	    -v "${CURRENT_DIR}/frontend_app:/srv/src" \
		--network service_network \
	    --name ${PROJECT_NAME}_frontend \
	    ${PROJECT_NAME}:frontend

run-service: stop-service
	docker run -d --rm \
	    --env-file ${CURRENT_DIR}/.env \
	    -p ${FASTAPI_PORT}:${FASTAPI_PORT} \
	    -v "${CURRENT_DIR}/src:/srv/src" \
	    -v "${CURRENT_DIR}/data:/srv/data" \
		--network service_network \
	    --name ${PROJECT_NAME}_container \
	    ${PROJECT_NAME}:dev serve

run: stop prepare-data build-network run-mongo run-frontend run-service
