"""Render short original instrumental demo loops at image build time."""
import json
import math
import sys
import wave
from array import array
from pathlib import Path

HERE = Path(__file__).parent
DURATION = 12
RATE = 16000


def render(song, directory):
    frames = array("h")
    beat = 60 / song["bpm"]
    melody = [0, 7, 12, 4, 2, 9, 7, 4]
    for frame in range(DURATION * RATE):
        t = frame / RATE
        step = int(t / beat)
        age = t % beat
        note = song["root"] + melody[step % len(melody)]
        hz = 440 * 2 ** ((note - 69) / 12)
        attack = min(1, age / 0.018)
        env = attack * math.exp(-age * 4.4) * min(1, (beat - age) / 0.035)
        lead = math.sin(math.tau * hz * age) + 0.22 * math.sin(math.tau * hz * 2 * age)
        bass = math.sin(math.tau * 440 * 2 ** ((song["root"] - 81) / 12) * t)
        fade = min(1, t / 0.15, (DURATION - t) / 0.5)
        frames.append(round(8500 * (env * lead + 0.28 * bass) * fade))
    if sys.byteorder != "little":
        frames.byteswap()
    with wave.open(str(directory / (song["_id"] + ".wav")), "wb") as output:
        output.setparams((1, 2, RATE, 0, "NONE", "not compressed"))
        output.writeframes(frames.tobytes())


if __name__ == "__main__":
    audio = HERE / "static" / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    for track in json.loads((HERE / "catalog.json").read_text()):
        render(track, audio)
