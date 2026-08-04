from framework.framework import view

# View functions: snake_case function names conform on their own.


@view
def list_posts():
    return {"posts": []}


@view
def get_post():
    return {"post": None}
