from setuptools import setup, find_packages

setup(
    name='LoggingTools',
    version='0.1.0', 
    description='This standardizes the logging for python applications.',
    author='David Saroka',  
    author_email='ds2286@cornell.edu',  
    url='https://github.com/EpiGenomicsCode/LoggingTools.git',
    packages=find_packages(),  # Automatically finds all packages
    install_requires=[  # List of dependencies
        "PyYAML",
        "pydantic",
        "pydantic-settings",
        "boto3",
        "setuptools"
    ],
    classifiers=[  # Additional metadata
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.11',
)
