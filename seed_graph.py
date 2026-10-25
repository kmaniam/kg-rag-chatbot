from knowledge_graph import add_relationship, save_graph, graph_stats

facts = [
    ("Oracle Database", "supports", "Transparent Data Encryption (TDE)"),
    ("Transparent Data Encryption (TDE)", "protects", "Data at rest"),
    ("Oracle TDE", "uses", "Keystore"),
    ("Oracle DBA", "manages", "Keystore configuration"),
    ("Oracle Database", "runs on", "Windows Server"),
]

for source, relation, target in facts:
    add_relationship(
        source,
        relation,
        target,
        document="starter_knowledge",
    )

save_graph()
print("Knowledge graph saved:", graph_stats())
