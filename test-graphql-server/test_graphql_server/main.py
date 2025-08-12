import strawberry
import enum
from typing import List
from strawberry.asgi import GraphQL
from faker import Faker

faker = Faker()



# --- BEGIN MASSIVE SCHEMA ---
def random_list(cls, min=1, max=5):
    return [cls() for _ in range(faker.random_int(min=min, max=max))]

@strawberry.enum
class BookFormat(enum.Enum):
    HARDCOVER = "HARDCOVER"
    PAPERBACK = "PAPERBACK"
    EBOOK = "EBOOK"
    AUDIOBOOK = "AUDIOBOOK"

@strawberry.enum
class Language(enum.Enum):
    EN = "EN"
    DE = "DE"
    FR = "FR"
    ES = "ES"
    IT = "IT"
    ZH = "ZH"

@strawberry.type
class Location:
    @strawberry.field
    def city(self) -> str: return faker.city()
    @strawberry.field
    def country(self) -> str: return faker.country()
    @strawberry.field
    def address(self) -> str: return faker.address()

@strawberry.type
class Award:
    @strawberry.field
    def name(self) -> str: return faker.word().title() + " Award"
    @strawberry.field
    def year(self) -> int: return int(faker.year())

@strawberry.type
class Review:
    @strawberry.field
    def reviewer(self) -> str: return faker.name()
    @strawberry.field
    def rating(self) -> float: return round(faker.pyfloat(left_digits=1, right_digits=1, positive=True, min_value=1, max_value=5), 1)
    @strawberry.field
    def comment(self) -> str: return faker.sentence()

@strawberry.type
class Genre:
    @strawberry.field
    def name(self) -> str: return faker.word().title()
    @strawberry.field
    def description(self) -> str: return faker.text(max_nb_chars=60)

@strawberry.type
class Employee:
    @strawberry.field
    def name(self) -> str: return faker.name()
    @strawberry.field
    def position(self) -> str: return faker.job()
    @strawberry.field
    def email(self) -> str: return faker.email()

@strawberry.type
class Store:
    @strawberry.field
    def name(self) -> str: return faker.company()
    @strawberry.field
    def location(self) -> Location: return Location()
    @strawberry.field
    def employees(self) -> List[Employee]: return random_list(Employee, 2, 10)

@strawberry.type
class Shipment:
    @strawberry.field
    def tracking_number(self) -> str: return faker.uuid4()
    @strawberry.field
    def shipped_date(self) -> str: return faker.date()
    @strawberry.field
    def delivered_date(self) -> str: return faker.date()

@strawberry.type
class Warehouse:
    @strawberry.field
    def name(self) -> str: return faker.company()
    @strawberry.field
    def location(self) -> Location: return Location()
    @strawberry.field
    def shipments(self) -> List[Shipment]: return random_list(Shipment, 1, 5)

@strawberry.type
class Membership:
    @strawberry.field
    def member_id(self) -> str: return faker.uuid4()
    @strawberry.field
    def start_date(self) -> str: return faker.date()
    @strawberry.field
    def end_date(self) -> str: return faker.date()

@strawberry.type
class Subscription:
    @strawberry.field
    def type(self) -> str: return faker.word()
    @strawberry.field
    def active(self) -> bool: return faker.boolean()

@strawberry.type
class Agency:
    @strawberry.field
    def name(self) -> str: return faker.company()
    @strawberry.field
    def clients(self) -> List["Client"]: return random_list(Client, 1, 5)

@strawberry.type
class Client:
    @strawberry.field
    def name(self) -> str: return faker.name()
    @strawberry.field
    def agency(self) -> Agency: return Agency()

@strawberry.type
class Currency:
    @strawberry.field
    def code(self) -> str: return faker.currency_code()
    @strawberry.field
    def name(self) -> str: return faker.currency_name()

@strawberry.type
class Contract:
    @strawberry.field
    def contract_id(self) -> str: return faker.uuid4()
    @strawberry.field
    def signed_date(self) -> str: return faker.date()
    @strawberry.field
    def parties(self) -> List[str]: return [faker.company() for _ in range(faker.random_int(min=2, max=5))]

