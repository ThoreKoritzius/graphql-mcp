import strawberry
import enum
from typing import List
from strawberry.asgi import GraphQL
from faker import Faker
import random

FAKER_SEED = 42
faker = Faker()
faker.seed_instance(FAKER_SEED)
random.seed(FAKER_SEED)

# ---- ENUMS ----
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

# ---- DATA CLASSES ----

@strawberry.type
class Location:
    city: str
    country: str
    address: str

@strawberry.type
class Award:
    name: str
    year: int

@strawberry.type
class Review:
    reviewer: str
    rating: float
    comment: str

@strawberry.type
class Genre:
    name: str
    description: str

@strawberry.type
class Employee:
    name: str
    position: str
    email: str

@strawberry.type
class Store:
    name: str
    location: Location
    employees: List[Employee]

@strawberry.type
class Shipment:
    tracking_number: str
    shipped_date: str
    delivered_date: str

@strawberry.type
class Warehouse:
    name: str
    location: Location
    shipments: List[Shipment]

@strawberry.type
class Membership:
    member_id: str
    start_date: str
    end_date: str

@strawberry.type
class Subscription:
    type: str
    active: bool

@strawberry.type
class Agency:
    name: str
    clients: List["Client"]

@strawberry.type
class Client:
    name: str
    agency: "Agency" = None  # Filled after creation

@strawberry.type
class Currency:
    code: str
    name: str

@strawberry.type
class Contract:
    contract_id: str
    signed_date: str
    parties: List[str]

@strawberry.type
class Event:
    name: str
    date: str
    location: Location

@strawberry.type
class LanguageInfo:
    language: Language
    proficiency: str

@strawberry.type
class Author:
    name: str
    bio: str
    location: Location
    awards: List[Award]
    agency: Agency
    books: List["Book"] = None  # Filled after creation

@strawberry.type
class Publisher:
    name: str
    location: Location
    books: List["Book"] = None  # Filled after creation
    employees: List[Employee]
    warehouses: List[Warehouse]

@strawberry.type
class Distributor:
    name: str
    location: Location
    owned_books: List["Book"] = None  # Filled after creation
    contracts: List[Contract]

@strawberry.type
class Seller:
    name: str
    location: Location
    books_for_sale: List["Book"] = None  # Filled after creation
    store: Store

@strawberry.type
class Book:
    title: str
    author: Author
    publisher: Publisher
    distributor: Distributor
    sellers: List[Seller]
    genre: Genre
    published_year: int
    format: BookFormat
    language: Language
    awards: List[Award]
    reviews: List[Review]
    events: List[Event]
    warehouse: Warehouse
    shipments: List[Shipment]
    membership: Membership
    subscription: Subscription
    agency: Agency
    contract: Contract
    currency: Currency
    language_info: LanguageInfo

# ---- PRE-GENERATE DATA ----

NUM_BOOKS = 8
NUM_AUTHORS = 5
NUM_PUBLISHERS = 3
NUM_DISTRIBUTORS = 3
NUM_SELLERS = 4
NUM_GENRES = 4
NUM_AWARDS = 4
NUM_REVIEWS = 6
NUM_EMPLOYEES = 10
NUM_STORES = 2
NUM_SHIPMENTS = 6
NUM_WAREHOUSES = 2
NUM_MEMBERSHIPS = 4
NUM_SUBSCRIPTIONS = 3
NUM_AGENCIES = 2
NUM_CLIENTS = 3
NUM_CURRENCIES = 2
NUM_CONTRACTS = 2
NUM_EVENTS = 2
NUM_LANGUAGEINFOS = 3

def gen_locations(n):
    return [Location(city=faker.city(), country=faker.country(), address=faker.address()) for _ in range(n)]

LOCATIONS = gen_locations(NUM_PUBLISHERS + NUM_DISTRIBUTORS + NUM_SELLERS + NUM_STORES + NUM_WAREHOUSES)

