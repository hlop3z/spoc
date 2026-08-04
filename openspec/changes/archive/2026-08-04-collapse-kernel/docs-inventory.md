# API reference inventory — task 1.3

39 `:::` directives across `docs/docs/api/*.md`. `mkdocs build --strict` fails on any that
no longer resolve, so every row marked DELETE or MOVE must be actioned in task 8.1.

## `core-utils.md`

| Directive                                  | Action | Reason                                  |
| ------------------------------------------ | ------ | --------------------------------------- |
| `spoc.core.exceptions.SpocError`           | KEEP   |                                         |
| `spoc.core.exceptions.AppNotFoundError`    | KEEP   |                                         |
| `spoc.core.exceptions.ModuleNotCachedError`| DELETE | cache API removed (task 4.4), no raiser |
| `spoc.core.exceptions.CircularDependencyError` | KEEP |                                       |
| `spoc.core.exceptions.ConfigurationError`  | KEEP   |                                         |
| `spoc.case_style.case_style`               | DELETE | style dispatcher removed (task 2.1)     |
| `spoc.case_style.to_snake_case`            | MOVE   | → `spoc.core.identity.to_snake_case`    |
| `spoc.case_style.to_camel_case`            | DELETE | task 2.1                                |
| `spoc.case_style.to_pascal_case`           | DELETE | task 2.1                                |
| `spoc.case_style.to_kebab_case`            | DELETE | task 2.1                                |
| `spoc.case_style.is_valid_case_style`      | DELETE | task 2.1                                |
| `spoc.inject_apps.inject_apps`             | MOVE   | → `spoc.core.paths.inject_apps`         |
| `spoc.inject_apps.ensure_directory`        | DELETE | one-line internal helper                |
| `spoc.inject_apps.add_to_python_path`      | DELETE | one-line internal helper                |

## `components.md`

| Directive                     | Action | Reason                                    |
| ----------------------------- | ------ | ----------------------------------------- |
| `spoc.components.component`   | MOVE   | → `spoc.core.declaration.component`       |
| `spoc.components.Internal`    | MOVE   | → `spoc.core.declaration.Internal`        |
| `spoc.components.is_spoc`     | MOVE   | → `spoc.core.declaration.is_spoc`         |
| `spoc.components.get_info`    | MOVE   | → `spoc.core.declaration.get_info`        |
| *(new)* `KindSpec`            | ADD    | the per-kind record (task 3.1)            |

## `registry.md`

| Directive                                     | Action | Reason                       |
| --------------------------------------------- | ------ | ---------------------------- |
| `spoc.core.registry.Registry`                 | KEEP   |                              |
| `spoc.core.registry.Component`                | KEEP   |                              |
| `spoc.core.identifier.parse`                  | MOVE   | → `spoc.core.identity.parse` |
| `spoc.core.identifier.compose`                | MOVE   | → `spoc.core.identity.compose` |
| `spoc.core.identifier.validate_segment`       | MOVE   | → `spoc.core.identity.validate_segment` |
| `spoc.core.identifier.Identifier`             | MOVE   | → `spoc.core.identity.Identifier` |
| `spoc.core.exceptions.MalformedIdentifierError` | KEEP |                              |
| `spoc.core.exceptions.InvalidSegmentError`    | KEEP   |                              |
| `spoc.core.exceptions.UnknownKindError`       | KEEP   |                              |
| `spoc.core.exceptions.UnknownNamespaceError`  | KEEP   |                              |
| `spoc.core.exceptions.UnknownObjectError`     | KEEP   |                              |
| `spoc.core.exceptions.DuplicateComponentError`| KEEP   |                              |
| `spoc.core.exceptions.ComponentKindMismatchError` | KEEP |                            |
| `spoc.core.exceptions.MissingNameError`       | KEEP   |                              |
| *(new)* `MetadataContractError`               | ADD    | task 3.5                     |
| *(new)* `MissingModuleError`                  | ADD    | task 4.7                     |

## `framework.md`

| Directive                      | Action | Reason                                   |
| ------------------------------ | ------ | ---------------------------------------- |
| `spoc.framework.Framework`     | KEEP   |                                          |
| `spoc.framework.Config`        | KEEP   |                                          |
| `spoc.framework.build_config`  | DELETE | becomes internal to the config adapter   |

## `importer.md`

| Directive                                          | Action | Reason                                |
| -------------------------------------------------- | ------ | ------------------------------------- |
| `spoc.core.importer.Importer`                      | MOVE   | → `spoc.core.loader.Loader` (task 7.2) |
| `spoc.core.importer.ModuleInfo`                    | DELETE | internal dataclass (task 4.6)         |
| `spoc.core.components_discovery.discover_components` | MOVE | → `spoc.core.declaration.discover`    |

## Module renames driving the MOVE rows

| Before                          | After                    |
| ------------------------------- | ------------------------ |
| `case_style.py` + `core/identifier.py` | `core/identity.py` |
| `components.py` + `core/components_discovery.py` | `core/declaration.py` |
| `core/importer.py`              | `core/loader.py`         |
| `core/config_loader.py` + `core/toml_core.py` | `core/config.py` |
| `inject_apps.py`                | `core/paths.py`          |
