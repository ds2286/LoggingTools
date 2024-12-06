from setuptools import setup, find_packages

extras = {
    "s3_tools": [
        "boto3",
        "S3Tools @ git+https://github.com/EpiGenomicsCode/S3Tools.git"
    ],
    "database": [
        "dbTools @ git+https://github.com/EpiGenomicsCode/dbTools.git"
    ]
}

# Dynamically create the 'all' group
extras['all'] = sum(extras.values(), [])

setup(
    name='LoggingTools',
    version='0.4.4', 
    description='This standardizes the logging for python applications.',
    author='David Saroka',  
    author_email='ds2286@cornell.edu',  
    url='https://github.com/EpiGenomicsCode/LoggingTools.git',
    packages=find_packages(),  # Automatically finds all packages
    package_data={
        'LoggingTools.config': ["*"]
    },
    install_requires=[  # List of dependencies
        "PyYAML",
        "pydantic",
        "pydantic-settings",
        "setuptools"
    ],
    extras_require=extras,
    classifiers=[  # Additional metadata
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.12',
)