AWARDS = [Award(name=faker.word().title() + " Award", year=int(faker.year())) for _ in range(NUM_AWARDS)]
REVIEWS = [Review(reviewer=faker.name(), rating=round(faker.random.uniform(1,5),1), comment=faker.sentence()) for _ in range(NUM_REVIEWS)]
GENRES = [Genre(name=faker.word().title(), description=faker.text(max_nb_chars=60)) for _ in range(NUM_GENRES)]
EMPLOYEES = [Employee(name=faker.name(), position=faker.job(), email=faker.email()) for _ in range(NUM_EMPLOYEES)]
SHIPMENTS = [Shipment(tracking_number=faker.uuid4(), shipped_date=faker.date(), delivered_date=faker.date()) for _ in range(NUM_SHIPMENTS)]
MEMBERSHIPS = [Membership(member_id=faker.uuid4(), start_date=faker.date(), end_date=faker.date()) for _ in range(NUM_MEMBERSHIPS)]
SUBSCRIPTIONS = [Subscription(type=faker.word(), active=faker.boolean()) for _ in range(NUM_SUBSCRIPTIONS)]
CURRENCIES = [Currency(code=faker.currency_code(), name=faker.currency_name()) for _ in range(NUM_CURRENCIES)]
CONTRACTS = [Contract(
    contract_id=faker.uuid4(), signed_date=faker.date(), parties=[faker.company() for _ in range(2)]
) for _ in range(NUM_CONTRACTS)]
EVENTS = [Event(name=faker.word().title() + " Event", date=faker.date(), location=LOCATIONS[i%len(LOCATIONS)]) for i in range(NUM_EVENTS)]
LANGUAGEINFOS = [LanguageInfo(language=Language.EN, proficiency=faker.word()) for _ in range(NUM_LANGUAGEINFOS)]

# Stores and Warehouses
STORES = [Store(name=faker.company(), location=LOCATIONS[NUM_PUBLISHERS+i], employees=EMPLOYEES[i*2:(i+1)*2]) for i in range(NUM_STORES)]
WAREHOUSES = [Warehouse(name=faker.company(), location=LOCATIONS[NUM_PUBLISHERS+NUM_DISTRIBUTORS+i], shipments=SHIPMENTS[i*3:(i+1)*3]) for i in range(NUM_WAREHOUSES)]

# Agencies/Clients
AGENCIES = []
CLIENTS = []
for i in range(NUM_AGENCIES):
    CL = [Client(name=faker.name()) for _ in range(NUM_CLIENTS)]
    AGENCIES.append(Agency(name=faker.company(), clients=CL))
    for c in CL:
        c.agency = AGENCIES[-1]
    CLIENTS.extend(CL)

# Authors (empty books list for now, will fill later after Book creation)
AUTHORS = [
    Author(
        name=faker.name(),
        bio=faker.text(max_nb_chars=120),
        location=LOCATIONS[i%len(LOCATIONS)],
        awards=[AWARDS[i%len(AWARDS)]],
        agency=AGENCIES[i%len(AGENCIES)],
    )
    for i in range(NUM_AUTHORS)
]

# Publishers (empty books list for now, will fill later)
PUBLISHERS = [
    Publisher(
        name=faker.company(),
        location=LOCATIONS[i%len(LOCATIONS)],
        employees=EMPLOYEES[i*3:(i+1)*3],
        warehouses=WAREHOUSES
    )
    for i in range(NUM_PUBLISHERS)
]

# Distributors (empty owned_books for now)
DISTRIBUTORS = [
    Distributor(
        name=faker.company(),
        location=LOCATIONS[(NUM_PUBLISHERS+i)%len(LOCATIONS)],
        contracts=CONTRACTS,
    )
    for i in range(NUM_DISTRIBUTORS)
]

# Sellers (empty books_for_sale for now)
SELLERS = [
    Seller(
        name=faker.company(),
        location=LOCATIONS[(NUM_PUBLISHERS+NUM_DISTRIBUTORS+i)%len(LOCATIONS)],
        store=STORES[i%len(STORES)],
    )
    for i in range(NUM_SELLERS)
]