@strawberry.type
class Event:
    @strawberry.field
    def name(self) -> str: return faker.word().title() + " Event"
    @strawberry.field
    def date(self) -> str: return faker.date()
    @strawberry.field
    def location(self) -> Location: return Location()

@strawberry.type
class LanguageInfo:
    @strawberry.field
    def language(self) -> Language:
        return faker.random_element(list(Language))
    @strawberry.field
    def proficiency(self) -> str: return faker.word()

# ... add 80+ more types in similar fashion ...

# Example: Generate many types dynamically
for i in range(20, 101):
    exec(f"""
@strawberry.type
class Type{i}:
    @strawberry.field
    def field1(self) -> str: return faker.word()
    @strawberry.field
    def field2(self) -> int: return faker.random_int(min=1, max=100)
    @strawberry.field
    def field3(self) -> bool: return faker.boolean()
    @strawberry.field
    def field4(self) -> float: return faker.pyfloat(left_digits=2, right_digits=2, positive=True)
    @strawberry.field
    def field5(self) -> str: return faker.sentence()
    """)

@strawberry.type
class Author:
    @strawberry.field
    def name(self) -> str: return faker.name()
    @strawberry.field
    def bio(self) -> str: return faker.text(max_nb_chars=120)
    @strawberry.field
    def location(self) -> Location: return Location()
    @strawberry.field
    def awards(self) -> List[Award]: return random_list(Award, 0, 3)
    @strawberry.field
    def books(self) -> List["Book"]: return random_list(Book, 1, 5)
    @strawberry.field
    def agency(self) -> Agency: return Agency()

@strawberry.type
class Publisher:
    @strawberry.field
    def name(self) -> str: return faker.company()
    @strawberry.field
    def location(self) -> Location: return Location()
    @strawberry.field
    def books(self) -> List["Book"]: return random_list(Book, 2, 8)
    @strawberry.field
    def employees(self) -> List[Employee]: return random_list(Employee, 5, 20)
    @strawberry.field
    def warehouses(self) -> List[Warehouse]: return random_list(Warehouse, 1, 3)

@strawberry.type
class Distributor:
    @strawberry.field
    def name(self) -> str: return faker.company()
    @strawberry.field
    def location(self) -> Location: return Location()
    @strawberry.field
    def owned_books(self) -> List["Book"]: return random_list(Book, 3, 10)
    @strawberry.field
    def contracts(self) -> List[Contract]: return random_list(Contract, 1, 5)

@strawberry.type
class Seller:
    @strawberry.field
    def name(self) -> str: return faker.company()
    @strawberry.field
    def location(self) -> Location: return Location()
    @strawberry.field
    def books_for_sale(self) -> List["Book"]: return random_list(Book, 1, 6)
    @strawberry.field
    def store(self) -> Store: return Store()

@strawberry.type
class Book:
    @strawberry.field
    def title(self) -> str: return faker.sentence(nb_words=4)
    @strawberry.field
    def author(self) -> Author: return Author()
    @strawberry.field
    def publisher(self) -> Publisher: return Publisher()
    @strawberry.field
    def distributor(self) -> Distributor: return Distributor()
    @strawberry.field
    def sellers(self) -> List[Seller]: return random_list(Seller, 1, 4)
    @strawberry.field
    def genre(self) -> Genre: return Genre()
    @strawberry.field
    def published_year(self) -> int: return int(faker.year())
    @strawberry.field
    def format(self) -> BookFormat:
        return faker.random_element(list(BookFormat))
    @strawberry.field
    def language(self) -> Language:
        return faker.random_element(list(Language))
    @strawberry.field
    def awards(self) -> List[Award]: return random_list(Award, 0, 2)
    @strawberry.field
    def reviews(self) -> List[Review]: return random_list(Review, 0, 5)
    @strawberry.field
    def events(self) -> List[Event]: return random_list(Event, 0, 2)
    @strawberry.field
    def warehouse(self) -> Warehouse: return Warehouse()
    @strawberry.field
    def shipments(self) -> List[Shipment]: return random_list(Shipment, 0, 3)
    @strawberry.field
    def membership(self) -> Membership: return Membership()
    @strawberry.field
    def subscription(self) -> Subscription: return Subscription()
    @strawberry.field
    def agency(self) -> Agency: return Agency()
    @strawberry.field
    def contract(self) -> Contract: return Contract()
    @strawberry.field
    def currency(self) -> Currency: return Currency()
    @strawberry.field
    def language_info(self) -> LanguageInfo: return LanguageInfo()


