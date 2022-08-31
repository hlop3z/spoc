import spoc


@spoc.component(config={"database": "default", "engine": "SQL"})
class MyType:
    name: str
