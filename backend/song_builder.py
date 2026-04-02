import json
import re
import anthropic
from ableton_client import AbletonClient


PLAN_SYSTEM_PROMPT = """You are an expert music producer. Given a song request, available instruments, and available effects, you produce a complete song plan as a single JSON object.

## MIDI reference
Notes: C2=36, C3=48, C4=60, D4=62, E4=64, F4=65, G4=67, A4=69, B4=71, C5=72, D5=74, E5=76, F5=77, G5=79, A5=81
Timing: beat 1=0.0, beat 2=1.0, beat 3=2.0, beat 4=3.0 in 4/4 time

## Drums (standard Drum Rack MIDI mapping)
Kick=36, Snare=38, Closed Hi-hat=42, Open Hi-hat=46, Clap=39, Ride=51, Crash=49
- Kick on beats 1 & 3 (0.0, 2.0), Snare on 2 & 4 (1.0, 3.0)
- Hi-hats every 0.5 beats for 8th notes, 0.25 for 16th notes
- Vary velocities: kick 110-127, snare 90-110, hi-hats 50-80 (vary each one slightly)

## Quality rules
- Melodies: use scale-appropriate notes, vary note lengths (mix 0.25/0.5/1.0/2.0 beats), add rests, avoid robotic even spacing
- Chords/Pads: proper voicing across 2 octaves, use inversions, long durations (2-4 beats), velocity 60-80
- Bass: low octaves (C2=36, C3=48), rhythmic patterns complementing kick, velocity 90-110
- Humanization: always vary velocities slightly — never identical velocity on every note
- Each scene should have different energy: Intro=sparse, Verse=building, Chorus=full energy, Outro=stripping back
- Write at least 8 bars (32 beats) of notes per clip for melodic parts, 4 bars (16 beats) for drums

## Output format
Return ONLY a valid JSON object with this exact structure, no other text:

{
  "tempo": <number>,
  "time_signature": {"numerator": <int>, "denominator": <int>},
  "key": "<key name>",
  "scenes": ["<name>", ...],
  "tracks": [
    {
      "name": "<track name>",
      "instrument": "<exact name from available instruments list>",
      "effects": ["<exact name from available effects list>"],
      "volume": <0.0-1.0>,
      "clips": {
        "<scene_index_as_string>": {
          "name": "<clip name>",
          "length": <beats as number>,
          "notes": [
            {"pitch": <int>, "start": <float>, "duration": <float>, "velocity": <int>},
            ...
          ]
        }
      }
    }
  ]
}

Use only instrument and effect names that appear exactly in the provided available lists.
Not every track needs a clip in every scene — omit scenes where an instrument is silent."""


def gather_context(ableton: AbletonClient) -> dict:
    print('  [gathering session info, instruments, effects...]')
    session = ableton.get_session_info()
    instruments = ableton.send({'action': 'list_instruments'})
    effects = ableton.send({'action': 'list_audio_effects'})
    return {
        'session': session,
        'instruments': instruments,
        'effects': effects,
    }


def plan_song(user_request: str, context: dict, client: anthropic.Anthropic) -> dict:
    prompt = f"""Song request: {user_request}

Available instruments:
{json.dumps(context['instruments'], indent=2)}

Available audio effects:
{json.dumps(context['effects'], indent=2)}

Current session state:
{json.dumps(context['session'], indent=2)}

Produce the complete song plan JSON now."""

    print('  [planning song — thinking through the whole structure...]')
    response = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=16000,
        system=PLAN_SYSTEM_PROMPT,
        messages=[{'role': 'user', 'content': prompt}],
    )

    raw = response.content[0].text.strip()

    # Strip markdown code fences if present
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)

    return json.loads(raw)


def execute_plan(plan: dict, ableton: AbletonClient):
    song = plan

    print(f'\n  Setting tempo: {song["tempo"]} BPM')
    ableton.set_tempo(song['tempo'])
    ableton.set_time_signature(
        song['time_signature']['numerator'],
        song['time_signature']['denominator'],
    )

    # Create scenes
    existing = ableton.send({'action': 'get_scenes'})
    existing_count = len(existing.get('scenes', []))
    needed = len(song['scenes'])

    for i in range(needed):
        if i >= existing_count:
            ableton.send({'action': 'create_scene', 'index': -1})
        ableton.send({'action': 'rename_scene', 'scene': i, 'name': song['scenes'][i]})
        print(f'  Scene {i}: {song["scenes"][i]}')

    # Create and populate tracks
    for track_plan in song['tracks']:
        print(f'\n  Building track: {track_plan["name"]}')

        # Create track
        result = ableton.send({'action': 'create_midi_track', 'index': -1})
        track_index = result['track_index']
        ableton.send({'action': 'rename_track', 'track': track_index, 'name': track_plan['name']})

        # Load instrument
        instrument = track_plan.get('instrument')
        if instrument:
            print(f'    Loading instrument: {instrument}')
            result = ableton.send({'action': 'load_instrument', 'track': track_index, 'name': instrument})
            if result.get('error'):
                print(f'    Warning: {result["error"]}')

        # Load effects
        for effect_name in track_plan.get('effects', []):
            print(f'    Loading effect: {effect_name}')
            result = ableton.send({'action': 'load_audio_effect', 'track': track_index, 'name': effect_name})
            if result.get('error'):
                print(f'    Warning: {result["error"]}')

        # Set volume
        volume = track_plan.get('volume', 0.8)
        ableton.set_track_volume(track_index, volume)

        # Populate clips per scene
        for scene_index_str, clip_plan in track_plan.get('clips', {}).items():
            scene_index = int(scene_index_str)
            scene_name = song['scenes'][scene_index] if scene_index < len(song['scenes']) else str(scene_index)
            print(f'    Writing clip: {clip_plan["name"]} ({scene_name})')

            ableton.send({
                'action': 'create_midi_clip',
                'track': track_index,
                'slot': scene_index,
                'length': clip_plan['length'],
            })
            ableton.send({
                'action': 'set_clip_name',
                'track': track_index,
                'slot': scene_index,
                'name': clip_plan['name'],
            })

            notes = clip_plan.get('notes', [])
            if notes:
                ableton.add_notes(track_index, scene_index, notes)

    print('\n  Done!')


def is_song_request(user_input: str) -> bool:
    keywords = ['create a song', 'make a song', 'build a song', 'write a song',
                'create a track', 'make a track', 'generate a song', 'compose a song',
                'song like', 'sounds like', 'in the style of']
    lower = user_input.lower()
    return any(k in lower for k in keywords)


def build_song(user_request: str, ableton: AbletonClient, client: anthropic.Anthropic) -> str:
    try:
        context = gather_context(ableton)
        plan = plan_song(user_request, context, client)

        # Show the plan summary before executing
        print(f'\n  Plan: {plan.get("key", "")} at {plan["tempo"]} BPM')
        print(f'  Scenes: {", ".join(plan["scenes"])}')
        print(f'  Tracks: {", ".join(t["name"] for t in plan["tracks"])}')
        print()

        execute_plan(plan, ableton)

        scene_list = ', '.join(plan['scenes'])
        track_list = ', '.join(t['name'] for t in plan['tracks'])
        return (
            f'Done! Built a {plan.get("key", "")} song at {plan["tempo"]} BPM.\n'
            f'Scenes: {scene_list}\n'
            f'Tracks: {track_list}\n\n'
            f'Launch each scene in order to play through the song.'
        )
    except json.JSONDecodeError as e:
        return f'Failed to parse song plan: {e}'
    except Exception as e:
        return f'Error building song: {e}'
