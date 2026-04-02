import anthropic
import json
from ableton_client import AbletonClient


TOOLS = [
    {
        "name": "get_session_info",
        "description": "Get the current Ableton session state: tempo, time signature, tracks, playback status.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "set_tempo",
        "description": "Set the session tempo in BPM.",
        "input_schema": {
            "type": "object",
            "properties": {
                "bpm": {"type": "number", "description": "Tempo in BPM (e.g. 120)"}
            },
            "required": ["bpm"],
        },
    },
    {
        "name": "set_time_signature",
        "description": "Set the session time signature.",
        "input_schema": {
            "type": "object",
            "properties": {
                "numerator": {"type": "integer", "description": "Top number (e.g. 4 for 4/4)"},
                "denominator": {"type": "integer", "description": "Bottom number (e.g. 4 for 4/4)"},
            },
            "required": ["numerator", "denominator"],
        },
    },
    {
        "name": "play",
        "description": "Start Ableton playback.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "stop",
        "description": "Stop Ableton playback.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_clip_info",
        "description": "Get details about a clip in a track slot, including its MIDI notes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "track": {"type": "integer", "description": "Track index (0-based)"},
                "slot": {"type": "integer", "description": "Clip slot index (0-based)"},
            },
            "required": ["track", "slot"],
        },
    },
    {
        "name": "create_midi_clip",
        "description": "Create a new empty MIDI clip in a track slot.",
        "input_schema": {
            "type": "object",
            "properties": {
                "track": {"type": "integer", "description": "Track index (0-based)"},
                "slot": {"type": "integer", "description": "Clip slot index (0-based)"},
                "length": {"type": "number", "description": "Clip length in beats (default 4.0)"},
            },
            "required": ["track", "slot"],
        },
    },
    {
        "name": "add_notes",
        "description": "Add MIDI notes to an existing clip.",
        "input_schema": {
            "type": "object",
            "properties": {
                "track": {"type": "integer", "description": "Track index (0-based)"},
                "slot": {"type": "integer", "description": "Clip slot index (0-based)"},
                "notes": {
                    "type": "array",
                    "description": "List of MIDI notes to add",
                    "items": {
                        "type": "object",
                        "properties": {
                            "pitch": {"type": "integer", "description": "MIDI note number (0-127). Middle C = 60"},
                            "start": {"type": "number", "description": "Start time in beats from clip start"},
                            "duration": {"type": "number", "description": "Note duration in beats"},
                            "velocity": {"type": "integer", "description": "Note velocity (0-127), default 100"},
                        },
                        "required": ["pitch", "start", "duration"],
                    },
                },
            },
            "required": ["track", "slot", "notes"],
        },
    },
    {
        "name": "clear_clip_notes",
        "description": "Remove all MIDI notes from a clip.",
        "input_schema": {
            "type": "object",
            "properties": {
                "track": {"type": "integer", "description": "Track index (0-based)"},
                "slot": {"type": "integer", "description": "Clip slot index (0-based)"},
            },
            "required": ["track", "slot"],
        },
    },
    {
        "name": "set_track_volume",
        "description": "Set a track's volume. Value is 0.0 (silent) to 1.0 (full).",
        "input_schema": {
            "type": "object",
            "properties": {
                "track": {"type": "integer"},
                "value": {"type": "number", "description": "Volume level 0.0–1.0"},
            },
            "required": ["track", "value"],
        },
    },
    {
        "name": "set_track_mute",
        "description": "Mute or unmute a track.",
        "input_schema": {
            "type": "object",
            "properties": {
                "track": {"type": "integer"},
                "muted": {"type": "boolean"},
            },
            "required": ["track", "muted"],
        },
    },
    {
        "name": "create_midi_track",
        "description": "Create a new MIDI track in the session.",
        "input_schema": {
            "type": "object",
            "properties": {
                "index": {"type": "integer", "description": "Position to insert the track (0-based). Use -1 to append at the end."},
            },
        },
    },
    {
        "name": "rename_track",
        "description": "Rename a track.",
        "input_schema": {
            "type": "object",
            "properties": {
                "track": {"type": "integer", "description": "Track index (0-based)"},
                "name": {"type": "string", "description": "New name for the track"},
            },
            "required": ["track", "name"],
        },
    },
    {
        "name": "list_instruments",
        "description": "List available instruments in the Ableton browser. Call this to discover what instruments can be loaded before calling load_instrument.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "load_instrument",
        "description": "Load an instrument onto a track by name. Use list_instruments first to find exact names. This replaces any existing instrument on the track.",
        "input_schema": {
            "type": "object",
            "properties": {
                "track": {"type": "integer", "description": "Track index (0-based)"},
                "name": {"type": "string", "description": "Exact instrument name as returned by list_instruments"},
            },
            "required": ["track", "name"],
        },
    },
    {
        "name": "delete_track",
        "description": "Delete a track from the session.",
        "input_schema": {
            "type": "object",
            "properties": {
                "track": {"type": "integer", "description": "Track index (0-based)"},
            },
            "required": ["track"],
        },
    },
    {
        "name": "set_clip_name",
        "description": "Set the name of a clip.",
        "input_schema": {
            "type": "object",
            "properties": {
                "track": {"type": "integer", "description": "Track index (0-based)"},
                "slot": {"type": "integer", "description": "Clip slot index (0-based)"},
                "name": {"type": "string", "description": "New clip name"},
            },
            "required": ["track", "slot", "name"],
        },
    },
    {
        "name": "launch_clip",
        "description": "Launch (play) a clip in a track slot.",
        "input_schema": {
            "type": "object",
            "properties": {
                "track": {"type": "integer", "description": "Track index (0-based)"},
                "slot": {"type": "integer", "description": "Clip slot index (0-based)"},
            },
            "required": ["track", "slot"],
        },
    },
    {
        "name": "stop_clip",
        "description": "Stop a playing clip in a track slot.",
        "input_schema": {
            "type": "object",
            "properties": {
                "track": {"type": "integer", "description": "Track index (0-based)"},
                "slot": {"type": "integer", "description": "Clip slot index (0-based)"},
            },
            "required": ["track", "slot"],
        },
    },
    {
        "name": "duplicate_clip",
        "description": "Duplicate a clip to another track/slot.",
        "input_schema": {
            "type": "object",
            "properties": {
                "track": {"type": "integer", "description": "Source track index (0-based)"},
                "slot": {"type": "integer", "description": "Source slot index (0-based)"},
                "dest_track": {"type": "integer", "description": "Destination track index (0-based)"},
                "dest_slot": {"type": "integer", "description": "Destination slot index (0-based)"},
            },
            "required": ["track", "slot", "dest_track", "dest_slot"],
        },
    },
    {
        "name": "get_device_parameters",
        "description": "Get all parameters for a device (instrument or effect) on a track. Call this before set_device_parameter to find parameter indices.",
        "input_schema": {
            "type": "object",
            "properties": {
                "track": {"type": "integer", "description": "Track index (0-based)"},
                "device": {"type": "integer", "description": "Device index on the track (0-based, default 0)"},
            },
            "required": ["track"],
        },
    },
    {
        "name": "set_device_parameter",
        "description": "Set a parameter value on a device (instrument or effect). Use get_device_parameters first to find the parameter index.",
        "input_schema": {
            "type": "object",
            "properties": {
                "track": {"type": "integer", "description": "Track index (0-based)"},
                "device": {"type": "integer", "description": "Device index on the track (0-based, default 0)"},
                "parameter": {"type": "integer", "description": "Parameter index from get_device_parameters"},
                "value": {"type": "number", "description": "New parameter value (within the parameter's min/max range)"},
            },
            "required": ["track", "parameter", "value"],
        },
    },
    {
        "name": "set_track_solo",
        "description": "Solo or unsolo a track.",
        "input_schema": {
            "type": "object",
            "properties": {
                "track": {"type": "integer"},
                "solo": {"type": "boolean"},
            },
            "required": ["track", "solo"],
        },
    },
]

