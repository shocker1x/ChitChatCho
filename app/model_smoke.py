"""Make one live model call to verify local credentials and configuration."""

from agent.llm import create_llm_client


def main() -> None:
    reply = create_llm_client().complete("Reply with a brief, friendly greeting.")
    print(reply)


if __name__ == "__main__":
    main()