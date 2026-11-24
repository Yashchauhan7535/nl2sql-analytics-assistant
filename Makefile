.PHONY: help install setup run test eval clean

help:
	@echo "Available commands:"
	@echo "  make install   Install python dependencies"
	@echo "  make setup     Create local SQLite database with Olist schema"
	@echo "  make run       Launch Streamlit analytics application"
	@echo "  make test      Execute pytest test suite"
	@echo "  make eval      Run 30-case evaluation benchmark"
	@echo "  make clean     Remove cache and temporary files"

install:
	pip install -r requirements.txt

setup:
	python setup_db.py

run:
	streamlit run app.py

test:
	pytest tests/ -v

eval:
	python evals/run_evals.py --dry-run

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
