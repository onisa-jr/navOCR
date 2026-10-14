from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="navocr",
    version="1.0.0",
    description="Native-like screen text OCR with Apple Live Text interaction for Linux using IndraOCR",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="onisajr",
    url="https://github.com/onisajr/navOCR",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "indra-ocr",
        "PyQt5",
        "Pillow",
        "numpy",
        "pynput",
    ],
    entry_points={
        "console_scripts": [
            "navocr = navocr.cli:main",
        ],
    },
    classifiers=[
        "Environment :: X11 Applications :: Qt",
        "Intended Audience :: End Users/Desktop",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Topic :: Multimedia :: Graphics :: Capture :: Screen Capture",
    ],
)
