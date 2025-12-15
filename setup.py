"""
Setup configuration for pyxelator
"""
from setuptools import setup, find_packages
from pathlib import Path

# Read the contents of README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

setup(
    name='pyxelator',
    version='0.3.1',
    author='Aria Uno Suseno',
    author_email='uno@idejongkok.com',
    description='Image-based automation for Selenium, Playwright & Appium - locate elements by screenshots',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/idejongkok/pyxelator',
    packages=find_packages(),
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Testing',
        'Topic :: Software Development :: Quality Assurance',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.10',
    install_requires=[
        'opencv-python>=4.5.0',
        'numpy>=1.19.0',
    ],
    extras_require={
        'selenium': ['selenium>=4.0.0'],
        'playwright': ['playwright>=1.20.0'],
        'appium': ['Appium-Python-Client>=2.0.0'],
        'dev': [
            'pytest>=7.0.0',
            'selenium>=4.0.0',
            'playwright>=1.20.0',
            'Appium-Python-Client>=2.0.0',
        ],
    },
    keywords='selenium playwright appium automation testing image-recognition opencv visual-testing mobile-automation',
    project_urls={
        'Bug Reports': 'https://github.com/idejongkok/pyxelator/issues',
        'Source': 'https://github.com/idejongkok/pyxelator',
        'Instagram': 'https://instagram.com/idejongkok',
    },
)
