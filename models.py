from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from sqlalchemy import Column, Integer, String, ForeignKey, Table, DATETIME

Base = declarative_base()

tag_post = Table(
    'tag_post',
    Base.metadata,
    Column('post_id', Integer, ForeignKey('post.id')),
    Column('tag_id', Integer, ForeignKey('tag.id'))
)


class Post(Base):
    __tablename__ = 'post'
    id = Column(Integer, autoincrement=True, primary_key=True, unique=True)
    url = Column(String, unique=True, nullable=False)
    title = Column(String, unique=False, nullable=False)
    image = Column(String, unique=False, nullable=True)
    date = Column(DATETIME, unique=False)
    writer_id = Column(Integer, ForeignKey('writer.id'))
    writer = relationship("Writer", back_populates='posts')
    tags = relationship('Tag', secondary=tag_post, back_populates='posts')


# TODO Имеет смысл переименовать таблицу в users
class Writer(Base):
    __tablename__ = 'writer'
    id = Column(Integer, autoincrement=True, primary_key=True, unique=True)
    url = Column(String, unique=True, nullable=False)
    name = Column(String, unique=False, nullable=False)
    posts = relationship("Post")
    comment = relationship("Comment")


# TODO Структура избыточна, так как данные по юзерам можно взять из соотв. таблицы
class Comment(Base):
    __tablename__ = 'comment'
    id = Column(Integer, primary_key=True, unique=True)
    commentable_id = Column(Integer, unique=False, nullable=False)
    parent_id = Column(Integer, ForeignKey('comment.id'), unique=False, nullable=True)
    body = Column(String, unique=False, nullable=False)
    user_name = Column(String, unique=False, nullable=False)
    user_id = Column(Integer, ForeignKey('writer.id'))
    user_url = Column(String, unique=True, nullable=False)
    parent = relationship('Comment', remote_side=[id])
    writer = relationship("Writer", back_populates='comment')


class Tag(Base):
    __tablename__ = 'tag'
    id = Column(Integer, autoincrement=True, primary_key=True, unique=True)
    url = Column(String, unique=True, nullable=False)
    name = Column(String, unique=False, nullable=False)
    posts = relationship('Post', secondary=tag_post)
