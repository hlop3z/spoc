import spoc


@spoc.plugin(config={"click": "command"})
class MyRouter:
    name: str
