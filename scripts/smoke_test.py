from src.retrieval.retriever import Retriever


QUERIES = (
    "ELSS lock-in period",
    "exit load of mid cap fund",
    "minimum SIP for mid cap fund",
)


def main() -> None:
    retriever = Retriever()
    for query in QUERIES:
        hits = retriever.retrieve(query)
        if not hits:
            raise RuntimeError(f"No qualifying vector hits for smoke query: {query}")
        print(f"\n{query}")
        for hit in hits[:3]:
            print(
                f"  score={hit['score']:.3f} "
                f"section={hit['metadata']['section']} "
                f"text={hit['text'][:180]}"
            )


if __name__ == "__main__":
    main()
