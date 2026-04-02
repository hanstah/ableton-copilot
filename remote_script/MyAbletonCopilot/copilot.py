import socket
import threading
import json
import queue

from _Framework.ControlSurface import ControlSurface
import Live


class CopilotScript(ControlSurface):
    def __init__(self, c_instance):
        ControlSurface.__init__(self, c_instance)
        self._request_queue = queue.Queue()
        self._server_socket = None

        self._server_thread = threading.Thread(target=self._start_server)
        self._server_thread.daemon = True
        self._server_thread.start()

        self.log_message('AbletonCopilot: started, listening on port 8765')

    # Called by Ableton on the main thread every ~100ms
    def update_display(self):
        while not self._request_queue.empty():
            try:
                command, response_event, response_holder = self._request_queue.get_nowait()
                try:
                    result = self._handle_command(command)
                except Exception as e:
                    result = {'error': str(e)}
                    self.log_message('AbletonCopilot error: ' + str(e))
                response_holder['result'] = result
                response_event.set()
            except queue.Empty:
                break
            except Exception as e:
                self.log_message('AbletonCopilot queue error: ' + str(e))

    def _start_server(self):
        try:
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
        except Exception as e:
            self.log_message('AbletonCopilot server error: ' + str(e))

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

            response_event = threading.Event()
            response_holder = {}
            self._request_queue.put((command, response_event, response_holder))

            responded = response_event.wait(timeout=30.0)
            if responded and 'result' in response_holder:
                result = response_holder['result']
            else:
                result = {'error': 'Ableton did not respond in time'}

            conn.sendall((json.dumps(result) + '\n').encode())
        except Exception as e:
            try:
                conn.sendall((json.dumps({'error': str(e)}) + '\n').encode())
            except Exception:
                pass
        finally:
            conn.close()

    def _handle_command(self, command):
        action = command.get('action')
        song = self.song()

        if action == 'get_session_info':
            return {
                'tempo': song.tempo,
                'time_signature': '{}/{}'.format(
                    song.signature_numerator,
                    song.signature_denominator
                ),
                'is_playing': song.is_playing,
                'tracks': [
                    {
                        'index': i,
                        'name': t.name,
                        'type': 'midi' if t.has_midi_input else 'audio',
                        'muted': t.mute,
                        'solo': t.solo,
                        'clip_count': sum(1 for s in t.clip_slots if s.has_clip),
                    }
                    for i, t in enumerate(song.tracks)
                ],
            }

        elif action == 'set_tempo':
            song.tempo = float(command['bpm'])
            return {'ok': True}

        elif action == 'set_time_signature':
            song.signature_numerator = int(command['numerator'])
            song.signature_denominator = int(command['denominator'])
            return {'ok': True}

        elif action == 'play':
            song.start_playing()
            return {'ok': True}

        elif action == 'stop':
            song.stop_playing()
            return {'ok': True}

        elif action == 'get_clip_info':
            track = song.tracks[command['track']]
            slot = track.clip_slots[command['slot']]
            if not slot.has_clip:
                return {'has_clip': False}
            clip = slot.clip
            notes = clip.get_notes_extended(0, 128, 0, clip.length)
            return {
                'has_clip': True,
                'name': clip.name,
                'length': clip.length,
                'notes': [
                    {'pitch': n.pitch, 'start': n.start_time, 'duration': n.duration, 'velocity': n.velocity}
                    for n in notes
                ],
            }

        elif action == 'create_midi_track':
            index = int(command.get('index', -1))
            song.create_midi_track(index)
            # Return updated track list
            return {
                'ok': True,
                'track_index': len(song.tracks) - 1 if index == -1 else index,
                'tracks': [{'index': i, 'name': t.name} for i, t in enumerate(song.tracks)],
            }

        elif action == 'rename_track':
            track = song.tracks[command['track']]
            track.name = command['name']
            return {'ok': True}

        elif action == 'create_midi_clip':
            track = song.tracks[command['track']]
            slot = track.clip_slots[command['slot']]
            if slot.has_clip:
                slot.delete_clip()
            slot.create_clip(float(command.get('length', 4.0)))
            return {'ok': True}

        elif action == 'add_notes':
            track = song.tracks[command['track']]
            clip = track.clip_slots[command['slot']].clip
            notes = tuple(
                Live.Clip.MidiNoteSpecification(
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
            track = song.tracks[command['track']]
            clip = track.clip_slots[command['slot']].clip
            clip.remove_notes_extended(0, 128, 0, clip.length)
            return {'ok': True}

        elif action == 'set_track_volume':
            track = song.tracks[command['track']]
            track.mixer_device.volume.value = float(command['value'])
            return {'ok': True}

        elif action == 'set_track_mute':
            track = song.tracks[command['track']]
            track.mute = bool(command['muted'])
            return {'ok': True}

        elif action == 'set_track_solo':
            track = song.tracks[command['track']]
            track.solo = bool(command['solo'])
            return {'ok': True}

        elif action == 'delete_track':
            song.delete_track(int(command['track']))
            return {
                'ok': True,
                'tracks': [{'index': i, 'name': t.name} for i, t in enumerate(song.tracks)],
            }

        elif action == 'set_clip_name':
            track = song.tracks[command['track']]
            clip = track.clip_slots[command['slot']].clip
            clip.name = command['name']
            return {'ok': True}

        elif action == 'launch_clip':
            track = song.tracks[command['track']]
            track.clip_slots[command['slot']].fire()
            return {'ok': True}

        elif action == 'stop_clip':
            track = song.tracks[command['track']]
            track.clip_slots[command['slot']].stop()
            return {'ok': True}

        elif action == 'duplicate_clip':
            src_track = song.tracks[command['track']]
            src_slot = src_track.clip_slots[command['slot']]
            dst_track = song.tracks[command['dest_track']]
            dst_slot = dst_track.clip_slots[command['dest_slot']]
            src_slot.duplicate_clip_to(dst_slot)
            return {'ok': True}

        elif action == 'get_device_parameters':
            track = song.tracks[command['track']]
            device_index = int(command.get('device', 0))
            if device_index >= len(track.devices):
                return {'error': 'Device index out of range', 'device_count': len(track.devices)}
            device = track.devices[device_index]
            return {
                'device_name': device.name,
                'parameters': [
                    {'index': i, 'name': p.name, 'value': p.value, 'min': p.min, 'max': p.max}
                    for i, p in enumerate(device.parameters)
                ],
            }

        elif action == 'set_device_parameter':
            track = song.tracks[command['track']]
            device = track.devices[int(command.get('device', 0))]
            param = device.parameters[int(command['parameter'])]
            param.value = float(command['value'])
            return {'ok': True, 'parameter': param.name, 'value': param.value}

        else:
            return {'error': 'Unknown action: {}'.format(action)}

    def disconnect(self):
        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception:
                pass
        ControlSurface.disconnect(self)
