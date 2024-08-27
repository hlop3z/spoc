#

<div style="text-align:center; margin-top: -60px;">
 <img src="assets/images/title.png" alt="Alt text" class="title-image" />
</div>

**SPOC** is a foundational framework designed to create dynamic and adaptable **`frameworks`**. It involves defining a schema for your **project**(s) and building upon that schema to create a flexible and powerful Application.

---

<p align="center" class="name-acronym" >
    {{ acronym("Single") }} — 
    {{ acronym("Point") }} — 
    {{ acronym("Of") }} — 
    {{ acronym("Connections") }}
</p>

---

<!-- termynal -->

```
$ python -m pip install spoc
---> 100%
Successfully installed spoc!
```

---

## SPOC **Workflow**

```mermaid
sequenceDiagram
autonumber
    Spoc -->> Framework: Create a Framework
    Note over Spoc,Framework: Step 1: Establish the Framework

    Note over Framework,Framework: Step 2: Handle the Components

    Framework -->> Application: Use Components
    Note over Framework,Application: Step 3: Extend Application

    Application -->> Spoc: Register the Application(s)
    Note over Spoc,Application: Step 4 to 7: Initialize the Framework

    Spoc -) Application: Load Settings
    Spoc -) Application: Load Environment Variables
    Spoc -) Application: Load Extra Components
    Spoc -) Application: Load Installed Apps

    Note over Application: Final Step: Utilize the Application(s)
```

### Explanation

- **Create a Framework Using SPOC**: Start by using SPOC to define the structure of your framework. This involves setting up the initial framework architecture.

- **Handle Components within the Framework**: Organize and manage the various components that make up your framework. These components are the building blocks that define the functionality of your framework.

- **Extend the Application Using Framework Components**: Incorporate the framework's components into your application. This step involves integrating these components to enhance and extend the capabilities of your application.

- **Register Applications with the Framework and SPOC**: Connect your applications to the framework, thereby registering them with SPOC. This registration process ensures that all applications are aware of the framework's components and configurations.

- **Load All Necessary Elements**: Sequentially load all required settings, environment variables, extra components, and installed apps into the framework. This step ensures that all elements are properly initialized and ready for use.

- **Utilize Your Fully Loaded Applications**: Once everything is loaded, you can effectively use your applications. This final step allows you to leverage all loaded components, extras, settings, and environment variables to operate your applications smoothly within the framework.

---

## Key Features of **SPOC**

### **Collecting Designated `Objects`**

**SPOC** enables you to collect specific **`Objects`** using a **`@custom_decorator`**.

**Example:**

```python title="example.py"
@component
def hello_world():
    print("Hello World")
```

### **Loading Extras**

To include **Extras**, list them under a dedicated **`attribute`** in your configuration file.

**Configuration Example:**

```toml title="spoc.toml"
[spoc]
# ...

[spoc.extras]
middleware = ["demo.middleware.function"] # (1)
before_server = ["demo.middleware.before_server_function"] # (2)
```

1. Extra of type **`middleware`**
2. Extra of type **`before_server`**

<style>
    .mermaid{
        text-align:center
    }
</style>
