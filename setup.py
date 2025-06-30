from setuptools import setup, find_packages
import os

# Read README for long description
def read_readme():
    try:
        with open("README.md", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "AI-powered Django monitoring that actually understands your app"

# Read requirements
def read_requirements():
    try:
        with open("requirements.txt", "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip() and not line.startswith("#")]
    except FileNotFoundError:
        return [
            "click>=8.1.7",
            "rich>=13.7.1", 
            "paramiko>=3.4.0",
            "google-generativeai>=0.8.3",
            "python-dotenv>=1.0.1",
            "pyyaml>=6.0.1",
        ]

setup(
    name="fend-sentry",
    version="0.1.0",
    description="AI-powered Django monitoring that actually understands your app",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    author="Fend Labs",
    author_email="labs@fend.ai",
    url="https://github.com/fendlabs/fend-sentry",  # Will be updated when repo is created
    project_urls={
        "Bug Tracker": "https://github.com/fendlabs/fend-sentry/issues",
        "Documentation": "https://github.com/fendlabs/fend-sentry#readme",
        "Source Code": "https://github.com/fendlabs/fend-sentry",
    },
    packages=find_packages(exclude=["tests*"]),
    py_modules=["cli", "config", "remote", "parser", "analyzer", "reporter"],
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "isort>=5.0.0",
            "mypy>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "fend-sentry=cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Software Development :: Debuggers",
        "Topic :: System :: Logging",
        "Topic :: System :: Monitoring",
        "Operating System :: OS Independent",
        "Environment :: Console",
    ],
    keywords="django monitoring ai logging sentry health-check devops",
    python_requires=">=3.8",
    include_package_data=True,
    zip_safe=False,
)