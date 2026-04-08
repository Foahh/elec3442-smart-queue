from setuptools import find_packages, setup

setup(
    name="smart-queue-estimator",
    version="0.1.0",
    description="Smart queue length and wait time estimator backend for Raspberry Pi",
    packages=find_packages(where="src"),
    py_modules=["config", "database", "db_models", "main", "schemas"],
    package_dir={"": "src"},
    python_requires=">=3.14",
    entry_points={
        "console_scripts": [
            "queue-estimator=main:main",
        ],
    },
)