SYSTEM_PROMPT = """You are an expert music producer and Ableton Live copilot. You create professional-quality music by combining deep music theory knowledge with precise control of Ableton Live.

## Instrument loading — CRITICAL RULES
- ALWAYS call list_instruments before load_instrument. Never guess or assume instrument names.
- Pick the best match from the returned list for the part (Wavetable for pads/leads, Operator for FM bass/sounds, Drum Rack for drums, Simpler for samples).
- After loading, call get_device_parameters then use set_device_parameter to shape the sound for the genre.

## MIDI reference
Notes: C4=60, D4=62, E4=64, F4=65, G4=67, A4=69, B4=71, C5=72
Timing: beat 1=0.0, beat 2=1.0, beat 3=2.0, beat 4=3.0 (4/4 time)

## MIDI quality rules

**Melodies**: Use scale-appropriate notes with musical phrasing. Vary note lengths (mix 0.25, 0.5, 1.0 beat durations). Add rests between phrases. Avoid robotic even spacing. Velocity 70-100.

**Chords/Pads**: Voice properly — use inversions, spread notes across 2 octaves. Don't stack all notes at the same octave. Velocity 60-80. Long durations (2-4 beats).

**Bass**: Stay in low octaves (C2=36, C3=48). Use rhythmic patterns that complement the kick. Velocity 90-110.

**Drums** (standard Drum Rack MIDI mapping):
- Kick=36, Snare=38, Closed Hi-hat=42, Open Hi-hat=46, Clap=39
- Kick on beats 1 & 3 (0.0, 2.0), Snare on 2 & 4 (1.0, 3.0)
- Hi-hats every 0.5 beats (8th notes) or 0.25 (16th notes)
- Vary velocities: kick 110-127, snare 90-110, hi-hats 50-80

**Humanization**: Always vary velocities slightly across repeated notes. Never use identical velocity for every note.

## Song creation workflow
1. get_session_info to check existing state
2. Set tempo and time signature for the genre
3. Call list_instruments ONCE to see all available instruments
4. For each part: create_midi_track → rename_track → load_instrument (exact name from list) → shape sound with set_device_parameter → create_midi_clip → set_clip_name → add_notes
5. Balance mix: lead ~0.85, pads ~0.7, bass ~0.8, drums ~0.9
6. One track per instrument — never share tracks

## Genre reference
- **Future bass / Illenium-style**: 140-150 BPM, A minor or C major, supersaw chords (Wavetable), emotional soaring lead melody, punchy 808 bass, four-on-the-floor kick + syncopated hi-hats
- **Lo-fi hip hop**: 70-90 BPM, jazz chords (maj7, min7), dusty drums, warm bass, mellow pads
- **House**: 120-128 BPM, four-on-the-floor kick, offbeat open hats, chord stabs on 2 & 4, walking bass
- **Trap**: 130-160 BPM (half-time feel), 808 slides, rapid 1/32 hi-hat rolls, sparse snare on beat 3"""


