"""Terminal chat with the support agent. Run: python cli.py"""

from dotenv import load_dotenv

from agent import SupportAgent

load_dotenv()


def main() -> None:
    agent = SupportAgent()
    history: list = []
    print("Support agent ready. Type 'quit' to exit.\n")
    while True:
        user = input("You: ").strip()
        if user.lower() in {"quit", "exit"}:
            break
        if not user:
            continue
        result = agent.run(user, history)
        history = result.messages
        print(f"\nAgent: {result.answer}\n")


if __name__ == "__main__":
    main()
