## [UV Features Link](https://docs.astral.sh/uv/getting-started/features/#scripts)

## Add Dependencies

```sh
uv add "fastapi[standard]"
```

## Development Dependencies

```sh
uv add ruff --dev
```

## Development Dependencies

```sh
uv add httpx --optional network
```

## Install Tool User-Wide

```sh
uv tool install
```

## Building The Package

```sh
uvx --from build pyproject-build --installer uv
```