def run_tool(name: str, inputs: dict, ableton: AbletonClient) -> str:
    if name == 'get_session_info':
        return json.dumps(ableton.get_session_info())
    elif name == 'set_tempo':
        return json.dumps(ableton.set_tempo(inputs['bpm']))
    elif name == 'set_time_signature':
        return json.dumps(ableton.set_time_signature(inputs['numerator'], inputs['denominator']))
    elif name == 'play':
        return json.dumps(ableton.play())
    elif name == 'stop':
        return json.dumps(ableton.stop())
    elif name == 'get_clip_info':
        return json.dumps(ableton.get_clip_info(inputs['track'], inputs['slot']))
    elif name == 'create_midi_clip':
        return json.dumps(ableton.create_midi_clip(inputs['track'], inputs['slot'], inputs.get('length', 4.0)))
    elif name == 'add_notes':
        return json.dumps(ableton.add_notes(inputs['track'], inputs['slot'], inputs['notes']))
    elif name == 'clear_clip_notes':
        return json.dumps(ableton.clear_clip_notes(inputs['track'], inputs['slot']))
    elif name == 'create_midi_track':
        return json.dumps(ableton.send({'action': 'create_midi_track', 'index': inputs.get('index', -1)}))
    elif name == 'rename_track':
        return json.dumps(ableton.send({'action': 'rename_track', 'track': inputs['track'], 'name': inputs['name']}))
    elif name == 'set_track_volume':
        return json.dumps(ableton.set_track_volume(inputs['track'], inputs['value']))
    elif name == 'set_track_mute':
        return json.dumps(ableton.set_track_mute(inputs['track'], inputs['muted']))
    elif name == 'set_track_solo':
        return json.dumps(ableton.set_track_solo(inputs['track'], inputs['solo']))
    elif name == 'list_instruments':
        return json.dumps(ableton.send({'action': 'list_instruments'}))
    elif name == 'load_instrument':
        return json.dumps(ableton.send({'action': 'load_instrument', 'track': inputs['track'], 'name': inputs['name']}))
    elif name == 'delete_track':
        return json.dumps(ableton.send({'action': 'delete_track', 'track': inputs['track']}))
    elif name == 'set_clip_name':
        return json.dumps(ableton.send({'action': 'set_clip_name', 'track': inputs['track'], 'slot': inputs['slot'], 'name': inputs['name']}))
    elif name == 'launch_clip':
        return json.dumps(ableton.send({'action': 'launch_clip', 'track': inputs['track'], 'slot': inputs['slot']}))
    elif name == 'stop_clip':
        return json.dumps(ableton.send({'action': 'stop_clip', 'track': inputs['track'], 'slot': inputs['slot']}))
    elif name == 'duplicate_clip':
        return json.dumps(ableton.send({'action': 'duplicate_clip', 'track': inputs['track'], 'slot': inputs['slot'], 'dest_track': inputs['dest_track'], 'dest_slot': inputs['dest_slot']}))
    elif name == 'get_device_parameters':
        return json.dumps(ableton.send({'action': 'get_device_parameters', 'track': inputs['track'], 'device': inputs.get('device', 0)}))
    elif name == 'set_device_parameter':
        return json.dumps(ableton.send({'action': 'set_device_parameter', 'track': inputs['track'], 'device': inputs.get('device', 0), 'parameter': inputs['parameter'], 'value': inputs['value']}))
    else:
        return json.dumps({'error': f'Unknown tool: {name}'})


def chat(messages: list, ableton: AbletonClient, client: anthropic.Anthropic) -> str:
    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        # Collect any text from this response turn
        text_output = ''
        tool_uses = []
        for block in response.content:
            if block.type == 'text':
                text_output += block.text
            elif block.type == 'tool_use':
                tool_uses.append(block)

        if response.stop_reason == 'end_turn' or not tool_uses:
            return text_output

        # Execute all tool calls and feed results back
        messages.append({'role': 'assistant', 'content': response.content})

        tool_results = []
        for block in tool_uses:
            print(f'  [tool: {block.name}]')
            result = run_tool(block.name, block.input, ableton)
            tool_results.append({
                'type': 'tool_result',
                'tool_use_id': block.id,
                'content': result,
            })

        messages.append({'role': 'user', 'content': tool_results})
