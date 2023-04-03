RUN = poetry run

test:
	$(RUN) python -m unittest discover
