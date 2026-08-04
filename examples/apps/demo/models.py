import dataclasses as dc

from framework.framework import model

# PEP 8 class names convert to their snake_case identifier automatically:
# Post → post, CommentThread → comment_thread.


@dc.dataclass
@model
class Post:
    id: int
    title: str


@dc.dataclass
@model
class CommentThread:
    id: int
    post_id: int
