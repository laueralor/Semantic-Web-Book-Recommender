NAMESPACES = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "ex": "http://example.org/booksystem#"
}

XPATH_USERS = ".//rdf:Description[ex:name]"
XPATH_BOOKS = ".//rdf:Description[ex:title]"

XPATH_USER_NAME = "./ex:name"
XPATH_USER_LEVEL = "./ex:readingLevel"
XPATH_USER_THEME = "./ex:preferredTheme"

XPATH_BOOK_TITLE = "./ex:title"
XPATH_BOOK_GENRE = "./ex:genre"
XPATH_BOOK_REQ_LEVEL = "./ex:requiredLevel"