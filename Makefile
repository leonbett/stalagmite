.PHONY: docker-build docker-run docker-clean

subject ?= tinyc
OUTPUT_DIRECTORY = output_docker/

docker-build:
	git rev-parse HEAD > klee-examples.commit
	docker build . -t symbolic-grammar-mining

docker-run:
	@echo "docker-run using Makefile"
	docker run --rm -d -v $(shell pwd)/output_docker:/stalagmite/data symbolic-grammar-mining --subject=$(subject) --all

docker-run-env:
	@echo "docker-run-env using specified env file [provide subject and envfile]"
	docker run --rm --env-file $(envfile) -d -v $(shell pwd)/output_docker:/stalagmite/data symbolic-grammar-mining --subject=$(subject) --all

docker-clean:
	rm -rf $(OUTPUT_DIRECTORY)

subjects-clean:
	find subjects/ -name "a.out" -delete
	find subjects/ -name "*.bc" -delete
	find subjects/ -type d -name "klee-*" -exec rm -r {} +
	find subjects/ -name "*.pdf" -delete
	find subjects/ -name "*.json" -delete

