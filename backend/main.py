import sys
import os
from pathlib import Path
import anthropic
from dotenv import load_dotenv
from ableton_client import AbletonClient
from claude_client import chat
from song_builder import build_song, is_song_request

load_dotenv(Path(__file__).parent.parent / '.env')


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

        if is_song_request(user_input):
            print('\n[Song builder mode — planning full song before executing]\n')
            response = build_song(user_input, ableton, client)
            print(f"\n{response}\n")
        else:
            messages.append({"role": "user", "content": user_input})
            try:
                response = chat(messages, ableton, client)
                print(f"\n{response}\n")
                messages.append({"role": "assistant", "content": response})
            except Exception as e:
                print(f"Error: {e}\n")
                messages.pop()


if __name__ == '__main__':
    main()
