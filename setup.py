import setuptools

with open("README.md", "r") as f:
    long_description = f.read()

setuptools.setup(
    name="ondewo-bpi",
    version="2.0.4",
    author="Ondewo GbmH",
    author_email="info@ondewo.com",
    description="This library starts a proxy for the cai server allowing for fulfillment hooks.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://bitbucket.org/ondewo/ondewo-bpi",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha",
        "Topic :: Software Development :: Libraries",
    ],
    python_requires=">=3.0.1",
)
