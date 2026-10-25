import json
import re
from pathlib import Path

import networkx as nx

GRAPH_DIR = Path("/app/data/knowledge_graph")
GRAPH_DIR.mkdir(parents=True, exist_ok=True)
GRAPH_FILE = GRAPH_DIR / "oracle_knowledge_graph.json"

graph = nx.MultiDiGraph()


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def add_relationship(source, relation, target, document="unknown"):
    source = normalize(source)
    relation = normalize(relation)
    target = normalize(target)
    document = normalize(document)

    if not source or not relation or not target:
        return False

    # Avoid duplicate edges from the same source document.
    for _, _, data in graph.edges(source, data=True):
        pass

    if graph.has_edge(source, target):
        for _, data in graph[source][target].items():
            if (
                data.get("relation", "").casefold() == relation.casefold()
                and data.get("source_document", "unknown") == document
            ):
                return False

    graph.add_node(source, label=source)
    graph.add_node(target, label=target)
    graph.add_edge(
        source,
        target,
        relation=relation,
        source_document=document,
    )
    return True


def remove_document_relationships(document):
    """Remove only edges extracted from this document, not starter facts."""
    to_remove = []

    for source, target, key, data in graph.edges(keys=True, data=True):
        if (
            data.get("source_document") == document
            and document != "starter_knowledge"
        ):
            to_remove.append((source, target, key))

    graph.remove_edges_from(to_remove)

    # Remove orphaned nodes only if they have no remaining relationships.
    for node in list(graph.nodes):
        if graph.degree(node) == 0:
            graph.remove_node(node)


def save_graph():
    data = nx.node_link_data(graph)
    GRAPH_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_graph():
    if not GRAPH_FILE.exists():
        return

    data = json.loads(GRAPH_FILE.read_text(encoding="utf-8"))
    restored = nx.node_link_graph(data, directed=True, multigraph=True)

    graph.clear()
    graph.graph.update(restored.graph)
    graph.add_nodes_from(restored.nodes(data=True))
    graph.add_edges_from(restored.edges(data=True, keys=True))


def search_graph(question: str, limit: int = 8):
    """Rank graph relationships by relevance to the question."""
    terms = set(re.findall(r"[a-zA-Z0-9]+", question.lower()))

    # Ignore common words that rarely help identify a graph fact.
    stop_words = {
        "what", "which", "when", "where", "why", "how", "does",
        "do", "did", "is", "are", "was", "were", "the", "a", "an",
        "and", "or", "to", "of", "for", "in", "on", "with", "should",
        "can", "could", "would", "before", "after", "about", "explain",
        "tell", "me", "please", "use", "used"
    }
    terms -= stop_words

    if not terms:
        return []

    ranked = []

    for source, target, data in graph.edges(data=True):
        relation = data.get("relation", "related to")
        source_doc = data.get("source_document", "unknown")

        source_terms = set(re.findall(r"[a-zA-Z0-9]+", source.lower()))
        target_terms = set(re.findall(r"[a-zA-Z0-9]+", target.lower()))
        relation_terms = set(re.findall(r"[a-zA-Z0-9]+", relation.lower()))

        entity_overlap = terms & (source_terms | target_terms)
        relation_overlap = terms & relation_terms

        # Require at least one meaningful entity or relation match.
        if not entity_overlap and not relation_overlap:
            continue

        score = (
            3 * len(terms & source_terms)
            + 3 * len(terms & target_terms)
            + len(relation_overlap)
        )

        # Prefer uploaded-document facts over starter examples.
        if source_doc != "starter_knowledge":
            score += 1

        rendered = (
            f"{source} --[{relation}]--> {target} "
            f"(source: {source_doc})"
        )
        ranked.append((score, rendered))

    ranked.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in ranked[:limit] if item[0] > 0]


def graph_stats():
    return {
        "entities": graph.number_of_nodes(),
        "relationships": graph.number_of_edges(),
    }


load_graph()
