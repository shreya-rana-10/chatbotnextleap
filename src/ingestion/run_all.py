from src.ingestion import chunk, embed, load_docs, scrape, store


def run() -> None:
    scrape.run()
    load_docs.run()
    chunk.run()
    embed.run()
    store.run()


if __name__ == "__main__":
    run()
