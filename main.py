import asyncio
import traceback

from nicegui import ui, app, run
import datetime
import time
import os
import shutil
import json
import tinytag
from faster_whisper import WhisperModel
from my_constants import *

os.makedirs(PROCESSED_DIR,exist_ok=True)
app.add_static_files(url_path='/static',local_directory=PROCESSED_DIR)



try:
    with open("cache.json") as f:
        files = json.loads(f.read())
    for row in files:
        try:
            float(row["datetime"])
            row["datetime"] = datetime.datetime.fromtimestamp(row["datetime"]).strftime('%m/%d/%Y %I:%M:%S %p')
        except:
            pass
except:
    files = []

def run_speech_to_text(model):
    for row in files:
        if not row["text"]:
            print(f"TTS on {row['fpath']}")
            # transcription not done
            try:
                segments, info = model.transcribe(row["fpath"], beam_size=5, language="en", vad_filter=True)
                if segments:
                    row["text"] = "".join(seg.text for seg in segments).strip() or "-"
                else:
                    row["text"] = "-"
                print(f"\t'{row['text']}'")
                with open("cache.json", 'w') as f:
                    f.write(json.dumps(files))
            except:
                print(traceback.format_exc())
                row["text"] = "-"
def load_file(fname):
    try:
        print('Process', fname)
        fpath = os.path.join(SOURCE_DIR, fname)
        metadata = tinytag.TinyTag.get(fpath)
        meta_processed = {
            "talkgroup": metadata.title,
            "length": metadata.duration,
            "datetime": datetime.datetime.fromtimestamp(os.path.getmtime(fpath)).strftime(
                '%m/%d/%Y %I:%M:%S %p'),
            "fname": f"/static/{fname}",
            "fpath": os.path.join(PROCESSED_DIR, fname),
            "text": ""
        }
        shutil.move(fpath, os.path.join(PROCESSED_DIR, fname))

        files.insert(0, meta_processed)
        with open("cache.json", 'w') as f:
            f.write(json.dumps(files, indent=2))
    except Exception as e:
        print(fname, e)

async def triggger_scan_for_files():
    wait_q = {} # maps file name to release time
    while True:
        if len(os.listdir(SOURCE_DIR)):
            for fname in os.listdir(SOURCE_DIR):
                if fname not in wait_q:
                    wait_q[fname] = time.time() + REBROADCAST_DELAY_SECONDS
                    print("enqueue", fname)

            poplist = []
            for fname, release_time in wait_q.items():
                if time.time() >= release_time:
                    print("process", fname)
                    await run.io_bound(load_file,fname)
                    poplist.append(fname)

            for p in poplist:
                wait_q.pop(p)

        await asyncio.sleep(1)

async def trigger_speech_to_text():
    model = await run.io_bound(WhisperModel, MODEL, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE)

    while True:
        await run.io_bound(run_speech_to_text, model)
        await asyncio.sleep(1)

app.on_startup(trigger_speech_to_text)
app.on_startup(triggger_scan_for_files)



@ui.page("/")
def main():
    # Request Android to not go into power-save mode
    ui.run_javascript('''
        let wakeLock = null;
        const requestWakeLock = async () => {
            try {
                wakeLock = await navigator.wakeLock.request('screen');
                console.log('Wake Lock is active');
            } catch (err) {
                console.error(`${err.name}, ${err.message}`);
            }
        };
        // Request lock when the page is clicked (browsers require a gesture)
        document.addEventListener('click', requestWakeLock);

        if ('mediaSession' in navigator) {{
                navigator.mediaSession.metadata = new MediaMetadata({{
                    title: 'Live Audio Stream',
                    artist: 'NiceGUI Server',
                    album: 'Auto-Refresh Table'
                }});
            }}
    ''')
    label_last_update_time = ui.label(
        f"Last updated {datetime.datetime.now().strftime('%m/%d/%Y %I:%M:%S %p')} ({os.path.getsize(PROCESSED_DIR) / 1024 / 1024} MB)")

    cb_auto_refresh = ui.checkbox("Auto-refresh on new files", value=True)
    cb_auto_play = ui.checkbox("Auto-play new files", value=False)
    cb_auto_refresh_tts = ui.checkbox("Auto-refresh on new text", value=False)

    def refresh():
        label_last_update_time.set_text(
            f"Last updated {datetime.datetime.now().strftime('%m/%d/%Y %I:%M:%S %p')} ({os.path.getsize(PROCESSED_DIR) / 1024 / 1024} MB)")
        table.rows[:] = files
        table.update()

    def scan_refresh():
        do_auto_play = False
        if (cb_auto_play.value and len(table.rows) != len(files)):
            do_auto_play = True

        if (cb_auto_refresh.value and len(table.rows) != len(files)) or (cb_auto_refresh_tts.value and  any([cf != uf for cf, uf in zip(table.rows, files)])):
            refresh()

        if do_auto_play:
            ui.run_javascript('setTimeout(() => { document.querySelector("audio").play() }, 500)')

    ui.button('Refresh', on_click=refresh)
    table = ui.table(columns=[
            {'name': 'talkgroup', 'label': 'Talkgroup', 'field': 'talkgroup', 'required': True, 'align': 'left',
             'sortable': True},
            {'name': 'text', 'label': 'Speech-To-Text', 'field': 'text', 'align': 'left', 'style': 'text-wrap: wrap'},
            {'name': 'fname', 'label': 'Audio File', 'field': 'fname', 'align': 'left'},
            {'name': 'datetime', 'label': 'Datetime', 'field': 'datetime', 'required': True, 'align': 'left',
             'sortable': True},
            # {'name': 'length', 'label': 'Length', 'field': 'length', 'required': True, 'align': 'left', 'sortable': True},
        ], rows=files, row_key="datetime", pagination=100).classes('w-full')

    table.add_slot('body-cell-fname', '''
        <q-td :props="props">
            <audio controls :src="props.value" style="height: 30px;"
                   @v-mounted="(el) => el.play()">
                Your browser does not support the audio element.
            </audio>
        </q-td>
    ''')
    ui.timer(0.5, scan_refresh)

ui.run(title=f"Scantastic for {LOCATION}", port=6969)
