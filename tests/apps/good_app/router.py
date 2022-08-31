import spoc


@spoc.component(config={"click": "command"})
class MyRouter:
    name: str
