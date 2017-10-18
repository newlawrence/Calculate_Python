#!/usr/bin/env python

import setuptools


if __name__ == '__main__':

    setuptools.setup(
        name='calculate',
        version='2.0.0rc1',
        packages=['calculate'],
        package_dir={'calculate': './calculate'},
        setup_requires=['cffi>=1.11.2'],
        install_requires=['cffi>=1.11.2'],
        cffi_modules=['build.py:ffi']
    )
