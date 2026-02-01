import pathlib


def main() -> None:
    for p in pathlib.Path(__file__).parent.rglob("actions_ai_description.yaml"):
        p.unlink()


if __name__ == "__main__":
    main()
