from setuptools import setup, find_packages

setup(
    name='styleswitcher_gui',
    version='1.0.0',
    description='A GUI for editing Devil May Cry 3 StyleSwitcher.ini',
    author='Your Name',
    packages=find_packages(where='.'),
    py_modules=['styleswitcher_gui'],
    install_requires=[
        'PyQt5>=5.15.0',
        'configparser>=5.0.0'
    ],
    entry_points={
        'console_scripts': [
            'styleswitcher-gui=styleswitcher_gui:main'
        ]
    },
    include_package_data=True,
    package_data={
        '': ['*.ini', '*.html']
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent'
    ],
)
