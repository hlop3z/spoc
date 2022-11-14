# API **Definitions**

## **Global** Tools

| Key            | Description                                                                                                            |
| -------------- | ---------------------------------------------------------------------------------------------------------------------- |
| **`base_dir`** | The base **Directory**. Path to **the project**.                                                                       |
| **`mode`**     | Framework's current **mode** (**`development`, `production`, `staging`** and **`custom`**).                            |
| **`env`**      | **Environment Variables** `TOML` file **`{env}.toml`** **Options** (**`development`, `production` , `staging`**).      |
| **`config`**   | Core (**Settings**) **`TOML`** files are **loaded here** (**`spoc.toml`**, **`pyproject.toml`** and **`{env}.toml`**). |
| **`settings`** | Pythonic (**Settings**) are **loaded here** (**`settings.py`**).                                                       |

## **Core** Tools

| Key                | Description                                                     | Variable(s)                      |
| ------------------ | --------------------------------------------------------------- | -------------------------------- |
| **`singleton`**    | Tool to create the **Framework**.                               | `(object: class)`                |
| **`component`**    | Tool to create **Component(s)** for your **Framework**.         | `(config: dict, metadata: dict)` |
| **`is_component`** | Tool to **verify** the **Component(s)** by adding **metadata**. | `(object: any, metadata: dict)`  |

**Example:**

```python
spoc.is_component(hello_world, components["command"])
```

## **FrameWork** Tools

| Key       | Description        | Variable(s)       |
| --------- | ------------------ | ----------------- |
| **`App`** | The **Framework**. | `(plugins: list)` |

**Example:**

```python
spoc.App(plugins=["commands"])
```

## **Project** Tools

| Key             | Description               |
| --------------- | ------------------------- |
| **`component`** | The **Components**.       |
| **`extras`**    | The Internal **Methods**. |
