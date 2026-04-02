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

SYSTEM_PROMPT = """You are an Ableton Live copilot. You help music producers control and create music in their Ableton session using natural language.

You have tools to:
- Read session state (tempo, tracks, clips, MIDI notes)
- Control playback (play, stop)
- Modify session settings (tempo, time signature)
- Create and edit MIDI clips (create clips, add notes, clear notes)
- Mix tracks (volume, mute, solo)

When creating MIDI, think carefully about music theory:
- Use appropriate scales and chord voicings for the genre/mood requested
- Consider rhythm, groove, and note duration for the style
- Middle C is MIDI note 60. C4=60, D4=62, E4=64, F4=65, G4=67, A4=69, B4=71, C5=72
- Beats start at 0.0. In 4/4 time, beat 1=0.0, beat 2=1.0, beat 3=2.0, beat 4=3.0

Always call get_session_info first if you need to know the current state of the session before making changes."""


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
    elif name == 'set_track_volume':
        return json.dumps(ableton.set_track_volume(inputs['track'], inputs['value']))
    elif name == 'set_track_mute':
        return json.dumps(ableton.set_track_mute(inputs['track'], inputs['muted']))
    elif name == 'set_track_solo':
        return json.dumps(ableton.set_track_solo(inputs['track'], inputs['solo']))
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
