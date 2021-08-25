# json-flattener

Python library for denormalizing/flattening lists of complex objects to tables/data frames, with roundtripping

## Notebook Example

[EXAMPLE.ipynb](https://github.com/cmungall/json-flattener/blob/main/EXAMPLE.ipynb)

## Description

Given YAML/JSON/JSON-Lines such as:

```yaml
- id: S001
  name: Lord of the Rings
  genres:
    - fantasy
  creator:
    name: JRR Tolkein
    from_country: England
  books:
    - id: S001.1
      name: Fellowship of the Ring
      price: 5.99
      summary: Hobbits
    - id: S001.2
      name: The Two Towers
      price: 5.99
      summary: More hobbits
    - id: S001.3
      name: Return of the King
      price: 6.99
      summary: Yet more hobbits
- id: S002
  name: The Culture Series
  genres:
    - scifi
  creator:
    name: Ian M Banks
    from_country: Scotland
  books:
    - id: S002.1
      name: Consider Phlebas
      price: 5.99
    - id: S002.2
      name: Player of Games
      price: 5.99
```

Denormalize using `jfl` command:

```bash
jfl flatten -C creator=flat -C books=multivalued -i examples/books1.yaml -o examples/books1-flattened.tsv
```



|id|name|genres|creator_name|creator_from_country|books_name|books_summary|books_price|books_id|creator_genres
|---|---|---|---|---|---|---|---|---|---|
|S001|Lord of the Rings|[fantasy]|JRR Tolkein|England|[Fellowship of the Ring\|The Two Towers\|Return of the King]|[Hobbits\|More hobbits\|Yet more hobbits]|[5.99\|5.99\|6.99]|[S001.1\|S001.2\|S001.3]|
|S002|The Culture Series|[scifi]|Ian M Banks|Scotland|[Consider Phlebas\|Player of Games]||[5.99\|5.99]|[S002.1\|S002.2]|


Convert back to JSON/YAML:

```bash
jfl unflatten -C creator=flat -C books=multivalued -i examples/books1.tsv -o examples/books1.yaml
```



This library also allows complex fields to be directly serialized as json or yaml (the default is to append `_json` to the key). For example:

```bash
jfl flatten -C creator=json -C books=json -i examples/books1.yaml -o examples/books1-jsonified.tsv
```

|id|name|genres|creator_json|books_json|
|---|---|---|---|---|
|S001|Lord of the Rings|[fantasy]|{\"name\": \"JRR Tolkein\", \"from_country\": \"England\"}|[{\"id\": \"S001.1\", \"name\": \"Fellowship of the Ring\", \"summary\": \"Hobbits\", \"price\": 5.99}, {\"id\": \"S001.2\", \"name\": \"The Two Towers\", \"summary\": \"More hobbits\", \"price\": 5.99}, {\"id\": \"S001.3\", \"name\": \"Return of the King\", \"summary\": \"Yet more hobbits\", \"price\": 6.99}]|
|S002|The Culture Series|[scifi]|{\"name\": \"Ian M Banks\", \"from_country\": \"Scotland\"}|[{\"id\": \"S002.1\", \"name\": \"Consider Phlebas\", \"price\": 5.99}, {\"id\": \"S002.2\", \"name\": \"Player of Games\", \"price\": 5.99}]|
|S003|Book of the New Sun|[scifi, fantasy]|{\"name\": \"Gene Wolfe\", \"genres\": [\"scifi\", \"fantasy\"], \"from_country\": \"USA\"}|[{\"id\": \"S003.1\", \"name\": \"Shadow of the Torturer\"}, {\"id\": \"S003.2\", \"name\": \"Claw of the Conciliator\", \"price\": 6.99}]|
|S004|Example with single book||{\"name\": \"Ms Writer\", \"genres\": [\"romance\"], \"from_country\": \"USA\"}|[{\"id\": \"S004.1\", \"name\": \"Blah\"}]|
|S005|Example with no books||{\"name\": \"Mr Unproductive\", \"genres\": [\"romance\", \"scifi\", \"fantasy\"], \"from_country\": \"USA\"}||


See

<iframe src="https://docs.google.com/presentation/d/e/2PACX-1vRyM06peU9BkrZbXJazuMlajw5s4Vbj5f0t0TE4hj_X9Ex_EASLSUZuaWUxYIhWbOC6CtPRtxrTGWQD/embed?start=false&loop=false&delayms=60000" frameborder="0" width="960" height="569" allowfullscreen="true" mozallowfullscreen="true" webkitallowfullscreen="true"></iframe>

The primary use case is to go from a rich *normalized* data model (as python objects, JSON, or YAML) to a flatter representation that is amenable to processing with:

 * Solr/Lucene
 * Pandas/R Dataframes
 * Excel/Google sheets
 * Unix cut/grep/cat/etc
 * Simple denormalized SQL database representations

The target denormalized format is a list of rows / a data matrix, where each cell is either an atom or a list of atoms.

## Method

 * Each top level key becomes a column
 * if the key value is a dict/object, then flatten
     * by default a '_' is used to separate the parent key from the inner key
     * e.g. the composition of `creator` and `from_country` becomes `creator_from_country`
     * currently one level of flattening is supported
 * if the key value is a list of atomic entities, then leave as is
 * if the key value is a list of dicts/objects, then flatten each key of this inner dict into a list
     * e.g. if `books` is a list of book objects, and `name` is a key on book, then `books_name` is a list of names of each book
     * order is significant - the first element of `books_name` is matched to the first element of `books_price`, etc
 * Allow any key to be serialized as yaml/json/pickle if configured

## Command line usage (TODO)

## Usage from Python

Documentation coming soon: see test folder for now


## use within LinkML



## Comparison

### Pandas json_normalize


 - https://pandas.pydata.org/pandas-docs/version/0.25.0/reference/api/pandas.io.json.json_normalize.html

### Java json-flattener

 https://github.com/wnameless/json-flattener

### Python

### csvjson

https://csvjson.com/json2csv

