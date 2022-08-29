import spoc


@spoc.plugin(config={"database": "default", "engine": "SQL"})
class MyType:
    name: str
