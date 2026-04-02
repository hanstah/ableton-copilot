import socket
import json


class AbletonClient:
    def __init__(self, host='localhost', port=8765):
        self.host = host
        self.port = port

    def send(self, command: dict) -> dict:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(60.0)
        try:
            s.connect((self.host, self.port))
            s.sendall((json.dumps(command) + '\n').encode())
            data = b''
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                data += chunk
                if data.endswith(b'\n'):
                    break
            return json.loads(data.decode().strip())
        finally:
            s.close()

    def get_session_info(self) -> dict:
        return self.send({'action': 'get_session_info'})

    def set_tempo(self, bpm: float) -> dict:
        return self.send({'action': 'set_tempo', 'bpm': bpm})

    def set_time_signature(self, numerator: int, denominator: int) -> dict:
        return self.send({'action': 'set_time_signature', 'numerator': numerator, 'denominator': denominator})

    def play(self) -> dict:
        return self.send({'action': 'play'})

    def stop(self) -> dict:
        return self.send({'action': 'stop'})

    def get_clip_info(self, track: int, slot: int) -> dict:
        return self.send({'action': 'get_clip_info', 'track': track, 'slot': slot})

    def create_midi_clip(self, track: int, slot: int, length: float = 4.0) -> dict:
        return self.send({'action': 'create_midi_clip', 'track': track, 'slot': slot, 'length': length})

    def add_notes(self, track: int, slot: int, notes: list) -> dict:
        return self.send({'action': 'add_notes', 'track': track, 'slot': slot, 'notes': notes})

    def clear_clip_notes(self, track: int, slot: int) -> dict:
        return self.send({'action': 'clear_clip_notes', 'track': track, 'slot': slot})

    def set_track_volume(self, track: int, value: float) -> dict:
        return self.send({'action': 'set_track_volume', 'track': track, 'value': value})

    def set_track_mute(self, track: int, muted: bool) -> dict:
        return self.send({'action': 'set_track_mute', 'track': track, 'muted': muted})

    def set_track_solo(self, track: int, solo: bool) -> dict:
        return self.send({'action': 'set_track_solo', 'track': track, 'solo': solo})
