# Lecture 3

## Retrieval-Augmented Generation

Retrieval-augmented generation, or RAG, combines retrieval with generation. The system first retrieves relevant chunks from an external knowledge source and then conditions the generator on those retrieved chunks.

## Why Use RAG

RAG reduces hallucination because the model is asked to answer with retrieved evidence instead of relying only on parametric memory. In course-material question answering, this makes answers easier to audit and cite.

## Standard Query Pipeline

A standard RAG query pipeline preprocesses the question, retrieves top-k chunks, optionally reranks them, builds a prompt context, and then generates the final answer with citations.
