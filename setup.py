from setuptools import setup, find_packages

setup(
    name="fend-sentry",
    version="0.1.0",
    description="AI-powered Django monitoring that actually understands your app",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Fend Labs",
    author_email="labs@fend.ai",
    url="https://github.com/fendlabs/fend-sentry",
    packages=find_packages(),
    install_requires=[
        "click>=8.1.7",
        "rich>=13.7.1", 
        "paramiko>=3.4.0",
        "google-generativeai>=0.8.3",
        "python-dotenv>=1.0.1",
        "pyyaml>=6.0.1",
    ],
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
    ],
    python_requires=">=3.8",
)