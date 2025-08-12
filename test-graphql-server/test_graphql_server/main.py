import strawberry
from typing import Optional
from strawberry.asgi import GraphQL

# Define a simple type
@strawberry.type
class Book:
    title: str
    author: str

# Query definition
@strawberry.type
class Query:
    @strawberry.field
    def hello(self) -> str:
        return "Hello, world!"

    @strawberry.field
    def books(self, author: Optional[str] = None) -> list[Book]:
        all_books = [
            Book(title="1984", author="George Orwell"),
            Book(title="A Brief History of Time", author="Stephen Hawking"),
            Book(title="The Selfish Gene", author="Richard Dawkins"),
            Book(title="Cosmos", author="Carl Sagan"),
            Book(title="The Origin of Species", author="Charles Darwin"),
            Book(title="The Elegant Universe", author="Brian Greene"),
            Book(title="Silent Spring", author="Rachel Carson"),
            Book(title="The Double Helix", author="James D. Watson"),
            Book(title="Why We Sleep", author="Matthew Walker"),
            Book(title="Gödel, Escher, Bach", author="Douglas Hofstadter"),
            Book(title="Surely You're Joking, Mr. Feynman!", author="Richard P. Feynman"),
            Book(title="Pale Blue Dot", author="Carl Sagan")
        ]

        if author:
            return [book for book in all_books if book.author == author]
        return all_books

# Mutation example
@strawberry.type
class Mutation:
    @strawberry.mutation
    def add_book(self, title: str, author: str) -> Book:
        # This example doesn't persist data; just returns the input
        return Book(title=title, author=author)

# Create schema and app
schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_app = GraphQL(schema)
app = graphql_app
