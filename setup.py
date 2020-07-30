import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()


setuptools.setup(
    name="leaderdata-sdk",
    version="0.0.1",
    author="shagohead",
    author_email="html.ru@gmail.com",
    description="LeaderData API SDK",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/LeaderId/leaderdata-sdk",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
    install_requires=['httpx>=0.11.0,<2'],
)
