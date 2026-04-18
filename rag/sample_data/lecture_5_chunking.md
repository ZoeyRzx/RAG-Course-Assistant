# Lecture 5

## Chunking Strategy

Chunking should usually preserve paragraph or section boundaries. A practical starting point is around 400 to 800 tokens per chunk, with a small overlap to keep neighboring context.

## Overlap

A typical overlap range is about 50 to 120 tokens. Too little overlap can lose context across boundaries, while too much overlap increases redundancy and index size.

## Retriever Defaults

For a first version of a RAG system, top-k values around 3 to 5 are usually enough. Retrieving too many chunks can pollute the prompt and make generation less focused.
