import dataclasses as dc

from framework.framework import model

# A snake_case class name already conforms, so no explicit name is needed.


@dc.dataclass
@model
class post:
    id: int
    title: str


@dc.dataclass
@model(name="comment_thread")
class CommentThread:
    id: int
    post_id: int
