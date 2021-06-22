CODE_CHECK_IMAGE=code_check_image
TEST_IMAGE=test_image
DOCKER_REGISTRY=registry-dev.ondewo.com:5000
ONDEWO_NAMESPACE=ondewo

run_code_checks: ## Start the code checks image and run the checks
	docker build -t ${CODE_CHECK_IMAGE} -f dockerfiles/code_checks.Dockerfile .
	docker run --rm ${CODE_CHECK_IMAGE} make flake8
	docker run --rm ${CODE_CHECK_IMAGE} make mypy

run_client_tests: ## Build a little image for running some tests
	docker build -t ${TEST_IMAGE} -f  ondewo-nlu-client-python/dockerfiles/python-test.Dockerfile ./ondewo-nlu-client-python
	docker run --rm ${TEST_IMAGE}

install:
	echo to install the bpi sip version, please contact office@ondewo.com for the submodule
	pip install -r requirements.txt

build_example:
	docker build -t ${DOCKER_REGISTRY}/${ONDEWO_NAMESPACE}/bpi-example-image:$(image_suffix) -f dockerfiles/Dockerfile .

push_example:
	docker push ${DOCKER_REGISTRY}/${ONDEWO_NAMESPACE}/bpi-example-image:$(image_suffix)
	docker tag ${DOCKER_REGISTRY}/${ONDEWO_NAMESPACE}/bpi-example-image:$(image_suffix) ${DOCKER_REGISTRY}/${ONDEWO_NAMESPACE}/bpi-example-image:latest
	docker push ${DOCKER_REGISTRY}/${ONDEWO_NAMESPACE}/bpi-example-image:latest

build_qa_example: export image_suffix=master
build_qa_example: export image=qa
build_qa_example: build_image_with_tag
build_sip_example: export image_suffix=master
build_sip_example: export image=sip
build_sip_example: build_image_with_tag

build_image_with_tag:
	docker build -t ${DOCKER_REGISTRY}/${ONDEWO_NAMESPACE}/bpi-$(image)-example-image:$(image_suffix) -f dockerfiles/$(image).Dockerfile .

push_image_with_tag:
	docker push ${DOCKER_REGISTRY}/${ONDEWO_NAMESPACE}/bpi-$(image)-example-image:$(image_suffix)
	docker tag ${DOCKER_REGISTRY}/${ONDEWO_NAMESPACE}/bpi-$(image)-example-image:$(image_suffix) ${DOCKER_REGISTRY}/${ONDEWO_NAMESPACE}/bpi-$(image)-example-image:latest
	docker push ${DOCKER_REGISTRY}/${ONDEWO_NAMESPACE}/bpi-$(image)-example-image:latest

run_qa_example:
	docker-compose up bpi_qa

kill_qa_example:
	docker-compose kill bpi_qa

run_bpi_example:
	docker-compose up bpi

kill_bpi_example:
	docker-compose kill bpi

# GRPC autocoder targets
generate_grpc_endpoint_relays:
	 python -m autocode.generate_endpoint_relays

push_to_pypi: build_package upload_package clear_package_data
	echo 'pushed to pypi :)'

build_package:
	python setup.py sdist bdist_wheel

upload_package:
	twine upload -r pypi dist/*

clear_package_data:
	rm -rf build dist ondewo_logging.egg-info