# Now, create the books, and fill in all references!
BOOKS = []
for i in range(NUM_BOOKS):
    # Distribute related objects round-robin
    author = AUTHORS[i % NUM_AUTHORS]
    publisher = PUBLISHERS[i % NUM_PUBLISHERS]
    distributor = DISTRIBUTORS[i % NUM_DISTRIBUTORS]
    sellers = [SELLERS[i % NUM_SELLERS]]
    awards = [AWARDS[i % len(AWARDS)]]
    reviews = [REVIEWS[i % len(REVIEWS)]]
    events = [EVENTS[i % len(EVENTS)]]
    warehouse = WAREHOUSES[i % len(WAREHOUSES)]
    shipments = [SHIPMENTS[i % len(SHIPMENTS)]]
    membership = MEMBERSHIPS[i % len(MEMBERSHIPS)]
    subscription = SUBSCRIPTIONS[i % len(SUBSCRIPTIONS)]
    agency = author.agency
    contract = CONTRACTS[i % len(CONTRACTS)]
    currency = CURRENCIES[i%len(CURRENCIES)]
    language_info = LANGUAGEINFOS[i % len(LANGUAGEINFOS)]
    genre = GENRES[i % len(GENRES)]
    
    book = Book(
        title=faker.sentence(nb_words=4),
        author=author,
        publisher=publisher,
        distributor=distributor,
        sellers=sellers,
        genre=genre,
        published_year=int(faker.year()),
        format=BookFormat.HARDCOVER,
        language=Language.EN,
        awards=awards,
        reviews=reviews,
        events=events,
        warehouse=warehouse,
        shipments=shipments,
        membership=membership,
        subscription=subscription,
        agency=agency,
        contract=contract,
        currency=currency,
        language_info=language_info,
    )
    BOOKS.append(book)

# Fill backrefs
for a in AUTHORS:
    a.books = [b for b in BOOKS if b.author is a]
for p in PUBLISHERS:
    p.books = [b for b in BOOKS if b.publisher is p]
for d in DISTRIBUTORS:
    d.owned_books = [b for b in BOOKS if b.distributor is d]
for s in SELLERS:
    s.books_for_sale = [b for b in BOOKS if s in b.sellers]

# ---- QUERY AND MUTATION ----

@strawberry.type
class Query:
    @strawberry.field
    def books(self) -> List[Book]:
        return BOOKS

    @strawberry.field
    def authors(self) -> List[Author]:
        return AUTHORS

    @strawberry.field
    def publishers(self) -> List[Publisher]:
        return PUBLISHERS

    @strawberry.field
    def distributors(self) -> List[Distributor]:
        return DISTRIBUTORS

    @strawberry.field
    def sellers(self) -> List[Seller]:
        return SELLERS

    @strawberry.field
    def genres(self) -> List[Genre]:
        return GENRES

    @strawberry.field
    def awards(self) -> List[Award]:
        return AWARDS

    @strawberry.field
    def reviews(self) -> List[Review]:
        return REVIEWS

    @strawberry.field
    def stores(self) -> List[Store]:
        return STORES

    @strawberry.field
    def employees(self) -> List[Employee]:
        return EMPLOYEES

    @strawberry.field
    def shipments(self) -> List[Shipment]:
        return SHIPMENTS

    @strawberry.field
    def warehouses(self) -> List[Warehouse]:
        return WAREHOUSES

    @strawberry.field
    def memberships(self) -> List[Membership]:
        return MEMBERSHIPS

    @strawberry.field
    def subscriptions(self) -> List[Subscription]:
        return SUBSCRIPTIONS

    @strawberry.field
    def agencies(self) -> List[Agency]:
        return AGENCIES

    @strawberry.field
    def clients(self) -> List[Client]:
        return CLIENTS

    @strawberry.field
    def currencies(self) -> List[Currency]:
        return CURRENCIES

    @strawberry.field
    def contracts(self) -> List[Contract]:
        return CONTRACTS

    @strawberry.field
    def events(self) -> List[Event]:
        return EVENTS

    @strawberry.field
    def language_infos(self) -> List[LanguageInfo]:
        return LANGUAGEINFOS

    @strawberry.field
    def hello(self) -> str:
        return "Hello, fixed world!"

@strawberry.type
class Mutation:
    @strawberry.mutation
    def add_book(self, title: str, author_name: str, publisher_name: str) -> Book:
        # No-op: Just return first book (demo purposes)
        return BOOKS[0]

schema = strawberry.Schema(query=Query, mutation=Mutation)
app = GraphQL(schema)
graphql_app = app