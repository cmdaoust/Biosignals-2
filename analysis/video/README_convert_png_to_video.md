# Turning the webcam pictures into a video: the "1:1" method

This note explains what `000_convert_png_to_avi.py` does when you run it with `--method 1to1`, step by step, and why each step is there. (The same script is saved in the lab repository as `03_encode_png_to_avi.py`.)

---

## The short version

During the experiment, the webcam does not record a video. It saves **one picture (a PNG file) for every moment it captures**, about 30 pictures a second, and it writes down **the exact time each picture was taken** in a separate spreadsheet.

The 1:1 method packs those pictures into **one video file**:

- **every picture appears exactly once**, in the order it was taken,
- **nothing is left out, repeated or changed**, down to the last pixel,
- and the spreadsheet of exact times is kept right next to the video.

This one video is what **both** heart-rate analyses read: ours (WebcamBiometrics) and FaceReader's. Because they read the same file, they see exactly the same pictures, which makes the comparison fair.

---

## Why we need this at all

### What the heart-rate analysis looks for

Each heartbeat pushes a little extra blood into the skin of the face, which changes the skin's colour very slightly, by about 1%, far too little to see by eye. The heart-rate analysis measures that tiny colour change in every picture and follows it over time. The rise and fall of the colour is the pulse.

That only works if:

1. **the colours in each picture are exactly as the camera recorded them.** Normal video formats (like the ones on your phone) throw away fine detail to save space. That detail is the same size as the pulse signal, so it would be lost.
2. **we know exactly when each picture was taken.** To find heartbeats, the analysis needs to know how far apart in time two pictures are.

### Why the timing is not simple

You might expect the camera to take a picture exactly every 1/30 of a second. It doesn't. Most pictures arrive about every 33 milliseconds (thousandths of a second), but now and then the camera pauses, and the next picture arrives 50 to 175 milliseconds later. Occasionally two pictures come closer together than usual.

So the only reliable record of *when* each picture was taken is the timestamps spreadsheet that was saved during the experiment.

### Why "1:1" and not the other kinds of video

The script can make three kinds of video. They exist for different jobs:

