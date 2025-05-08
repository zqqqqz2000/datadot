from setuptools import setup, find_packages

setup(
    name="datadot",
    version="1.0.0",
    description="A functional data navigation tool for Python",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="DataDot Contributors",
    author_email="example@example.com",
    url="https://github.com/yourusername/datadot",
    packages=find_packages(),
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
        "Programming Language :: Python :: 3.14",
    ],
    python_requires=">=3.8",
) 