# Welcome to **S.P.O.C**

**SPOC** aims to be the **base** for building **elastic** **`frameworks`**.
The idea is to create a schema for your **project**(s) and then build up on that **schema**.

> **S.P.O.C** is the acronym of **Single Point of Contact**

---

## Spoc **WorkFlow**

```mermaid
sequenceDiagram
autonumber
    Spoc -->> Framework: Create a Framework
    Spoc -->> Framework: Create a Project
    Note over Spoc,Framework: Step[1]: Create your Framework's Base
    Framework -->> Component: Create a Component
    Note over Component,Framework: Step[2]: Create your Components
    Component -->> Spoc: Register the Component
    Note over Spoc,Framework: Step[3]: Build your Framework
    Spoc -) Framework: Load the Settings
    Spoc -) Framework: Load Installed Apps
    Spoc -) Framework: Load all Components
    Note over Spoc,Framework: Finally: Use your Framework
```
