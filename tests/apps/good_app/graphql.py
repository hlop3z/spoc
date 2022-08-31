import spoc


@spoc.component(config={"type": "Query", "controls": "INPUT"})
class MyGQL:
    name: str
