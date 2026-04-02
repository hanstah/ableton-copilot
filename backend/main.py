import sys
import anthropic
from ableton_client import AbletonClient
from claude_client import chat


def main():
    ableton = AbletonClient()
    client = anthropic.Anthropic()
    messages = []

    # Verify connection
    try:
        info = ableton.get_session_info()
        print(f"Connected to Ableton. Tempo: {info.get('tempo')} BPM, Tracks: {len(info.get('tracks', []))}")
    except Exception as e:
        print(f"Could not connect to Ableton: {e}")
        print("Make sure Ableton is running with the MyAbletonCopilot remote script loaded.")
        sys.exit(1)

    print("\nAbleton Copilot ready. Type your request, or 'quit' to exit.\n")

    while True:
        try:
            user_input = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not user_input:
            continue
        if user_input.lower() in ('quit', 'exit', 'q'):
            print("Goodbye.")
            break

        messages.append({"role": "user", "content": user_input})

        try:
            response = chat(messages, ableton, client)
            print(f"\n{response}\n")
            messages.append({"role": "assistant", "content": response})
        except Exception as e:
            print(f"Error: {e}\n")
            # Remove the last user message so the conversation stays valid
            messages.pop()


if __name__ == '__main__':
    main()