| Method | File it makes | What it is for |
|---|---|---|
| `1to1` | `<id>_1to1_ffv1.avi` | **Both heart-rate analyses** (ours and FaceReader's). Every picture once, nothing changed. |
| `1to1-facereader` | `<id>_1to1_facereader.avi` | Spare option only: the same pictures uncompressed (about 30 GB), in case FaceReader can't open the normal 1:1 video. Not needed at the moment. |
| `realtime` | `<id>_realtime_30fps.avi` | **FaceReader's facial-expression analysis.** Built so that "time in the video" equals "time in the experiment". To do that, it repeats a picture when the camera paused and skips one when the camera ran fast. |

The `realtime` video is good for matching expressions to events, but **bad for heart rate**: a repeated picture makes the colour signal sit flat and then jump, which looks like nothing a real pulse does, and skipped pictures are lost data. That is why the heart-rate analysis uses the 1:1 video instead. The file name always says which method made it, so they can't be mixed up.

---

## Why an .avi and not an .mkv (changed 7 Oct 2026)

Until 7 October the 1:1 video was saved as `<id>_1to1.mkv`. The pictures inside are exactly the same; only the "wrapper" around them changed. We switched because of FaceReader:

- An `.mkv` file doesn't state its data rate (bits per second), and FaceReader uses that number to judge video quality. It couldn't find it, so it showed **"the frame rate / bit rate / resolution is too low"** on every picture and analysed the video in a lower-quality mode.
- With the very same pictures in an `.avi`, the warning disappears and FaceReader's heartbeat detection is much better (for r2433, 85–99% of real heartbeats found instead of 24–43%).
- Our own analysis gets identical pictures from either file and uses the timestamps spreadsheet for timing, so its results don't change.

Using one `.avi` for both analyses also means there is only **one video per participant** on the drive.

**Participants converted before 7 October** still have an `.mkv`. Turn it into the `.avi` (no re-compression, takes about as long as copying the file) and remove the `.mkv` once every picture has been checked:

```powershell
python C:\Users\carme\OneDrive\Documents\GitHub\Biosignals2\analysis\video\004_convert_mkv_to_avi.py --all --delete-mkv
```

Until then, `003_run_webcam_biometrics.py` still reads the `.mkv` without problems.

---

## What goes in

For each participant, the script needs two things from the folder set as `WEBCAM_DIR` in `config.py` (currently `D:\Biosignals2_png_data`):

| Item | What it is |
|---|---|
| `<id>_frames\` | A folder of pictures: `frame_000000.png`, `frame_000001.png`, `frame_000002.png`, … one per captured moment, numbered in the order they were taken. |
| `<id>_frame_timestamps.csv` | A spreadsheet with one row per picture. The important columns are `frame_index` (the picture's number) and `time_since_recording_start` (when it was taken, in seconds since the webcam started recording). |

`<id>` is the participant ID, which is everything before the first underscore, so `r2433_frames` goes with `r2433_frame_timestamps.csv`.

---

## What the script does, step by step

### Step 1: Read the timestamps spreadsheet and check it makes sense

The script reads every row and checks:

- **the spreadsheet has the columns it needs.** If not, it was probably made by an older version of the experiment, and the script stops and says so.
- **no picture is listed twice.** If one is, the times were saved twice by mistake, and it stops.
- **the times always go forward.** Each picture must be later than the one before it. If not, something went wrong when saving, and it stops.
- **the picture numbers run 0, 1, 2, 3… without gaps.** If there is a gap, it warns you but carries on, because the times themselves are still correct.

It then prints a short summary, for example:

```
Timestamp rows        : 33666 (last frame at 1120.669 s)
Measured average fps  : 30.041
Frame interval        : min 11.8 ms, max 155.8 ms
```

This tells you how many pictures there are, how long the recording lasted, the average number of pictures per second, and the shortest and longest gaps between pictures. A longest gap of 100–200 ms is normal for this camera.

### Step 2: Check that every listed picture really exists

It compares the spreadsheet with the picture folder:

- **A picture in the spreadsheet but missing from the folder:** it stops, because the video would have a hole in it.
- **A picture in the folder but missing from the spreadsheet:** it warns you and leaves that picture out. This normally happens when the experiment was stopped early: the pictures were saved, but the experiment didn't get the chance to write their times down. Without a time, a picture is no use for the heart-rate analysis, so leaving it out is the safe choice.

### Step 3: Find the picture size

It opens the first picture to find its size (for this camera, 640 × 480 pixels) and checks every later picture is the same size as it goes. A picture of a different size would mean something is wrong, so it stops.

### Step 4: Pack every picture, once, into one video file

It reads the pictures one by one, **in the order of the timestamps spreadsheet**, and passes each one to a program called **ffmpeg**, which writes the video file.

The video is saved in a format called **FFV1**. The important thing about FFV1 is that it is **lossless**: like a zip file, it makes the data smaller for storage, but when the video is opened again you get back **exactly** the same pixels, with nothing rounded off or smoothed. (We checked this: every picture read back out of the video was identical to the original PNG.) The colours are kept exactly as the camera stored them.

Every picture is used **exactly once**. Nothing is repeated, nothing is skipped. So:

> picture number *i* in the video = PNG number *i* = row *i* of the timestamps spreadsheet.

That one-to-one match is where the name "1:1" comes from, and it is what lets the heart-rate analysis give each picture its true time.

The script prints a progress line every 3,000 pictures. If anything goes wrong while writing, it deletes the half-written file so that an incomplete video is never left lying around looking usable.

### Step 5: Give the video a "speed" label, which is only a label

Every video file has to state how many pictures per second it should be played at. The script uses the **average** from Step 1 (for example 30.041). This only affects how fast the video plays if you open it in a media player.

**It is not used for timing.** Because the camera did not take pictures evenly, "picture number ÷ 30.041" is *not* the real time of a picture. The real times are only in the timestamps spreadsheet. The heart-rate analysis always uses the spreadsheet, never this label.

### Step 6: Put a copy of the timestamps spreadsheet next to the video

The video is only half of what the analysis needs. Without its timestamps it would have to assume the pictures were evenly spaced, which they weren't. Over a 19-minute session, that mistake adds up to almost two seconds by the end, enough to put every heartbeat in the wrong place.

So the script copies `<id>_frame_timestamps.csv` into the same folder as the video, so the two always travel together. If a timestamps file with that name is already there **and it is different**, the script does **not** overwrite it. It warns you instead, because one of the two belongs to a different recording and you need to check which.

### Step 7: Report what it made

At the end it prints the file it wrote, its size and the number of pictures, for example:

```
Done. Wrote: D:\Biosignals2_video\r2433_1to1_ffv1.avi (5.27 GB, 33666 frames)
```

**The number of pictures should match the number of rows in Step 1.**

---

## Where the files go

By default, everything is saved to `VIDEO_DIR` from `config.py`, currently the folder `D:\Biosignals2_video` on the external hard drive:

```
D:\Biosignals2_video\
    r2433_1to1_ffv1.avi          ← the video (used by WebcamBiometrics AND FaceReader)
    r2433_frame_timestamps.csv   ← the copy of its timestamps
```

You can send them somewhere else with `--output-dir`.

These videos are **working copies**. They can always be made again from the original pictures, which are the files to keep safe (on Box).

---

## How to run it

**Everyone in the picture folder at once:**

```powershell
python C:\Users\carme\OneDrive\Documents\GitHub\Biosignals2\analysis\video\000_convert_png_to_avi.py D:\Biosignals2_png_data --method 1to1
```

**One participant:**

```powershell
python C:\Users\carme\OneDrive\Documents\GitHub\Biosignals2\analysis\video\000_convert_png_to_avi.py D:\Biosignals2_png_data\r2433_frames D:\Biosignals2_png_data\r2433_frame_timestamps.csv --method 1to1
```

You normally don't need to run it yourself: `003_run_webcam_biometrics.py` runs it automatically for any participant who doesn't have a 1:1 video yet.

Things to know:

- **`--method` must always be given.** The script refuses to guess, so the wrong kind of video is never made by accident.
- **It never overwrites a video.** A participant who already has `<id>_1to1_ffv1.avi` is skipped, so if a long batch is interrupted, just run the same command again and it carries on where it stopped. To redo a participant, delete their video first.
- **One participant failing doesn't stop the others.** A summary at the end lists who was done, who was skipped and who failed.
- It needs **ffmpeg** installed (`winget install ffmpeg`).

---

## How to check it worked

1. **Picture count:** the `Done.` line should show the same number of pictures as the timestamps rows at the start.
2. **Size:** an uncompressed copy would be about 29 GB for a 19-minute session. The 1:1 file should be smaller; how much smaller depends on the camera picture. Note this size to plan storage.
3. **Exact match (optional, but worth doing once):** `05_verify_roundtrip.py` in `Biosignals2_Lab\code\webcam` compares pictures from the video with the original PNGs and reports any difference:

   ```powershell
   python 05_verify_roundtrip.py D:\Biosignals2_png_data\r2433_frames D:\Biosignals2_video\r2433_1to1_ffv1.avi
   ```

---

## Messages you might see

| Message | What it means | What to do |
|---|---|---|
| `... is missing column(s) ...` | The timestamps spreadsheet isn't in the expected format. | Check it is the `<id>_frame_timestamps.csv` saved by the current experiment. |
| `Duplicate frame_index values` | Some picture times were saved twice. | Check the spreadsheet; it may need cleaning. |
| `time_since_recording_start is not strictly increasing` | A picture's time is earlier than the one before it. | Check the spreadsheet for a mix-up. |
| `frame(s) in the CSV have no PNG` | Pictures listed in the spreadsheet are missing from the folder. | Check the picture folder was copied completely. |
| `[WARNING] ... PNG(s) have no timestamp row` | Some pictures have no recorded time (usually the experiment stopped early). | Nothing; they are left out on purpose. |
| `[WARNING] frame_index is not contiguous` | The picture numbers skip somewhere. | The video is still correct, but check the recording. |
| `already exists - delete it first to redo it` | This participant already has a 1:1 video. | Nothing, or delete it if you want to remake it. |
| `[WARNING] ... already exists and DIFFERS` | A different timestamps file is already next to the videos. | Find out which recording each belongs to before going on. |
| `ffmpeg not found on PATH` | ffmpeg isn't installed, or this window can't find it. | Install it (`winget install ffmpeg`) and open a new window. |
