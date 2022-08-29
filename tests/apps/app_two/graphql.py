import spoc


@spoc.plugin(config={"type": "Query", "controls": "INPUT"})
class MyGQL:
    name: str
