from sqlalchemy import Column, Integer, String, Boolean


class Intro(Base):
    __tablename__ = 'intros'

    id = Column(Integer, primary_key=True)
    question = Column(Integer)
    age = Column(Integer)
    name = Column(String)
    pronouns = Column(String)
    about = Column(String)
    nsfw = Column(Boolean)

class Server(Base):
    __tablename__ = 'servers'

    id = Column(Integer, primary_key=True)

    intro_channel = Column(String)
    log_channel = Column(String)

    mod_role = Column(String)
    unveri_role = Column(String)
    member_role = Column(String)
    nsfw_role = Column(String)
    minor_role = Column(String)
    adult_role = Column(String)