# Query definition
@strawberry.type
class Query:
    @strawberry.field
    def hello(self) -> str:
        return faker.sentence()

    @strawberry.field
    def books(self) -> List[Book]:
        return [Book() for _ in range(faker.random_int(min=5, max=20))]
    @strawberry.field
    def authors(self) -> List[Author]:
        return [Author() for _ in range(faker.random_int(min=5, max=20))]
    @strawberry.field
    def publishers(self) -> List[Publisher]:
        return [Publisher() for _ in range(faker.random_int(min=3, max=10))]
    @strawberry.field
    def distributors(self) -> List[Distributor]:
        return [Distributor() for _ in range(faker.random_int(min=2, max=8))]
    @strawberry.field
    def sellers(self) -> List[Seller]:
        return [Seller() for _ in range(faker.random_int(min=5, max=15))]
    @strawberry.field
    def genres(self) -> List[Genre]:
        return [Genre() for _ in range(faker.random_int(min=5, max=15))]
    @strawberry.field
    def awards(self) -> List[Award]:
        return [Award() for _ in range(faker.random_int(min=2, max=10))]
    @strawberry.field
    def reviews(self) -> List[Review]:
        return [Review() for _ in range(faker.random_int(min=5, max=20))]
    @strawberry.field
    def stores(self) -> List[Store]:
        return [Store() for _ in range(faker.random_int(min=3, max=10))]
    @strawberry.field
    def employees(self) -> List[Employee]:
        return [Employee() for _ in range(faker.random_int(min=10, max=30))]
    @strawberry.field
    def shipments(self) -> List[Shipment]:
        return [Shipment() for _ in range(faker.random_int(min=5, max=15))]
    @strawberry.field
    def warehouses(self) -> List[Warehouse]:
        return [Warehouse() for _ in range(faker.random_int(min=2, max=6))]
    @strawberry.field
    def memberships(self) -> List[Membership]:
        return [Membership() for _ in range(faker.random_int(min=5, max=15))]
    @strawberry.field
    def subscriptions(self) -> List[Subscription]:
        return [Subscription() for _ in range(faker.random_int(min=5, max=15))]
    @strawberry.field
    def agencies(self) -> List[Agency]:
        return [Agency() for _ in range(faker.random_int(min=2, max=8))]
    @strawberry.field
    def clients(self) -> List[Client]:
        return [Client() for _ in range(faker.random_int(min=5, max=20))]
    @strawberry.field
    def currencies(self) -> List[Currency]:
        return [Currency() for _ in range(faker.random_int(min=3, max=10))]
    @strawberry.field
    def contracts(self) -> List[Contract]:
        return [Contract() for _ in range(faker.random_int(min=5, max=15))]
    @strawberry.field
    def events(self) -> List[Event]:
        return [Event() for _ in range(faker.random_int(min=2, max=8))]
    @strawberry.field
    def language_infos(self) -> List[LanguageInfo]:
        return [LanguageInfo() for _ in range(faker.random_int(min=5, max=15))]


# Mutation example
@strawberry.type
class Mutation:
    @strawberry.mutation
    def add_book(self, title: str, author_name: str, publisher_name: str) -> Book:
        # Just return a Book with random data, ignoring input for faker-only demo
        return Book()

# Create schema and app
schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_app = GraphQL(schema)
app = graphql_app
