import Live
import socket
import threading
import json


class CopilotScript:
    def __init__(self, c_instance):
        self._live = c_instance
        self._song = c_instance.song()
        self._server_socket = None

        self._thread = threading.Thread(target=self._start_server)
        self._thread.daemon = True
        self._thread.start()

    def _start_server(self):
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind(('localhost', 8765))
        self._server_socket.listen(5)
        while True:
            try:
                conn, _ = self._server_socket.accept()
                handler = threading.Thread(target=self._handle_connection, args=(conn,))
                handler.daemon = True
                handler.start()
            except Exception:
                break

    def _handle_connection(self, conn):
        try:
            data = b''
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                data += chunk
                if data.endswith(b'\n'):
                    break
            command = json.loads(data.decode().strip())
            result = self._handle_command(command)
            conn.sendall((json.dumps(result) + '\n').encode())
        except Exception as e:
            conn.sendall((json.dumps({'error': str(e)}) + '\n').encode())
        finally:
            conn.close()

    def _handle_command(self, command):
        action = command.get('action')

        if action == 'get_session_info':
            return {
                'tempo': self._song.tempo,
                'time_signature': f"{self._song.signature_numerator}/{self._song.signature_denominator}",
                'is_playing': self._song.is_playing,
                'tracks': [
                    {
                        'index': i,
                        'name': t.name,
                        'muted': t.mute,
                        'solo': t.solo,
                        'clip_count': sum(1 for s in t.clip_slots if s.has_clip),
                    }
                    for i, t in enumerate(self._song.tracks)
                ],
            }

        elif action == 'set_tempo':
            self._song.tempo = float(command['bpm'])
            return {'ok': True}

        elif action == 'set_time_signature':
            self._song.signature_numerator = int(command['numerator'])
            self._song.signature_denominator = int(command['denominator'])
            return {'ok': True}

        elif action == 'play':
            self._song.start_playing()
            return {'ok': True}

        elif action == 'stop':
            self._song.stop_playing()
            return {'ok': True}

        elif action == 'get_clip_info':
            track = self._song.tracks[command['track']]
            slot = track.clip_slots[command['slot']]
            if not slot.has_clip:
                return {'has_clip': False}
            clip = slot.clip
            notes = clip.get_notes(0, 0, clip.length, 128)
            return {
                'has_clip': True,
                'name': clip.name,
                'length': clip.length,
                'notes': [
                    {'pitch': n[0], 'start': n[1], 'duration': n[2], 'velocity': n[3]}
                    for n in notes
                ],
            }

        elif action == 'create_midi_clip':
            track = self._song.tracks[command['track']]
            slot = track.clip_slots[command['slot']]
            if slot.has_clip:
                slot.delete_clip()
            slot.create_clip(float(command.get('length', 4.0)))
            return {'ok': True}

        elif action == 'add_notes':
            track = self._song.tracks[command['track']]
            clip = track.clip_slots[command['slot']].clip
            notes = tuple(
                Live.Clip.MidiNote(
                    pitch=int(n['pitch']),
                    start_time=float(n['start']),
                    duration=float(n['duration']),
                    velocity=int(n.get('velocity', 100)),
                    mute=False,
                )
                for n in command['notes']
            )
            clip.add_new_notes(notes)
            return {'ok': True}

        elif action == 'clear_clip_notes':
            track = self._song.tracks[command['track']]
            clip = track.clip_slots[command['slot']].clip
            clip.remove_notes(0, 0, clip.length, 128)
            return {'ok': True}

        elif action == 'set_track_volume':
            track = self._song.tracks[command['track']]
            track.mixer_device.volume.value = float(command['value'])
            return {'ok': True}

        elif action == 'set_track_mute':
            track = self._song.tracks[command['track']]
            track.mute = bool(command['muted'])
            return {'ok': True}

        elif action == 'set_track_solo':
            track = self._song.tracks[command['track']]
            track.solo = bool(command['solo'])
            return {'ok': True}

        else:
            return {'error': f'Unknown action: {action}'}

    def disconnect(self):
        if self._server_socket:
            self._server_socket.close()
