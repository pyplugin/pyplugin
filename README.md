# pyplugin
![Pytest Status](https://github.com/pyplugin/pyplugin/actions/workflows/pytest.yml/badge.svg)
[![codecov](https://codecov.io/github/pyplugin/pyplugin/branch/main/graph/badge.svg?token=1PH1NHTGXP)](https://codecov.io/github/pyplugin/pyplugin)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://raw.githubusercontent.com/pyplugin/pyplugin/main/LICENSE)
[![Documentation Status](https://readthedocs.org/projects/pyplugin/badge/?version=stable)](https://pyplugin.readthedocs.io/en/stable/?badge=stable)
![Pylint Status](https://github.com/pyplugin/pyplugin/actions/workflows/pylint.yml/badge.svg)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Pyplugin is a plugin framework library, supporting declarative-style plugin writing, allowing modular, swappable
functionality in any codebase. 

See
[Getting Started](https://pyplugin.readthedocs.io/en/latest/getting_started.html) for more.


| Version Name | Latest Tag | Release Notes                                                             | Patch Notes                                                             | Documentation                                            | Release Date | End Support Date |
|--------------|------------|---------------------------------------------------------------------------|-------------------------------------------------------------------------|----------------------------------------------------------|--------------|------------------|
| 0.6          | v0.6.0     | [Release Notes](https://github.com/pyplugin/pyplugin/releases/tag/v0.6.0) | [Patch Notes](https://github.com/pyplugin/pyplugin/releases/tag/v0.6.0) | [Documentation](https://pyplugin.readthedocs.io/en/0.6/) | 19 July 2025  |                  |


## Changelog v0.6

### Features

- Upgrade to support Python 3.13

## Contributing
Want a new feature, found a bug, or have questions? Feel free to add to our issue board on Github:
[Open Issues](https://github.com/pyplugin/pyplugin/issues)

We welcome any developer who enjoys the package enough to contribute. 
If you want to be added as a contributor and check out the 
[Developer's Guide](https://github.com/pyplugin/pyplugin/wiki/Developer's-Guide).

## Introduction
Plugins are arbitrary callables. They can declare other plugins as requirements while operating under
certain guarantees:

- A plugin can be loaded (i.e. called) exactly once until it is unloaded.
- A plugin's dependencies will be loaded before.
- A plugin's loaded dependents will be reloaded after.
- When a plugin is unloaded, its loaded dependents will be unloaded before.

This paradigm naturally puts an emphasis on the structure of packages and applications and less on its orchestration.
This allows consumers of applications to easily swap or add plugins while guaranteeing conformity to API
contracts.

## Install
```
pip install pyplugin
```
