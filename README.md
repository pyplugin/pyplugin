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
| 0.4          | v0.4.1     | [Release Notes](https://github.com/pyplugin/pyplugin/releases/tag/v0.4.0) | [Patch Notes](https://github.com/pyplugin/pyplugin/releases/tag/v0.4.1) | [Documentation](https://pyplugin.readthedocs.io/en/0.4/) | 23 Oct 2023  |                  |


## Changelog v0.4

### Features

- Added new setting `register_mode` which can be used to configure how plugins get registered upon
  initialization.
- Added `set_flag` function that will set a particular setting globally.
- Added `unset_flag` function to reset a setting to default.
- Added `with_flag` context manager to temporarily set a setting.

### Fixes

- Fixes dynamic requirements being registered in other parts of the load function (e.g. when loading a dependency).
- Fixes groups reloading entirely when loading individual elements.
- Fixes copying of requirements when copying a Plugin.

## Contributing
Want a new feature, found a bug, or have questions? Feel free to add to our issue board on Github:
[Open Issues](https://github.com/pyplugin/pyplugin/issues>)

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
The package is currently **not available** on pypi pending a [PEP 541 request](https://github.com/pypi/support/issues/3063>).

The package can be configured as a Github dependency in a `requirements.txt`

```
pyplugin @ git+https://github.com/pyplugin/pyplugin@main
```

or to pin to a tag

```
pyplugin @ git+https://github.com/pyplugin/pyplugin@v0.1
```
