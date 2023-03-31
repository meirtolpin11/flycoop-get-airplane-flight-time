from peewee import *

sqlite_db = SqliteDatabase('flycoop.db')


class Flights(Model):
    airplane_id = IntegerField()
    departure = DateTimeField()
    landing = DateTimeField()
    flight_time = FloatField()

    class Meta:
        database = sqlite_db

class Maintenance(Model):
    airplane_id = IntegerField()
    date = DateTimeField()

    class Meta:
        database = sqlite_db

class Airplanes(Model):
    airplane_id = IntegerField()
    registration = CharField()
    airplane_type = CharField()

    class Meta:
        database = sqlite_db


sqlite_db.create_tables([Flights, Maintenance, Airplanes])
