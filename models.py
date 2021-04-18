from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base


MemoryBase = declarative_base()

class Intro(MemoryBase):
    __tablename__ = 'intros'

    id = Column(Integer, primary_key=True)
    server = Column(Integer)

    question = Column(Integer)

    age = Column(Integer)
    name = Column(String)
    pronouns = Column(String)
    about = Column(String)
    nsfw = Column(Boolean)


StorageBase = declarative_base()

class Server(StorageBase):
    __tablename__ = 'servers'

    id = Column(Integer, primary_key=True)

    intro_channel = Column(Integer)
    log_channel = Column(Integer)

    mod_role = Column(Integer)
    unveri_role = Column(Integer)
    member_role = Column(Integer)
    nsfw_role = Column(Integer)
    minor_role = Column(Integer)
    adult_role = Column(Integer)
