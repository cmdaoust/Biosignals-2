#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This experiment was created using PsychoPy3 Experiment Builder (v2026.1.3),
    on June 12, 2026, at 10:55
If you publish work using this script the most relevant publication is:

    Peirce J, Gray JR, Simpson S, MacAskill M, Höchenberger R, Sogo H, Kastman E, Lindeløv JK. (2019) 
        PsychoPy2: Experiments in behavior made easy Behav Res 51: 195. 
        https://doi.org/10.3758/s13428-018-01193-y

"""

# --- Import packages ---
from psychopy import locale_setup
from psychopy import prefs
from psychopy import plugins
plugins.activatePlugins()
from psychopy import sound, gui, visual, core, data, event, logging, clock, colors, layout, hardware
from psychopy.tools import environmenttools
from psychopy.constants import (
    NOT_STARTED, STARTED, PLAYING, PAUSED, STOPPED, STOPPING, FINISHED, PRESSED, 
    RELEASED, FOREVER, priority
)

import numpy as np  # whole numpy lib is available, prepend 'np.'
from numpy import (sin, cos, tan, log, log10, pi, average,
                   sqrt, std, deg2rad, rad2deg, linspace, asarray)
from numpy.random import random, randint, normal, shuffle, choice as randchoice
import os  # handy system and path functions
import sys  # to get file system encoding

import psychopy.iohub as io
from psychopy.hardware import keyboard

# --- Setup global variables (available in all functions) ---
# create a device manager to handle hardware (keyboards, mice, mirophones, speakers, etc.)
deviceManager = hardware.DeviceManager()
# ensure that relative paths start from the same directory as this script
_thisDir = os.path.dirname(os.path.abspath(__file__))
# store info about the experiment session
psychopyVersion = '2026.1.3'
expName = 'Biosignals2_internalcamera_Psychopy'  # from the Builder filename that created this script
expVersion = ''
# a list of functions to run when the experiment ends (starts off blank)
runAtExit = []
# information about this experiment
expInfo = {
    'participant': f"{randint(0, 999999):06.0f}",
    'session': '001',
    'date|hid': data.getDateStr(),
    'expName|hid': expName,
    'expVersion|hid': expVersion,
    'psychopyVersion|hid': psychopyVersion,
}

# --- Define some variables which will change depending on pilot mode ---
'''
To run in pilot mode, either use the run/pilot toggle in Builder, Coder and Runner, 
or run the experiment with `--pilot` as an argument. To change what pilot 
#mode does, check out the 'Pilot mode' tab in preferences.
'''
# work out from system args whether we are running in pilot mode
PILOTING = core.setPilotModeFromArgs()
# start off with values from experiment settings
_fullScr = True
_winSize = [1920, 1080]
# if in pilot mode, apply overrides according to preferences
if PILOTING:
    # force windowed mode
    if prefs.piloting['forceWindowed']:
        _fullScr = False
        # set window size
        _winSize = prefs.piloting['forcedWindowSize']
    # replace default participant ID
    if prefs.piloting['replaceParticipantID']:
        expInfo['participant'] = 'pilot'

def showExpInfoDlg(expInfo):
    """
    Show participant info dialog.
    Parameters
    ==========
    expInfo : dict
        Information about this experiment.
    
    Returns
    ==========
    dict
        Information about this experiment.
    """
    # show participant info dialog
    dlg = gui.DlgFromDict(
        dictionary=expInfo, sortKeys=False, title=expName, alwaysOnTop=True
    )
    if dlg.OK == False:
        core.quit()  # user pressed cancel
    # return expInfo
    return expInfo


def setupData(expInfo, dataDir=None):
    """
    Make an ExperimentHandler to handle trials and saving.
    
    Parameters
    ==========
    expInfo : dict
        Information about this experiment, created by the `setupExpInfo` function.
    dataDir : Path, str or None
        Folder to save the data to, leave as None to create a folder in the current directory.    
    Returns
    ==========
    psychopy.data.ExperimentHandler
        Handler object for this experiment, contains the data to save and information about 
        where to save it to.
    """
    # remove dialog-specific syntax from expInfo
    for key, val in expInfo.copy().items():
        newKey, _ = data.utils.parsePipeSyntax(key)
        expInfo[newKey] = expInfo.pop(key)
    
    # data file name stem = absolute path + name; later add .psyexp, .csv, .log, etc
    if dataDir is None:
        dataDir = _thisDir
    filename = u'data/%s_%s_%s' % (expInfo['participant'], expName, expInfo['date'])
    # make sure filename is relative to dataDir
    if os.path.isabs(filename):
        dataDir = os.path.commonprefix([dataDir, filename])
        filename = os.path.relpath(filename, dataDir)
    
    # an ExperimentHandler isn't essential but helps with data saving
    thisExp = data.ExperimentHandler(
        name=expName, version=expVersion,
        extraInfo=expInfo, runtimeInfo=None,
        originPath='C:\\Users\\irise_lab\\Documents\\Biosignals2\\Experiment\\Biosignals2_internalcamera_Psychopy_lastrun.py',
        savePickle=True, saveWideText=True,
        dataFileName=dataDir + os.sep + filename, sortColumns='time'
    )
    # store pilot mode in data file
    thisExp.addData('piloting', PILOTING, priority=priority.LOW)
    thisExp.setPriority('thisRow.t', priority.CRITICAL)
    thisExp.setPriority('expName', priority.LOW)
    # return experiment handler
    return thisExp


def setupLogging(filename):
    """
    Setup a log file and tell it what level to log at.
    
    Parameters
    ==========
    filename : str or pathlib.Path
        Filename to save log file and data files as, doesn't need an extension.
    
    Returns
    ==========
    psychopy.logging.LogFile
        Text stream to receive inputs from the logging system.
    """
    # set how much information should be printed to the console / app
    if PILOTING:
        logging.console.setLevel(
            prefs.piloting['pilotConsoleLoggingLevel']
        )
    else:
        logging.console.setLevel('warning')
    # save a log file for detail verbose info
    logFile = logging.LogFile(filename+'.log')
    if PILOTING:
        logFile.setLevel(
            prefs.piloting['pilotLoggingLevel']
        )
    else:
        logFile.setLevel(
            logging.getLevel('info')
        )
    
    return logFile


def setupWindow(expInfo=None, win=None):
    """
    Setup the Window
    
    Parameters
    ==========
    expInfo : dict
        Information about this experiment, created by the `setupExpInfo` function.
    win : psychopy.visual.Window
        Window to setup - leave as None to create a new window.
    
    Returns
    ==========
    psychopy.visual.Window
        Window in which to run this experiment.
    """
    if PILOTING:
        logging.debug('Fullscreen settings ignored as running in pilot mode.')
    
    if win is None:
        # if not given a window to setup, make one
        win = visual.Window(
            size=_winSize, fullscr=_fullScr, screen=0,
            winType='pyglet', allowGUI=False, allowStencil=True,
            monitor='testMonitor', color=[0,0,0], colorSpace='rgb',
            backgroundImage='', backgroundFit='none',
            blendMode='avg', useFBO=True,
            units='height',
            checkTiming=False  # we're going to do this ourselves in a moment
        )
    else:
        # if we have a window, just set the attributes which are safe to set
        win.color = [0,0,0]
        win.colorSpace = 'rgb'
        win.backgroundImage = ''
        win.backgroundFit = 'none'
        win.units = 'height'
    if expInfo is not None:
        # get/measure frame rate if not already in expInfo
        if win._monitorFrameRate is None:
            win._monitorFrameRate = win.getActualFrameRate(infoMsg='Attempting to measure frame rate of screen, please wait...')
        expInfo['frameRate'] = win._monitorFrameRate
    win.hideMessage()
    if PILOTING:
        # show a visual indicator if we're in piloting mode
        if prefs.piloting['showPilotingIndicator']:
            win.showPilotingIndicator()
        # always show the mouse in piloting mode
        if prefs.piloting['forceMouseVisible']:
            win.mouseVisible = True
    
    return win


def setupDevices(expInfo, thisExp, win):
    """
    Setup whatever devices are available (mouse, keyboard, speaker, eyetracker, etc.) and add them to 
    the device manager (deviceManager)
    
    Parameters
    ==========
    expInfo : dict
        Information about this experiment, created by the `setupExpInfo` function.
    thisExp : psychopy.data.ExperimentHandler
        Handler object for this experiment, contains the data to save and information about 
        where to save it to.
    win : psychopy.visual.Window
        Window in which to run this experiment.
    Returns
    ==========
    bool
        True if completed successfully.
    """
    # --- Setup input devices ---
    ioConfig = {}
    
    # Setup iohub keyboard
    ioConfig['Keyboard'] = dict(use_keymap='psychopy')
    
    # Setup iohub experiment
    ioConfig['Experiment'] = dict(filename=thisExp.dataFileName)
    
    # Start ioHub server
    ioServer = io.launchHubServer(window=win, **ioConfig)
    
    # store ioServer object in the device manager
    deviceManager.ioServer = ioServer
    
    # create a default keyboard (e.g. to check for escape)
    if deviceManager.getDevice('defaultKeyboard') is None:
        deviceManager.addDevice(
            deviceClass='keyboard', deviceName='defaultKeyboard', backend='iohub'
        )
    # return True if completed successfully
    return True

def pauseExperiment(thisExp, win=None, timers=[], currentRoutine=None):
    """
    Pause this experiment, preventing the flow from advancing to the next routine until resumed.
    
    Parameters
    ==========
    thisExp : psychopy.data.ExperimentHandler
        Handler object for this experiment, contains the data to save and information about 
        where to save it to.
    win : psychopy.visual.Window
        Window for this experiment.
    timers : list, tuple
        List of timers to reset once pausing is finished.
    currentRoutine : psychopy.data.Routine
        Current Routine we are in at time of pausing, if any. This object tells PsychoPy what Components to pause/play/dispatch.
    """
    # if we are not paused, do nothing
    if thisExp.status != PAUSED:
        return
    
    # start a timer to figure out how long we're paused for
    pauseTimer = core.Clock()
    # pause any playback components
    if currentRoutine is not None:
        for comp in currentRoutine.getPlaybackComponents():
            comp.pause()
    # make sure we have a keyboard
    defaultKeyboard = deviceManager.getDevice('defaultKeyboard')
    if defaultKeyboard is None:
        defaultKeyboard = deviceManager.addKeyboard(
            deviceClass='keyboard',
            deviceName='defaultKeyboard',
            backend='ioHub',
        )
    # run a while loop while we wait to unpause
    while thisExp.status == PAUSED:
        # check for quit (typically the Esc key)
        if defaultKeyboard.getKeys(keyList=['escape']):
            endExperiment(thisExp, win=win)
        # dispatch messages on response components
        if currentRoutine is not None:
            for comp in currentRoutine.getDispatchComponents():
                comp.device.dispatchMessages()
        # sleep 1ms so other threads can execute
        clock.time.sleep(0.001)
    # if stop was requested while paused, quit
    if thisExp.status == FINISHED:
        endExperiment(thisExp, win=win)
    # resume any playback components
    if currentRoutine is not None:
        for comp in currentRoutine.getPlaybackComponents():
            comp.play()
    # reset any timers
    for timer in timers:
        timer.addTime(-pauseTimer.getTime())


def run(expInfo, thisExp, win, globalClock=None, thisSession=None):
    """
    Run the experiment flow.
    
    Parameters
    ==========
    expInfo : dict
        Information about this experiment, created by the `setupExpInfo` function.
    thisExp : psychopy.data.ExperimentHandler
        Handler object for this experiment, contains the data to save and information about 
        where to save it to.
    psychopy.visual.Window
        Window in which to run this experiment.
    globalClock : psychopy.core.clock.Clock or None
        Clock to get global time from - supply None to make a new one.
    thisSession : psychopy.session.Session or None
        Handle of the Session object this experiment is being run from, if any.
    """
    # mark experiment as started
    thisExp.status = STARTED
    # update experiment info
    expInfo['date'] = data.getDateStr()
    expInfo['expName'] = expName
    expInfo['expVersion'] = expVersion
    expInfo['psychopyVersion'] = psychopyVersion
    # make sure window is set to foreground to prevent losing focus
    win.winHandle.activate()
    # make sure variables created by exec are available globally
    exec = environmenttools.setExecEnvironment(globals())
    # get device handles from dict of input devices
    ioServer = deviceManager.ioServer
    # get/create a default keyboard (e.g. to check for escape)
    defaultKeyboard = deviceManager.getDevice('defaultKeyboard')
    if defaultKeyboard is None:
        deviceManager.addDevice(
            deviceClass='keyboard', deviceName='defaultKeyboard', backend='ioHub'
        )
    eyetracker = deviceManager.getDevice('eyetracker')
    # make sure we're running in the directory for this experiment
    os.chdir(_thisDir)
    # get filename from ExperimentHandler for convenience
    filename = thisExp.dataFileName
    frameTolerance = 0.001  # how close to onset before 'same' frame
    endExpNow = False  # flag for 'escape' or other condition => quit the exp
    # get frame duration from frame rate in expInfo
    if 'frameRate' in expInfo and expInfo['frameRate'] is not None:
        frameDur = 1.0 / round(expInfo['frameRate'])
    else:
        frameDur = 1.0 / 60.0  # could not measure, so guess
    
    # Start Code - component code to be run after the window creation
    
    # --- Initialize components for Routine "trigger_setup" ---
    # Run 'Begin Experiment' code from code
    import serial
    import time
    import random
    
    
    
    #----
    # CAMERA SETUP
    #----
    import cv2
    import time
    import threading
    import csv
    
    class WebcamRecorder:
        def __init__(self, output_path):
            self.output_path = output_path
            self.timestamps = []
            self._stop_event = threading.Event()
            self._thread = None
            self._start_wall_time = None
            self._fps = None
            self._cap = None
    
        def warmup(self):
            self._cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            for _ in range(5):
                self._cap.read()
            t0 = time.time()
            for _ in range(60):
                self._cap.read()
            self._fps = 60 / (time.time() - t0)
    
        def _record(self):
            cap = self._cap
            width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fourcc = cv2.VideoWriter_fourcc(*'MJPG')
            out = cv2.VideoWriter(self.output_path.replace('.mp4', '.avi'), fourcc, self._fps, (width, height))
            self._start_wall_time = time.time()
            frame_idx = 0
            while not self._stop_event.is_set():
                ret, frame = cap.read()
                if not ret:
                    break
                out.write(frame)
                self.timestamps.append((frame_idx, time.time()))
                frame_idx += 1
            cap.release()
            out.release()
    
        def start(self):
            self._thread = threading.Thread(target=self._record, daemon=True)
            self._thread.start()
            while self._start_wall_time is None:
                time.sleep(0.01)
    
        def stop(self):
            self._stop_event.set()
            self._thread.join()
    
        def save_timestamps(self, path):
            with open(path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['frame_index', 'wall_time', 'time_since_recording_start'])
                for idx, t in self.timestamps:
                    writer.writerow([idx, t, round(t - self._start_wall_time, 6)])
    
    participant_id = expInfo['participant']
    save_dir = f'data/webcam'
    os.makedirs(save_dir, exist_ok=True)
    
    recorder = WebcamRecorder(f'{save_dir}/{participant_id}_recording.mp4')
    recorder.warmup()
    recorder.start()
    experiment_start_wall = time.time()
    
    # -------------------------
    # COUNTERBALANCING SETUP
    # -------------------------
    
    # Determines which stimulus set (positive or negative videos) is presented first.
    # Must be updated manually at the start of the experiment - record in counterbalancing_tracker
    # 'pos_first' = positive block in block 1, negative in block 2.
    # 'neg_first' = negative block in block 1, positive in block 2.
    condition_order = 'neg_first'
    
    # Tracks how many valence/arousal rating pairs have been presented to this participant.
    # Incremented at the start of each rating pair; used to alternate the rating order.
    rating_pair_count = 0
    
    # Starting order for momentary rating pairs (pre/post baseline, post-induction, post-recovery).
    # Must be set-up manually and tracked in counterbalancing_tracker
    # rating_start = 'arousal_first'
    rating_start = 'valence_first'
    
    # Same counter and starting order logic for stimuli ratings (video_rating loop).
    # stim_rating_start is set to the opposite of rating_start so that the two
    # rating contexts do not both begin with the same dimension.
    stim_rating_pair_count = 0
    stim_rating_start = 'arousal_first' if rating_start == 'valence_first' else 'valence_first'
    
    # -------------------------
    # MISC
    # -------------------------
    
    # Tracks how many experimental blocks have been completed.
    # Used by block_setup to determine which stimulus file to load.
    block_count = 0
    
    # Holds the current stimulus condition ('positive' or 'negative').
    # Set during block_setup and used to assign EEG triggers.
    stim_condition = ""
    
    # Duration of the stim_recovery period in seconds.
    recovery_duration = 180
    
    # ==============================
    # SERIAL / TRIGGER SETUP
    # ==============================
    
    
    USE_REAL_SERIAL = False  # <-- toggle this (True in lab, False when testing)
    
    # ------------------------------
    # Fake serial class
    # ------------------------------
    class FakeSerial:
        def __init__(self, *args, **kwargs):
            print("[FakeSerial] Using mock serial port")
    
        def write(self, data):
            try:
                decoded = data.decode()
            except:
                decoded = data
            print(f"[FakeSerial write] {decoded}")
            time.sleep(0.005)  # simulate small hardware delay
    
        def read(self, size=1):
            return b"\x00" * size
    
        def readline(self):
            return b"0\n"
    
        def close(self):
            print("[FakeSerial] closed")
    
        def flush(self):
            pass
    
        @property
        def in_waiting(self):
            return 0
    
    
    # ------------------------------
    # Initialise serial connection
    # ------------------------------
    if USE_REAL_SERIAL:
        try:
            import serial
            ser = serial.Serial(
                "COM3",
                115200,
                timeout=1,
                bytesize=8,
                stopbits=1
            )
            print("[Serial] Connected to COM3")
    
        except Exception as e:
            print(f"[Serial] Failed ({e}) → falling back to FakeSerial")
            ser = FakeSerial()
    else:
        ser = FakeSerial()
    
    
    # ------------------------------
    # Reset / initialise device
    # ------------------------------
    try:
        ser.write(b'RR')  # Reset port to prepare for first trigger
        print("[Serial] Reset command sent")
    except Exception as e:
        print(f"[Serial] Reset failed: {e}")
    
    """
    # Configure serial port (customize COM port as needed)
    ser = serial.Serial("COM3", 115200, timeout=1, bytesize=8, stopbits=1)
     
    # Open the port and reset
    #ser.open()
    ser.write('RR'.encode())  # Reset port to prepare for first trigger
    """
    # Assign Hex codes to each trigger being sent
    baseline_trigger = '01'
    neg_stim1_trigger = '02'
    neg_stim2_trigger = '04'
    neg_stim_recovery_trigger = '08'
    pos_stim1_trigger = '10'
    pos_stim2_trigger = '20'
    pos_stim_recovery_trigger = '40'
    temp_sync_trigger = '80'
    # Run 'Begin Experiment' code from webcam_code
    import sys
    sys.path.insert(0, os.getcwd())   # biometrics_server.py sits next to this experiment
    from biometrics_server import BiometricsRecorder
    
    # clock      → the `time` column (globalClock, same as trial.started — for joining to trials).
    # mono_clock → the `mono_time` column (core.getTime never resets — a safety net).
    # `globalClock`, `core`, `filename` all come from Builder.
    bio = BiometricsRecorder(
        clock=lambda: globalClock.getTime(format='float'),
        mono_clock=core.getTime,
        log=filename + '_biometrics.csv',
    ).start()
    
    # --- Initialize components for Routine "overview" ---
    overview_txt = visual.TextStim(win=win, name='overview_txt',
        text='Welcome to the study!\n\nIn this session, you will alternate between rest and video blocks. \n\nDuring rest blocks, a fixation cross will appear in the centre of the screen. Please focus on the cross throughout the block. \n\nDuring video blocks, you will watch a series of short video clips. Please watch each clip until it ends.\n\nAt the end of each block, you will be asked a series of questions about how you feel.\n\nThe session follows this sequence:\n\nRest → Videos → Rest → Videos → Rest\n\n\nWhen you are ready to begin, press the SPACEBAR.\n\n',
        font='Arial',
        pos=(0, 0), draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=0.0);
    key_resp_overview = keyboard.Keyboard(deviceName='defaultKeyboard')
    
    # --- Initialize components for Routine "momentary_valence_rating_A" ---
    momentary_valence_mouse_A = event.Mouse(win=win)
    x, y = [None, None]
    momentary_valence_mouse_A.mouseClock = core.Clock()
    momentary_valence_question_txt_A = visual.TextStim(win=win, name='momentary_valence_question_txt_A',
        text='How do you feel right now?',
        font='Arial',
        pos=(0, 0.2), draggable=True, height=0.04, wrapWidth=1.8, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-2.0);
    momentary_valence_slider_A = visual.Slider(win=win, name='momentary_valence_slider_A',
        startValue=None, size=(0.8, 0.03), pos=[0,0], units=win.units,
        labels=None, ticks=(1, 2, 3, 4, 5, 6, 7), granularity=1.0,
        style='rating', styleTweaks=(), opacity=None,
        labelColor='LightGray', markerColor=[-1.0000, -1.0000, -1.0000], lineColor='White', colorSpace='rgb',
        font='Open Sans', labelHeight=0.03,
        flip=False, ori=0.0, depth=-3, readOnly=False)
    momentary_pleasant_txt_A = visual.TextStim(win=win, name='momentary_pleasant_txt_A',
        text='very pleasant',
        font='Arial',
        pos=[0,0], draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-4.0);
    momentary_unpleasant_txt_A = visual.TextStim(win=win, name='momentary_unpleasant_txt_A',
        text='very unpleasant',
        font='Arial',
        pos=[0,0], draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-5.0);
    mouse_instuct_txt = visual.TextStim(win=win, name='mouse_instuct_txt',
        text='Use your mouse to select the point on the slider.',
        font='Arial',
        pos=(0, 0.1), draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-6.0);
    
    # --- Initialize components for Routine "momentary_arousal_rating" ---
    momentary_arousal_mouse = event.Mouse(win=win)
    x, y = [None, None]
    momentary_arousal_mouse.mouseClock = core.Clock()
    momentary_arousal_question_txt = visual.TextStim(win=win, name='momentary_arousal_question_txt',
        text='How do you feel right now?',
        font='Arial',
        pos=(0, 0.2), draggable=True, height=0.04, wrapWidth=1.8, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-2.0);
    momentary_arousal_slider = visual.Slider(win=win, name='momentary_arousal_slider',
        startValue=None, size=(0.8, 0.03), pos=[0,0], units=win.units,
        labels=None, ticks=(1, 2, 3, 4, 5, 6, 7), granularity=1.0,
        style='rating', styleTweaks=(), opacity=None,
        labelColor='LightGray', markerColor=[-1.0000, -1.0000, -1.0000], lineColor='White', colorSpace='rgb',
        font='Open Sans', labelHeight=0.03,
        flip=False, ori=0.0, depth=-3, readOnly=False)
    momentary_alert_txt = visual.TextStim(win=win, name='momentary_alert_txt',
        text='very alert',
        font='Arial',
        pos=[0,0], draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-4.0);
    momentary_not_alert_txt = visual.TextStim(win=win, name='momentary_not_alert_txt',
        text='not alert at all',
        font='Arial',
        pos=[0,0], draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-5.0);
    mouse_instruct_txt_1 = visual.TextStim(win=win, name='mouse_instruct_txt_1',
        text='Use your mouse to select the point on the slider.',
        font='Arial',
        pos=(0, 0.1), draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-6.0);
    
    # --- Initialize components for Routine "momentary_valence_rating_B" ---
    momentary_valence_mouse_B = event.Mouse(win=win)
    x, y = [None, None]
    momentary_valence_mouse_B.mouseClock = core.Clock()
    momentary_valence_question_txt_B = visual.TextStim(win=win, name='momentary_valence_question_txt_B',
        text='How do you feel right now?',
        font='Arial',
        pos=(0, 0.2), draggable=True, height=0.04, wrapWidth=1.8, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-2.0);
    momentary_valence_slider_B = visual.Slider(win=win, name='momentary_valence_slider_B',
        startValue=None, size=(0.8, 0.03), pos=[0,0], units=win.units,
        labels=None, ticks=(1, 2, 3, 4, 5, 6, 7), granularity=1.0,
        style='rating', styleTweaks=(), opacity=None,
        labelColor='LightGray', markerColor=[-1.0000, -1.0000, -1.0000], lineColor='White', colorSpace='rgb',
        font='Open Sans', labelHeight=0.03,
        flip=False, ori=0.0, depth=-3, readOnly=False)
    momentary_pleasant_txt_B = visual.TextStim(win=win, name='momentary_pleasant_txt_B',
        text='very pleasant',
        font='Arial',
        pos=[0,0], draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-4.0);
    momentary_unpleasant_txt_B = visual.TextStim(win=win, name='momentary_unpleasant_txt_B',
        text='very unpleasant',
        font='Arial',
        pos=[0,0], draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-5.0);
    mouse_instruct_txt_2 = visual.TextStim(win=win, name='mouse_instruct_txt_2',
        text='Use your mouse to select the point on the slider.',
        font='Arial',
        pos=(0, 0.1), draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-6.0);
    
    # --- Initialize components for Routine "baseline_instruct" ---
    baseline_instruct_txt = visual.TextStim(win=win, name='baseline_instruct_txt',
        text='You are about to begin a 3-minute rest period. Please focus on the cross displayed on the screen.',
        font='Arial',
        pos=(0, 0), draggable=False, height=0.05, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=0.0);
    
    # --- Initialize components for Routine "baseline" ---
    fixation_baseline = visual.TextStim(win=win, name='fixation_baseline',
        text='+',
        font='Arial',
        pos=(0, 0), draggable=False, height=0.1, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=0.0);
    
    # --- Initialize components for Routine "momentary_valence_rating_A" ---
    momentary_valence_mouse_A = event.Mouse(win=win)
    x, y = [None, None]
    momentary_valence_mouse_A.mouseClock = core.Clock()
    momentary_valence_question_txt_A = visual.TextStim(win=win, name='momentary_valence_question_txt_A',
        text='How do you feel right now?',
        font='Arial',
        pos=(0, 0.2), draggable=True, height=0.04, wrapWidth=1.8, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-2.0);
    momentary_valence_slider_A = visual.Slider(win=win, name='momentary_valence_slider_A',
        startValue=None, size=(0.8, 0.03), pos=[0,0], units=win.units,
        labels=None, ticks=(1, 2, 3, 4, 5, 6, 7), granularity=1.0,
        style='rating', styleTweaks=(), opacity=None,
        labelColor='LightGray', markerColor=[-1.0000, -1.0000, -1.0000], lineColor='White', colorSpace='rgb',
        font='Open Sans', labelHeight=0.03,
        flip=False, ori=0.0, depth=-3, readOnly=False)
    momentary_pleasant_txt_A = visual.TextStim(win=win, name='momentary_pleasant_txt_A',
        text='very pleasant',
        font='Arial',
        pos=[0,0], draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-4.0);
    momentary_unpleasant_txt_A = visual.TextStim(win=win, name='momentary_unpleasant_txt_A',
        text='very unpleasant',
        font='Arial',
        pos=[0,0], draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-5.0);
    mouse_instuct_txt = visual.TextStim(win=win, name='mouse_instuct_txt',
        text='Use your mouse to select the point on the slider.',
        font='Arial',
        pos=(0, 0.1), draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-6.0);
    
    # --- Initialize components for Routine "momentary_arousal_rating" ---
    momentary_arousal_mouse = event.Mouse(win=win)
    x, y = [None, None]
    momentary_arousal_mouse.mouseClock = core.Clock()
    momentary_arousal_question_txt = visual.TextStim(win=win, name='momentary_arousal_question_txt',
        text='How do you feel right now?',
        font='Arial',
        pos=(0, 0.2), draggable=True, height=0.04, wrapWidth=1.8, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-2.0);
    momentary_arousal_slider = visual.Slider(win=win, name='momentary_arousal_slider',
        startValue=None, size=(0.8, 0.03), pos=[0,0], units=win.units,
        labels=None, ticks=(1, 2, 3, 4, 5, 6, 7), granularity=1.0,
        style='rating', styleTweaks=(), opacity=None,
        labelColor='LightGray', markerColor=[-1.0000, -1.0000, -1.0000], lineColor='White', colorSpace='rgb',
        font='Open Sans', labelHeight=0.03,
        flip=False, ori=0.0, depth=-3, readOnly=False)
    momentary_alert_txt = visual.TextStim(win=win, name='momentary_alert_txt',
        text='very alert',
        font='Arial',
        pos=[0,0], draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-4.0);
    momentary_not_alert_txt = visual.TextStim(win=win, name='momentary_not_alert_txt',
        text='not alert at all',
        font='Arial',
        pos=[0,0], draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-5.0);
    mouse_instruct_txt_1 = visual.TextStim(win=win, name='mouse_instruct_txt_1',
        text='Use your mouse to select the point on the slider.',
        font='Arial',
        pos=(0, 0.1), draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-6.0);
    
    # --- Initialize components for Routine "momentary_valence_rating_B" ---
    momentary_valence_mouse_B = event.Mouse(win=win)
    x, y = [None, None]
    momentary_valence_mouse_B.mouseClock = core.Clock()
    momentary_valence_question_txt_B = visual.TextStim(win=win, name='momentary_valence_question_txt_B',
        text='How do you feel right now?',
        font='Arial',
        pos=(0, 0.2), draggable=True, height=0.04, wrapWidth=1.8, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-2.0);
    momentary_valence_slider_B = visual.Slider(win=win, name='momentary_valence_slider_B',
        startValue=None, size=(0.8, 0.03), pos=[0,0], units=win.units,
        labels=None, ticks=(1, 2, 3, 4, 5, 6, 7), granularity=1.0,
        style='rating', styleTweaks=(), opacity=None,
        labelColor='LightGray', markerColor=[-1.0000, -1.0000, -1.0000], lineColor='White', colorSpace='rgb',
        font='Open Sans', labelHeight=0.03,
        flip=False, ori=0.0, depth=-3, readOnly=False)
    momentary_pleasant_txt_B = visual.TextStim(win=win, name='momentary_pleasant_txt_B',
        text='very pleasant',
        font='Arial',
        pos=[0,0], draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-4.0);
    momentary_unpleasant_txt_B = visual.TextStim(win=win, name='momentary_unpleasant_txt_B',
        text='very unpleasant',
        font='Arial',
        pos=[0,0], draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-5.0);
    mouse_instruct_txt_2 = visual.TextStim(win=win, name='mouse_instruct_txt_2',
        text='Use your mouse to select the point on the slider.',
        font='Arial',
        pos=(0, 0.1), draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-6.0);
    
    # --- Initialize components for Routine "block_setup" ---
    
    # --- Initialize components for Routine "video_instruct" ---
    video_instruct_txt = visual.TextStim(win=win, name='video_instruct_txt',
        text='You are about to begin a 3-minute video block. During this time, please pay attention to the video clips on the screen.',
        font='Arial',
        pos=(0, 0), draggable=False, height=0.05, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=0.0);
    
    # --- Initialize components for Routine "stimuli" ---
    video = visual.MovieStim(
        win, name='video',
        filename=None, movieLib='ffpyplayer',
        loop=False, volume=1.0, noAudio=False,
        pos=(0, 0), size=(1,0.5), units=win.units,
        ori=0.0, anchor='center',opacity=None, contrast=1.0,
        depth=0
    )
    
    # --- Initialize components for Routine "momentary_valence_rating_A" ---
    momentary_valence_mouse_A = event.Mouse(win=win)
    x, y = [None, None]
    momentary_valence_mouse_A.mouseClock = core.Clock()
    momentary_valence_question_txt_A = visual.TextStim(win=win, name='momentary_valence_question_txt_A',
        text='How do you feel right now?',
        font='Arial',
        pos=(0, 0.2), draggable=True, height=0.04, wrapWidth=1.8, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-2.0);
    momentary_valence_slider_A = visual.Slider(win=win, name='momentary_valence_slider_A',
        startValue=None, size=(0.8, 0.03), pos=[0,0], units=win.units,
        labels=None, ticks=(1, 2, 3, 4, 5, 6, 7), granularity=1.0,
        style='rating', styleTweaks=(), opacity=None,
        labelColor='LightGray', markerColor=[-1.0000, -1.0000, -1.0000], lineColor='White', colorSpace='rgb',
        font='Open Sans', labelHeight=0.03,
        flip=False, ori=0.0, depth=-3, readOnly=False)
    momentary_pleasant_txt_A = visual.TextStim(win=win, name='momentary_pleasant_txt_A',
        text='very pleasant',
        font='Arial',
        pos=[0,0], draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-4.0);
    momentary_unpleasant_txt_A = visual.TextStim(win=win, name='momentary_unpleasant_txt_A',
        text='very unpleasant',
        font='Arial',
        pos=[0,0], draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-5.0);
    mouse_instuct_txt = visual.TextStim(win=win, name='mouse_instuct_txt',
        text='Use your mouse to select the point on the slider.',
        font='Arial',
        pos=(0, 0.1), draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-6.0);
    
    # --- Initialize components for Routine "momentary_arousal_rating" ---
    momentary_arousal_mouse = event.Mouse(win=win)
    x, y = [None, None]
    momentary_arousal_mouse.mouseClock = core.Clock()
    momentary_arousal_question_txt = visual.TextStim(win=win, name='momentary_arousal_question_txt',
        text='How do you feel right now?',
        font='Arial',
        pos=(0, 0.2), draggable=True, height=0.04, wrapWidth=1.8, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-2.0);
    momentary_arousal_slider = visual.Slider(win=win, name='momentary_arousal_slider',
        startValue=None, size=(0.8, 0.03), pos=[0,0], units=win.units,
        labels=None, ticks=(1, 2, 3, 4, 5, 6, 7), granularity=1.0,
        style='rating', styleTweaks=(), opacity=None,
        labelColor='LightGray', markerColor=[-1.0000, -1.0000, -1.0000], lineColor='White', colorSpace='rgb',
        font='Open Sans', labelHeight=0.03,
        flip=False, ori=0.0, depth=-3, readOnly=False)
    momentary_alert_txt = visual.TextStim(win=win, name='momentary_alert_txt',
        text='very alert',
        font='Arial',
        pos=[0,0], draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-4.0);
    momentary_not_alert_txt = visual.TextStim(win=win, name='momentary_not_alert_txt',
        text='not alert at all',
        font='Arial',
        pos=[0,0], draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-5.0);
    mouse_instruct_txt_1 = visual.TextStim(win=win, name='mouse_instruct_txt_1',
        text='Use your mouse to select the point on the slider.',
        font='Arial',
        pos=(0, 0.1), draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-6.0);
    
    # --- Initialize components for Routine "momentary_valence_rating_B" ---
    momentary_valence_mouse_B = event.Mouse(win=win)
    x, y = [None, None]
    momentary_valence_mouse_B.mouseClock = core.Clock()
    momentary_valence_question_txt_B = visual.TextStim(win=win, name='momentary_valence_question_txt_B',
        text='How do you feel right now?',
        font='Arial',
        pos=(0, 0.2), draggable=True, height=0.04, wrapWidth=1.8, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-2.0);
    momentary_valence_slider_B = visual.Slider(win=win, name='momentary_valence_slider_B',
        startValue=None, size=(0.8, 0.03), pos=[0,0], units=win.units,
        labels=None, ticks=(1, 2, 3, 4, 5, 6, 7), granularity=1.0,
        style='rating', styleTweaks=(), opacity=None,
        labelColor='LightGray', markerColor=[-1.0000, -1.0000, -1.0000], lineColor='White', colorSpace='rgb',
        font='Open Sans', labelHeight=0.03,
        flip=False, ori=0.0, depth=-3, readOnly=False)
    momentary_pleasant_txt_B = visual.TextStim(win=win, name='momentary_pleasant_txt_B',
        text='very pleasant',
        font='Arial',
        pos=[0,0], draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-4.0);
    momentary_unpleasant_txt_B = visual.TextStim(win=win, name='momentary_unpleasant_txt_B',
        text='very unpleasant',
        font='Arial',
        pos=[0,0], draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-5.0);
    mouse_instruct_txt_2 = visual.TextStim(win=win, name='mouse_instruct_txt_2',
        text='Use your mouse to select the point on the slider.',
        font='Arial',
        pos=(0, 0.1), draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-6.0);
    
    # --- Initialize components for Routine "baseline_instruct" ---
    baseline_instruct_txt = visual.TextStim(win=win, name='baseline_instruct_txt',
        text='You are about to begin a 3-minute rest period. Please focus on the cross displayed on the screen.',
        font='Arial',
        pos=(0, 0), draggable=False, height=0.05, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=0.0);
    
    # --- Initialize components for Routine "stim_recovery" ---
    fixation_stim_recovery = visual.TextStim(win=win, name='fixation_stim_recovery',
        text='+',
        font='Arial',
        pos=(0, 0), draggable=False, height=0.1, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=0.0);
    
    # --- Initialize components for Routine "momentary_valence_rating_A" ---
    momentary_valence_mouse_A = event.Mouse(win=win)
    x, y = [None, None]
    momentary_valence_mouse_A.mouseClock = core.Clock()
    momentary_valence_question_txt_A = visual.TextStim(win=win, name='momentary_valence_question_txt_A',
        text='How do you feel right now?',
        font='Arial',
        pos=(0, 0.2), draggable=True, height=0.04, wrapWidth=1.8, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-2.0);
    momentary_valence_slider_A = visual.Slider(win=win, name='momentary_valence_slider_A',
        startValue=None, size=(0.8, 0.03), pos=[0,0], units=win.units,
        labels=None, ticks=(1, 2, 3, 4, 5, 6, 7), granularity=1.0,
        style='rating', styleTweaks=(), opacity=None,
        labelColor='LightGray', markerColor=[-1.0000, -1.0000, -1.0000], lineColor='White', colorSpace='rgb',
        font='Open Sans', labelHeight=0.03,
        flip=False, ori=0.0, depth=-3, readOnly=False)
    momentary_pleasant_txt_A = visual.TextStim(win=win, name='momentary_pleasant_txt_A',
        text='very pleasant',
        font='Arial',
        pos=[0,0], draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-4.0);
    momentary_unpleasant_txt_A = visual.TextStim(win=win, name='momentary_unpleasant_txt_A',
        text='very unpleasant',
        font='Arial',
        pos=[0,0], draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-5.0);
    mouse_instuct_txt = visual.TextStim(win=win, name='mouse_instuct_txt',
        text='Use your mouse to select the point on the slider.',
        font='Arial',
        pos=(0, 0.1), draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-6.0);
    
    # --- Initialize components for Routine "momentary_arousal_rating" ---
    momentary_arousal_mouse = event.Mouse(win=win)
    x, y = [None, None]
    momentary_arousal_mouse.mouseClock = core.Clock()
    momentary_arousal_question_txt = visual.TextStim(win=win, name='momentary_arousal_question_txt',
        text='How do you feel right now?',
        font='Arial',
        pos=(0, 0.2), draggable=True, height=0.04, wrapWidth=1.8, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-2.0);
    momentary_arousal_slider = visual.Slider(win=win, name='momentary_arousal_slider',
        startValue=None, size=(0.8, 0.03), pos=[0,0], units=win.units,
        labels=None, ticks=(1, 2, 3, 4, 5, 6, 7), granularity=1.0,
        style='rating', styleTweaks=(), opacity=None,
        labelColor='LightGray', markerColor=[-1.0000, -1.0000, -1.0000], lineColor='White', colorSpace='rgb',
        font='Open Sans', labelHeight=0.03,
        flip=False, ori=0.0, depth=-3, readOnly=False)
    momentary_alert_txt = visual.TextStim(win=win, name='momentary_alert_txt',
        text='very alert',
        font='Arial',
        pos=[0,0], draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-4.0);
    momentary_not_alert_txt = visual.TextStim(win=win, name='momentary_not_alert_txt',
        text='not alert at all',
        font='Arial',
        pos=[0,0], draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-5.0);
    mouse_instruct_txt_1 = visual.TextStim(win=win, name='mouse_instruct_txt_1',
        text='Use your mouse to select the point on the slider.',
        font='Arial',
        pos=(0, 0.1), draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-6.0);
    
    # --- Initialize components for Routine "momentary_valence_rating_B" ---
    momentary_valence_mouse_B = event.Mouse(win=win)
    x, y = [None, None]
    momentary_valence_mouse_B.mouseClock = core.Clock()
    momentary_valence_question_txt_B = visual.TextStim(win=win, name='momentary_valence_question_txt_B',
        text='How do you feel right now?',
        font='Arial',
        pos=(0, 0.2), draggable=True, height=0.04, wrapWidth=1.8, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-2.0);
    momentary_valence_slider_B = visual.Slider(win=win, name='momentary_valence_slider_B',
        startValue=None, size=(0.8, 0.03), pos=[0,0], units=win.units,
        labels=None, ticks=(1, 2, 3, 4, 5, 6, 7), granularity=1.0,
        style='rating', styleTweaks=(), opacity=None,
        labelColor='LightGray', markerColor=[-1.0000, -1.0000, -1.0000], lineColor='White', colorSpace='rgb',
        font='Open Sans', labelHeight=0.03,
        flip=False, ori=0.0, depth=-3, readOnly=False)
    momentary_pleasant_txt_B = visual.TextStim(win=win, name='momentary_pleasant_txt_B',
        text='very pleasant',
        font='Arial',
        pos=[0,0], draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-4.0);
    momentary_unpleasant_txt_B = visual.TextStim(win=win, name='momentary_unpleasant_txt_B',
        text='very unpleasant',
        font='Arial',
        pos=[0,0], draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-5.0);
    mouse_instruct_txt_2 = visual.TextStim(win=win, name='mouse_instruct_txt_2',
        text='Use your mouse to select the point on the slider.',
        font='Arial',
        pos=(0, 0.1), draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-6.0);
    
    # --- Initialize components for Routine "stim_rating_instruct" ---
    stim_rating_instruct_txt = visual.TextStim(win=win, name='stim_rating_instruct_txt',
        text='You’ve now completed all video and rest blocks.\n\nYou will now be asked to answer some final questions about the videos.\n\n',
        font='Arial',
        pos=(0, 0), draggable=False, height=0.05, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=0.0);
    
    # --- Initialize components for Routine "stimuli_emo_rating" ---
    stim_arousal_mouse_2 = event.Mouse(win=win)
    x, y = [None, None]
    stim_arousal_mouse_2.mouseClock = core.Clock()
    stimuli_emo_question_txt = visual.TextStim(win=win, name='stimuli_emo_question_txt',
        text='How did you feel while watching this video?',
        font='Arial',
        pos=(0, 0.03), draggable=True, height=0.04, wrapWidth=1.8, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-2.0);
    stimuli_emo_subquest_txt = visual.TextStim(win=win, name='stimuli_emo_subquest_txt',
        text='(Please type ONE word below)',
        font='Arial',
        pos=(0, -0.01), draggable=True, height=0.03, wrapWidth=1.8, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-3.0);
    intensitySlider = visual.Slider(win=win, name='intensitySlider',
        startValue=None, size=(0.8, 0.03), pos=[0,0], units=win.units,
        labels=None, ticks=(1, 2, 3, 4, 5, 6, 7), granularity=1.0,
        style='rating', styleTweaks=(), opacity=None,
        labelColor='LightGray', markerColor=[-1.0000, -1.0000, -1.0000], lineColor='White', colorSpace='rgb',
        font='Open Sans', labelHeight=0.03,
        flip=False, ori=0.0, depth=-4, readOnly=False)
    intensitySlider_txt_very_intense = visual.TextStim(win=win, name='intensitySlider_txt_very_intense',
        text='very intense',
        font='Arial',
        pos=(0.6,-0.4), draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-5.0);
    intensitySlider_txt_not_intense = visual.TextStim(win=win, name='intensitySlider_txt_not_intense',
        text='not intense at all',
        font='Arial',
        pos=(-0.6,-0.4), draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-6.0);
    screenshot_image_arousal_2 = visual.ImageStim(
        win=win,
        name='screenshot_image_arousal_2', 
        image='default.png', mask=None, anchor='center',
        ori=0.0, pos=(0, 0.3), draggable=False, size=(None, 0.3),
        color=[1,1,1], colorSpace='rgb', opacity=None,
        flipHoriz=False, flipVert=False,
        texRes=128.0, interpolate=True, depth=-7.0)
    emotionText = visual.TextBox2(
         win, text=None, placeholder='Type here...', font='Arial',
         ori=0.0, pos=(0, -0.1), draggable=False,      letterHeight=0.03,
         size=(0.6, 0.05), borderWidth=2.0,
         color='white', colorSpace='rgb',
         opacity=None,
         bold=False, italic=False,
         lineSpacing=1.0, speechPoint=None,
         padding=0.0, alignment='center',
         anchor='center', overflow='visible',
         fillColor=None, borderColor=[0.6549, 0.6549, 0.6549],
         flipHoriz=False, flipVert=False, languageStyle='LTR',
         editable=True,
         name='emotionText',
         depth=-8, autoLog=True,
    )
    intensityQuestion = visual.TextStim(win=win, name='intensityQuestion',
        text='How intense was this feeling?',
        font='Arial',
        pos=(0, -0.25), draggable=False, height=0.04, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-9.0);
    
    # --- Initialize components for Routine "stimuli_valence_rating_A" ---
    stim_valence_mouse_A = event.Mouse(win=win)
    x, y = [None, None]
    stim_valence_mouse_A.mouseClock = core.Clock()
    stimuli_valence_question_txt_A = visual.TextStim(win=win, name='stimuli_valence_question_txt_A',
        text='Overall, how did you feel while watching this video?',
        font='Arial',
        pos=(0, 0.025), draggable=True, height=0.04, wrapWidth=1.8, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-2.0);
    stim_valence_slider_A = visual.Slider(win=win, name='stim_valence_slider_A',
        startValue=None, size=(0.8, 0.03), pos=[0,0], units=win.units,
        labels=None, ticks=(1, 2, 3, 4, 5, 6, 7), granularity=1.0,
        style='rating', styleTweaks=(), opacity=None,
        labelColor='LightGray', markerColor=[-1.0000, -1.0000, -1.0000], lineColor='White', colorSpace='rgb',
        font='Open Sans', labelHeight=0.03,
        flip=False, ori=0.0, depth=-3, readOnly=False)
    stim_pleasant_txt_A = visual.TextStim(win=win, name='stim_pleasant_txt_A',
        text='very pleasant',
        font='Arial',
        pos=(0.5,-0.25), draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-4.0);
    stim_unpleasant_txt_A = visual.TextStim(win=win, name='stim_unpleasant_txt_A',
        text='very unpleasant',
        font='Arial',
        pos=(-0.51,-0.25), draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-5.0);
    screenshot_image_valence_A = visual.ImageStim(
        win=win,
        name='screenshot_image_valence_A', 
        image='default.png', mask=None, anchor='center',
        ori=0.0, pos=(0, 0.3), draggable=False, size=(None, 0.3),
        color=[1,1,1], colorSpace='rgb', opacity=None,
        flipHoriz=False, flipVert=False,
        texRes=128.0, interpolate=True, depth=-6.0)
    mouse_instruct_txt_3 = visual.TextStim(win=win, name='mouse_instruct_txt_3',
        text='Use your mouse to select the point on the slider.',
        font='Arial',
        pos=(0, -0.04), draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-7.0);
    
    # --- Initialize components for Routine "stimuli_arousal_rating" ---
    stim_arousal_mouse = event.Mouse(win=win)
    x, y = [None, None]
    stim_arousal_mouse.mouseClock = core.Clock()
    stimuli_arousal_question_txt = visual.TextStim(win=win, name='stimuli_arousal_question_txt',
        text='Overall, how did you feel while watching this video?',
        font='Arial',
        pos=(0, 0.025), draggable=True, height=0.04, wrapWidth=1.8, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-2.0);
    stim_arousal_slider = visual.Slider(win=win, name='stim_arousal_slider',
        startValue=None, size=(0.8, 0.03), pos=[0,0], units=win.units,
        labels=None, ticks=(1, 2, 3, 4, 5, 6, 7), granularity=1.0,
        style='rating', styleTweaks=(), opacity=None,
        labelColor='LightGray', markerColor=[-1.0000, -1.0000, -1.0000], lineColor='White', colorSpace='rgb',
        font='Open Sans', labelHeight=0.03,
        flip=False, ori=0.0, depth=-3, readOnly=False)
    stim_alert_txt = visual.TextStim(win=win, name='stim_alert_txt',
        text='very alert',
        font='Arial',
        pos=(0.5,-0.25), draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-4.0);
    stim_not_alert_txt = visual.TextStim(win=win, name='stim_not_alert_txt',
        text='not alert at all',
        font='Arial',
        pos=(-0.5,-0.25), draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-5.0);
    screenshot_image_arousal = visual.ImageStim(
        win=win,
        name='screenshot_image_arousal', 
        image='default.png', mask=None, anchor='center',
        ori=0.0, pos=(0, 0.3), draggable=False, size=(None, 0.3),
        color=[1,1,1], colorSpace='rgb', opacity=None,
        flipHoriz=False, flipVert=False,
        texRes=128.0, interpolate=True, depth=-6.0)
    mouse_instruct_txt_4 = visual.TextStim(win=win, name='mouse_instruct_txt_4',
        text='Use your mouse to select the point on the slider.',
        font='Arial',
        pos=(0, -0.04), draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-7.0);
    
    # --- Initialize components for Routine "stimuli_valence_rating_B" ---
    stim_valence_mouse_B = event.Mouse(win=win)
    x, y = [None, None]
    stim_valence_mouse_B.mouseClock = core.Clock()
    stimuli_valence_question_txt_B = visual.TextStim(win=win, name='stimuli_valence_question_txt_B',
        text='Overall, how did you feel while watching this video?',
        font='Arial',
        pos=(0, 0.025), draggable=True, height=0.04, wrapWidth=1.8, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-2.0);
    stim_valence_slider_B = visual.Slider(win=win, name='stim_valence_slider_B',
        startValue=None, size=(0.8, 0.03), pos=[0,0], units=win.units,
        labels=None, ticks=(1, 2, 3, 4, 5, 6, 7), granularity=1.0,
        style='rating', styleTweaks=(), opacity=None,
        labelColor='LightGray', markerColor=[-1.0000, -1.0000, -1.0000], lineColor='White', colorSpace='rgb',
        font='Open Sans', labelHeight=0.03,
        flip=False, ori=0.0, depth=-3, readOnly=False)
    stim_pleasant_txt_B = visual.TextStim(win=win, name='stim_pleasant_txt_B',
        text='very pleasant',
        font='Arial',
        pos=(0.5,-0.25), draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-4.0);
    stim_unpleasant_txt_B = visual.TextStim(win=win, name='stim_unpleasant_txt_B',
        text='very unpleasant',
        font='Arial',
        pos=(-0.51,-0.25), draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-5.0);
    screenshot_image_valence_B = visual.ImageStim(
        win=win,
        name='screenshot_image_valence_B', 
        image='default.png', mask=None, anchor='center',
        ori=0.0, pos=(0, 0.3), draggable=False, size=(None, 0.3),
        color=[1,1,1], colorSpace='rgb', opacity=None,
        flipHoriz=False, flipVert=False,
        texRes=128.0, interpolate=True, depth=-6.0)
    moust_instruct_txt_5 = visual.TextStim(win=win, name='moust_instruct_txt_5',
        text='Use your mouse to select the point on the slider.',
        font='Arial',
        pos=(0, -0.04), draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-7.0);
    
    # --- Initialize components for Routine "approach_rating" ---
    stim_approach_mouse = event.Mouse(win=win)
    x, y = [None, None]
    stim_approach_mouse.mouseClock = core.Clock()
    stim_approach_slider = visual.Slider(win=win, name='stim_approach_slider',
        startValue=None, size=(0.8, 0.03), pos=(0, -0.2), units=win.units,
        labels=None, ticks=(1, 2, 3, 4, 5, 6, 7), granularity=1.0,
        style='rating', styleTweaks=(), opacity=None,
        labelColor='LightGray', markerColor=[-1.0000, -1.0000, -1.0000], lineColor='White', colorSpace='rgb',
        font='Open Sans', labelHeight=0.03,
        flip=False, ori=0.0, depth=-2, readOnly=False)
    stim_approach_question_txt = visual.TextStim(win=win, name='stim_approach_question_txt',
        text='How much did you want to watch this?',
        font='Arial',
        pos=(0, 0.025), draggable=False, height=0.04, wrapWidth=2.2, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-3.0);
    screenshot_image_approach = visual.ImageStim(
        win=win,
        name='screenshot_image_approach', 
        image='default.png', mask=None, anchor='center',
        ori=0.0, pos=(0, 0.3), draggable=False, size=(None, 0.3),
        color=[1,1,1], colorSpace='rgb', opacity=None,
        flipHoriz=False, flipVert=False,
        texRes=128.0, interpolate=True, depth=-4.0)
    not_at_all_txt = visual.TextStim(win=win, name='not_at_all_txt',
        text='Strongly wanted to avoid it',
        font='Arial',
        pos=(-0.6,-0.25), draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-5.0);
    approach_txt = visual.TextStim(win=win, name='approach_txt',
        text='Strongly wanted to watch it',
        font='Arial',
        pos=(0.6,-0.25), draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-6.0);
    moust_instruct_6_txt = visual.TextStim(win=win, name='moust_instruct_6_txt',
        text='Use your mouse to select the point on the slider.',
        font='Arial',
        pos=(0, -0.04), draggable=False, height=0.03, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=-7.0);
    
    # --- Initialize components for Routine "end" ---
    end_text = visual.TextStim(win=win, name='end_text',
        text="Thank you! You\\'ve completed the study.\n\nPlease let the experimenter know you\\'re finished.",
        font='Arial',
        pos=(0, 0), draggable=False, height=0.05, wrapWidth=None, ori=0.0, 
        color='white', colorSpace='rgb', opacity=None, 
        languageStyle='LTR',
        depth=0.0);
    
    # create some handy timers
    
    # global clock to track the time since experiment started
    if globalClock is None:
        # create a clock if not given one
        globalClock = core.Clock()
    if isinstance(globalClock, str):
        # if given a string, make a clock accoridng to it
        if globalClock == 'float':
            # get timestamps as a simple value
            globalClock = core.Clock(format='float')
        elif globalClock == 'iso':
            # get timestamps in ISO format
            globalClock = core.Clock(format='%Y-%m-%d_%H:%M:%S.%f%z')
        else:
            # get timestamps in a custom format
            globalClock = core.Clock(format=globalClock)
    if ioServer is not None:
        ioServer.syncClock(globalClock)
    logging.setDefaultClock(globalClock)
    if eyetracker is not None:
        eyetracker.enableEventReporting()
    # routine timer to track time remaining of each (possibly non-slip) routine
    routineTimer = core.Clock()
    win.flip()  # flip window to reset last flip timer
    # store the exact time the global clock started
    expInfo['expStart'] = data.getDateStr(
        format='%Y-%m-%d %Hh%M.%S.%f %z', fractionalSecondDigits=6
    )
    
    # --- Prepare to start Routine "trigger_setup" ---
    # create an object to store info about Routine trigger_setup
    trigger_setup = data.Routine(
        name='trigger_setup',
        components=[],
    )
    trigger_setup.status = NOT_STARTED
    continueRoutine = True
    # update component parameters for each repeat
    # Run 'Begin Routine' code from code
    # set variable to record valence and arousal ratings
    condition = 'pre_baseline'
    
    #----
    # Log time for camera
    # ---
    thisExp.addData('onset_wall', time.time())
    thisExp.addData('time_since_recording_start', time.time() - experiment_start_wall)
    # Run 'Begin Routine' code from webcam_code
    bio.clear()
    # store start times for trigger_setup
    trigger_setup.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
    trigger_setup.tStart = globalClock.getTime(format='float')
    trigger_setup.status = STARTED
    thisExp.addData('trigger_setup.started', trigger_setup.tStart)
    trigger_setup.maxDuration = None
    # keep track of which components have finished
    trigger_setupComponents = trigger_setup.components
    for thisComponent in trigger_setup.components:
        thisComponent.tStart = None
        thisComponent.tStop = None
        thisComponent.tStartRefresh = None
        thisComponent.tStopRefresh = None
        if hasattr(thisComponent, 'status'):
            thisComponent.status = NOT_STARTED
    # reset timers
    t = 0
    _timeToFirstFrame = win.getFutureFlipTime(clock="now")
    frameN = -1
    
    # --- Run Routine "trigger_setup" ---
    thisExp.currentRoutine = trigger_setup
    trigger_setup.forceEnded = routineForceEnded = not continueRoutine
    while continueRoutine:
        # get current time
        t = routineTimer.getTime()
        tThisFlip = win.getFutureFlipTime(clock=routineTimer)
        tThisFlipGlobal = win.getFutureFlipTime(clock=None)
        frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
        # update/draw components on each frame
        
        # check for quit (typically the Esc key)
        if defaultKeyboard.getKeys(keyList=["escape"]):
            thisExp.status = FINISHED
        if thisExp.status == FINISHED or endExpNow:
            endExperiment(thisExp, win=win)
            return
        # pause experiment here if requested
        if thisExp.status == PAUSED:
            pauseExperiment(
                thisExp=thisExp, 
                win=win, 
                timers=[routineTimer, globalClock], 
                currentRoutine=trigger_setup,
            )
            # skip the frame we paused on
            continue
        
        # has a Component requested the Routine to end?
        if not continueRoutine:
            trigger_setup.forceEnded = routineForceEnded = True
        # has the Routine been forcibly ended?
        if trigger_setup.forceEnded or routineForceEnded:
            break
        # has every Component finished?
        continueRoutine = False
        for thisComponent in trigger_setup.components:
            if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                continueRoutine = True
                break  # at least one component has not yet finished
        
        # refresh the screen
        if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
            win.flip()
    
    # --- Ending Routine "trigger_setup" ---
    for thisComponent in trigger_setup.components:
        if hasattr(thisComponent, "setAutoDraw"):
            thisComponent.setAutoDraw(False)
    # store stop times for trigger_setup
    trigger_setup.tStop = globalClock.getTime(format='float')
    trigger_setup.tStopRefresh = tThisFlipGlobal
    thisExp.addData('trigger_setup.stopped', trigger_setup.tStop)
    # Run 'End Routine' code from code
    thisExp.addData("conditionOrder", condition_order)
    thisExp.nextEntry()
    # the Routine "trigger_setup" was not non-slip safe, so reset the non-slip timer
    routineTimer.reset()
    
    # --- Prepare to start Routine "overview" ---
    # create an object to store info about Routine overview
    overview = data.Routine(
        name='overview',
        components=[overview_txt, key_resp_overview],
    )
    overview.status = NOT_STARTED
    continueRoutine = True
    # update component parameters for each repeat
    # create starting attributes for key_resp_overview
    key_resp_overview.keys = []
    key_resp_overview.rt = []
    _key_resp_overview_allKeys = []
    # store start times for overview
    overview.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
    overview.tStart = globalClock.getTime(format='float')
    overview.status = STARTED
    thisExp.addData('overview.started', overview.tStart)
    overview.maxDuration = None
    # keep track of which components have finished
    overviewComponents = overview.components
    for thisComponent in overview.components:
        thisComponent.tStart = None
        thisComponent.tStop = None
        thisComponent.tStartRefresh = None
        thisComponent.tStopRefresh = None
        if hasattr(thisComponent, 'status'):
            thisComponent.status = NOT_STARTED
    # reset timers
    t = 0
    _timeToFirstFrame = win.getFutureFlipTime(clock="now")
    frameN = -1
    
    # --- Run Routine "overview" ---
    thisExp.currentRoutine = overview
    overview.forceEnded = routineForceEnded = not continueRoutine
    while continueRoutine:
        # get current time
        t = routineTimer.getTime()
        tThisFlip = win.getFutureFlipTime(clock=routineTimer)
        tThisFlipGlobal = win.getFutureFlipTime(clock=None)
        frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
        # update/draw components on each frame
        
        # *overview_txt* updates
        
        # if overview_txt is starting this frame...
        if overview_txt.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
            # keep track of start time/frame for later
            overview_txt.frameNStart = frameN  # exact frame index
            overview_txt.tStart = t  # local t and not account for scr refresh
            overview_txt.tStartRefresh = tThisFlipGlobal  # on global time
            win.timeOnFlip(overview_txt, 'tStartRefresh')  # time at next scr refresh
            # add timestamp to datafile
            thisExp.timestampOnFlip(win, 'overview_txt.started')
            # update status
            overview_txt.status = STARTED
            overview_txt.setAutoDraw(True)
        
        # if overview_txt is active this frame...
        if overview_txt.status == STARTED:
            # update params
            pass
        
        # *key_resp_overview* updates
        waitOnFlip = False
        
        # if key_resp_overview is starting this frame...
        if key_resp_overview.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
            # keep track of start time/frame for later
            key_resp_overview.frameNStart = frameN  # exact frame index
            key_resp_overview.tStart = t  # local t and not account for scr refresh
            key_resp_overview.tStartRefresh = tThisFlipGlobal  # on global time
            win.timeOnFlip(key_resp_overview, 'tStartRefresh')  # time at next scr refresh
            # add timestamp to datafile
            thisExp.timestampOnFlip(win, 'key_resp_overview.started')
            # update status
            key_resp_overview.status = STARTED
            # keyboard checking is just starting
            waitOnFlip = True
            win.callOnFlip(key_resp_overview.clock.reset)  # t=0 on next screen flip
            win.callOnFlip(key_resp_overview.clearEvents, eventType='keyboard')  # clear events on next screen flip
        if key_resp_overview.status == STARTED and not waitOnFlip:
            theseKeys = key_resp_overview.getKeys(keyList=['space'], ignoreKeys=["escape"], waitRelease=False)
            _key_resp_overview_allKeys.extend(theseKeys)
            if len(_key_resp_overview_allKeys):
                key_resp_overview.keys = _key_resp_overview_allKeys[-1].name  # just the last key pressed
                key_resp_overview.rt = _key_resp_overview_allKeys[-1].rt
                key_resp_overview.duration = _key_resp_overview_allKeys[-1].duration
                # a response ends the routine
                continueRoutine = False
        
        # check for quit (typically the Esc key)
        if defaultKeyboard.getKeys(keyList=["escape"]):
            thisExp.status = FINISHED
        if thisExp.status == FINISHED or endExpNow:
            endExperiment(thisExp, win=win)
            return
        # pause experiment here if requested
        if thisExp.status == PAUSED:
            pauseExperiment(
                thisExp=thisExp, 
                win=win, 
                timers=[routineTimer, globalClock], 
                currentRoutine=overview,
            )
            # skip the frame we paused on
            continue
        
        # has a Component requested the Routine to end?
        if not continueRoutine:
            overview.forceEnded = routineForceEnded = True
        # has the Routine been forcibly ended?
        if overview.forceEnded or routineForceEnded:
            break
        # has every Component finished?
        continueRoutine = False
        for thisComponent in overview.components:
            if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                continueRoutine = True
                break  # at least one component has not yet finished
        
        # refresh the screen
        if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
            win.flip()
    
    # --- Ending Routine "overview" ---
    for thisComponent in overview.components:
        if hasattr(thisComponent, "setAutoDraw"):
            thisComponent.setAutoDraw(False)
    # store stop times for overview
    overview.tStop = globalClock.getTime(format='float')
    overview.tStopRefresh = tThisFlipGlobal
    thisExp.addData('overview.stopped', overview.tStop)
    # check responses
    if key_resp_overview.keys in ['', [], None]:  # No response was made
        key_resp_overview.keys = None
    thisExp.addData('key_resp_overview.keys',key_resp_overview.keys)
    if key_resp_overview.keys != None:  # we had a response
        thisExp.addData('key_resp_overview.rt', key_resp_overview.rt)
        thisExp.addData('key_resp_overview.duration', key_resp_overview.duration)
    thisExp.nextEntry()
    # the Routine "overview" was not non-slip safe, so reset the non-slip timer
    routineTimer.reset()
    
    # set up handler to look after randomisation of conditions etc
    pre_baseline_ratings = data.TrialHandler2(
        name='pre_baseline_ratings',
        nReps=1.0, 
        method='random', 
        extraInfo=expInfo, 
        originPath=-1, 
        trialList=[None], 
        seed=None, 
        isTrials=True, 
    )
    thisExp.addLoop(pre_baseline_ratings)  # add the loop to the experiment
    thisPre_baseline_rating = pre_baseline_ratings.trialList[0]  # so we can initialise stimuli with some values
    # abbreviate parameter names if possible (e.g. rgb = thisPre_baseline_rating.rgb)
    if thisPre_baseline_rating != None:
        for paramName in thisPre_baseline_rating:
            globals()[paramName] = thisPre_baseline_rating[paramName]
    if thisSession is not None:
        # if running in a Session with a Liaison client, send data up to now
        thisSession.sendExperimentData()
    
    for thisPre_baseline_rating in pre_baseline_ratings:
        pre_baseline_ratings.status = STARTED
        if hasattr(thisPre_baseline_rating, 'status'):
            thisPre_baseline_rating.status = STARTED
        currentLoop = pre_baseline_ratings
        thisExp.timestampOnFlip(win, 'thisRow.t', format=globalClock.format)
        if thisSession is not None:
            # if running in a Session with a Liaison client, send data up to now
            thisSession.sendExperimentData()
        # abbreviate parameter names if possible (e.g. rgb = thisPre_baseline_rating.rgb)
        if thisPre_baseline_rating != None:
            for paramName in thisPre_baseline_rating:
                globals()[paramName] = thisPre_baseline_rating[paramName]
        
        # --- Prepare to start Routine "momentary_valence_rating_A" ---
        # create an object to store info about Routine momentary_valence_rating_A
        momentary_valence_rating_A = data.Routine(
            name='momentary_valence_rating_A',
            components=[momentary_valence_mouse_A, momentary_valence_question_txt_A, momentary_valence_slider_A, momentary_pleasant_txt_A, momentary_unpleasant_txt_A, mouse_instuct_txt],
        )
        momentary_valence_rating_A.status = NOT_STARTED
        continueRoutine = True
        # update component parameters for each repeat
        # Run 'Begin Routine' code from momentary_valence_rating_code_A
        momentary_valence_mouse_A.setVisible(True)
        timer = None
        
        condition = stim_condition
        
        # determine which slider will appear first
        rating_pair_count += 1
        if rating_pair_count % 2 == 1:
            rating_order = rating_start
        else:
            rating_order = 'arousal_first' if rating_start == 'valence_first' else 'valence_first'
        
        if rating_order == 'arousal_first':
            continueRoutine = False
        # setup some python lists for storing info about the momentary_valence_mouse_A
        momentary_valence_mouse_A.x = []
        momentary_valence_mouse_A.y = []
        momentary_valence_mouse_A.leftButton = []
        momentary_valence_mouse_A.midButton = []
        momentary_valence_mouse_A.rightButton = []
        momentary_valence_mouse_A.time = []
        gotValidClick = False  # until a click is received
        momentary_valence_slider_A.reset()
        momentary_valence_slider_A.setPos((0,0))
        momentary_pleasant_txt_A.setPos((0.5, -0.05))
        momentary_unpleasant_txt_A.setPos((-0.5, -0.05))
        # store start times for momentary_valence_rating_A
        momentary_valence_rating_A.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
        momentary_valence_rating_A.tStart = globalClock.getTime(format='float')
        momentary_valence_rating_A.status = STARTED
        thisExp.addData('momentary_valence_rating_A.started', momentary_valence_rating_A.tStart)
        momentary_valence_rating_A.maxDuration = None
        # keep track of which components have finished
        momentary_valence_rating_AComponents = momentary_valence_rating_A.components
        for thisComponent in momentary_valence_rating_A.components:
            thisComponent.tStart = None
            thisComponent.tStop = None
            thisComponent.tStartRefresh = None
            thisComponent.tStopRefresh = None
            if hasattr(thisComponent, 'status'):
                thisComponent.status = NOT_STARTED
        # reset timers
        t = 0
        _timeToFirstFrame = win.getFutureFlipTime(clock="now")
        frameN = -1
        
        # --- Run Routine "momentary_valence_rating_A" ---
        thisExp.currentRoutine = momentary_valence_rating_A
        momentary_valence_rating_A.forceEnded = routineForceEnded = not continueRoutine
        while continueRoutine:
            # if trial has changed, end Routine now
            if hasattr(thisPre_baseline_rating, 'status') and thisPre_baseline_rating.status == STOPPING:
                continueRoutine = False
            # get current time
            t = routineTimer.getTime()
            tThisFlip = win.getFutureFlipTime(clock=routineTimer)
            tThisFlipGlobal = win.getFutureFlipTime(clock=None)
            frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
            # update/draw components on each frame
            # Run 'Each Frame' code from momentary_valence_rating_code_A
            if momentary_valence_slider_A.getRating() is not None:
            
                if timer is None:
                    timer = core.CountdownTimer(2)
            
                if timer.getTime() < 0:
                    continueRoutine = False
            # *momentary_valence_mouse_A* updates
            
            # if momentary_valence_mouse_A is starting this frame...
            if momentary_valence_mouse_A.status == NOT_STARTED and t >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                momentary_valence_mouse_A.frameNStart = frameN  # exact frame index
                momentary_valence_mouse_A.tStart = t  # local t and not account for scr refresh
                momentary_valence_mouse_A.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(momentary_valence_mouse_A, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.addData('momentary_valence_mouse_A.started', t)
                # update status
                momentary_valence_mouse_A.status = STARTED
                momentary_valence_mouse_A.mouseClock.reset()
                prevButtonState = momentary_valence_mouse_A.getPressed()  # if button is down already this ISN'T a new click
            if momentary_valence_mouse_A.status == STARTED:  # only update if started and not finished!
                buttons = momentary_valence_mouse_A.getPressed()
                if buttons != prevButtonState:  # button state changed?
                    prevButtonState = buttons
                    if sum(buttons) > 0:  # state changed to a new click
                        pass
                        x, y = momentary_valence_mouse_A.getPos()
                        momentary_valence_mouse_A.x.append(float(x))
                        momentary_valence_mouse_A.y.append(float(y))
                        buttons = momentary_valence_mouse_A.getPressed()
                        momentary_valence_mouse_A.leftButton.append(buttons[0])
                        momentary_valence_mouse_A.midButton.append(buttons[1])
                        momentary_valence_mouse_A.rightButton.append(buttons[2])
                        momentary_valence_mouse_A.time.append(momentary_valence_mouse_A.mouseClock.getTime())
            
            # *momentary_valence_question_txt_A* updates
            
            # if momentary_valence_question_txt_A is starting this frame...
            if momentary_valence_question_txt_A.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                momentary_valence_question_txt_A.frameNStart = frameN  # exact frame index
                momentary_valence_question_txt_A.tStart = t  # local t and not account for scr refresh
                momentary_valence_question_txt_A.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(momentary_valence_question_txt_A, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'momentary_valence_question_txt_A.started')
                # update status
                momentary_valence_question_txt_A.status = STARTED
                momentary_valence_question_txt_A.setAutoDraw(True)
            
            # if momentary_valence_question_txt_A is active this frame...
            if momentary_valence_question_txt_A.status == STARTED:
                # update params
                pass
            
            # *momentary_valence_slider_A* updates
            
            # if momentary_valence_slider_A is starting this frame...
            if momentary_valence_slider_A.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                momentary_valence_slider_A.frameNStart = frameN  # exact frame index
                momentary_valence_slider_A.tStart = t  # local t and not account for scr refresh
                momentary_valence_slider_A.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(momentary_valence_slider_A, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'momentary_valence_slider_A.started')
                # update status
                momentary_valence_slider_A.status = STARTED
                momentary_valence_slider_A.setAutoDraw(True)
            
            # if momentary_valence_slider_A is active this frame...
            if momentary_valence_slider_A.status == STARTED:
                # update params
                pass
            
            # *momentary_pleasant_txt_A* updates
            
            # if momentary_pleasant_txt_A is starting this frame...
            if momentary_pleasant_txt_A.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                momentary_pleasant_txt_A.frameNStart = frameN  # exact frame index
                momentary_pleasant_txt_A.tStart = t  # local t and not account for scr refresh
                momentary_pleasant_txt_A.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(momentary_pleasant_txt_A, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'momentary_pleasant_txt_A.started')
                # update status
                momentary_pleasant_txt_A.status = STARTED
                momentary_pleasant_txt_A.setAutoDraw(True)
            
            # if momentary_pleasant_txt_A is active this frame...
            if momentary_pleasant_txt_A.status == STARTED:
                # update params
                pass
            
            # *momentary_unpleasant_txt_A* updates
            
            # if momentary_unpleasant_txt_A is starting this frame...
            if momentary_unpleasant_txt_A.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                momentary_unpleasant_txt_A.frameNStart = frameN  # exact frame index
                momentary_unpleasant_txt_A.tStart = t  # local t and not account for scr refresh
                momentary_unpleasant_txt_A.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(momentary_unpleasant_txt_A, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'momentary_unpleasant_txt_A.started')
                # update status
                momentary_unpleasant_txt_A.status = STARTED
                momentary_unpleasant_txt_A.setAutoDraw(True)
            
            # if momentary_unpleasant_txt_A is active this frame...
            if momentary_unpleasant_txt_A.status == STARTED:
                # update params
                pass
            
            # *mouse_instuct_txt* updates
            
            # if mouse_instuct_txt is starting this frame...
            if mouse_instuct_txt.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                mouse_instuct_txt.frameNStart = frameN  # exact frame index
                mouse_instuct_txt.tStart = t  # local t and not account for scr refresh
                mouse_instuct_txt.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(mouse_instuct_txt, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'mouse_instuct_txt.started')
                # update status
                mouse_instuct_txt.status = STARTED
                mouse_instuct_txt.setAutoDraw(True)
            
            # if mouse_instuct_txt is active this frame...
            if mouse_instuct_txt.status == STARTED:
                # update params
                pass
            
            # check for quit (typically the Esc key)
            if defaultKeyboard.getKeys(keyList=["escape"]):
                thisExp.status = FINISHED
            if thisExp.status == FINISHED or endExpNow:
                endExperiment(thisExp, win=win)
                return
            # pause experiment here if requested
            if thisExp.status == PAUSED:
                pauseExperiment(
                    thisExp=thisExp, 
                    win=win, 
                    timers=[routineTimer, globalClock], 
                    currentRoutine=momentary_valence_rating_A,
                )
                # skip the frame we paused on
                continue
            
            # has a Component requested the Routine to end?
            if not continueRoutine:
                momentary_valence_rating_A.forceEnded = routineForceEnded = True
            # has the Routine been forcibly ended?
            if momentary_valence_rating_A.forceEnded or routineForceEnded:
                break
            # has every Component finished?
            continueRoutine = False
            for thisComponent in momentary_valence_rating_A.components:
                if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                    continueRoutine = True
                    break  # at least one component has not yet finished
            
            # refresh the screen
            if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                win.flip()
        
        # --- Ending Routine "momentary_valence_rating_A" ---
        for thisComponent in momentary_valence_rating_A.components:
            if hasattr(thisComponent, "setAutoDraw"):
                thisComponent.setAutoDraw(False)
        # store stop times for momentary_valence_rating_A
        momentary_valence_rating_A.tStop = globalClock.getTime(format='float')
        momentary_valence_rating_A.tStopRefresh = tThisFlipGlobal
        thisExp.addData('momentary_valence_rating_A.stopped', momentary_valence_rating_A.tStop)
        # Run 'End Routine' code from momentary_valence_rating_code_A
        momentary_valence_mouse_A.setVisible(False)
        
        thisExp.addData('condition', condition)
        # store data for pre_baseline_ratings (TrialHandler)
        pre_baseline_ratings.addData('momentary_valence_mouse_A.x', momentary_valence_mouse_A.x)
        pre_baseline_ratings.addData('momentary_valence_mouse_A.y', momentary_valence_mouse_A.y)
        pre_baseline_ratings.addData('momentary_valence_mouse_A.leftButton', momentary_valence_mouse_A.leftButton)
        pre_baseline_ratings.addData('momentary_valence_mouse_A.midButton', momentary_valence_mouse_A.midButton)
        pre_baseline_ratings.addData('momentary_valence_mouse_A.rightButton', momentary_valence_mouse_A.rightButton)
        pre_baseline_ratings.addData('momentary_valence_mouse_A.time', momentary_valence_mouse_A.time)
        pre_baseline_ratings.addData('momentary_valence_slider_A.response', momentary_valence_slider_A.getRating())
        pre_baseline_ratings.addData('momentary_valence_slider_A.rt', momentary_valence_slider_A.getRT())
        # the Routine "momentary_valence_rating_A" was not non-slip safe, so reset the non-slip timer
        routineTimer.reset()
        
        # --- Prepare to start Routine "momentary_arousal_rating" ---
        # create an object to store info about Routine momentary_arousal_rating
        momentary_arousal_rating = data.Routine(
            name='momentary_arousal_rating',
            components=[momentary_arousal_mouse, momentary_arousal_question_txt, momentary_arousal_slider, momentary_alert_txt, momentary_not_alert_txt, mouse_instruct_txt_1],
        )
        momentary_arousal_rating.status = NOT_STARTED
        continueRoutine = True
        # update component parameters for each repeat
        # Run 'Begin Routine' code from momentary_arousal_rating_code_B
        momentary_arousal_mouse.setVisible(True)
        timer = None
        
        condition = stim_condition
        # setup some python lists for storing info about the momentary_arousal_mouse
        momentary_arousal_mouse.x = []
        momentary_arousal_mouse.y = []
        momentary_arousal_mouse.leftButton = []
        momentary_arousal_mouse.midButton = []
        momentary_arousal_mouse.rightButton = []
        momentary_arousal_mouse.time = []
        gotValidClick = False  # until a click is received
        momentary_arousal_slider.reset()
        momentary_arousal_slider.setPos((0,0))
        momentary_alert_txt.setPos((0.5, -0.05))
        momentary_not_alert_txt.setPos((-0.5, -0.05))
        # store start times for momentary_arousal_rating
        momentary_arousal_rating.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
        momentary_arousal_rating.tStart = globalClock.getTime(format='float')
        momentary_arousal_rating.status = STARTED
        thisExp.addData('momentary_arousal_rating.started', momentary_arousal_rating.tStart)
        momentary_arousal_rating.maxDuration = None
        # keep track of which components have finished
        momentary_arousal_ratingComponents = momentary_arousal_rating.components
        for thisComponent in momentary_arousal_rating.components:
            thisComponent.tStart = None
            thisComponent.tStop = None
            thisComponent.tStartRefresh = None
            thisComponent.tStopRefresh = None
            if hasattr(thisComponent, 'status'):
                thisComponent.status = NOT_STARTED
        # reset timers
        t = 0
        _timeToFirstFrame = win.getFutureFlipTime(clock="now")
        frameN = -1
        
        # --- Run Routine "momentary_arousal_rating" ---
        thisExp.currentRoutine = momentary_arousal_rating
        momentary_arousal_rating.forceEnded = routineForceEnded = not continueRoutine
        while continueRoutine:
            # if trial has changed, end Routine now
            if hasattr(thisPre_baseline_rating, 'status') and thisPre_baseline_rating.status == STOPPING:
                continueRoutine = False
            # get current time
            t = routineTimer.getTime()
            tThisFlip = win.getFutureFlipTime(clock=routineTimer)
            tThisFlipGlobal = win.getFutureFlipTime(clock=None)
            frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
            # update/draw components on each frame
            # Run 'Each Frame' code from momentary_arousal_rating_code_B
            if momentary_arousal_slider.getRating() is not None:
            
                if timer is None:
                    timer = core.CountdownTimer(2)
            
                if timer.getTime() < 0:
                    continueRoutine = False
            # *momentary_arousal_mouse* updates
            
            # if momentary_arousal_mouse is starting this frame...
            if momentary_arousal_mouse.status == NOT_STARTED and t >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                momentary_arousal_mouse.frameNStart = frameN  # exact frame index
                momentary_arousal_mouse.tStart = t  # local t and not account for scr refresh
                momentary_arousal_mouse.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(momentary_arousal_mouse, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.addData('momentary_arousal_mouse.started', t)
                # update status
                momentary_arousal_mouse.status = STARTED
                momentary_arousal_mouse.mouseClock.reset()
                prevButtonState = momentary_arousal_mouse.getPressed()  # if button is down already this ISN'T a new click
            if momentary_arousal_mouse.status == STARTED:  # only update if started and not finished!
                buttons = momentary_arousal_mouse.getPressed()
                if buttons != prevButtonState:  # button state changed?
                    prevButtonState = buttons
                    if sum(buttons) > 0:  # state changed to a new click
                        pass
                        x, y = momentary_arousal_mouse.getPos()
                        momentary_arousal_mouse.x.append(float(x))
                        momentary_arousal_mouse.y.append(float(y))
                        buttons = momentary_arousal_mouse.getPressed()
                        momentary_arousal_mouse.leftButton.append(buttons[0])
                        momentary_arousal_mouse.midButton.append(buttons[1])
                        momentary_arousal_mouse.rightButton.append(buttons[2])
                        momentary_arousal_mouse.time.append(momentary_arousal_mouse.mouseClock.getTime())
            
            # *momentary_arousal_question_txt* updates
            
            # if momentary_arousal_question_txt is starting this frame...
            if momentary_arousal_question_txt.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                momentary_arousal_question_txt.frameNStart = frameN  # exact frame index
                momentary_arousal_question_txt.tStart = t  # local t and not account for scr refresh
                momentary_arousal_question_txt.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(momentary_arousal_question_txt, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'momentary_arousal_question_txt.started')
                # update status
                momentary_arousal_question_txt.status = STARTED
                momentary_arousal_question_txt.setAutoDraw(True)
            
            # if momentary_arousal_question_txt is active this frame...
            if momentary_arousal_question_txt.status == STARTED:
                # update params
                pass
            
            # *momentary_arousal_slider* updates
            
            # if momentary_arousal_slider is starting this frame...
            if momentary_arousal_slider.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                momentary_arousal_slider.frameNStart = frameN  # exact frame index
                momentary_arousal_slider.tStart = t  # local t and not account for scr refresh
                momentary_arousal_slider.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(momentary_arousal_slider, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'momentary_arousal_slider.started')
                # update status
                momentary_arousal_slider.status = STARTED
                momentary_arousal_slider.setAutoDraw(True)
            
            # if momentary_arousal_slider is active this frame...
            if momentary_arousal_slider.status == STARTED:
                # update params
                pass
            
            # *momentary_alert_txt* updates
            
            # if momentary_alert_txt is starting this frame...
            if momentary_alert_txt.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                momentary_alert_txt.frameNStart = frameN  # exact frame index
                momentary_alert_txt.tStart = t  # local t and not account for scr refresh
                momentary_alert_txt.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(momentary_alert_txt, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'momentary_alert_txt.started')
                # update status
                momentary_alert_txt.status = STARTED
                momentary_alert_txt.setAutoDraw(True)
            
            # if momentary_alert_txt is active this frame...
            if momentary_alert_txt.status == STARTED:
                # update params
                pass
            
            # *momentary_not_alert_txt* updates
            
            # if momentary_not_alert_txt is starting this frame...
            if momentary_not_alert_txt.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                momentary_not_alert_txt.frameNStart = frameN  # exact frame index
                momentary_not_alert_txt.tStart = t  # local t and not account for scr refresh
                momentary_not_alert_txt.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(momentary_not_alert_txt, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'momentary_not_alert_txt.started')
                # update status
                momentary_not_alert_txt.status = STARTED
                momentary_not_alert_txt.setAutoDraw(True)
            
            # if momentary_not_alert_txt is active this frame...
            if momentary_not_alert_txt.status == STARTED:
                # update params
                pass
            
            # *mouse_instruct_txt_1* updates
            
            # if mouse_instruct_txt_1 is starting this frame...
            if mouse_instruct_txt_1.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                mouse_instruct_txt_1.frameNStart = frameN  # exact frame index
                mouse_instruct_txt_1.tStart = t  # local t and not account for scr refresh
                mouse_instruct_txt_1.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(mouse_instruct_txt_1, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'mouse_instruct_txt_1.started')
                # update status
                mouse_instruct_txt_1.status = STARTED
                mouse_instruct_txt_1.setAutoDraw(True)
            
            # if mouse_instruct_txt_1 is active this frame...
            if mouse_instruct_txt_1.status == STARTED:
                # update params
                pass
            
            # check for quit (typically the Esc key)
            if defaultKeyboard.getKeys(keyList=["escape"]):
                thisExp.status = FINISHED
            if thisExp.status == FINISHED or endExpNow:
                endExperiment(thisExp, win=win)
                return
            # pause experiment here if requested
            if thisExp.status == PAUSED:
                pauseExperiment(
                    thisExp=thisExp, 
                    win=win, 
                    timers=[routineTimer, globalClock], 
                    currentRoutine=momentary_arousal_rating,
                )
                # skip the frame we paused on
                continue
            
            # has a Component requested the Routine to end?
            if not continueRoutine:
                momentary_arousal_rating.forceEnded = routineForceEnded = True
            # has the Routine been forcibly ended?
            if momentary_arousal_rating.forceEnded or routineForceEnded:
                break
            # has every Component finished?
            continueRoutine = False
            for thisComponent in momentary_arousal_rating.components:
                if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                    continueRoutine = True
                    break  # at least one component has not yet finished
            
            # refresh the screen
            if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                win.flip()
        
        # --- Ending Routine "momentary_arousal_rating" ---
        for thisComponent in momentary_arousal_rating.components:
            if hasattr(thisComponent, "setAutoDraw"):
                thisComponent.setAutoDraw(False)
        # store stop times for momentary_arousal_rating
        momentary_arousal_rating.tStop = globalClock.getTime(format='float')
        momentary_arousal_rating.tStopRefresh = tThisFlipGlobal
        thisExp.addData('momentary_arousal_rating.stopped', momentary_arousal_rating.tStop)
        # Run 'End Routine' code from momentary_arousal_rating_code_B
        thisExp.addData('condition', condition)
        # store data for pre_baseline_ratings (TrialHandler)
        pre_baseline_ratings.addData('momentary_arousal_mouse.x', momentary_arousal_mouse.x)
        pre_baseline_ratings.addData('momentary_arousal_mouse.y', momentary_arousal_mouse.y)
        pre_baseline_ratings.addData('momentary_arousal_mouse.leftButton', momentary_arousal_mouse.leftButton)
        pre_baseline_ratings.addData('momentary_arousal_mouse.midButton', momentary_arousal_mouse.midButton)
        pre_baseline_ratings.addData('momentary_arousal_mouse.rightButton', momentary_arousal_mouse.rightButton)
        pre_baseline_ratings.addData('momentary_arousal_mouse.time', momentary_arousal_mouse.time)
        pre_baseline_ratings.addData('momentary_arousal_slider.response', momentary_arousal_slider.getRating())
        pre_baseline_ratings.addData('momentary_arousal_slider.rt', momentary_arousal_slider.getRT())
        # the Routine "momentary_arousal_rating" was not non-slip safe, so reset the non-slip timer
        routineTimer.reset()
        
        # --- Prepare to start Routine "momentary_valence_rating_B" ---
        # create an object to store info about Routine momentary_valence_rating_B
        momentary_valence_rating_B = data.Routine(
            name='momentary_valence_rating_B',
            components=[momentary_valence_mouse_B, momentary_valence_question_txt_B, momentary_valence_slider_B, momentary_pleasant_txt_B, momentary_unpleasant_txt_B, mouse_instruct_txt_2],
        )
        momentary_valence_rating_B.status = NOT_STARTED
        continueRoutine = True
        # update component parameters for each repeat
        # Run 'Begin Routine' code from momentary_valence_rating_code_B
        momentary_valence_mouse_B.setVisible(True)
        timer = None
        
        condition = stim_condition
        
        # determine which slider will appear first
        if rating_order == 'valence_first':
            continueRoutine = False
        # setup some python lists for storing info about the momentary_valence_mouse_B
        momentary_valence_mouse_B.x = []
        momentary_valence_mouse_B.y = []
        momentary_valence_mouse_B.leftButton = []
        momentary_valence_mouse_B.midButton = []
        momentary_valence_mouse_B.rightButton = []
        momentary_valence_mouse_B.time = []
        gotValidClick = False  # until a click is received
        momentary_valence_slider_B.reset()
        momentary_valence_slider_B.setPos((0,0))
        momentary_pleasant_txt_B.setPos((0.5, -0.05))
        momentary_unpleasant_txt_B.setPos((-0.5, -0.05))
        # store start times for momentary_valence_rating_B
        momentary_valence_rating_B.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
        momentary_valence_rating_B.tStart = globalClock.getTime(format='float')
        momentary_valence_rating_B.status = STARTED
        thisExp.addData('momentary_valence_rating_B.started', momentary_valence_rating_B.tStart)
        momentary_valence_rating_B.maxDuration = None
        # keep track of which components have finished
        momentary_valence_rating_BComponents = momentary_valence_rating_B.components
        for thisComponent in momentary_valence_rating_B.components:
            thisComponent.tStart = None
            thisComponent.tStop = None
            thisComponent.tStartRefresh = None
            thisComponent.tStopRefresh = None
            if hasattr(thisComponent, 'status'):
                thisComponent.status = NOT_STARTED
        # reset timers
        t = 0
        _timeToFirstFrame = win.getFutureFlipTime(clock="now")
        frameN = -1
        
        # --- Run Routine "momentary_valence_rating_B" ---
        thisExp.currentRoutine = momentary_valence_rating_B
        momentary_valence_rating_B.forceEnded = routineForceEnded = not continueRoutine
        while continueRoutine:
            # if trial has changed, end Routine now
            if hasattr(thisPre_baseline_rating, 'status') and thisPre_baseline_rating.status == STOPPING:
                continueRoutine = False
            # get current time
            t = routineTimer.getTime()
            tThisFlip = win.getFutureFlipTime(clock=routineTimer)
            tThisFlipGlobal = win.getFutureFlipTime(clock=None)
            frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
            # update/draw components on each frame
            # Run 'Each Frame' code from momentary_valence_rating_code_B
            if momentary_valence_slider_B.getRating() is not None:
            
                if timer is None:
                    timer = core.CountdownTimer(2)
            
                if timer.getTime() < 0:
                    continueRoutine = False
            # *momentary_valence_mouse_B* updates
            
            # if momentary_valence_mouse_B is starting this frame...
            if momentary_valence_mouse_B.status == NOT_STARTED and t >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                momentary_valence_mouse_B.frameNStart = frameN  # exact frame index
                momentary_valence_mouse_B.tStart = t  # local t and not account for scr refresh
                momentary_valence_mouse_B.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(momentary_valence_mouse_B, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.addData('momentary_valence_mouse_B.started', t)
                # update status
                momentary_valence_mouse_B.status = STARTED
                momentary_valence_mouse_B.mouseClock.reset()
                prevButtonState = momentary_valence_mouse_B.getPressed()  # if button is down already this ISN'T a new click
            if momentary_valence_mouse_B.status == STARTED:  # only update if started and not finished!
                buttons = momentary_valence_mouse_B.getPressed()
                if buttons != prevButtonState:  # button state changed?
                    prevButtonState = buttons
                    if sum(buttons) > 0:  # state changed to a new click
                        pass
                        x, y = momentary_valence_mouse_B.getPos()
                        momentary_valence_mouse_B.x.append(float(x))
                        momentary_valence_mouse_B.y.append(float(y))
                        buttons = momentary_valence_mouse_B.getPressed()
                        momentary_valence_mouse_B.leftButton.append(buttons[0])
                        momentary_valence_mouse_B.midButton.append(buttons[1])
                        momentary_valence_mouse_B.rightButton.append(buttons[2])
                        momentary_valence_mouse_B.time.append(momentary_valence_mouse_B.mouseClock.getTime())
            
            # *momentary_valence_question_txt_B* updates
            
            # if momentary_valence_question_txt_B is starting this frame...
            if momentary_valence_question_txt_B.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                momentary_valence_question_txt_B.frameNStart = frameN  # exact frame index
                momentary_valence_question_txt_B.tStart = t  # local t and not account for scr refresh
                momentary_valence_question_txt_B.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(momentary_valence_question_txt_B, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'momentary_valence_question_txt_B.started')
                # update status
                momentary_valence_question_txt_B.status = STARTED
                momentary_valence_question_txt_B.setAutoDraw(True)
            
            # if momentary_valence_question_txt_B is active this frame...
            if momentary_valence_question_txt_B.status == STARTED:
                # update params
                pass
            
            # *momentary_valence_slider_B* updates
            
            # if momentary_valence_slider_B is starting this frame...
            if momentary_valence_slider_B.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                momentary_valence_slider_B.frameNStart = frameN  # exact frame index
                momentary_valence_slider_B.tStart = t  # local t and not account for scr refresh
                momentary_valence_slider_B.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(momentary_valence_slider_B, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'momentary_valence_slider_B.started')
                # update status
                momentary_valence_slider_B.status = STARTED
                momentary_valence_slider_B.setAutoDraw(True)
            
            # if momentary_valence_slider_B is active this frame...
            if momentary_valence_slider_B.status == STARTED:
                # update params
                pass
            
            # *momentary_pleasant_txt_B* updates
            
            # if momentary_pleasant_txt_B is starting this frame...
            if momentary_pleasant_txt_B.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                momentary_pleasant_txt_B.frameNStart = frameN  # exact frame index
                momentary_pleasant_txt_B.tStart = t  # local t and not account for scr refresh
                momentary_pleasant_txt_B.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(momentary_pleasant_txt_B, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'momentary_pleasant_txt_B.started')
                # update status
                momentary_pleasant_txt_B.status = STARTED
                momentary_pleasant_txt_B.setAutoDraw(True)
            
            # if momentary_pleasant_txt_B is active this frame...
            if momentary_pleasant_txt_B.status == STARTED:
                # update params
                pass
            
            # *momentary_unpleasant_txt_B* updates
            
            # if momentary_unpleasant_txt_B is starting this frame...
            if momentary_unpleasant_txt_B.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                momentary_unpleasant_txt_B.frameNStart = frameN  # exact frame index
                momentary_unpleasant_txt_B.tStart = t  # local t and not account for scr refresh
                momentary_unpleasant_txt_B.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(momentary_unpleasant_txt_B, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'momentary_unpleasant_txt_B.started')
                # update status
                momentary_unpleasant_txt_B.status = STARTED
                momentary_unpleasant_txt_B.setAutoDraw(True)
            
            # if momentary_unpleasant_txt_B is active this frame...
            if momentary_unpleasant_txt_B.status == STARTED:
                # update params
                pass
            
            # *mouse_instruct_txt_2* updates
            
            # if mouse_instruct_txt_2 is starting this frame...
            if mouse_instruct_txt_2.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                mouse_instruct_txt_2.frameNStart = frameN  # exact frame index
                mouse_instruct_txt_2.tStart = t  # local t and not account for scr refresh
                mouse_instruct_txt_2.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(mouse_instruct_txt_2, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'mouse_instruct_txt_2.started')
                # update status
                mouse_instruct_txt_2.status = STARTED
                mouse_instruct_txt_2.setAutoDraw(True)
            
            # if mouse_instruct_txt_2 is active this frame...
            if mouse_instruct_txt_2.status == STARTED:
                # update params
                pass
            
            # check for quit (typically the Esc key)
            if defaultKeyboard.getKeys(keyList=["escape"]):
                thisExp.status = FINISHED
            if thisExp.status == FINISHED or endExpNow:
                endExperiment(thisExp, win=win)
                return
            # pause experiment here if requested
            if thisExp.status == PAUSED:
                pauseExperiment(
                    thisExp=thisExp, 
                    win=win, 
                    timers=[routineTimer, globalClock], 
                    currentRoutine=momentary_valence_rating_B,
                )
                # skip the frame we paused on
                continue
            
            # has a Component requested the Routine to end?
            if not continueRoutine:
                momentary_valence_rating_B.forceEnded = routineForceEnded = True
            # has the Routine been forcibly ended?
            if momentary_valence_rating_B.forceEnded or routineForceEnded:
                break
            # has every Component finished?
            continueRoutine = False
            for thisComponent in momentary_valence_rating_B.components:
                if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                    continueRoutine = True
                    break  # at least one component has not yet finished
            
            # refresh the screen
            if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                win.flip()
        
        # --- Ending Routine "momentary_valence_rating_B" ---
        for thisComponent in momentary_valence_rating_B.components:
            if hasattr(thisComponent, "setAutoDraw"):
                thisComponent.setAutoDraw(False)
        # store stop times for momentary_valence_rating_B
        momentary_valence_rating_B.tStop = globalClock.getTime(format='float')
        momentary_valence_rating_B.tStopRefresh = tThisFlipGlobal
        thisExp.addData('momentary_valence_rating_B.stopped', momentary_valence_rating_B.tStop)
        # Run 'End Routine' code from momentary_valence_rating_code_B
        momentary_valence_mouse_B.setVisible(False)
        
        thisExp.addData('condition', condition)
        # store data for pre_baseline_ratings (TrialHandler)
        pre_baseline_ratings.addData('momentary_valence_mouse_B.x', momentary_valence_mouse_B.x)
        pre_baseline_ratings.addData('momentary_valence_mouse_B.y', momentary_valence_mouse_B.y)
        pre_baseline_ratings.addData('momentary_valence_mouse_B.leftButton', momentary_valence_mouse_B.leftButton)
        pre_baseline_ratings.addData('momentary_valence_mouse_B.midButton', momentary_valence_mouse_B.midButton)
        pre_baseline_ratings.addData('momentary_valence_mouse_B.rightButton', momentary_valence_mouse_B.rightButton)
        pre_baseline_ratings.addData('momentary_valence_mouse_B.time', momentary_valence_mouse_B.time)
        pre_baseline_ratings.addData('momentary_valence_slider_B.response', momentary_valence_slider_B.getRating())
        pre_baseline_ratings.addData('momentary_valence_slider_B.rt', momentary_valence_slider_B.getRT())
        # the Routine "momentary_valence_rating_B" was not non-slip safe, so reset the non-slip timer
        routineTimer.reset()
        # mark thisPre_baseline_rating as finished
        if hasattr(thisPre_baseline_rating, 'status'):
            thisPre_baseline_rating.status = FINISHED
        # if awaiting a pause, pause now
        if pre_baseline_ratings.status == PAUSED:
            thisExp.status = PAUSED
            pauseExperiment(
                thisExp=thisExp, 
                win=win, 
                timers=[globalClock], 
            )
            # once done pausing, restore running status
            pre_baseline_ratings.status = STARTED
        thisExp.nextEntry()
        
    # completed 1.0 repeats of 'pre_baseline_ratings'
    pre_baseline_ratings.status = FINISHED
    
    if thisSession is not None:
        # if running in a Session with a Liaison client, send data up to now
        thisSession.sendExperimentData()
    
    # --- Prepare to start Routine "baseline_instruct" ---
    # create an object to store info about Routine baseline_instruct
    baseline_instruct = data.Routine(
        name='baseline_instruct',
        components=[baseline_instruct_txt],
    )
    baseline_instruct.status = NOT_STARTED
    continueRoutine = True
    # update component parameters for each repeat
    # store start times for baseline_instruct
    baseline_instruct.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
    baseline_instruct.tStart = globalClock.getTime(format='float')
    baseline_instruct.status = STARTED
    thisExp.addData('baseline_instruct.started', baseline_instruct.tStart)
    baseline_instruct.maxDuration = None
    # keep track of which components have finished
    baseline_instructComponents = baseline_instruct.components
    for thisComponent in baseline_instruct.components:
        thisComponent.tStart = None
        thisComponent.tStop = None
        thisComponent.tStartRefresh = None
        thisComponent.tStopRefresh = None
        if hasattr(thisComponent, 'status'):
            thisComponent.status = NOT_STARTED
    # reset timers
    t = 0
    _timeToFirstFrame = win.getFutureFlipTime(clock="now")
    frameN = -1
    
    # --- Run Routine "baseline_instruct" ---
    thisExp.currentRoutine = baseline_instruct
    baseline_instruct.forceEnded = routineForceEnded = not continueRoutine
    while continueRoutine and routineTimer.getTime() < 8.0:
        # get current time
        t = routineTimer.getTime()
        tThisFlip = win.getFutureFlipTime(clock=routineTimer)
        tThisFlipGlobal = win.getFutureFlipTime(clock=None)
        frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
        # update/draw components on each frame
        
        # *baseline_instruct_txt* updates
        
        # if baseline_instruct_txt is starting this frame...
        if baseline_instruct_txt.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
            # keep track of start time/frame for later
            baseline_instruct_txt.frameNStart = frameN  # exact frame index
            baseline_instruct_txt.tStart = t  # local t and not account for scr refresh
            baseline_instruct_txt.tStartRefresh = tThisFlipGlobal  # on global time
            win.timeOnFlip(baseline_instruct_txt, 'tStartRefresh')  # time at next scr refresh
            # add timestamp to datafile
            thisExp.timestampOnFlip(win, 'baseline_instruct_txt.started')
            # update status
            baseline_instruct_txt.status = STARTED
            baseline_instruct_txt.setAutoDraw(True)
        
        # if baseline_instruct_txt is active this frame...
        if baseline_instruct_txt.status == STARTED:
            # update params
            pass
        
        # if baseline_instruct_txt is stopping this frame...
        if baseline_instruct_txt.status == STARTED:
            # is it time to stop? (based on global clock, using actual start)
            if tThisFlipGlobal > baseline_instruct_txt.tStartRefresh + 8-frameTolerance:
                # keep track of stop time/frame for later
                baseline_instruct_txt.tStop = t  # not accounting for scr refresh
                baseline_instruct_txt.tStopRefresh = tThisFlipGlobal  # on global time
                baseline_instruct_txt.frameNStop = frameN  # exact frame index
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'baseline_instruct_txt.stopped')
                # update status
                baseline_instruct_txt.status = FINISHED
                baseline_instruct_txt.setAutoDraw(False)
        
        # check for quit (typically the Esc key)
        if defaultKeyboard.getKeys(keyList=["escape"]):
            thisExp.status = FINISHED
        if thisExp.status == FINISHED or endExpNow:
            endExperiment(thisExp, win=win)
            return
        # pause experiment here if requested
        if thisExp.status == PAUSED:
            pauseExperiment(
                thisExp=thisExp, 
                win=win, 
                timers=[routineTimer, globalClock], 
                currentRoutine=baseline_instruct,
            )
            # skip the frame we paused on
            continue
        
        # has a Component requested the Routine to end?
        if not continueRoutine:
            baseline_instruct.forceEnded = routineForceEnded = True
        # has the Routine been forcibly ended?
        if baseline_instruct.forceEnded or routineForceEnded:
            break
        # has every Component finished?
        continueRoutine = False
        for thisComponent in baseline_instruct.components:
            if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                continueRoutine = True
                break  # at least one component has not yet finished
        
        # refresh the screen
        if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
            win.flip()
    
    # --- Ending Routine "baseline_instruct" ---
    for thisComponent in baseline_instruct.components:
        if hasattr(thisComponent, "setAutoDraw"):
            thisComponent.setAutoDraw(False)
    # store stop times for baseline_instruct
    baseline_instruct.tStop = globalClock.getTime(format='float')
    baseline_instruct.tStopRefresh = tThisFlipGlobal
    thisExp.addData('baseline_instruct.stopped', baseline_instruct.tStop)
    # using non-slip timing so subtract the expected duration of this Routine (unless ended on request)
    if baseline_instruct.maxDurationReached:
        routineTimer.addTime(-baseline_instruct.maxDuration)
    elif baseline_instruct.forceEnded:
        routineTimer.reset()
    else:
        routineTimer.addTime(-8.000000)
    thisExp.nextEntry()
    
    # --- Prepare to start Routine "baseline" ---
    # create an object to store info about Routine baseline
    baseline = data.Routine(
        name='baseline',
        components=[fixation_baseline],
    )
    baseline.status = NOT_STARTED
    continueRoutine = True
    # update component parameters for each repeat
    # Run 'Begin Routine' code from baseline_trigger_code
    #----
    # Log time for camera
    # ---
    thisExp.addData('onset_wall', time.time())
    thisExp.addData('time_since_recording_start', time.time() - experiment_start_wall)
    
    stimulus_trigger_sent = False
    stimulus_trigger_cleared = False
    # store start times for baseline
    baseline.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
    baseline.tStart = globalClock.getTime(format='float')
    baseline.status = STARTED
    thisExp.addData('baseline.started', baseline.tStart)
    baseline.maxDuration = None
    # keep track of which components have finished
    baselineComponents = baseline.components
    for thisComponent in baseline.components:
        thisComponent.tStart = None
        thisComponent.tStop = None
        thisComponent.tStartRefresh = None
        thisComponent.tStopRefresh = None
        if hasattr(thisComponent, 'status'):
            thisComponent.status = NOT_STARTED
    # reset timers
    t = 0
    _timeToFirstFrame = win.getFutureFlipTime(clock="now")
    frameN = -1
    
    # --- Run Routine "baseline" ---
    thisExp.currentRoutine = baseline
    baseline.forceEnded = routineForceEnded = not continueRoutine
    while continueRoutine:
        # get current time
        t = routineTimer.getTime()
        tThisFlip = win.getFutureFlipTime(clock=routineTimer)
        tThisFlipGlobal = win.getFutureFlipTime(clock=None)
        frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
        # update/draw components on each frame
        
        # *fixation_baseline* updates
        
        # if fixation_baseline is starting this frame...
        if fixation_baseline.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
            # keep track of start time/frame for later
            fixation_baseline.frameNStart = frameN  # exact frame index
            fixation_baseline.tStart = t  # local t and not account for scr refresh
            fixation_baseline.tStartRefresh = tThisFlipGlobal  # on global time
            win.timeOnFlip(fixation_baseline, 'tStartRefresh')  # time at next scr refresh
            # add timestamp to datafile
            thisExp.timestampOnFlip(win, 'fixation_baseline.started')
            # update status
            fixation_baseline.status = STARTED
            fixation_baseline.setAutoDraw(True)
        
        # if fixation_baseline is active this frame...
        if fixation_baseline.status == STARTED:
            # update params
            pass
        
        # if fixation_baseline is stopping this frame...
        if fixation_baseline.status == STARTED:
            # is it time to stop? (based on global clock, using actual start)
            if tThisFlipGlobal > fixation_baseline.tStartRefresh + recovery_duration-frameTolerance:
                # keep track of stop time/frame for later
                fixation_baseline.tStop = t  # not accounting for scr refresh
                fixation_baseline.tStopRefresh = tThisFlipGlobal  # on global time
                fixation_baseline.frameNStop = frameN  # exact frame index
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'fixation_baseline.stopped')
                # update status
                fixation_baseline.status = FINISHED
                fixation_baseline.setAutoDraw(False)
        # Run 'Each Frame' code from baseline_trigger_code
        # --- Stimulus ON trigger ---
        if fixation_baseline.status == STARTED and not stimulus_trigger_sent:
            win.callOnFlip(ser.write, str.encode(baseline_trigger))
            stimulus_trigger_sent = True
        
        # --- Stimulus OFF trigger ---
        if fixation_baseline.status == FINISHED and not stimulus_trigger_cleared:
            win.callOnFlip(ser.write, str.encode('00'))
            stimulus_trigger_cleared = True
        
        # check for quit (typically the Esc key)
        if defaultKeyboard.getKeys(keyList=["escape"]):
            thisExp.status = FINISHED
        if thisExp.status == FINISHED or endExpNow:
            endExperiment(thisExp, win=win)
            return
        # pause experiment here if requested
        if thisExp.status == PAUSED:
            pauseExperiment(
                thisExp=thisExp, 
                win=win, 
                timers=[routineTimer, globalClock], 
                currentRoutine=baseline,
            )
            # skip the frame we paused on
            continue
        
        # has a Component requested the Routine to end?
        if not continueRoutine:
            baseline.forceEnded = routineForceEnded = True
        # has the Routine been forcibly ended?
        if baseline.forceEnded or routineForceEnded:
            break
        # has every Component finished?
        continueRoutine = False
        for thisComponent in baseline.components:
            if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                continueRoutine = True
                break  # at least one component has not yet finished
        
        # refresh the screen
        if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
            win.flip()
    
    # --- Ending Routine "baseline" ---
    for thisComponent in baseline.components:
        if hasattr(thisComponent, "setAutoDraw"):
            thisComponent.setAutoDraw(False)
    # store stop times for baseline
    baseline.tStop = globalClock.getTime(format='float')
    baseline.tStopRefresh = tThisFlipGlobal
    thisExp.addData('baseline.stopped', baseline.tStop)
    # Run 'End Routine' code from baseline_trigger_code
    ser.write ('RR'.encode('utf-8'))
    
    # set variable to record valence and arousal ratings
    condition = 'post_baseline'
    thisExp.nextEntry()
    # the Routine "baseline" was not non-slip safe, so reset the non-slip timer
    routineTimer.reset()
    
    # set up handler to look after randomisation of conditions etc
    post_baseline_ratings = data.TrialHandler2(
        name='post_baseline_ratings',
        nReps=1.0, 
        method='random', 
        extraInfo=expInfo, 
        originPath=-1, 
        trialList=[None], 
        seed=None, 
        isTrials=True, 
    )
    thisExp.addLoop(post_baseline_ratings)  # add the loop to the experiment
    thisPost_baseline_rating = post_baseline_ratings.trialList[0]  # so we can initialise stimuli with some values
    # abbreviate parameter names if possible (e.g. rgb = thisPost_baseline_rating.rgb)
    if thisPost_baseline_rating != None:
        for paramName in thisPost_baseline_rating:
            globals()[paramName] = thisPost_baseline_rating[paramName]
    if thisSession is not None:
        # if running in a Session with a Liaison client, send data up to now
        thisSession.sendExperimentData()
    
    for thisPost_baseline_rating in post_baseline_ratings:
        post_baseline_ratings.status = STARTED
        if hasattr(thisPost_baseline_rating, 'status'):
            thisPost_baseline_rating.status = STARTED
        currentLoop = post_baseline_ratings
        thisExp.timestampOnFlip(win, 'thisRow.t', format=globalClock.format)
        if thisSession is not None:
            # if running in a Session with a Liaison client, send data up to now
            thisSession.sendExperimentData()
        # abbreviate parameter names if possible (e.g. rgb = thisPost_baseline_rating.rgb)
        if thisPost_baseline_rating != None:
            for paramName in thisPost_baseline_rating:
                globals()[paramName] = thisPost_baseline_rating[paramName]
        
        # --- Prepare to start Routine "momentary_valence_rating_A" ---
        # create an object to store info about Routine momentary_valence_rating_A
        momentary_valence_rating_A = data.Routine(
            name='momentary_valence_rating_A',
            components=[momentary_valence_mouse_A, momentary_valence_question_txt_A, momentary_valence_slider_A, momentary_pleasant_txt_A, momentary_unpleasant_txt_A, mouse_instuct_txt],
        )
        momentary_valence_rating_A.status = NOT_STARTED
        continueRoutine = True
        # update component parameters for each repeat
        # Run 'Begin Routine' code from momentary_valence_rating_code_A
        momentary_valence_mouse_A.setVisible(True)
        timer = None
        
        condition = stim_condition
        
        # determine which slider will appear first
        rating_pair_count += 1
        if rating_pair_count % 2 == 1:
            rating_order = rating_start
        else:
            rating_order = 'arousal_first' if rating_start == 'valence_first' else 'valence_first'
        
        if rating_order == 'arousal_first':
            continueRoutine = False
        # setup some python lists for storing info about the momentary_valence_mouse_A
        momentary_valence_mouse_A.x = []
        momentary_valence_mouse_A.y = []
        momentary_valence_mouse_A.leftButton = []
        momentary_valence_mouse_A.midButton = []
        momentary_valence_mouse_A.rightButton = []
        momentary_valence_mouse_A.time = []
        gotValidClick = False  # until a click is received
        momentary_valence_slider_A.reset()
        momentary_valence_slider_A.setPos((0,0))
        momentary_pleasant_txt_A.setPos((0.5, -0.05))
        momentary_unpleasant_txt_A.setPos((-0.5, -0.05))
        # store start times for momentary_valence_rating_A
        momentary_valence_rating_A.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
        momentary_valence_rating_A.tStart = globalClock.getTime(format='float')
        momentary_valence_rating_A.status = STARTED
        thisExp.addData('momentary_valence_rating_A.started', momentary_valence_rating_A.tStart)
        momentary_valence_rating_A.maxDuration = None
        # keep track of which components have finished
        momentary_valence_rating_AComponents = momentary_valence_rating_A.components
        for thisComponent in momentary_valence_rating_A.components:
            thisComponent.tStart = None
            thisComponent.tStop = None
            thisComponent.tStartRefresh = None
            thisComponent.tStopRefresh = None
            if hasattr(thisComponent, 'status'):
                thisComponent.status = NOT_STARTED
        # reset timers
        t = 0
        _timeToFirstFrame = win.getFutureFlipTime(clock="now")
        frameN = -1
        
        # --- Run Routine "momentary_valence_rating_A" ---
        thisExp.currentRoutine = momentary_valence_rating_A
        momentary_valence_rating_A.forceEnded = routineForceEnded = not continueRoutine
        while continueRoutine:
            # if trial has changed, end Routine now
            if hasattr(thisPost_baseline_rating, 'status') and thisPost_baseline_rating.status == STOPPING:
                continueRoutine = False
            # get current time
            t = routineTimer.getTime()
            tThisFlip = win.getFutureFlipTime(clock=routineTimer)
            tThisFlipGlobal = win.getFutureFlipTime(clock=None)
            frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
            # update/draw components on each frame
            # Run 'Each Frame' code from momentary_valence_rating_code_A
            if momentary_valence_slider_A.getRating() is not None:
            
                if timer is None:
                    timer = core.CountdownTimer(2)
            
                if timer.getTime() < 0:
                    continueRoutine = False
            # *momentary_valence_mouse_A* updates
            
            # if momentary_valence_mouse_A is starting this frame...
            if momentary_valence_mouse_A.status == NOT_STARTED and t >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                momentary_valence_mouse_A.frameNStart = frameN  # exact frame index
                momentary_valence_mouse_A.tStart = t  # local t and not account for scr refresh
                momentary_valence_mouse_A.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(momentary_valence_mouse_A, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.addData('momentary_valence_mouse_A.started', t)
                # update status
                momentary_valence_mouse_A.status = STARTED
                momentary_valence_mouse_A.mouseClock.reset()
                prevButtonState = momentary_valence_mouse_A.getPressed()  # if button is down already this ISN'T a new click
            if momentary_valence_mouse_A.status == STARTED:  # only update if started and not finished!
                buttons = momentary_valence_mouse_A.getPressed()
                if buttons != prevButtonState:  # button state changed?
                    prevButtonState = buttons
                    if sum(buttons) > 0:  # state changed to a new click
                        pass
                        x, y = momentary_valence_mouse_A.getPos()
                        momentary_valence_mouse_A.x.append(float(x))
                        momentary_valence_mouse_A.y.append(float(y))
                        buttons = momentary_valence_mouse_A.getPressed()
                        momentary_valence_mouse_A.leftButton.append(buttons[0])
                        momentary_valence_mouse_A.midButton.append(buttons[1])
                        momentary_valence_mouse_A.rightButton.append(buttons[2])
                        momentary_valence_mouse_A.time.append(momentary_valence_mouse_A.mouseClock.getTime())
            
            # *momentary_valence_question_txt_A* updates
            
            # if momentary_valence_question_txt_A is starting this frame...
            if momentary_valence_question_txt_A.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                momentary_valence_question_txt_A.frameNStart = frameN  # exact frame index
                momentary_valence_question_txt_A.tStart = t  # local t and not account for scr refresh
                momentary_valence_question_txt_A.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(momentary_valence_question_txt_A, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'momentary_valence_question_txt_A.started')
                # update status
                momentary_valence_question_txt_A.status = STARTED
                momentary_valence_question_txt_A.setAutoDraw(True)
            
            # if momentary_valence_question_txt_A is active this frame...
            if momentary_valence_question_txt_A.status == STARTED:
                # update params
                pass
            
            # *momentary_valence_slider_A* updates
            
            # if momentary_valence_slider_A is starting this frame...
            if momentary_valence_slider_A.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                momentary_valence_slider_A.frameNStart = frameN  # exact frame index
                momentary_valence_slider_A.tStart = t  # local t and not account for scr refresh
                momentary_valence_slider_A.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(momentary_valence_slider_A, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'momentary_valence_slider_A.started')
                # update status
                momentary_valence_slider_A.status = STARTED
                momentary_valence_slider_A.setAutoDraw(True)
            
            # if momentary_valence_slider_A is active this frame...
            if momentary_valence_slider_A.status == STARTED:
                # update params
                pass
            
            # *momentary_pleasant_txt_A* updates
            
            # if momentary_pleasant_txt_A is starting this frame...
            if momentary_pleasant_txt_A.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                momentary_pleasant_txt_A.frameNStart = frameN  # exact frame index
                momentary_pleasant_txt_A.tStart = t  # local t and not account for scr refresh
                momentary_pleasant_txt_A.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(momentary_pleasant_txt_A, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'momentary_pleasant_txt_A.started')
                # update status
                momentary_pleasant_txt_A.status = STARTED
                momentary_pleasant_txt_A.setAutoDraw(True)
            
            # if momentary_pleasant_txt_A is active this frame...
            if momentary_pleasant_txt_A.status == STARTED:
                # update params
                pass
            
            # *momentary_unpleasant_txt_A* updates
            
            # if momentary_unpleasant_txt_A is starting this frame...
            if momentary_unpleasant_txt_A.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                momentary_unpleasant_txt_A.frameNStart = frameN  # exact frame index
                momentary_unpleasant_txt_A.tStart = t  # local t and not account for scr refresh
                momentary_unpleasant_txt_A.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(momentary_unpleasant_txt_A, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'momentary_unpleasant_txt_A.started')
                # update status
                momentary_unpleasant_txt_A.status = STARTED
                momentary_unpleasant_txt_A.setAutoDraw(True)
            
            # if momentary_unpleasant_txt_A is active this frame...
            if momentary_unpleasant_txt_A.status == STARTED:
                # update params
                pass
            
            # *mouse_instuct_txt* updates
            
            # if mouse_instuct_txt is starting this frame...
            if mouse_instuct_txt.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                mouse_instuct_txt.frameNStart = frameN  # exact frame index
                mouse_instuct_txt.tStart = t  # local t and not account for scr refresh
                mouse_instuct_txt.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(mouse_instuct_txt, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'mouse_instuct_txt.started')
                # update status
                mouse_instuct_txt.status = STARTED
                mouse_instuct_txt.setAutoDraw(True)
            
            # if mouse_instuct_txt is active this frame...
            if mouse_instuct_txt.status == STARTED:
                # update params
                pass
            
            # check for quit (typically the Esc key)
            if defaultKeyboard.getKeys(keyList=["escape"]):
                thisExp.status = FINISHED
            if thisExp.status == FINISHED or endExpNow:
                endExperiment(thisExp, win=win)
                return
            # pause experiment here if requested
            if thisExp.status == PAUSED:
                pauseExperiment(
                    thisExp=thisExp, 
                    win=win, 
                    timers=[routineTimer, globalClock], 
                    currentRoutine=momentary_valence_rating_A,
                )
                # skip the frame we paused on
                continue
            
            # has a Component requested the Routine to end?
            if not continueRoutine:
                momentary_valence_rating_A.forceEnded = routineForceEnded = True
            # has the Routine been forcibly ended?
            if momentary_valence_rating_A.forceEnded or routineForceEnded:
                break
            # has every Component finished?
            continueRoutine = False
            for thisComponent in momentary_valence_rating_A.components:
                if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                    continueRoutine = True
                    break  # at least one component has not yet finished
            
            # refresh the screen
            if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                win.flip()
        
        # --- Ending Routine "momentary_valence_rating_A" ---
        for thisComponent in momentary_valence_rating_A.components:
            if hasattr(thisComponent, "setAutoDraw"):
                thisComponent.setAutoDraw(False)
        # store stop times for momentary_valence_rating_A
        momentary_valence_rating_A.tStop = globalClock.getTime(format='float')
        momentary_valence_rating_A.tStopRefresh = tThisFlipGlobal
        thisExp.addData('momentary_valence_rating_A.stopped', momentary_valence_rating_A.tStop)
        # Run 'End Routine' code from momentary_valence_rating_code_A
        momentary_valence_mouse_A.setVisible(False)
        
        thisExp.addData('condition', condition)
        # store data for post_baseline_ratings (TrialHandler)
        post_baseline_ratings.addData('momentary_valence_mouse_A.x', momentary_valence_mouse_A.x)
        post_baseline_ratings.addData('momentary_valence_mouse_A.y', momentary_valence_mouse_A.y)
        post_baseline_ratings.addData('momentary_valence_mouse_A.leftButton', momentary_valence_mouse_A.leftButton)
        post_baseline_ratings.addData('momentary_valence_mouse_A.midButton', momentary_valence_mouse_A.midButton)
        post_baseline_ratings.addData('momentary_valence_mouse_A.rightButton', momentary_valence_mouse_A.rightButton)
        post_baseline_ratings.addData('momentary_valence_mouse_A.time', momentary_valence_mouse_A.time)
        post_baseline_ratings.addData('momentary_valence_slider_A.response', momentary_valence_slider_A.getRating())
        post_baseline_ratings.addData('momentary_valence_slider_A.rt', momentary_valence_slider_A.getRT())
        # the Routine "momentary_valence_rating_A" was not non-slip safe, so reset the non-slip timer
        routineTimer.reset()
        
        # --- Prepare to start Routine "momentary_arousal_rating" ---
        # create an object to store info about Routine momentary_arousal_rating
        momentary_arousal_rating = data.Routine(
            name='momentary_arousal_rating',
            components=[momentary_arousal_mouse, momentary_arousal_question_txt, momentary_arousal_slider, momentary_alert_txt, momentary_not_alert_txt, mouse_instruct_txt_1],
        )
        momentary_arousal_rating.status = NOT_STARTED
        continueRoutine = True
        # update component parameters for each repeat
        # Run 'Begin Routine' code from momentary_arousal_rating_code_B
        momentary_arousal_mouse.setVisible(True)
        timer = None
        
        condition = stim_condition
        # setup some python lists for storing info about the momentary_arousal_mouse
        momentary_arousal_mouse.x = []
        momentary_arousal_mouse.y = []
        momentary_arousal_mouse.leftButton = []
        momentary_arousal_mouse.midButton = []
        momentary_arousal_mouse.rightButton = []
        momentary_arousal_mouse.time = []
        gotValidClick = False  # until a click is received
        momentary_arousal_slider.reset()
        momentary_arousal_slider.setPos((0,0))
        momentary_alert_txt.setPos((0.5, -0.05))
        momentary_not_alert_txt.setPos((-0.5, -0.05))
        # store start times for momentary_arousal_rating
        momentary_arousal_rating.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
        momentary_arousal_rating.tStart = globalClock.getTime(format='float')
        momentary_arousal_rating.status = STARTED
        thisExp.addData('momentary_arousal_rating.started', momentary_arousal_rating.tStart)
        momentary_arousal_rating.maxDuration = None
        # keep track of which components have finished
        momentary_arousal_ratingComponents = momentary_arousal_rating.components
        for thisComponent in momentary_arousal_rating.components:
            thisComponent.tStart = None
            thisComponent.tStop = None
            thisComponent.tStartRefresh = None
            thisComponent.tStopRefresh = None
            if hasattr(thisComponent, 'status'):
                thisComponent.status = NOT_STARTED
        # reset timers
        t = 0
        _timeToFirstFrame = win.getFutureFlipTime(clock="now")
        frameN = -1
        
        # --- Run Routine "momentary_arousal_rating" ---
        thisExp.currentRoutine = momentary_arousal_rating
        momentary_arousal_rating.forceEnded = routineForceEnded = not continueRoutine
        while continueRoutine:
            # if trial has changed, end Routine now
            if hasattr(thisPost_baseline_rating, 'status') and thisPost_baseline_rating.status == STOPPING:
                continueRoutine = False
            # get current time
            t = routineTimer.getTime()
            tThisFlip = win.getFutureFlipTime(clock=routineTimer)
            tThisFlipGlobal = win.getFutureFlipTime(clock=None)
            frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
            # update/draw components on each frame
            # Run 'Each Frame' code from momentary_arousal_rating_code_B
            if momentary_arousal_slider.getRating() is not None:
            
                if timer is None:
                    timer = core.CountdownTimer(2)
            
                if timer.getTime() < 0:
                    continueRoutine = False
            # *momentary_arousal_mouse* updates
            
            # if momentary_arousal_mouse is starting this frame...
            if momentary_arousal_mouse.status == NOT_STARTED and t >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                momentary_arousal_mouse.frameNStart = frameN  # exact frame index
                momentary_arousal_mouse.tStart = t  # local t and not account for scr refresh
                momentary_arousal_mouse.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(momentary_arousal_mouse, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.addData('momentary_arousal_mouse.started', t)
                # update status
                momentary_arousal_mouse.status = STARTED
                momentary_arousal_mouse.mouseClock.reset()
                prevButtonState = momentary_arousal_mouse.getPressed()  # if button is down already this ISN'T a new click
            if momentary_arousal_mouse.status == STARTED:  # only update if started and not finished!
                buttons = momentary_arousal_mouse.getPressed()
                if buttons != prevButtonState:  # button state changed?
                    prevButtonState = buttons
                    if sum(buttons) > 0:  # state changed to a new click
                        pass
                        x, y = momentary_arousal_mouse.getPos()
                        momentary_arousal_mouse.x.append(float(x))
                        momentary_arousal_mouse.y.append(float(y))
                        buttons = momentary_arousal_mouse.getPressed()
                        momentary_arousal_mouse.leftButton.append(buttons[0])
                        momentary_arousal_mouse.midButton.append(buttons[1])
                        momentary_arousal_mouse.rightButton.append(buttons[2])
                        momentary_arousal_mouse.time.append(momentary_arousal_mouse.mouseClock.getTime())
            
            # *momentary_arousal_question_txt* updates
            
            # if momentary_arousal_question_txt is starting this frame...
            if momentary_arousal_question_txt.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                momentary_arousal_question_txt.frameNStart = frameN  # exact frame index
                momentary_arousal_question_txt.tStart = t  # local t and not account for scr refresh
                momentary_arousal_question_txt.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(momentary_arousal_question_txt, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'momentary_arousal_question_txt.started')
                # update status
                momentary_arousal_question_txt.status = STARTED
                momentary_arousal_question_txt.setAutoDraw(True)
            
            # if momentary_arousal_question_txt is active this frame...
            if momentary_arousal_question_txt.status == STARTED:
                # update params
                pass
            
            # *momentary_arousal_slider* updates
            
            # if momentary_arousal_slider is starting this frame...
            if momentary_arousal_slider.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                momentary_arousal_slider.frameNStart = frameN  # exact frame index
                momentary_arousal_slider.tStart = t  # local t and not account for scr refresh
                momentary_arousal_slider.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(momentary_arousal_slider, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'momentary_arousal_slider.started')
                # update status
                momentary_arousal_slider.status = STARTED
                momentary_arousal_slider.setAutoDraw(True)
            
            # if momentary_arousal_slider is active this frame...
            if momentary_arousal_slider.status == STARTED:
                # update params
                pass
            
            # *momentary_alert_txt* updates
            
            # if momentary_alert_txt is starting this frame...
            if momentary_alert_txt.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                momentary_alert_txt.frameNStart = frameN  # exact frame index
                momentary_alert_txt.tStart = t  # local t and not account for scr refresh
                momentary_alert_txt.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(momentary_alert_txt, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'momentary_alert_txt.started')
                # update status
                momentary_alert_txt.status = STARTED
                momentary_alert_txt.setAutoDraw(True)
            
            # if momentary_alert_txt is active this frame...
            if momentary_alert_txt.status == STARTED:
                # update params
                pass
            
            # *momentary_not_alert_txt* updates
            
            # if momentary_not_alert_txt is starting this frame...
            if momentary_not_alert_txt.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                momentary_not_alert_txt.frameNStart = frameN  # exact frame index
                momentary_not_alert_txt.tStart = t  # local t and not account for scr refresh
                momentary_not_alert_txt.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(momentary_not_alert_txt, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'momentary_not_alert_txt.started')
                # update status
                momentary_not_alert_txt.status = STARTED
                momentary_not_alert_txt.setAutoDraw(True)
            
            # if momentary_not_alert_txt is active this frame...
            if momentary_not_alert_txt.status == STARTED:
                # update params
                pass
            
            # *mouse_instruct_txt_1* updates
            
            # if mouse_instruct_txt_1 is starting this frame...
            if mouse_instruct_txt_1.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                mouse_instruct_txt_1.frameNStart = frameN  # exact frame index
                mouse_instruct_txt_1.tStart = t  # local t and not account for scr refresh
                mouse_instruct_txt_1.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(mouse_instruct_txt_1, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'mouse_instruct_txt_1.started')
                # update status
                mouse_instruct_txt_1.status = STARTED
                mouse_instruct_txt_1.setAutoDraw(True)
            
            # if mouse_instruct_txt_1 is active this frame...
            if mouse_instruct_txt_1.status == STARTED:
                # update params
                pass
            
            # check for quit (typically the Esc key)
            if defaultKeyboard.getKeys(keyList=["escape"]):
                thisExp.status = FINISHED
            if thisExp.status == FINISHED or endExpNow:
                endExperiment(thisExp, win=win)
                return
            # pause experiment here if requested
            if thisExp.status == PAUSED:
                pauseExperiment(
                    thisExp=thisExp, 
                    win=win, 
                    timers=[routineTimer, globalClock], 
                    currentRoutine=momentary_arousal_rating,
                )
                # skip the frame we paused on
                continue
            
            # has a Component requested the Routine to end?
            if not continueRoutine:
                momentary_arousal_rating.forceEnded = routineForceEnded = True
            # has the Routine been forcibly ended?
            if momentary_arousal_rating.forceEnded or routineForceEnded:
                break
            # has every Component finished?
            continueRoutine = False
            for thisComponent in momentary_arousal_rating.components:
                if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                    continueRoutine = True
                    break  # at least one component has not yet finished
            
            # refresh the screen
            if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                win.flip()
        
        # --- Ending Routine "momentary_arousal_rating" ---
        for thisComponent in momentary_arousal_rating.components:
            if hasattr(thisComponent, "setAutoDraw"):
                thisComponent.setAutoDraw(False)
        # store stop times for momentary_arousal_rating
        momentary_arousal_rating.tStop = globalClock.getTime(format='float')
        momentary_arousal_rating.tStopRefresh = tThisFlipGlobal
        thisExp.addData('momentary_arousal_rating.stopped', momentary_arousal_rating.tStop)
        # Run 'End Routine' code from momentary_arousal_rating_code_B
        thisExp.addData('condition', condition)
        # store data for post_baseline_ratings (TrialHandler)
        post_baseline_ratings.addData('momentary_arousal_mouse.x', momentary_arousal_mouse.x)
        post_baseline_ratings.addData('momentary_arousal_mouse.y', momentary_arousal_mouse.y)
        post_baseline_ratings.addData('momentary_arousal_mouse.leftButton', momentary_arousal_mouse.leftButton)
        post_baseline_ratings.addData('momentary_arousal_mouse.midButton', momentary_arousal_mouse.midButton)
        post_baseline_ratings.addData('momentary_arousal_mouse.rightButton', momentary_arousal_mouse.rightButton)
        post_baseline_ratings.addData('momentary_arousal_mouse.time', momentary_arousal_mouse.time)
        post_baseline_ratings.addData('momentary_arousal_slider.response', momentary_arousal_slider.getRating())
        post_baseline_ratings.addData('momentary_arousal_slider.rt', momentary_arousal_slider.getRT())
        # the Routine "momentary_arousal_rating" was not non-slip safe, so reset the non-slip timer
        routineTimer.reset()
        
        # --- Prepare to start Routine "momentary_valence_rating_B" ---
        # create an object to store info about Routine momentary_valence_rating_B
        momentary_valence_rating_B = data.Routine(
            name='momentary_valence_rating_B',
            components=[momentary_valence_mouse_B, momentary_valence_question_txt_B, momentary_valence_slider_B, momentary_pleasant_txt_B, momentary_unpleasant_txt_B, mouse_instruct_txt_2],
        )
        momentary_valence_rating_B.status = NOT_STARTED
        continueRoutine = True
        # update component parameters for each repeat
        # Run 'Begin Routine' code from momentary_valence_rating_code_B
        momentary_valence_mouse_B.setVisible(True)
        timer = None
        
        condition = stim_condition
        
        # determine which slider will appear first
        if rating_order == 'valence_first':
            continueRoutine = False
        # setup some python lists for storing info about the momentary_valence_mouse_B
        momentary_valence_mouse_B.x = []
        momentary_valence_mouse_B.y = []
        momentary_valence_mouse_B.leftButton = []
        momentary_valence_mouse_B.midButton = []
        momentary_valence_mouse_B.rightButton = []
        momentary_valence_mouse_B.time = []
        gotValidClick = False  # until a click is received
        momentary_valence_slider_B.reset()
        momentary_valence_slider_B.setPos((0,0))
        momentary_pleasant_txt_B.setPos((0.5, -0.05))
        momentary_unpleasant_txt_B.setPos((-0.5, -0.05))
        # store start times for momentary_valence_rating_B
        momentary_valence_rating_B.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
        momentary_valence_rating_B.tStart = globalClock.getTime(format='float')
        momentary_valence_rating_B.status = STARTED
        thisExp.addData('momentary_valence_rating_B.started', momentary_valence_rating_B.tStart)
        momentary_valence_rating_B.maxDuration = None
        # keep track of which components have finished
        momentary_valence_rating_BComponents = momentary_valence_rating_B.components
        for thisComponent in momentary_valence_rating_B.components:
            thisComponent.tStart = None
            thisComponent.tStop = None
            thisComponent.tStartRefresh = None
            thisComponent.tStopRefresh = None
            if hasattr(thisComponent, 'status'):
                thisComponent.status = NOT_STARTED
        # reset timers
        t = 0
        _timeToFirstFrame = win.getFutureFlipTime(clock="now")
        frameN = -1
        
        # --- Run Routine "momentary_valence_rating_B" ---
        thisExp.currentRoutine = momentary_valence_rating_B
        momentary_valence_rating_B.forceEnded = routineForceEnded = not continueRoutine
        while continueRoutine:
            # if trial has changed, end Routine now
            if hasattr(thisPost_baseline_rating, 'status') and thisPost_baseline_rating.status == STOPPING:
                continueRoutine = False
            # get current time
            t = routineTimer.getTime()
            tThisFlip = win.getFutureFlipTime(clock=routineTimer)
            tThisFlipGlobal = win.getFutureFlipTime(clock=None)
            frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
            # update/draw components on each frame
            # Run 'Each Frame' code from momentary_valence_rating_code_B
            if momentary_valence_slider_B.getRating() is not None:
            
                if timer is None:
                    timer = core.CountdownTimer(2)
            
                if timer.getTime() < 0:
                    continueRoutine = False
            # *momentary_valence_mouse_B* updates
            
            # if momentary_valence_mouse_B is starting this frame...
            if momentary_valence_mouse_B.status == NOT_STARTED and t >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                momentary_valence_mouse_B.frameNStart = frameN  # exact frame index
                momentary_valence_mouse_B.tStart = t  # local t and not account for scr refresh
                momentary_valence_mouse_B.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(momentary_valence_mouse_B, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.addData('momentary_valence_mouse_B.started', t)
                # update status
                momentary_valence_mouse_B.status = STARTED
                momentary_valence_mouse_B.mouseClock.reset()
                prevButtonState = momentary_valence_mouse_B.getPressed()  # if button is down already this ISN'T a new click
            if momentary_valence_mouse_B.status == STARTED:  # only update if started and not finished!
                buttons = momentary_valence_mouse_B.getPressed()
                if buttons != prevButtonState:  # button state changed?
                    prevButtonState = buttons
                    if sum(buttons) > 0:  # state changed to a new click
                        pass
                        x, y = momentary_valence_mouse_B.getPos()
                        momentary_valence_mouse_B.x.append(float(x))
                        momentary_valence_mouse_B.y.append(float(y))
                        buttons = momentary_valence_mouse_B.getPressed()
                        momentary_valence_mouse_B.leftButton.append(buttons[0])
                        momentary_valence_mouse_B.midButton.append(buttons[1])
                        momentary_valence_mouse_B.rightButton.append(buttons[2])
                        momentary_valence_mouse_B.time.append(momentary_valence_mouse_B.mouseClock.getTime())
            
            # *momentary_valence_question_txt_B* updates
            
            # if momentary_valence_question_txt_B is starting this frame...
            if momentary_valence_question_txt_B.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                momentary_valence_question_txt_B.frameNStart = frameN  # exact frame index
                momentary_valence_question_txt_B.tStart = t  # local t and not account for scr refresh
                momentary_valence_question_txt_B.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(momentary_valence_question_txt_B, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'momentary_valence_question_txt_B.started')
                # update status
                momentary_valence_question_txt_B.status = STARTED
                momentary_valence_question_txt_B.setAutoDraw(True)
            
            # if momentary_valence_question_txt_B is active this frame...
            if momentary_valence_question_txt_B.status == STARTED:
                # update params
                pass
            
            # *momentary_valence_slider_B* updates
            
            # if momentary_valence_slider_B is starting this frame...
            if momentary_valence_slider_B.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                momentary_valence_slider_B.frameNStart = frameN  # exact frame index
                momentary_valence_slider_B.tStart = t  # local t and not account for scr refresh
                momentary_valence_slider_B.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(momentary_valence_slider_B, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'momentary_valence_slider_B.started')
                # update status
                momentary_valence_slider_B.status = STARTED
                momentary_valence_slider_B.setAutoDraw(True)
            
            # if momentary_valence_slider_B is active this frame...
            if momentary_valence_slider_B.status == STARTED:
                # update params
                pass
            
            # *momentary_pleasant_txt_B* updates
            
            # if momentary_pleasant_txt_B is starting this frame...
            if momentary_pleasant_txt_B.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                momentary_pleasant_txt_B.frameNStart = frameN  # exact frame index
                momentary_pleasant_txt_B.tStart = t  # local t and not account for scr refresh
                momentary_pleasant_txt_B.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(momentary_pleasant_txt_B, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'momentary_pleasant_txt_B.started')
                # update status
                momentary_pleasant_txt_B.status = STARTED
                momentary_pleasant_txt_B.setAutoDraw(True)
            
            # if momentary_pleasant_txt_B is active this frame...
            if momentary_pleasant_txt_B.status == STARTED:
                # update params
                pass
            
            # *momentary_unpleasant_txt_B* updates
            
            # if momentary_unpleasant_txt_B is starting this frame...
            if momentary_unpleasant_txt_B.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                momentary_unpleasant_txt_B.frameNStart = frameN  # exact frame index
                momentary_unpleasant_txt_B.tStart = t  # local t and not account for scr refresh
                momentary_unpleasant_txt_B.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(momentary_unpleasant_txt_B, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'momentary_unpleasant_txt_B.started')
                # update status
                momentary_unpleasant_txt_B.status = STARTED
                momentary_unpleasant_txt_B.setAutoDraw(True)
            
            # if momentary_unpleasant_txt_B is active this frame...
            if momentary_unpleasant_txt_B.status == STARTED:
                # update params
                pass
            
            # *mouse_instruct_txt_2* updates
            
            # if mouse_instruct_txt_2 is starting this frame...
            if mouse_instruct_txt_2.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                mouse_instruct_txt_2.frameNStart = frameN  # exact frame index
                mouse_instruct_txt_2.tStart = t  # local t and not account for scr refresh
                mouse_instruct_txt_2.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(mouse_instruct_txt_2, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'mouse_instruct_txt_2.started')
                # update status
                mouse_instruct_txt_2.status = STARTED
                mouse_instruct_txt_2.setAutoDraw(True)
            
            # if mouse_instruct_txt_2 is active this frame...
            if mouse_instruct_txt_2.status == STARTED:
                # update params
                pass
            
            # check for quit (typically the Esc key)
            if defaultKeyboard.getKeys(keyList=["escape"]):
                thisExp.status = FINISHED
            if thisExp.status == FINISHED or endExpNow:
                endExperiment(thisExp, win=win)
                return
            # pause experiment here if requested
            if thisExp.status == PAUSED:
                pauseExperiment(
                    thisExp=thisExp, 
                    win=win, 
                    timers=[routineTimer, globalClock], 
                    currentRoutine=momentary_valence_rating_B,
                )
                # skip the frame we paused on
                continue
            
            # has a Component requested the Routine to end?
            if not continueRoutine:
                momentary_valence_rating_B.forceEnded = routineForceEnded = True
            # has the Routine been forcibly ended?
            if momentary_valence_rating_B.forceEnded or routineForceEnded:
                break
            # has every Component finished?
            continueRoutine = False
            for thisComponent in momentary_valence_rating_B.components:
                if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                    continueRoutine = True
                    break  # at least one component has not yet finished
            
            # refresh the screen
            if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                win.flip()
        
        # --- Ending Routine "momentary_valence_rating_B" ---
        for thisComponent in momentary_valence_rating_B.components:
            if hasattr(thisComponent, "setAutoDraw"):
                thisComponent.setAutoDraw(False)
        # store stop times for momentary_valence_rating_B
        momentary_valence_rating_B.tStop = globalClock.getTime(format='float')
        momentary_valence_rating_B.tStopRefresh = tThisFlipGlobal
        thisExp.addData('momentary_valence_rating_B.stopped', momentary_valence_rating_B.tStop)
        # Run 'End Routine' code from momentary_valence_rating_code_B
        momentary_valence_mouse_B.setVisible(False)
        
        thisExp.addData('condition', condition)
        # store data for post_baseline_ratings (TrialHandler)
        post_baseline_ratings.addData('momentary_valence_mouse_B.x', momentary_valence_mouse_B.x)
        post_baseline_ratings.addData('momentary_valence_mouse_B.y', momentary_valence_mouse_B.y)
        post_baseline_ratings.addData('momentary_valence_mouse_B.leftButton', momentary_valence_mouse_B.leftButton)
        post_baseline_ratings.addData('momentary_valence_mouse_B.midButton', momentary_valence_mouse_B.midButton)
        post_baseline_ratings.addData('momentary_valence_mouse_B.rightButton', momentary_valence_mouse_B.rightButton)
        post_baseline_ratings.addData('momentary_valence_mouse_B.time', momentary_valence_mouse_B.time)
        post_baseline_ratings.addData('momentary_valence_slider_B.response', momentary_valence_slider_B.getRating())
        post_baseline_ratings.addData('momentary_valence_slider_B.rt', momentary_valence_slider_B.getRT())
        # the Routine "momentary_valence_rating_B" was not non-slip safe, so reset the non-slip timer
        routineTimer.reset()
        # mark thisPost_baseline_rating as finished
        if hasattr(thisPost_baseline_rating, 'status'):
            thisPost_baseline_rating.status = FINISHED
        # if awaiting a pause, pause now
        if post_baseline_ratings.status == PAUSED:
            thisExp.status = PAUSED
            pauseExperiment(
                thisExp=thisExp, 
                win=win, 
                timers=[globalClock], 
            )
            # once done pausing, restore running status
            post_baseline_ratings.status = STARTED
        thisExp.nextEntry()
        
    # completed 1.0 repeats of 'post_baseline_ratings'
    post_baseline_ratings.status = FINISHED
    
    if thisSession is not None:
        # if running in a Session with a Liaison client, send data up to now
        thisSession.sendExperimentData()
    
    # set up handler to look after randomisation of conditions etc
    experimental_conditions = data.TrialHandler2(
        name='experimental_conditions',
        nReps=2.0, 
        method='random', 
        extraInfo=expInfo, 
        originPath=-1, 
        trialList=[None], 
        seed=None, 
        isTrials=True, 
    )
    thisExp.addLoop(experimental_conditions)  # add the loop to the experiment
    thisExperimental_condition = experimental_conditions.trialList[0]  # so we can initialise stimuli with some values
    # abbreviate parameter names if possible (e.g. rgb = thisExperimental_condition.rgb)
    if thisExperimental_condition != None:
        for paramName in thisExperimental_condition:
            globals()[paramName] = thisExperimental_condition[paramName]
    if thisSession is not None:
        # if running in a Session with a Liaison client, send data up to now
        thisSession.sendExperimentData()
    
    for thisExperimental_condition in experimental_conditions:
        experimental_conditions.status = STARTED
        if hasattr(thisExperimental_condition, 'status'):
            thisExperimental_condition.status = STARTED
        currentLoop = experimental_conditions
        thisExp.timestampOnFlip(win, 'thisRow.t', format=globalClock.format)
        if thisSession is not None:
            # if running in a Session with a Liaison client, send data up to now
            thisSession.sendExperimentData()
        # abbreviate parameter names if possible (e.g. rgb = thisExperimental_condition.rgb)
        if thisExperimental_condition != None:
            for paramName in thisExperimental_condition:
                globals()[paramName] = thisExperimental_condition[paramName]
        
        # set up handler to look after randomisation of conditions etc
        stim_block_and_ratings = data.TrialHandler2(
            name='stim_block_and_ratings',
            nReps=1.0, 
            method='random', 
            extraInfo=expInfo, 
            originPath=-1, 
            trialList=[None], 
            seed=None, 
            isTrials=True, 
        )
        thisExp.addLoop(stim_block_and_ratings)  # add the loop to the experiment
        thisStim_block_and_rating = stim_block_and_ratings.trialList[0]  # so we can initialise stimuli with some values
        # abbreviate parameter names if possible (e.g. rgb = thisStim_block_and_rating.rgb)
        if thisStim_block_and_rating != None:
            for paramName in thisStim_block_and_rating:
                globals()[paramName] = thisStim_block_and_rating[paramName]
        if thisSession is not None:
            # if running in a Session with a Liaison client, send data up to now
            thisSession.sendExperimentData()
        
        for thisStim_block_and_rating in stim_block_and_ratings:
            stim_block_and_ratings.status = STARTED
            if hasattr(thisStim_block_and_rating, 'status'):
                thisStim_block_and_rating.status = STARTED
            currentLoop = stim_block_and_ratings
            thisExp.timestampOnFlip(win, 'thisRow.t', format=globalClock.format)
            if thisSession is not None:
                # if running in a Session with a Liaison client, send data up to now
                thisSession.sendExperimentData()
            # abbreviate parameter names if possible (e.g. rgb = thisStim_block_and_rating.rgb)
            if thisStim_block_and_rating != None:
                for paramName in thisStim_block_and_rating:
                    globals()[paramName] = thisStim_block_and_rating[paramName]
            
            # --- Prepare to start Routine "block_setup" ---
            # create an object to store info about Routine block_setup
            block_setup = data.Routine(
                name='block_setup',
                components=[],
            )
            block_setup.status = NOT_STARTED
            continueRoutine = True
            # update component parameters for each repeat
            # Run 'Begin Routine' code from code_3
            block_count = block_count +1
            
            if condition_order == 'pos_first':
                if block_count == 1:
                    stim_file = 'positive_stim.csv'
                    stim_condition = 'positive'
                elif block_count == 2:
                    stim_file = 'negative_stim.csv'
                    stim_condition = 'negative'
            elif condition_order == 'neg_first':
                if block_count == 1:
                    stim_file = 'negative_stim.csv'
                    stim_condition = 'negative'
                elif block_count == 2:
                    stim_file = 'positive_stim.csv'
                    stim_condition = 'positive'
            # store start times for block_setup
            block_setup.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
            block_setup.tStart = globalClock.getTime(format='float')
            block_setup.status = STARTED
            thisExp.addData('block_setup.started', block_setup.tStart)
            block_setup.maxDuration = None
            # keep track of which components have finished
            block_setupComponents = block_setup.components
            for thisComponent in block_setup.components:
                thisComponent.tStart = None
                thisComponent.tStop = None
                thisComponent.tStartRefresh = None
                thisComponent.tStopRefresh = None
                if hasattr(thisComponent, 'status'):
                    thisComponent.status = NOT_STARTED
            # reset timers
            t = 0
            _timeToFirstFrame = win.getFutureFlipTime(clock="now")
            frameN = -1
            
            # --- Run Routine "block_setup" ---
            thisExp.currentRoutine = block_setup
            block_setup.forceEnded = routineForceEnded = not continueRoutine
            while continueRoutine:
                # if trial has changed, end Routine now
                if hasattr(thisStim_block_and_rating, 'status') and thisStim_block_and_rating.status == STOPPING:
                    continueRoutine = False
                # get current time
                t = routineTimer.getTime()
                tThisFlip = win.getFutureFlipTime(clock=routineTimer)
                tThisFlipGlobal = win.getFutureFlipTime(clock=None)
                frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
                # update/draw components on each frame
                
                # check for quit (typically the Esc key)
                if defaultKeyboard.getKeys(keyList=["escape"]):
                    thisExp.status = FINISHED
                if thisExp.status == FINISHED or endExpNow:
                    endExperiment(thisExp, win=win)
                    return
                # pause experiment here if requested
                if thisExp.status == PAUSED:
                    pauseExperiment(
                        thisExp=thisExp, 
                        win=win, 
                        timers=[routineTimer, globalClock], 
                        currentRoutine=block_setup,
                    )
                    # skip the frame we paused on
                    continue
                
                # has a Component requested the Routine to end?
                if not continueRoutine:
                    block_setup.forceEnded = routineForceEnded = True
                # has the Routine been forcibly ended?
                if block_setup.forceEnded or routineForceEnded:
                    break
                # has every Component finished?
                continueRoutine = False
                for thisComponent in block_setup.components:
                    if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                        continueRoutine = True
                        break  # at least one component has not yet finished
                
                # refresh the screen
                if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                    win.flip()
            
            # --- Ending Routine "block_setup" ---
            for thisComponent in block_setup.components:
                if hasattr(thisComponent, "setAutoDraw"):
                    thisComponent.setAutoDraw(False)
            # store stop times for block_setup
            block_setup.tStop = globalClock.getTime(format='float')
            block_setup.tStopRefresh = tThisFlipGlobal
            thisExp.addData('block_setup.stopped', block_setup.tStop)
            # the Routine "block_setup" was not non-slip safe, so reset the non-slip timer
            routineTimer.reset()
            
            # --- Prepare to start Routine "video_instruct" ---
            # create an object to store info about Routine video_instruct
            video_instruct = data.Routine(
                name='video_instruct',
                components=[video_instruct_txt],
            )
            video_instruct.status = NOT_STARTED
            continueRoutine = True
            # update component parameters for each repeat
            # store start times for video_instruct
            video_instruct.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
            video_instruct.tStart = globalClock.getTime(format='float')
            video_instruct.status = STARTED
            thisExp.addData('video_instruct.started', video_instruct.tStart)
            video_instruct.maxDuration = None
            # keep track of which components have finished
            video_instructComponents = video_instruct.components
            for thisComponent in video_instruct.components:
                thisComponent.tStart = None
                thisComponent.tStop = None
                thisComponent.tStartRefresh = None
                thisComponent.tStopRefresh = None
                if hasattr(thisComponent, 'status'):
                    thisComponent.status = NOT_STARTED
            # reset timers
            t = 0
            _timeToFirstFrame = win.getFutureFlipTime(clock="now")
            frameN = -1
            
            # --- Run Routine "video_instruct" ---
            thisExp.currentRoutine = video_instruct
            video_instruct.forceEnded = routineForceEnded = not continueRoutine
            while continueRoutine and routineTimer.getTime() < 8.0:
                # if trial has changed, end Routine now
                if hasattr(thisStim_block_and_rating, 'status') and thisStim_block_and_rating.status == STOPPING:
                    continueRoutine = False
                # get current time
                t = routineTimer.getTime()
                tThisFlip = win.getFutureFlipTime(clock=routineTimer)
                tThisFlipGlobal = win.getFutureFlipTime(clock=None)
                frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
                # update/draw components on each frame
                
                # *video_instruct_txt* updates
                
                # if video_instruct_txt is starting this frame...
                if video_instruct_txt.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                    # keep track of start time/frame for later
                    video_instruct_txt.frameNStart = frameN  # exact frame index
                    video_instruct_txt.tStart = t  # local t and not account for scr refresh
                    video_instruct_txt.tStartRefresh = tThisFlipGlobal  # on global time
                    win.timeOnFlip(video_instruct_txt, 'tStartRefresh')  # time at next scr refresh
                    # add timestamp to datafile
                    thisExp.timestampOnFlip(win, 'video_instruct_txt.started')
                    # update status
                    video_instruct_txt.status = STARTED
                    video_instruct_txt.setAutoDraw(True)
                
                # if video_instruct_txt is active this frame...
                if video_instruct_txt.status == STARTED:
                    # update params
                    pass
                
                # if video_instruct_txt is stopping this frame...
                if video_instruct_txt.status == STARTED:
                    # is it time to stop? (based on global clock, using actual start)
                    if tThisFlipGlobal > video_instruct_txt.tStartRefresh + 8-frameTolerance:
                        # keep track of stop time/frame for later
                        video_instruct_txt.tStop = t  # not accounting for scr refresh
                        video_instruct_txt.tStopRefresh = tThisFlipGlobal  # on global time
                        video_instruct_txt.frameNStop = frameN  # exact frame index
                        # add timestamp to datafile
                        thisExp.timestampOnFlip(win, 'video_instruct_txt.stopped')
                        # update status
                        video_instruct_txt.status = FINISHED
                        video_instruct_txt.setAutoDraw(False)
                
                # check for quit (typically the Esc key)
                if defaultKeyboard.getKeys(keyList=["escape"]):
                    thisExp.status = FINISHED
                if thisExp.status == FINISHED or endExpNow:
                    endExperiment(thisExp, win=win)
                    return
                # pause experiment here if requested
                if thisExp.status == PAUSED:
                    pauseExperiment(
                        thisExp=thisExp, 
                        win=win, 
                        timers=[routineTimer, globalClock], 
                        currentRoutine=video_instruct,
                    )
                    # skip the frame we paused on
                    continue
                
                # has a Component requested the Routine to end?
                if not continueRoutine:
                    video_instruct.forceEnded = routineForceEnded = True
                # has the Routine been forcibly ended?
                if video_instruct.forceEnded or routineForceEnded:
                    break
                # has every Component finished?
                continueRoutine = False
                for thisComponent in video_instruct.components:
                    if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                        continueRoutine = True
                        break  # at least one component has not yet finished
                
                # refresh the screen
                if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                    win.flip()
            
            # --- Ending Routine "video_instruct" ---
            for thisComponent in video_instruct.components:
                if hasattr(thisComponent, "setAutoDraw"):
                    thisComponent.setAutoDraw(False)
            # store stop times for video_instruct
            video_instruct.tStop = globalClock.getTime(format='float')
            video_instruct.tStopRefresh = tThisFlipGlobal
            thisExp.addData('video_instruct.stopped', video_instruct.tStop)
            # using non-slip timing so subtract the expected duration of this Routine (unless ended on request)
            if video_instruct.maxDurationReached:
                routineTimer.addTime(-video_instruct.maxDuration)
            elif video_instruct.forceEnded:
                routineTimer.reset()
            else:
                routineTimer.addTime(-8.000000)
            
            # set up handler to look after randomisation of conditions etc
            stim_block = data.TrialHandler2(
                name='stim_block',
                nReps=1.0, 
                method='random', 
                extraInfo=expInfo, 
                originPath=-1, 
                trialList=data.importConditions(
                stim_file, 
                selection='0:4'
            )
            , 
                seed=None, 
                isTrials=True, 
            )
            thisExp.addLoop(stim_block)  # add the loop to the experiment
            thisStim_block = stim_block.trialList[0]  # so we can initialise stimuli with some values
            # abbreviate parameter names if possible (e.g. rgb = thisStim_block.rgb)
            if thisStim_block != None:
                for paramName in thisStim_block:
                    globals()[paramName] = thisStim_block[paramName]
            if thisSession is not None:
                # if running in a Session with a Liaison client, send data up to now
                thisSession.sendExperimentData()
            
            for thisStim_block in stim_block:
                stim_block.status = STARTED
                if hasattr(thisStim_block, 'status'):
                    thisStim_block.status = STARTED
                currentLoop = stim_block
                thisExp.timestampOnFlip(win, 'thisRow.t', format=globalClock.format)
                if thisSession is not None:
                    # if running in a Session with a Liaison client, send data up to now
                    thisSession.sendExperimentData()
                # abbreviate parameter names if possible (e.g. rgb = thisStim_block.rgb)
                if thisStim_block != None:
                    for paramName in thisStim_block:
                        globals()[paramName] = thisStim_block[paramName]
                
                # --- Prepare to start Routine "stimuli" ---
                # create an object to store info about Routine stimuli
                stimuli = data.Routine(
                    name='stimuli',
                    components=[video],
                )
                stimuli.status = NOT_STARTED
                continueRoutine = True
                # update component parameters for each repeat
                video.setMovie(stim_path)
                # Run 'Begin Routine' code from stim_trigger_code
                #----
                # Log time for camera
                # ---
                thisExp.addData('onset_wall', time.time())
                thisExp.addData('time_since_recording_start', time.time() - experiment_start_wall)
                
                if trigger_name == 'Nstim1_trig':
                    neg_stim_trigger = neg_stim1_trigger
                elif trigger_name == 'Nstim2_trig':
                     neg_stim_trigger = neg_stim2_trigger
                if trigger_name == 'Pstim1_trig':
                    pos_stim_trigger = pos_stim1_trigger
                elif trigger_name == 'Pstim2_trig':
                    pos_stim_trigger = pos_stim2_trigger    
                
                
                stimulus_trigger_sent = False
                stimulus_trigger_cleared = False
                # store start times for stimuli
                stimuli.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
                stimuli.tStart = globalClock.getTime(format='float')
                stimuli.status = STARTED
                thisExp.addData('stimuli.started', stimuli.tStart)
                stimuli.maxDuration = None
                # keep track of which components have finished
                stimuliComponents = stimuli.components
                for thisComponent in stimuli.components:
                    thisComponent.tStart = None
                    thisComponent.tStop = None
                    thisComponent.tStartRefresh = None
                    thisComponent.tStopRefresh = None
                    if hasattr(thisComponent, 'status'):
                        thisComponent.status = NOT_STARTED
                # reset timers
                t = 0
                _timeToFirstFrame = win.getFutureFlipTime(clock="now")
                frameN = -1
                
                # --- Run Routine "stimuli" ---
                thisExp.currentRoutine = stimuli
                stimuli.forceEnded = routineForceEnded = not continueRoutine
                while continueRoutine:
                    # if trial has changed, end Routine now
                    if hasattr(thisStim_block, 'status') and thisStim_block.status == STOPPING:
                        continueRoutine = False
                    # get current time
                    t = routineTimer.getTime()
                    tThisFlip = win.getFutureFlipTime(clock=routineTimer)
                    tThisFlipGlobal = win.getFutureFlipTime(clock=None)
                    frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
                    # update/draw components on each frame
                    
                    # *video* updates
                    
                    # if video is starting this frame...
                    if video.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                        # keep track of start time/frame for later
                        video.frameNStart = frameN  # exact frame index
                        video.tStart = t  # local t and not account for scr refresh
                        video.tStartRefresh = tThisFlipGlobal  # on global time
                        win.timeOnFlip(video, 'tStartRefresh')  # time at next scr refresh
                        # add timestamp to datafile
                        thisExp.timestampOnFlip(win, 'video.started')
                        # update status
                        video.status = STARTED
                        video.setAutoDraw(True)
                        video.play()
                    
                    # if video is stopping this frame...
                    if video.status == STARTED:
                        if bool(False) or video.isFinished:
                            # keep track of stop time/frame for later
                            video.tStop = t  # not accounting for scr refresh
                            video.tStopRefresh = tThisFlipGlobal  # on global time
                            video.frameNStop = frameN  # exact frame index
                            # add timestamp to datafile
                            thisExp.timestampOnFlip(win, 'video.stopped')
                            # update status
                            video.status = FINISHED
                            video.setAutoDraw(False)
                    if video.status == FINISHED:  # force-end the Routine
                        continueRoutine = False
                    # Run 'Each Frame' code from stim_trigger_code
                    # Set trigger value based on condition
                    if stim_condition == 'negative':
                        stim_trigger = neg_stim_trigger
                    elif stim_condition == 'positive':
                        stim_trigger = pos_stim_trigger
                    
                    # --- Stimulus ON ---
                    if video.status == STARTED and not stimulus_trigger_sent:
                        win.callOnFlip(ser.write, str.encode(stim_trigger))
                        stimulus_trigger_sent = True
                    
                    # --- Stimulus OFF ---
                    if video.status == FINISHED and not stimulus_trigger_cleared:
                        win.callOnFlip(ser.write, str.encode('00'))
                        ser.write('RR'.encode('utf-8'))
                        stimulus_trigger_cleared = True
                    
                    
                                
                    
                    # check for quit (typically the Esc key)
                    if defaultKeyboard.getKeys(keyList=["escape"]):
                        thisExp.status = FINISHED
                    if thisExp.status == FINISHED or endExpNow:
                        endExperiment(thisExp, win=win)
                        return
                    # pause experiment here if requested
                    if thisExp.status == PAUSED:
                        pauseExperiment(
                            thisExp=thisExp, 
                            win=win, 
                            timers=[routineTimer, globalClock], 
                            currentRoutine=stimuli,
                        )
                        # skip the frame we paused on
                        continue
                    
                    # has a Component requested the Routine to end?
                    if not continueRoutine:
                        stimuli.forceEnded = routineForceEnded = True
                    # has the Routine been forcibly ended?
                    if stimuli.forceEnded or routineForceEnded:
                        break
                    # has every Component finished?
                    continueRoutine = False
                    for thisComponent in stimuli.components:
                        if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                            continueRoutine = True
                            break  # at least one component has not yet finished
                    
                    # refresh the screen
                    if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                        win.flip()
                
                # --- Ending Routine "stimuli" ---
                for thisComponent in stimuli.components:
                    if hasattr(thisComponent, "setAutoDraw"):
                        thisComponent.setAutoDraw(False)
                # store stop times for stimuli
                stimuli.tStop = globalClock.getTime(format='float')
                stimuli.tStopRefresh = tThisFlipGlobal
                thisExp.addData('stimuli.stopped', stimuli.tStop)
                video.setAutoDraw(False)
                video.stop()  # ensure movie has stopped at end of Routine
                # Run 'End Routine' code from stim_trigger_code
                ser.write ('RR'.encode('utf-8'))
                # the Routine "stimuli" was not non-slip safe, so reset the non-slip timer
                routineTimer.reset()
                # mark thisStim_block as finished
                if hasattr(thisStim_block, 'status'):
                    thisStim_block.status = FINISHED
                # if awaiting a pause, pause now
                if stim_block.status == PAUSED:
                    thisExp.status = PAUSED
                    pauseExperiment(
                        thisExp=thisExp, 
                        win=win, 
                        timers=[globalClock], 
                    )
                    # once done pausing, restore running status
                    stim_block.status = STARTED
                thisExp.nextEntry()
                
            # completed 1.0 repeats of 'stim_block'
            stim_block.status = FINISHED
            
            if thisSession is not None:
                # if running in a Session with a Liaison client, send data up to now
                thisSession.sendExperimentData()
            
            # set up handler to look after randomisation of conditions etc
            post_emotion_induction_ratings = data.TrialHandler2(
                name='post_emotion_induction_ratings',
                nReps=1.0, 
                method='random', 
                extraInfo=expInfo, 
                originPath=-1, 
                trialList=[None], 
                seed=None, 
                isTrials=True, 
            )
            thisExp.addLoop(post_emotion_induction_ratings)  # add the loop to the experiment
            thisPost_emotion_induction_rating = post_emotion_induction_ratings.trialList[0]  # so we can initialise stimuli with some values
            # abbreviate parameter names if possible (e.g. rgb = thisPost_emotion_induction_rating.rgb)
            if thisPost_emotion_induction_rating != None:
                for paramName in thisPost_emotion_induction_rating:
                    globals()[paramName] = thisPost_emotion_induction_rating[paramName]
            if thisSession is not None:
                # if running in a Session with a Liaison client, send data up to now
                thisSession.sendExperimentData()
            
            for thisPost_emotion_induction_rating in post_emotion_induction_ratings:
                post_emotion_induction_ratings.status = STARTED
                if hasattr(thisPost_emotion_induction_rating, 'status'):
                    thisPost_emotion_induction_rating.status = STARTED
                currentLoop = post_emotion_induction_ratings
                thisExp.timestampOnFlip(win, 'thisRow.t', format=globalClock.format)
                if thisSession is not None:
                    # if running in a Session with a Liaison client, send data up to now
                    thisSession.sendExperimentData()
                # abbreviate parameter names if possible (e.g. rgb = thisPost_emotion_induction_rating.rgb)
                if thisPost_emotion_induction_rating != None:
                    for paramName in thisPost_emotion_induction_rating:
                        globals()[paramName] = thisPost_emotion_induction_rating[paramName]
                
                # --- Prepare to start Routine "momentary_valence_rating_A" ---
                # create an object to store info about Routine momentary_valence_rating_A
                momentary_valence_rating_A = data.Routine(
                    name='momentary_valence_rating_A',
                    components=[momentary_valence_mouse_A, momentary_valence_question_txt_A, momentary_valence_slider_A, momentary_pleasant_txt_A, momentary_unpleasant_txt_A, mouse_instuct_txt],
                )
                momentary_valence_rating_A.status = NOT_STARTED
                continueRoutine = True
                # update component parameters for each repeat
                # Run 'Begin Routine' code from momentary_valence_rating_code_A
                momentary_valence_mouse_A.setVisible(True)
                timer = None
                
                condition = stim_condition
                
                # determine which slider will appear first
                rating_pair_count += 1
                if rating_pair_count % 2 == 1:
                    rating_order = rating_start
                else:
                    rating_order = 'arousal_first' if rating_start == 'valence_first' else 'valence_first'
                
                if rating_order == 'arousal_first':
                    continueRoutine = False
                # setup some python lists for storing info about the momentary_valence_mouse_A
                momentary_valence_mouse_A.x = []
                momentary_valence_mouse_A.y = []
                momentary_valence_mouse_A.leftButton = []
                momentary_valence_mouse_A.midButton = []
                momentary_valence_mouse_A.rightButton = []
                momentary_valence_mouse_A.time = []
                gotValidClick = False  # until a click is received
                momentary_valence_slider_A.reset()
                momentary_valence_slider_A.setPos((0,0))
                momentary_pleasant_txt_A.setPos((0.5, -0.05))
                momentary_unpleasant_txt_A.setPos((-0.5, -0.05))
                # store start times for momentary_valence_rating_A
                momentary_valence_rating_A.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
                momentary_valence_rating_A.tStart = globalClock.getTime(format='float')
                momentary_valence_rating_A.status = STARTED
                thisExp.addData('momentary_valence_rating_A.started', momentary_valence_rating_A.tStart)
                momentary_valence_rating_A.maxDuration = None
                # keep track of which components have finished
                momentary_valence_rating_AComponents = momentary_valence_rating_A.components
                for thisComponent in momentary_valence_rating_A.components:
                    thisComponent.tStart = None
                    thisComponent.tStop = None
                    thisComponent.tStartRefresh = None
                    thisComponent.tStopRefresh = None
                    if hasattr(thisComponent, 'status'):
                        thisComponent.status = NOT_STARTED
                # reset timers
                t = 0
                _timeToFirstFrame = win.getFutureFlipTime(clock="now")
                frameN = -1
                
                # --- Run Routine "momentary_valence_rating_A" ---
                thisExp.currentRoutine = momentary_valence_rating_A
                momentary_valence_rating_A.forceEnded = routineForceEnded = not continueRoutine
                while continueRoutine:
                    # if trial has changed, end Routine now
                    if hasattr(thisPost_emotion_induction_rating, 'status') and thisPost_emotion_induction_rating.status == STOPPING:
                        continueRoutine = False
                    # get current time
                    t = routineTimer.getTime()
                    tThisFlip = win.getFutureFlipTime(clock=routineTimer)
                    tThisFlipGlobal = win.getFutureFlipTime(clock=None)
                    frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
                    # update/draw components on each frame
                    # Run 'Each Frame' code from momentary_valence_rating_code_A
                    if momentary_valence_slider_A.getRating() is not None:
                    
                        if timer is None:
                            timer = core.CountdownTimer(2)
                    
                        if timer.getTime() < 0:
                            continueRoutine = False
                    # *momentary_valence_mouse_A* updates
                    
                    # if momentary_valence_mouse_A is starting this frame...
                    if momentary_valence_mouse_A.status == NOT_STARTED and t >= 0.0-frameTolerance:
                        # keep track of start time/frame for later
                        momentary_valence_mouse_A.frameNStart = frameN  # exact frame index
                        momentary_valence_mouse_A.tStart = t  # local t and not account for scr refresh
                        momentary_valence_mouse_A.tStartRefresh = tThisFlipGlobal  # on global time
                        win.timeOnFlip(momentary_valence_mouse_A, 'tStartRefresh')  # time at next scr refresh
                        # add timestamp to datafile
                        thisExp.addData('momentary_valence_mouse_A.started', t)
                        # update status
                        momentary_valence_mouse_A.status = STARTED
                        momentary_valence_mouse_A.mouseClock.reset()
                        prevButtonState = momentary_valence_mouse_A.getPressed()  # if button is down already this ISN'T a new click
                    if momentary_valence_mouse_A.status == STARTED:  # only update if started and not finished!
                        buttons = momentary_valence_mouse_A.getPressed()
                        if buttons != prevButtonState:  # button state changed?
                            prevButtonState = buttons
                            if sum(buttons) > 0:  # state changed to a new click
                                pass
                                x, y = momentary_valence_mouse_A.getPos()
                                momentary_valence_mouse_A.x.append(float(x))
                                momentary_valence_mouse_A.y.append(float(y))
                                buttons = momentary_valence_mouse_A.getPressed()
                                momentary_valence_mouse_A.leftButton.append(buttons[0])
                                momentary_valence_mouse_A.midButton.append(buttons[1])
                                momentary_valence_mouse_A.rightButton.append(buttons[2])
                                momentary_valence_mouse_A.time.append(momentary_valence_mouse_A.mouseClock.getTime())
                    
                    # *momentary_valence_question_txt_A* updates
                    
                    # if momentary_valence_question_txt_A is starting this frame...
                    if momentary_valence_question_txt_A.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                        # keep track of start time/frame for later
                        momentary_valence_question_txt_A.frameNStart = frameN  # exact frame index
                        momentary_valence_question_txt_A.tStart = t  # local t and not account for scr refresh
                        momentary_valence_question_txt_A.tStartRefresh = tThisFlipGlobal  # on global time
                        win.timeOnFlip(momentary_valence_question_txt_A, 'tStartRefresh')  # time at next scr refresh
                        # add timestamp to datafile
                        thisExp.timestampOnFlip(win, 'momentary_valence_question_txt_A.started')
                        # update status
                        momentary_valence_question_txt_A.status = STARTED
                        momentary_valence_question_txt_A.setAutoDraw(True)
                    
                    # if momentary_valence_question_txt_A is active this frame...
                    if momentary_valence_question_txt_A.status == STARTED:
                        # update params
                        pass
                    
                    # *momentary_valence_slider_A* updates
                    
                    # if momentary_valence_slider_A is starting this frame...
                    if momentary_valence_slider_A.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                        # keep track of start time/frame for later
                        momentary_valence_slider_A.frameNStart = frameN  # exact frame index
                        momentary_valence_slider_A.tStart = t  # local t and not account for scr refresh
                        momentary_valence_slider_A.tStartRefresh = tThisFlipGlobal  # on global time
                        win.timeOnFlip(momentary_valence_slider_A, 'tStartRefresh')  # time at next scr refresh
                        # add timestamp to datafile
                        thisExp.timestampOnFlip(win, 'momentary_valence_slider_A.started')
                        # update status
                        momentary_valence_slider_A.status = STARTED
                        momentary_valence_slider_A.setAutoDraw(True)
                    
                    # if momentary_valence_slider_A is active this frame...
                    if momentary_valence_slider_A.status == STARTED:
                        # update params
                        pass
                    
                    # *momentary_pleasant_txt_A* updates
                    
                    # if momentary_pleasant_txt_A is starting this frame...
                    if momentary_pleasant_txt_A.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                        # keep track of start time/frame for later
                        momentary_pleasant_txt_A.frameNStart = frameN  # exact frame index
                        momentary_pleasant_txt_A.tStart = t  # local t and not account for scr refresh
                        momentary_pleasant_txt_A.tStartRefresh = tThisFlipGlobal  # on global time
                        win.timeOnFlip(momentary_pleasant_txt_A, 'tStartRefresh')  # time at next scr refresh
                        # add timestamp to datafile
                        thisExp.timestampOnFlip(win, 'momentary_pleasant_txt_A.started')
                        # update status
                        momentary_pleasant_txt_A.status = STARTED
                        momentary_pleasant_txt_A.setAutoDraw(True)
                    
                    # if momentary_pleasant_txt_A is active this frame...
                    if momentary_pleasant_txt_A.status == STARTED:
                        # update params
                        pass
                    
                    # *momentary_unpleasant_txt_A* updates
                    
                    # if momentary_unpleasant_txt_A is starting this frame...
                    if momentary_unpleasant_txt_A.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                        # keep track of start time/frame for later
                        momentary_unpleasant_txt_A.frameNStart = frameN  # exact frame index
                        momentary_unpleasant_txt_A.tStart = t  # local t and not account for scr refresh
                        momentary_unpleasant_txt_A.tStartRefresh = tThisFlipGlobal  # on global time
                        win.timeOnFlip(momentary_unpleasant_txt_A, 'tStartRefresh')  # time at next scr refresh
                        # add timestamp to datafile
                        thisExp.timestampOnFlip(win, 'momentary_unpleasant_txt_A.started')
                        # update status
                        momentary_unpleasant_txt_A.status = STARTED
                        momentary_unpleasant_txt_A.setAutoDraw(True)
                    
                    # if momentary_unpleasant_txt_A is active this frame...
                    if momentary_unpleasant_txt_A.status == STARTED:
                        # update params
                        pass
                    
                    # *mouse_instuct_txt* updates
                    
                    # if mouse_instuct_txt is starting this frame...
                    if mouse_instuct_txt.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                        # keep track of start time/frame for later
                        mouse_instuct_txt.frameNStart = frameN  # exact frame index
                        mouse_instuct_txt.tStart = t  # local t and not account for scr refresh
                        mouse_instuct_txt.tStartRefresh = tThisFlipGlobal  # on global time
                        win.timeOnFlip(mouse_instuct_txt, 'tStartRefresh')  # time at next scr refresh
                        # add timestamp to datafile
                        thisExp.timestampOnFlip(win, 'mouse_instuct_txt.started')
                        # update status
                        mouse_instuct_txt.status = STARTED
                        mouse_instuct_txt.setAutoDraw(True)
                    
                    # if mouse_instuct_txt is active this frame...
                    if mouse_instuct_txt.status == STARTED:
                        # update params
                        pass
                    
                    # check for quit (typically the Esc key)
                    if defaultKeyboard.getKeys(keyList=["escape"]):
                        thisExp.status = FINISHED
                    if thisExp.status == FINISHED or endExpNow:
                        endExperiment(thisExp, win=win)
                        return
                    # pause experiment here if requested
                    if thisExp.status == PAUSED:
                        pauseExperiment(
                            thisExp=thisExp, 
                            win=win, 
                            timers=[routineTimer, globalClock], 
                            currentRoutine=momentary_valence_rating_A,
                        )
                        # skip the frame we paused on
                        continue
                    
                    # has a Component requested the Routine to end?
                    if not continueRoutine:
                        momentary_valence_rating_A.forceEnded = routineForceEnded = True
                    # has the Routine been forcibly ended?
                    if momentary_valence_rating_A.forceEnded or routineForceEnded:
                        break
                    # has every Component finished?
                    continueRoutine = False
                    for thisComponent in momentary_valence_rating_A.components:
                        if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                            continueRoutine = True
                            break  # at least one component has not yet finished
                    
                    # refresh the screen
                    if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                        win.flip()
                
                # --- Ending Routine "momentary_valence_rating_A" ---
                for thisComponent in momentary_valence_rating_A.components:
                    if hasattr(thisComponent, "setAutoDraw"):
                        thisComponent.setAutoDraw(False)
                # store stop times for momentary_valence_rating_A
                momentary_valence_rating_A.tStop = globalClock.getTime(format='float')
                momentary_valence_rating_A.tStopRefresh = tThisFlipGlobal
                thisExp.addData('momentary_valence_rating_A.stopped', momentary_valence_rating_A.tStop)
                # Run 'End Routine' code from momentary_valence_rating_code_A
                momentary_valence_mouse_A.setVisible(False)
                
                thisExp.addData('condition', condition)
                # store data for post_emotion_induction_ratings (TrialHandler)
                post_emotion_induction_ratings.addData('momentary_valence_mouse_A.x', momentary_valence_mouse_A.x)
                post_emotion_induction_ratings.addData('momentary_valence_mouse_A.y', momentary_valence_mouse_A.y)
                post_emotion_induction_ratings.addData('momentary_valence_mouse_A.leftButton', momentary_valence_mouse_A.leftButton)
                post_emotion_induction_ratings.addData('momentary_valence_mouse_A.midButton', momentary_valence_mouse_A.midButton)
                post_emotion_induction_ratings.addData('momentary_valence_mouse_A.rightButton', momentary_valence_mouse_A.rightButton)
                post_emotion_induction_ratings.addData('momentary_valence_mouse_A.time', momentary_valence_mouse_A.time)
                post_emotion_induction_ratings.addData('momentary_valence_slider_A.response', momentary_valence_slider_A.getRating())
                post_emotion_induction_ratings.addData('momentary_valence_slider_A.rt', momentary_valence_slider_A.getRT())
                # the Routine "momentary_valence_rating_A" was not non-slip safe, so reset the non-slip timer
                routineTimer.reset()
                
                # --- Prepare to start Routine "momentary_arousal_rating" ---
                # create an object to store info about Routine momentary_arousal_rating
                momentary_arousal_rating = data.Routine(
                    name='momentary_arousal_rating',
                    components=[momentary_arousal_mouse, momentary_arousal_question_txt, momentary_arousal_slider, momentary_alert_txt, momentary_not_alert_txt, mouse_instruct_txt_1],
                )
                momentary_arousal_rating.status = NOT_STARTED
                continueRoutine = True
                # update component parameters for each repeat
                # Run 'Begin Routine' code from momentary_arousal_rating_code_B
                momentary_arousal_mouse.setVisible(True)
                timer = None
                
                condition = stim_condition
                # setup some python lists for storing info about the momentary_arousal_mouse
                momentary_arousal_mouse.x = []
                momentary_arousal_mouse.y = []
                momentary_arousal_mouse.leftButton = []
                momentary_arousal_mouse.midButton = []
                momentary_arousal_mouse.rightButton = []
                momentary_arousal_mouse.time = []
                gotValidClick = False  # until a click is received
                momentary_arousal_slider.reset()
                momentary_arousal_slider.setPos((0,0))
                momentary_alert_txt.setPos((0.5, -0.05))
                momentary_not_alert_txt.setPos((-0.5, -0.05))
                # store start times for momentary_arousal_rating
                momentary_arousal_rating.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
                momentary_arousal_rating.tStart = globalClock.getTime(format='float')
                momentary_arousal_rating.status = STARTED
                thisExp.addData('momentary_arousal_rating.started', momentary_arousal_rating.tStart)
                momentary_arousal_rating.maxDuration = None
                # keep track of which components have finished
                momentary_arousal_ratingComponents = momentary_arousal_rating.components
                for thisComponent in momentary_arousal_rating.components:
                    thisComponent.tStart = None
                    thisComponent.tStop = None
                    thisComponent.tStartRefresh = None
                    thisComponent.tStopRefresh = None
                    if hasattr(thisComponent, 'status'):
                        thisComponent.status = NOT_STARTED
                # reset timers
                t = 0
                _timeToFirstFrame = win.getFutureFlipTime(clock="now")
                frameN = -1
                
                # --- Run Routine "momentary_arousal_rating" ---
                thisExp.currentRoutine = momentary_arousal_rating
                momentary_arousal_rating.forceEnded = routineForceEnded = not continueRoutine
                while continueRoutine:
                    # if trial has changed, end Routine now
                    if hasattr(thisPost_emotion_induction_rating, 'status') and thisPost_emotion_induction_rating.status == STOPPING:
                        continueRoutine = False
                    # get current time
                    t = routineTimer.getTime()
                    tThisFlip = win.getFutureFlipTime(clock=routineTimer)
                    tThisFlipGlobal = win.getFutureFlipTime(clock=None)
                    frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
                    # update/draw components on each frame
                    # Run 'Each Frame' code from momentary_arousal_rating_code_B
                    if momentary_arousal_slider.getRating() is not None:
                    
                        if timer is None:
                            timer = core.CountdownTimer(2)
                    
                        if timer.getTime() < 0:
                            continueRoutine = False
                    # *momentary_arousal_mouse* updates
                    
                    # if momentary_arousal_mouse is starting this frame...
                    if momentary_arousal_mouse.status == NOT_STARTED and t >= 0.0-frameTolerance:
                        # keep track of start time/frame for later
                        momentary_arousal_mouse.frameNStart = frameN  # exact frame index
                        momentary_arousal_mouse.tStart = t  # local t and not account for scr refresh
                        momentary_arousal_mouse.tStartRefresh = tThisFlipGlobal  # on global time
                        win.timeOnFlip(momentary_arousal_mouse, 'tStartRefresh')  # time at next scr refresh
                        # add timestamp to datafile
                        thisExp.addData('momentary_arousal_mouse.started', t)
                        # update status
                        momentary_arousal_mouse.status = STARTED
                        momentary_arousal_mouse.mouseClock.reset()
                        prevButtonState = momentary_arousal_mouse.getPressed()  # if button is down already this ISN'T a new click
                    if momentary_arousal_mouse.status == STARTED:  # only update if started and not finished!
                        buttons = momentary_arousal_mouse.getPressed()
                        if buttons != prevButtonState:  # button state changed?
                            prevButtonState = buttons
                            if sum(buttons) > 0:  # state changed to a new click
                                pass
                                x, y = momentary_arousal_mouse.getPos()
                                momentary_arousal_mouse.x.append(float(x))
                                momentary_arousal_mouse.y.append(float(y))
                                buttons = momentary_arousal_mouse.getPressed()
                                momentary_arousal_mouse.leftButton.append(buttons[0])
                                momentary_arousal_mouse.midButton.append(buttons[1])
                                momentary_arousal_mouse.rightButton.append(buttons[2])
                                momentary_arousal_mouse.time.append(momentary_arousal_mouse.mouseClock.getTime())
                    
                    # *momentary_arousal_question_txt* updates
                    
                    # if momentary_arousal_question_txt is starting this frame...
                    if momentary_arousal_question_txt.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                        # keep track of start time/frame for later
                        momentary_arousal_question_txt.frameNStart = frameN  # exact frame index
                        momentary_arousal_question_txt.tStart = t  # local t and not account for scr refresh
                        momentary_arousal_question_txt.tStartRefresh = tThisFlipGlobal  # on global time
                        win.timeOnFlip(momentary_arousal_question_txt, 'tStartRefresh')  # time at next scr refresh
                        # add timestamp to datafile
                        thisExp.timestampOnFlip(win, 'momentary_arousal_question_txt.started')
                        # update status
                        momentary_arousal_question_txt.status = STARTED
                        momentary_arousal_question_txt.setAutoDraw(True)
                    
                    # if momentary_arousal_question_txt is active this frame...
                    if momentary_arousal_question_txt.status == STARTED:
                        # update params
                        pass
                    
                    # *momentary_arousal_slider* updates
                    
                    # if momentary_arousal_slider is starting this frame...
                    if momentary_arousal_slider.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                        # keep track of start time/frame for later
                        momentary_arousal_slider.frameNStart = frameN  # exact frame index
                        momentary_arousal_slider.tStart = t  # local t and not account for scr refresh
                        momentary_arousal_slider.tStartRefresh = tThisFlipGlobal  # on global time
                        win.timeOnFlip(momentary_arousal_slider, 'tStartRefresh')  # time at next scr refresh
                        # add timestamp to datafile
                        thisExp.timestampOnFlip(win, 'momentary_arousal_slider.started')
                        # update status
                        momentary_arousal_slider.status = STARTED
                        momentary_arousal_slider.setAutoDraw(True)
                    
                    # if momentary_arousal_slider is active this frame...
                    if momentary_arousal_slider.status == STARTED:
                        # update params
                        pass
                    
                    # *momentary_alert_txt* updates
                    
                    # if momentary_alert_txt is starting this frame...
                    if momentary_alert_txt.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                        # keep track of start time/frame for later
                        momentary_alert_txt.frameNStart = frameN  # exact frame index
                        momentary_alert_txt.tStart = t  # local t and not account for scr refresh
                        momentary_alert_txt.tStartRefresh = tThisFlipGlobal  # on global time
                        win.timeOnFlip(momentary_alert_txt, 'tStartRefresh')  # time at next scr refresh
                        # add timestamp to datafile
                        thisExp.timestampOnFlip(win, 'momentary_alert_txt.started')
                        # update status
                        momentary_alert_txt.status = STARTED
                        momentary_alert_txt.setAutoDraw(True)
                    
                    # if momentary_alert_txt is active this frame...
                    if momentary_alert_txt.status == STARTED:
                        # update params
                        pass
                    
                    # *momentary_not_alert_txt* updates
                    
                    # if momentary_not_alert_txt is starting this frame...
                    if momentary_not_alert_txt.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                        # keep track of start time/frame for later
                        momentary_not_alert_txt.frameNStart = frameN  # exact frame index
                        momentary_not_alert_txt.tStart = t  # local t and not account for scr refresh
                        momentary_not_alert_txt.tStartRefresh = tThisFlipGlobal  # on global time
                        win.timeOnFlip(momentary_not_alert_txt, 'tStartRefresh')  # time at next scr refresh
                        # add timestamp to datafile
                        thisExp.timestampOnFlip(win, 'momentary_not_alert_txt.started')
                        # update status
                        momentary_not_alert_txt.status = STARTED
                        momentary_not_alert_txt.setAutoDraw(True)
                    
                    # if momentary_not_alert_txt is active this frame...
                    if momentary_not_alert_txt.status == STARTED:
                        # update params
                        pass
                    
                    # *mouse_instruct_txt_1* updates
                    
                    # if mouse_instruct_txt_1 is starting this frame...
                    if mouse_instruct_txt_1.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                        # keep track of start time/frame for later
                        mouse_instruct_txt_1.frameNStart = frameN  # exact frame index
                        mouse_instruct_txt_1.tStart = t  # local t and not account for scr refresh
                        mouse_instruct_txt_1.tStartRefresh = tThisFlipGlobal  # on global time
                        win.timeOnFlip(mouse_instruct_txt_1, 'tStartRefresh')  # time at next scr refresh
                        # add timestamp to datafile
                        thisExp.timestampOnFlip(win, 'mouse_instruct_txt_1.started')
                        # update status
                        mouse_instruct_txt_1.status = STARTED
                        mouse_instruct_txt_1.setAutoDraw(True)
                    
                    # if mouse_instruct_txt_1 is active this frame...
                    if mouse_instruct_txt_1.status == STARTED:
                        # update params
                        pass
                    
                    # check for quit (typically the Esc key)
                    if defaultKeyboard.getKeys(keyList=["escape"]):
                        thisExp.status = FINISHED
                    if thisExp.status == FINISHED or endExpNow:
                        endExperiment(thisExp, win=win)
                        return
                    # pause experiment here if requested
                    if thisExp.status == PAUSED:
                        pauseExperiment(
                            thisExp=thisExp, 
                            win=win, 
                            timers=[routineTimer, globalClock], 
                            currentRoutine=momentary_arousal_rating,
                        )
                        # skip the frame we paused on
                        continue
                    
                    # has a Component requested the Routine to end?
                    if not continueRoutine:
                        momentary_arousal_rating.forceEnded = routineForceEnded = True
                    # has the Routine been forcibly ended?
                    if momentary_arousal_rating.forceEnded or routineForceEnded:
                        break
                    # has every Component finished?
                    continueRoutine = False
                    for thisComponent in momentary_arousal_rating.components:
                        if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                            continueRoutine = True
                            break  # at least one component has not yet finished
                    
                    # refresh the screen
                    if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                        win.flip()
                
                # --- Ending Routine "momentary_arousal_rating" ---
                for thisComponent in momentary_arousal_rating.components:
                    if hasattr(thisComponent, "setAutoDraw"):
                        thisComponent.setAutoDraw(False)
                # store stop times for momentary_arousal_rating
                momentary_arousal_rating.tStop = globalClock.getTime(format='float')
                momentary_arousal_rating.tStopRefresh = tThisFlipGlobal
                thisExp.addData('momentary_arousal_rating.stopped', momentary_arousal_rating.tStop)
                # Run 'End Routine' code from momentary_arousal_rating_code_B
                thisExp.addData('condition', condition)
                # store data for post_emotion_induction_ratings (TrialHandler)
                post_emotion_induction_ratings.addData('momentary_arousal_mouse.x', momentary_arousal_mouse.x)
                post_emotion_induction_ratings.addData('momentary_arousal_mouse.y', momentary_arousal_mouse.y)
                post_emotion_induction_ratings.addData('momentary_arousal_mouse.leftButton', momentary_arousal_mouse.leftButton)
                post_emotion_induction_ratings.addData('momentary_arousal_mouse.midButton', momentary_arousal_mouse.midButton)
                post_emotion_induction_ratings.addData('momentary_arousal_mouse.rightButton', momentary_arousal_mouse.rightButton)
                post_emotion_induction_ratings.addData('momentary_arousal_mouse.time', momentary_arousal_mouse.time)
                post_emotion_induction_ratings.addData('momentary_arousal_slider.response', momentary_arousal_slider.getRating())
                post_emotion_induction_ratings.addData('momentary_arousal_slider.rt', momentary_arousal_slider.getRT())
                # the Routine "momentary_arousal_rating" was not non-slip safe, so reset the non-slip timer
                routineTimer.reset()
                
                # --- Prepare to start Routine "momentary_valence_rating_B" ---
                # create an object to store info about Routine momentary_valence_rating_B
                momentary_valence_rating_B = data.Routine(
                    name='momentary_valence_rating_B',
                    components=[momentary_valence_mouse_B, momentary_valence_question_txt_B, momentary_valence_slider_B, momentary_pleasant_txt_B, momentary_unpleasant_txt_B, mouse_instruct_txt_2],
                )
                momentary_valence_rating_B.status = NOT_STARTED
                continueRoutine = True
                # update component parameters for each repeat
                # Run 'Begin Routine' code from momentary_valence_rating_code_B
                momentary_valence_mouse_B.setVisible(True)
                timer = None
                
                condition = stim_condition
                
                # determine which slider will appear first
                if rating_order == 'valence_first':
                    continueRoutine = False
                # setup some python lists for storing info about the momentary_valence_mouse_B
                momentary_valence_mouse_B.x = []
                momentary_valence_mouse_B.y = []
                momentary_valence_mouse_B.leftButton = []
                momentary_valence_mouse_B.midButton = []
                momentary_valence_mouse_B.rightButton = []
                momentary_valence_mouse_B.time = []
                gotValidClick = False  # until a click is received
                momentary_valence_slider_B.reset()
                momentary_valence_slider_B.setPos((0,0))
                momentary_pleasant_txt_B.setPos((0.5, -0.05))
                momentary_unpleasant_txt_B.setPos((-0.5, -0.05))
                # store start times for momentary_valence_rating_B
                momentary_valence_rating_B.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
                momentary_valence_rating_B.tStart = globalClock.getTime(format='float')
                momentary_valence_rating_B.status = STARTED
                thisExp.addData('momentary_valence_rating_B.started', momentary_valence_rating_B.tStart)
                momentary_valence_rating_B.maxDuration = None
                # keep track of which components have finished
                momentary_valence_rating_BComponents = momentary_valence_rating_B.components
                for thisComponent in momentary_valence_rating_B.components:
                    thisComponent.tStart = None
                    thisComponent.tStop = None
                    thisComponent.tStartRefresh = None
                    thisComponent.tStopRefresh = None
                    if hasattr(thisComponent, 'status'):
                        thisComponent.status = NOT_STARTED
                # reset timers
                t = 0
                _timeToFirstFrame = win.getFutureFlipTime(clock="now")
                frameN = -1
                
                # --- Run Routine "momentary_valence_rating_B" ---
                thisExp.currentRoutine = momentary_valence_rating_B
                momentary_valence_rating_B.forceEnded = routineForceEnded = not continueRoutine
                while continueRoutine:
                    # if trial has changed, end Routine now
                    if hasattr(thisPost_emotion_induction_rating, 'status') and thisPost_emotion_induction_rating.status == STOPPING:
                        continueRoutine = False
                    # get current time
                    t = routineTimer.getTime()
                    tThisFlip = win.getFutureFlipTime(clock=routineTimer)
                    tThisFlipGlobal = win.getFutureFlipTime(clock=None)
                    frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
                    # update/draw components on each frame
                    # Run 'Each Frame' code from momentary_valence_rating_code_B
                    if momentary_valence_slider_B.getRating() is not None:
                    
                        if timer is None:
                            timer = core.CountdownTimer(2)
                    
                        if timer.getTime() < 0:
                            continueRoutine = False
                    # *momentary_valence_mouse_B* updates
                    
                    # if momentary_valence_mouse_B is starting this frame...
                    if momentary_valence_mouse_B.status == NOT_STARTED and t >= 0.0-frameTolerance:
                        # keep track of start time/frame for later
                        momentary_valence_mouse_B.frameNStart = frameN  # exact frame index
                        momentary_valence_mouse_B.tStart = t  # local t and not account for scr refresh
                        momentary_valence_mouse_B.tStartRefresh = tThisFlipGlobal  # on global time
                        win.timeOnFlip(momentary_valence_mouse_B, 'tStartRefresh')  # time at next scr refresh
                        # add timestamp to datafile
                        thisExp.addData('momentary_valence_mouse_B.started', t)
                        # update status
                        momentary_valence_mouse_B.status = STARTED
                        momentary_valence_mouse_B.mouseClock.reset()
                        prevButtonState = momentary_valence_mouse_B.getPressed()  # if button is down already this ISN'T a new click
                    if momentary_valence_mouse_B.status == STARTED:  # only update if started and not finished!
                        buttons = momentary_valence_mouse_B.getPressed()
                        if buttons != prevButtonState:  # button state changed?
                            prevButtonState = buttons
                            if sum(buttons) > 0:  # state changed to a new click
                                pass
                                x, y = momentary_valence_mouse_B.getPos()
                                momentary_valence_mouse_B.x.append(float(x))
                                momentary_valence_mouse_B.y.append(float(y))
                                buttons = momentary_valence_mouse_B.getPressed()
                                momentary_valence_mouse_B.leftButton.append(buttons[0])
                                momentary_valence_mouse_B.midButton.append(buttons[1])
                                momentary_valence_mouse_B.rightButton.append(buttons[2])
                                momentary_valence_mouse_B.time.append(momentary_valence_mouse_B.mouseClock.getTime())
                    
                    # *momentary_valence_question_txt_B* updates
                    
                    # if momentary_valence_question_txt_B is starting this frame...
                    if momentary_valence_question_txt_B.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                        # keep track of start time/frame for later
                        momentary_valence_question_txt_B.frameNStart = frameN  # exact frame index
                        momentary_valence_question_txt_B.tStart = t  # local t and not account for scr refresh
                        momentary_valence_question_txt_B.tStartRefresh = tThisFlipGlobal  # on global time
                        win.timeOnFlip(momentary_valence_question_txt_B, 'tStartRefresh')  # time at next scr refresh
                        # add timestamp to datafile
                        thisExp.timestampOnFlip(win, 'momentary_valence_question_txt_B.started')
                        # update status
                        momentary_valence_question_txt_B.status = STARTED
                        momentary_valence_question_txt_B.setAutoDraw(True)
                    
                    # if momentary_valence_question_txt_B is active this frame...
                    if momentary_valence_question_txt_B.status == STARTED:
                        # update params
                        pass
                    
                    # *momentary_valence_slider_B* updates
                    
                    # if momentary_valence_slider_B is starting this frame...
                    if momentary_valence_slider_B.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                        # keep track of start time/frame for later
                        momentary_valence_slider_B.frameNStart = frameN  # exact frame index
                        momentary_valence_slider_B.tStart = t  # local t and not account for scr refresh
                        momentary_valence_slider_B.tStartRefresh = tThisFlipGlobal  # on global time
                        win.timeOnFlip(momentary_valence_slider_B, 'tStartRefresh')  # time at next scr refresh
                        # add timestamp to datafile
                        thisExp.timestampOnFlip(win, 'momentary_valence_slider_B.started')
                        # update status
                        momentary_valence_slider_B.status = STARTED
                        momentary_valence_slider_B.setAutoDraw(True)
                    
                    # if momentary_valence_slider_B is active this frame...
                    if momentary_valence_slider_B.status == STARTED:
                        # update params
                        pass
                    
                    # *momentary_pleasant_txt_B* updates
                    
                    # if momentary_pleasant_txt_B is starting this frame...
                    if momentary_pleasant_txt_B.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                        # keep track of start time/frame for later
                        momentary_pleasant_txt_B.frameNStart = frameN  # exact frame index
                        momentary_pleasant_txt_B.tStart = t  # local t and not account for scr refresh
                        momentary_pleasant_txt_B.tStartRefresh = tThisFlipGlobal  # on global time
                        win.timeOnFlip(momentary_pleasant_txt_B, 'tStartRefresh')  # time at next scr refresh
                        # add timestamp to datafile
                        thisExp.timestampOnFlip(win, 'momentary_pleasant_txt_B.started')
                        # update status
                        momentary_pleasant_txt_B.status = STARTED
                        momentary_pleasant_txt_B.setAutoDraw(True)
                    
                    # if momentary_pleasant_txt_B is active this frame...
                    if momentary_pleasant_txt_B.status == STARTED:
                        # update params
                        pass
                    
                    # *momentary_unpleasant_txt_B* updates
                    
                    # if momentary_unpleasant_txt_B is starting this frame...
                    if momentary_unpleasant_txt_B.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                        # keep track of start time/frame for later
                        momentary_unpleasant_txt_B.frameNStart = frameN  # exact frame index
                        momentary_unpleasant_txt_B.tStart = t  # local t and not account for scr refresh
                        momentary_unpleasant_txt_B.tStartRefresh = tThisFlipGlobal  # on global time
                        win.timeOnFlip(momentary_unpleasant_txt_B, 'tStartRefresh')  # time at next scr refresh
                        # add timestamp to datafile
                        thisExp.timestampOnFlip(win, 'momentary_unpleasant_txt_B.started')
                        # update status
                        momentary_unpleasant_txt_B.status = STARTED
                        momentary_unpleasant_txt_B.setAutoDraw(True)
                    
                    # if momentary_unpleasant_txt_B is active this frame...
                    if momentary_unpleasant_txt_B.status == STARTED:
                        # update params
                        pass
                    
                    # *mouse_instruct_txt_2* updates
                    
                    # if mouse_instruct_txt_2 is starting this frame...
                    if mouse_instruct_txt_2.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                        # keep track of start time/frame for later
                        mouse_instruct_txt_2.frameNStart = frameN  # exact frame index
                        mouse_instruct_txt_2.tStart = t  # local t and not account for scr refresh
                        mouse_instruct_txt_2.tStartRefresh = tThisFlipGlobal  # on global time
                        win.timeOnFlip(mouse_instruct_txt_2, 'tStartRefresh')  # time at next scr refresh
                        # add timestamp to datafile
                        thisExp.timestampOnFlip(win, 'mouse_instruct_txt_2.started')
                        # update status
                        mouse_instruct_txt_2.status = STARTED
                        mouse_instruct_txt_2.setAutoDraw(True)
                    
                    # if mouse_instruct_txt_2 is active this frame...
                    if mouse_instruct_txt_2.status == STARTED:
                        # update params
                        pass
                    
                    # check for quit (typically the Esc key)
                    if defaultKeyboard.getKeys(keyList=["escape"]):
                        thisExp.status = FINISHED
                    if thisExp.status == FINISHED or endExpNow:
                        endExperiment(thisExp, win=win)
                        return
                    # pause experiment here if requested
                    if thisExp.status == PAUSED:
                        pauseExperiment(
                            thisExp=thisExp, 
                            win=win, 
                            timers=[routineTimer, globalClock], 
                            currentRoutine=momentary_valence_rating_B,
                        )
                        # skip the frame we paused on
                        continue
                    
                    # has a Component requested the Routine to end?
                    if not continueRoutine:
                        momentary_valence_rating_B.forceEnded = routineForceEnded = True
                    # has the Routine been forcibly ended?
                    if momentary_valence_rating_B.forceEnded or routineForceEnded:
                        break
                    # has every Component finished?
                    continueRoutine = False
                    for thisComponent in momentary_valence_rating_B.components:
                        if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                            continueRoutine = True
                            break  # at least one component has not yet finished
                    
                    # refresh the screen
                    if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                        win.flip()
                
                # --- Ending Routine "momentary_valence_rating_B" ---
                for thisComponent in momentary_valence_rating_B.components:
                    if hasattr(thisComponent, "setAutoDraw"):
                        thisComponent.setAutoDraw(False)
                # store stop times for momentary_valence_rating_B
                momentary_valence_rating_B.tStop = globalClock.getTime(format='float')
                momentary_valence_rating_B.tStopRefresh = tThisFlipGlobal
                thisExp.addData('momentary_valence_rating_B.stopped', momentary_valence_rating_B.tStop)
                # Run 'End Routine' code from momentary_valence_rating_code_B
                momentary_valence_mouse_B.setVisible(False)
                
                thisExp.addData('condition', condition)
                # store data for post_emotion_induction_ratings (TrialHandler)
                post_emotion_induction_ratings.addData('momentary_valence_mouse_B.x', momentary_valence_mouse_B.x)
                post_emotion_induction_ratings.addData('momentary_valence_mouse_B.y', momentary_valence_mouse_B.y)
                post_emotion_induction_ratings.addData('momentary_valence_mouse_B.leftButton', momentary_valence_mouse_B.leftButton)
                post_emotion_induction_ratings.addData('momentary_valence_mouse_B.midButton', momentary_valence_mouse_B.midButton)
                post_emotion_induction_ratings.addData('momentary_valence_mouse_B.rightButton', momentary_valence_mouse_B.rightButton)
                post_emotion_induction_ratings.addData('momentary_valence_mouse_B.time', momentary_valence_mouse_B.time)
                post_emotion_induction_ratings.addData('momentary_valence_slider_B.response', momentary_valence_slider_B.getRating())
                post_emotion_induction_ratings.addData('momentary_valence_slider_B.rt', momentary_valence_slider_B.getRT())
                # the Routine "momentary_valence_rating_B" was not non-slip safe, so reset the non-slip timer
                routineTimer.reset()
                # mark thisPost_emotion_induction_rating as finished
                if hasattr(thisPost_emotion_induction_rating, 'status'):
                    thisPost_emotion_induction_rating.status = FINISHED
                # if awaiting a pause, pause now
                if post_emotion_induction_ratings.status == PAUSED:
                    thisExp.status = PAUSED
                    pauseExperiment(
                        thisExp=thisExp, 
                        win=win, 
                        timers=[globalClock], 
                    )
                    # once done pausing, restore running status
                    post_emotion_induction_ratings.status = STARTED
                thisExp.nextEntry()
                
            # completed 1.0 repeats of 'post_emotion_induction_ratings'
            post_emotion_induction_ratings.status = FINISHED
            
            if thisSession is not None:
                # if running in a Session with a Liaison client, send data up to now
                thisSession.sendExperimentData()
            # mark thisStim_block_and_rating as finished
            if hasattr(thisStim_block_and_rating, 'status'):
                thisStim_block_and_rating.status = FINISHED
            # if awaiting a pause, pause now
            if stim_block_and_ratings.status == PAUSED:
                thisExp.status = PAUSED
                pauseExperiment(
                    thisExp=thisExp, 
                    win=win, 
                    timers=[globalClock], 
                )
                # once done pausing, restore running status
                stim_block_and_ratings.status = STARTED
            thisExp.nextEntry()
            
        # completed 1.0 repeats of 'stim_block_and_ratings'
        stim_block_and_ratings.status = FINISHED
        
        if thisSession is not None:
            # if running in a Session with a Liaison client, send data up to now
            thisSession.sendExperimentData()
        
        # --- Prepare to start Routine "baseline_instruct" ---
        # create an object to store info about Routine baseline_instruct
        baseline_instruct = data.Routine(
            name='baseline_instruct',
            components=[baseline_instruct_txt],
        )
        baseline_instruct.status = NOT_STARTED
        continueRoutine = True
        # update component parameters for each repeat
        # store start times for baseline_instruct
        baseline_instruct.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
        baseline_instruct.tStart = globalClock.getTime(format='float')
        baseline_instruct.status = STARTED
        thisExp.addData('baseline_instruct.started', baseline_instruct.tStart)
        baseline_instruct.maxDuration = None
        # keep track of which components have finished
        baseline_instructComponents = baseline_instruct.components
        for thisComponent in baseline_instruct.components:
            thisComponent.tStart = None
            thisComponent.tStop = None
            thisComponent.tStartRefresh = None
            thisComponent.tStopRefresh = None
            if hasattr(thisComponent, 'status'):
                thisComponent.status = NOT_STARTED
        # reset timers
        t = 0
        _timeToFirstFrame = win.getFutureFlipTime(clock="now")
        frameN = -1
        
        # --- Run Routine "baseline_instruct" ---
        thisExp.currentRoutine = baseline_instruct
        baseline_instruct.forceEnded = routineForceEnded = not continueRoutine
        while continueRoutine and routineTimer.getTime() < 8.0:
            # if trial has changed, end Routine now
            if hasattr(thisExperimental_condition, 'status') and thisExperimental_condition.status == STOPPING:
                continueRoutine = False
            # get current time
            t = routineTimer.getTime()
            tThisFlip = win.getFutureFlipTime(clock=routineTimer)
            tThisFlipGlobal = win.getFutureFlipTime(clock=None)
            frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
            # update/draw components on each frame
            
            # *baseline_instruct_txt* updates
            
            # if baseline_instruct_txt is starting this frame...
            if baseline_instruct_txt.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                baseline_instruct_txt.frameNStart = frameN  # exact frame index
                baseline_instruct_txt.tStart = t  # local t and not account for scr refresh
                baseline_instruct_txt.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(baseline_instruct_txt, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'baseline_instruct_txt.started')
                # update status
                baseline_instruct_txt.status = STARTED
                baseline_instruct_txt.setAutoDraw(True)
            
            # if baseline_instruct_txt is active this frame...
            if baseline_instruct_txt.status == STARTED:
                # update params
                pass
            
            # if baseline_instruct_txt is stopping this frame...
            if baseline_instruct_txt.status == STARTED:
                # is it time to stop? (based on global clock, using actual start)
                if tThisFlipGlobal > baseline_instruct_txt.tStartRefresh + 8-frameTolerance:
                    # keep track of stop time/frame for later
                    baseline_instruct_txt.tStop = t  # not accounting for scr refresh
                    baseline_instruct_txt.tStopRefresh = tThisFlipGlobal  # on global time
                    baseline_instruct_txt.frameNStop = frameN  # exact frame index
                    # add timestamp to datafile
                    thisExp.timestampOnFlip(win, 'baseline_instruct_txt.stopped')
                    # update status
                    baseline_instruct_txt.status = FINISHED
                    baseline_instruct_txt.setAutoDraw(False)
            
            # check for quit (typically the Esc key)
            if defaultKeyboard.getKeys(keyList=["escape"]):
                thisExp.status = FINISHED
            if thisExp.status == FINISHED or endExpNow:
                endExperiment(thisExp, win=win)
                return
            # pause experiment here if requested
            if thisExp.status == PAUSED:
                pauseExperiment(
                    thisExp=thisExp, 
                    win=win, 
                    timers=[routineTimer, globalClock], 
                    currentRoutine=baseline_instruct,
                )
                # skip the frame we paused on
                continue
            
            # has a Component requested the Routine to end?
            if not continueRoutine:
                baseline_instruct.forceEnded = routineForceEnded = True
            # has the Routine been forcibly ended?
            if baseline_instruct.forceEnded or routineForceEnded:
                break
            # has every Component finished?
            continueRoutine = False
            for thisComponent in baseline_instruct.components:
                if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                    continueRoutine = True
                    break  # at least one component has not yet finished
            
            # refresh the screen
            if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                win.flip()
        
        # --- Ending Routine "baseline_instruct" ---
        for thisComponent in baseline_instruct.components:
            if hasattr(thisComponent, "setAutoDraw"):
                thisComponent.setAutoDraw(False)
        # store stop times for baseline_instruct
        baseline_instruct.tStop = globalClock.getTime(format='float')
        baseline_instruct.tStopRefresh = tThisFlipGlobal
        thisExp.addData('baseline_instruct.stopped', baseline_instruct.tStop)
        # using non-slip timing so subtract the expected duration of this Routine (unless ended on request)
        if baseline_instruct.maxDurationReached:
            routineTimer.addTime(-baseline_instruct.maxDuration)
        elif baseline_instruct.forceEnded:
            routineTimer.reset()
        else:
            routineTimer.addTime(-8.000000)
        
        # --- Prepare to start Routine "stim_recovery" ---
        # create an object to store info about Routine stim_recovery
        stim_recovery = data.Routine(
            name='stim_recovery',
            components=[fixation_stim_recovery],
        )
        stim_recovery.status = NOT_STARTED
        continueRoutine = True
        # update component parameters for each repeat
        # Run 'Begin Routine' code from stim_recovery_trigger_code
        #----
        # Log time for camera
        # ---
        thisExp.addData('onset_wall', time.time())
        thisExp.addData('time_since_recording_start', time.time() - experiment_start_wall)
        
        stimulus_trigger_sent = False
        stimulus_trigger_cleared = False
        # store start times for stim_recovery
        stim_recovery.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
        stim_recovery.tStart = globalClock.getTime(format='float')
        stim_recovery.status = STARTED
        thisExp.addData('stim_recovery.started', stim_recovery.tStart)
        stim_recovery.maxDuration = None
        # keep track of which components have finished
        stim_recoveryComponents = stim_recovery.components
        for thisComponent in stim_recovery.components:
            thisComponent.tStart = None
            thisComponent.tStop = None
            thisComponent.tStartRefresh = None
            thisComponent.tStopRefresh = None
            if hasattr(thisComponent, 'status'):
                thisComponent.status = NOT_STARTED
        # reset timers
        t = 0
        _timeToFirstFrame = win.getFutureFlipTime(clock="now")
        frameN = -1
        
        # --- Run Routine "stim_recovery" ---
        thisExp.currentRoutine = stim_recovery
        stim_recovery.forceEnded = routineForceEnded = not continueRoutine
        while continueRoutine:
            # if trial has changed, end Routine now
            if hasattr(thisExperimental_condition, 'status') and thisExperimental_condition.status == STOPPING:
                continueRoutine = False
            # get current time
            t = routineTimer.getTime()
            tThisFlip = win.getFutureFlipTime(clock=routineTimer)
            tThisFlipGlobal = win.getFutureFlipTime(clock=None)
            frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
            # update/draw components on each frame
            
            # *fixation_stim_recovery* updates
            
            # if fixation_stim_recovery is starting this frame...
            if fixation_stim_recovery.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                fixation_stim_recovery.frameNStart = frameN  # exact frame index
                fixation_stim_recovery.tStart = t  # local t and not account for scr refresh
                fixation_stim_recovery.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(fixation_stim_recovery, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'fixation_stim_recovery.started')
                # update status
                fixation_stim_recovery.status = STARTED
                fixation_stim_recovery.setAutoDraw(True)
            
            # if fixation_stim_recovery is active this frame...
            if fixation_stim_recovery.status == STARTED:
                # update params
                pass
            
            # if fixation_stim_recovery is stopping this frame...
            if fixation_stim_recovery.status == STARTED:
                # is it time to stop? (based on global clock, using actual start)
                if tThisFlipGlobal > fixation_stim_recovery.tStartRefresh + recovery_duration-frameTolerance:
                    # keep track of stop time/frame for later
                    fixation_stim_recovery.tStop = t  # not accounting for scr refresh
                    fixation_stim_recovery.tStopRefresh = tThisFlipGlobal  # on global time
                    fixation_stim_recovery.frameNStop = frameN  # exact frame index
                    # add timestamp to datafile
                    thisExp.timestampOnFlip(win, 'fixation_stim_recovery.stopped')
                    # update status
                    fixation_stim_recovery.status = FINISHED
                    fixation_stim_recovery.setAutoDraw(False)
            # Run 'Each Frame' code from stim_recovery_trigger_code
            # Send triggers
            if condition == 'negative' or stim_condition == 'negative':
                trigger = neg_stim_recovery_trigger
            elif condition == 'positive' or stim_condition == 'positive':
                trigger = pos_stim_recovery_trigger
            
            if fixation_stim_recovery.status == STARTED and not stimulus_trigger_sent:
                win.callOnFlip(ser.write, str.encode(trigger))
                stimulus_trigger_sent = True
            
            if fixation_stim_recovery.status == FINISHED and not stimulus_trigger_cleared:
                win.callOnFlip(ser.write, str.encode('00'))
                ser.write('RR'.encode('utf-8'))
                stimulus_trigger_cleared = True
            
            # check for quit (typically the Esc key)
            if defaultKeyboard.getKeys(keyList=["escape"]):
                thisExp.status = FINISHED
            if thisExp.status == FINISHED or endExpNow:
                endExperiment(thisExp, win=win)
                return
            # pause experiment here if requested
            if thisExp.status == PAUSED:
                pauseExperiment(
                    thisExp=thisExp, 
                    win=win, 
                    timers=[routineTimer, globalClock], 
                    currentRoutine=stim_recovery,
                )
                # skip the frame we paused on
                continue
            
            # has a Component requested the Routine to end?
            if not continueRoutine:
                stim_recovery.forceEnded = routineForceEnded = True
            # has the Routine been forcibly ended?
            if stim_recovery.forceEnded or routineForceEnded:
                break
            # has every Component finished?
            continueRoutine = False
            for thisComponent in stim_recovery.components:
                if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                    continueRoutine = True
                    break  # at least one component has not yet finished
            
            # refresh the screen
            if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                win.flip()
        
        # --- Ending Routine "stim_recovery" ---
        for thisComponent in stim_recovery.components:
            if hasattr(thisComponent, "setAutoDraw"):
                thisComponent.setAutoDraw(False)
        # store stop times for stim_recovery
        stim_recovery.tStop = globalClock.getTime(format='float')
        stim_recovery.tStopRefresh = tThisFlipGlobal
        thisExp.addData('stim_recovery.stopped', stim_recovery.tStop)
        # Run 'End Routine' code from stim_recovery_trigger_code
        ser.write ('RR'.encode('utf-8'))
        # the Routine "stim_recovery" was not non-slip safe, so reset the non-slip timer
        routineTimer.reset()
        
        # set up handler to look after randomisation of conditions etc
        post_emotion_recovery_ratings = data.TrialHandler2(
            name='post_emotion_recovery_ratings',
            nReps=1.0, 
            method='random', 
            extraInfo=expInfo, 
            originPath=-1, 
            trialList=[None], 
            seed=None, 
            isTrials=True, 
        )
        thisExp.addLoop(post_emotion_recovery_ratings)  # add the loop to the experiment
        thisPost_emotion_recovery_rating = post_emotion_recovery_ratings.trialList[0]  # so we can initialise stimuli with some values
        # abbreviate parameter names if possible (e.g. rgb = thisPost_emotion_recovery_rating.rgb)
        if thisPost_emotion_recovery_rating != None:
            for paramName in thisPost_emotion_recovery_rating:
                globals()[paramName] = thisPost_emotion_recovery_rating[paramName]
        if thisSession is not None:
            # if running in a Session with a Liaison client, send data up to now
            thisSession.sendExperimentData()
        
        for thisPost_emotion_recovery_rating in post_emotion_recovery_ratings:
            post_emotion_recovery_ratings.status = STARTED
            if hasattr(thisPost_emotion_recovery_rating, 'status'):
                thisPost_emotion_recovery_rating.status = STARTED
            currentLoop = post_emotion_recovery_ratings
            thisExp.timestampOnFlip(win, 'thisRow.t', format=globalClock.format)
            if thisSession is not None:
                # if running in a Session with a Liaison client, send data up to now
                thisSession.sendExperimentData()
            # abbreviate parameter names if possible (e.g. rgb = thisPost_emotion_recovery_rating.rgb)
            if thisPost_emotion_recovery_rating != None:
                for paramName in thisPost_emotion_recovery_rating:
                    globals()[paramName] = thisPost_emotion_recovery_rating[paramName]
            
            # --- Prepare to start Routine "momentary_valence_rating_A" ---
            # create an object to store info about Routine momentary_valence_rating_A
            momentary_valence_rating_A = data.Routine(
                name='momentary_valence_rating_A',
                components=[momentary_valence_mouse_A, momentary_valence_question_txt_A, momentary_valence_slider_A, momentary_pleasant_txt_A, momentary_unpleasant_txt_A, mouse_instuct_txt],
            )
            momentary_valence_rating_A.status = NOT_STARTED
            continueRoutine = True
            # update component parameters for each repeat
            # Run 'Begin Routine' code from momentary_valence_rating_code_A
            momentary_valence_mouse_A.setVisible(True)
            timer = None
            
            condition = stim_condition
            
            # determine which slider will appear first
            rating_pair_count += 1
            if rating_pair_count % 2 == 1:
                rating_order = rating_start
            else:
                rating_order = 'arousal_first' if rating_start == 'valence_first' else 'valence_first'
            
            if rating_order == 'arousal_first':
                continueRoutine = False
            # setup some python lists for storing info about the momentary_valence_mouse_A
            momentary_valence_mouse_A.x = []
            momentary_valence_mouse_A.y = []
            momentary_valence_mouse_A.leftButton = []
            momentary_valence_mouse_A.midButton = []
            momentary_valence_mouse_A.rightButton = []
            momentary_valence_mouse_A.time = []
            gotValidClick = False  # until a click is received
            momentary_valence_slider_A.reset()
            momentary_valence_slider_A.setPos((0,0))
            momentary_pleasant_txt_A.setPos((0.5, -0.05))
            momentary_unpleasant_txt_A.setPos((-0.5, -0.05))
            # store start times for momentary_valence_rating_A
            momentary_valence_rating_A.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
            momentary_valence_rating_A.tStart = globalClock.getTime(format='float')
            momentary_valence_rating_A.status = STARTED
            thisExp.addData('momentary_valence_rating_A.started', momentary_valence_rating_A.tStart)
            momentary_valence_rating_A.maxDuration = None
            # keep track of which components have finished
            momentary_valence_rating_AComponents = momentary_valence_rating_A.components
            for thisComponent in momentary_valence_rating_A.components:
                thisComponent.tStart = None
                thisComponent.tStop = None
                thisComponent.tStartRefresh = None
                thisComponent.tStopRefresh = None
                if hasattr(thisComponent, 'status'):
                    thisComponent.status = NOT_STARTED
            # reset timers
            t = 0
            _timeToFirstFrame = win.getFutureFlipTime(clock="now")
            frameN = -1
            
            # --- Run Routine "momentary_valence_rating_A" ---
            thisExp.currentRoutine = momentary_valence_rating_A
            momentary_valence_rating_A.forceEnded = routineForceEnded = not continueRoutine
            while continueRoutine:
                # if trial has changed, end Routine now
                if hasattr(thisPost_emotion_recovery_rating, 'status') and thisPost_emotion_recovery_rating.status == STOPPING:
                    continueRoutine = False
                # get current time
                t = routineTimer.getTime()
                tThisFlip = win.getFutureFlipTime(clock=routineTimer)
                tThisFlipGlobal = win.getFutureFlipTime(clock=None)
                frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
                # update/draw components on each frame
                # Run 'Each Frame' code from momentary_valence_rating_code_A
                if momentary_valence_slider_A.getRating() is not None:
                
                    if timer is None:
                        timer = core.CountdownTimer(2)
                
                    if timer.getTime() < 0:
                        continueRoutine = False
                # *momentary_valence_mouse_A* updates
                
                # if momentary_valence_mouse_A is starting this frame...
                if momentary_valence_mouse_A.status == NOT_STARTED and t >= 0.0-frameTolerance:
                    # keep track of start time/frame for later
                    momentary_valence_mouse_A.frameNStart = frameN  # exact frame index
                    momentary_valence_mouse_A.tStart = t  # local t and not account for scr refresh
                    momentary_valence_mouse_A.tStartRefresh = tThisFlipGlobal  # on global time
                    win.timeOnFlip(momentary_valence_mouse_A, 'tStartRefresh')  # time at next scr refresh
                    # add timestamp to datafile
                    thisExp.addData('momentary_valence_mouse_A.started', t)
                    # update status
                    momentary_valence_mouse_A.status = STARTED
                    momentary_valence_mouse_A.mouseClock.reset()
                    prevButtonState = momentary_valence_mouse_A.getPressed()  # if button is down already this ISN'T a new click
                if momentary_valence_mouse_A.status == STARTED:  # only update if started and not finished!
                    buttons = momentary_valence_mouse_A.getPressed()
                    if buttons != prevButtonState:  # button state changed?
                        prevButtonState = buttons
                        if sum(buttons) > 0:  # state changed to a new click
                            pass
                            x, y = momentary_valence_mouse_A.getPos()
                            momentary_valence_mouse_A.x.append(float(x))
                            momentary_valence_mouse_A.y.append(float(y))
                            buttons = momentary_valence_mouse_A.getPressed()
                            momentary_valence_mouse_A.leftButton.append(buttons[0])
                            momentary_valence_mouse_A.midButton.append(buttons[1])
                            momentary_valence_mouse_A.rightButton.append(buttons[2])
                            momentary_valence_mouse_A.time.append(momentary_valence_mouse_A.mouseClock.getTime())
                
                # *momentary_valence_question_txt_A* updates
                
                # if momentary_valence_question_txt_A is starting this frame...
                if momentary_valence_question_txt_A.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                    # keep track of start time/frame for later
                    momentary_valence_question_txt_A.frameNStart = frameN  # exact frame index
                    momentary_valence_question_txt_A.tStart = t  # local t and not account for scr refresh
                    momentary_valence_question_txt_A.tStartRefresh = tThisFlipGlobal  # on global time
                    win.timeOnFlip(momentary_valence_question_txt_A, 'tStartRefresh')  # time at next scr refresh
                    # add timestamp to datafile
                    thisExp.timestampOnFlip(win, 'momentary_valence_question_txt_A.started')
                    # update status
                    momentary_valence_question_txt_A.status = STARTED
                    momentary_valence_question_txt_A.setAutoDraw(True)
                
                # if momentary_valence_question_txt_A is active this frame...
                if momentary_valence_question_txt_A.status == STARTED:
                    # update params
                    pass
                
                # *momentary_valence_slider_A* updates
                
                # if momentary_valence_slider_A is starting this frame...
                if momentary_valence_slider_A.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                    # keep track of start time/frame for later
                    momentary_valence_slider_A.frameNStart = frameN  # exact frame index
                    momentary_valence_slider_A.tStart = t  # local t and not account for scr refresh
                    momentary_valence_slider_A.tStartRefresh = tThisFlipGlobal  # on global time
                    win.timeOnFlip(momentary_valence_slider_A, 'tStartRefresh')  # time at next scr refresh
                    # add timestamp to datafile
                    thisExp.timestampOnFlip(win, 'momentary_valence_slider_A.started')
                    # update status
                    momentary_valence_slider_A.status = STARTED
                    momentary_valence_slider_A.setAutoDraw(True)
                
                # if momentary_valence_slider_A is active this frame...
                if momentary_valence_slider_A.status == STARTED:
                    # update params
                    pass
                
                # *momentary_pleasant_txt_A* updates
                
                # if momentary_pleasant_txt_A is starting this frame...
                if momentary_pleasant_txt_A.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                    # keep track of start time/frame for later
                    momentary_pleasant_txt_A.frameNStart = frameN  # exact frame index
                    momentary_pleasant_txt_A.tStart = t  # local t and not account for scr refresh
                    momentary_pleasant_txt_A.tStartRefresh = tThisFlipGlobal  # on global time
                    win.timeOnFlip(momentary_pleasant_txt_A, 'tStartRefresh')  # time at next scr refresh
                    # add timestamp to datafile
                    thisExp.timestampOnFlip(win, 'momentary_pleasant_txt_A.started')
                    # update status
                    momentary_pleasant_txt_A.status = STARTED
                    momentary_pleasant_txt_A.setAutoDraw(True)
                
                # if momentary_pleasant_txt_A is active this frame...
                if momentary_pleasant_txt_A.status == STARTED:
                    # update params
                    pass
                
                # *momentary_unpleasant_txt_A* updates
                
                # if momentary_unpleasant_txt_A is starting this frame...
                if momentary_unpleasant_txt_A.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                    # keep track of start time/frame for later
                    momentary_unpleasant_txt_A.frameNStart = frameN  # exact frame index
                    momentary_unpleasant_txt_A.tStart = t  # local t and not account for scr refresh
                    momentary_unpleasant_txt_A.tStartRefresh = tThisFlipGlobal  # on global time
                    win.timeOnFlip(momentary_unpleasant_txt_A, 'tStartRefresh')  # time at next scr refresh
                    # add timestamp to datafile
                    thisExp.timestampOnFlip(win, 'momentary_unpleasant_txt_A.started')
                    # update status
                    momentary_unpleasant_txt_A.status = STARTED
                    momentary_unpleasant_txt_A.setAutoDraw(True)
                
                # if momentary_unpleasant_txt_A is active this frame...
                if momentary_unpleasant_txt_A.status == STARTED:
                    # update params
                    pass
                
                # *mouse_instuct_txt* updates
                
                # if mouse_instuct_txt is starting this frame...
                if mouse_instuct_txt.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                    # keep track of start time/frame for later
                    mouse_instuct_txt.frameNStart = frameN  # exact frame index
                    mouse_instuct_txt.tStart = t  # local t and not account for scr refresh
                    mouse_instuct_txt.tStartRefresh = tThisFlipGlobal  # on global time
                    win.timeOnFlip(mouse_instuct_txt, 'tStartRefresh')  # time at next scr refresh
                    # add timestamp to datafile
                    thisExp.timestampOnFlip(win, 'mouse_instuct_txt.started')
                    # update status
                    mouse_instuct_txt.status = STARTED
                    mouse_instuct_txt.setAutoDraw(True)
                
                # if mouse_instuct_txt is active this frame...
                if mouse_instuct_txt.status == STARTED:
                    # update params
                    pass
                
                # check for quit (typically the Esc key)
                if defaultKeyboard.getKeys(keyList=["escape"]):
                    thisExp.status = FINISHED
                if thisExp.status == FINISHED or endExpNow:
                    endExperiment(thisExp, win=win)
                    return
                # pause experiment here if requested
                if thisExp.status == PAUSED:
                    pauseExperiment(
                        thisExp=thisExp, 
                        win=win, 
                        timers=[routineTimer, globalClock], 
                        currentRoutine=momentary_valence_rating_A,
                    )
                    # skip the frame we paused on
                    continue
                
                # has a Component requested the Routine to end?
                if not continueRoutine:
                    momentary_valence_rating_A.forceEnded = routineForceEnded = True
                # has the Routine been forcibly ended?
                if momentary_valence_rating_A.forceEnded or routineForceEnded:
                    break
                # has every Component finished?
                continueRoutine = False
                for thisComponent in momentary_valence_rating_A.components:
                    if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                        continueRoutine = True
                        break  # at least one component has not yet finished
                
                # refresh the screen
                if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                    win.flip()
            
            # --- Ending Routine "momentary_valence_rating_A" ---
            for thisComponent in momentary_valence_rating_A.components:
                if hasattr(thisComponent, "setAutoDraw"):
                    thisComponent.setAutoDraw(False)
            # store stop times for momentary_valence_rating_A
            momentary_valence_rating_A.tStop = globalClock.getTime(format='float')
            momentary_valence_rating_A.tStopRefresh = tThisFlipGlobal
            thisExp.addData('momentary_valence_rating_A.stopped', momentary_valence_rating_A.tStop)
            # Run 'End Routine' code from momentary_valence_rating_code_A
            momentary_valence_mouse_A.setVisible(False)
            
            thisExp.addData('condition', condition)
            # store data for post_emotion_recovery_ratings (TrialHandler)
            post_emotion_recovery_ratings.addData('momentary_valence_mouse_A.x', momentary_valence_mouse_A.x)
            post_emotion_recovery_ratings.addData('momentary_valence_mouse_A.y', momentary_valence_mouse_A.y)
            post_emotion_recovery_ratings.addData('momentary_valence_mouse_A.leftButton', momentary_valence_mouse_A.leftButton)
            post_emotion_recovery_ratings.addData('momentary_valence_mouse_A.midButton', momentary_valence_mouse_A.midButton)
            post_emotion_recovery_ratings.addData('momentary_valence_mouse_A.rightButton', momentary_valence_mouse_A.rightButton)
            post_emotion_recovery_ratings.addData('momentary_valence_mouse_A.time', momentary_valence_mouse_A.time)
            post_emotion_recovery_ratings.addData('momentary_valence_slider_A.response', momentary_valence_slider_A.getRating())
            post_emotion_recovery_ratings.addData('momentary_valence_slider_A.rt', momentary_valence_slider_A.getRT())
            # the Routine "momentary_valence_rating_A" was not non-slip safe, so reset the non-slip timer
            routineTimer.reset()
            
            # --- Prepare to start Routine "momentary_arousal_rating" ---
            # create an object to store info about Routine momentary_arousal_rating
            momentary_arousal_rating = data.Routine(
                name='momentary_arousal_rating',
                components=[momentary_arousal_mouse, momentary_arousal_question_txt, momentary_arousal_slider, momentary_alert_txt, momentary_not_alert_txt, mouse_instruct_txt_1],
            )
            momentary_arousal_rating.status = NOT_STARTED
            continueRoutine = True
            # update component parameters for each repeat
            # Run 'Begin Routine' code from momentary_arousal_rating_code_B
            momentary_arousal_mouse.setVisible(True)
            timer = None
            
            condition = stim_condition
            # setup some python lists for storing info about the momentary_arousal_mouse
            momentary_arousal_mouse.x = []
            momentary_arousal_mouse.y = []
            momentary_arousal_mouse.leftButton = []
            momentary_arousal_mouse.midButton = []
            momentary_arousal_mouse.rightButton = []
            momentary_arousal_mouse.time = []
            gotValidClick = False  # until a click is received
            momentary_arousal_slider.reset()
            momentary_arousal_slider.setPos((0,0))
            momentary_alert_txt.setPos((0.5, -0.05))
            momentary_not_alert_txt.setPos((-0.5, -0.05))
            # store start times for momentary_arousal_rating
            momentary_arousal_rating.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
            momentary_arousal_rating.tStart = globalClock.getTime(format='float')
            momentary_arousal_rating.status = STARTED
            thisExp.addData('momentary_arousal_rating.started', momentary_arousal_rating.tStart)
            momentary_arousal_rating.maxDuration = None
            # keep track of which components have finished
            momentary_arousal_ratingComponents = momentary_arousal_rating.components
            for thisComponent in momentary_arousal_rating.components:
                thisComponent.tStart = None
                thisComponent.tStop = None
                thisComponent.tStartRefresh = None
                thisComponent.tStopRefresh = None
                if hasattr(thisComponent, 'status'):
                    thisComponent.status = NOT_STARTED
            # reset timers
            t = 0
            _timeToFirstFrame = win.getFutureFlipTime(clock="now")
            frameN = -1
            
            # --- Run Routine "momentary_arousal_rating" ---
            thisExp.currentRoutine = momentary_arousal_rating
            momentary_arousal_rating.forceEnded = routineForceEnded = not continueRoutine
            while continueRoutine:
                # if trial has changed, end Routine now
                if hasattr(thisPost_emotion_recovery_rating, 'status') and thisPost_emotion_recovery_rating.status == STOPPING:
                    continueRoutine = False
                # get current time
                t = routineTimer.getTime()
                tThisFlip = win.getFutureFlipTime(clock=routineTimer)
                tThisFlipGlobal = win.getFutureFlipTime(clock=None)
                frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
                # update/draw components on each frame
                # Run 'Each Frame' code from momentary_arousal_rating_code_B
                if momentary_arousal_slider.getRating() is not None:
                
                    if timer is None:
                        timer = core.CountdownTimer(2)
                
                    if timer.getTime() < 0:
                        continueRoutine = False
                # *momentary_arousal_mouse* updates
                
                # if momentary_arousal_mouse is starting this frame...
                if momentary_arousal_mouse.status == NOT_STARTED and t >= 0.0-frameTolerance:
                    # keep track of start time/frame for later
                    momentary_arousal_mouse.frameNStart = frameN  # exact frame index
                    momentary_arousal_mouse.tStart = t  # local t and not account for scr refresh
                    momentary_arousal_mouse.tStartRefresh = tThisFlipGlobal  # on global time
                    win.timeOnFlip(momentary_arousal_mouse, 'tStartRefresh')  # time at next scr refresh
                    # add timestamp to datafile
                    thisExp.addData('momentary_arousal_mouse.started', t)
                    # update status
                    momentary_arousal_mouse.status = STARTED
                    momentary_arousal_mouse.mouseClock.reset()
                    prevButtonState = momentary_arousal_mouse.getPressed()  # if button is down already this ISN'T a new click
                if momentary_arousal_mouse.status == STARTED:  # only update if started and not finished!
                    buttons = momentary_arousal_mouse.getPressed()
                    if buttons != prevButtonState:  # button state changed?
                        prevButtonState = buttons
                        if sum(buttons) > 0:  # state changed to a new click
                            pass
                            x, y = momentary_arousal_mouse.getPos()
                            momentary_arousal_mouse.x.append(float(x))
                            momentary_arousal_mouse.y.append(float(y))
                            buttons = momentary_arousal_mouse.getPressed()
                            momentary_arousal_mouse.leftButton.append(buttons[0])
                            momentary_arousal_mouse.midButton.append(buttons[1])
                            momentary_arousal_mouse.rightButton.append(buttons[2])
                            momentary_arousal_mouse.time.append(momentary_arousal_mouse.mouseClock.getTime())
                
                # *momentary_arousal_question_txt* updates
                
                # if momentary_arousal_question_txt is starting this frame...
                if momentary_arousal_question_txt.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                    # keep track of start time/frame for later
                    momentary_arousal_question_txt.frameNStart = frameN  # exact frame index
                    momentary_arousal_question_txt.tStart = t  # local t and not account for scr refresh
                    momentary_arousal_question_txt.tStartRefresh = tThisFlipGlobal  # on global time
                    win.timeOnFlip(momentary_arousal_question_txt, 'tStartRefresh')  # time at next scr refresh
                    # add timestamp to datafile
                    thisExp.timestampOnFlip(win, 'momentary_arousal_question_txt.started')
                    # update status
                    momentary_arousal_question_txt.status = STARTED
                    momentary_arousal_question_txt.setAutoDraw(True)
                
                # if momentary_arousal_question_txt is active this frame...
                if momentary_arousal_question_txt.status == STARTED:
                    # update params
                    pass
                
                # *momentary_arousal_slider* updates
                
                # if momentary_arousal_slider is starting this frame...
                if momentary_arousal_slider.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                    # keep track of start time/frame for later
                    momentary_arousal_slider.frameNStart = frameN  # exact frame index
                    momentary_arousal_slider.tStart = t  # local t and not account for scr refresh
                    momentary_arousal_slider.tStartRefresh = tThisFlipGlobal  # on global time
                    win.timeOnFlip(momentary_arousal_slider, 'tStartRefresh')  # time at next scr refresh
                    # add timestamp to datafile
                    thisExp.timestampOnFlip(win, 'momentary_arousal_slider.started')
                    # update status
                    momentary_arousal_slider.status = STARTED
                    momentary_arousal_slider.setAutoDraw(True)
                
                # if momentary_arousal_slider is active this frame...
                if momentary_arousal_slider.status == STARTED:
                    # update params
                    pass
                
                # *momentary_alert_txt* updates
                
                # if momentary_alert_txt is starting this frame...
                if momentary_alert_txt.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                    # keep track of start time/frame for later
                    momentary_alert_txt.frameNStart = frameN  # exact frame index
                    momentary_alert_txt.tStart = t  # local t and not account for scr refresh
                    momentary_alert_txt.tStartRefresh = tThisFlipGlobal  # on global time
                    win.timeOnFlip(momentary_alert_txt, 'tStartRefresh')  # time at next scr refresh
                    # add timestamp to datafile
                    thisExp.timestampOnFlip(win, 'momentary_alert_txt.started')
                    # update status
                    momentary_alert_txt.status = STARTED
                    momentary_alert_txt.setAutoDraw(True)
                
                # if momentary_alert_txt is active this frame...
                if momentary_alert_txt.status == STARTED:
                    # update params
                    pass
                
                # *momentary_not_alert_txt* updates
                
                # if momentary_not_alert_txt is starting this frame...
                if momentary_not_alert_txt.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                    # keep track of start time/frame for later
                    momentary_not_alert_txt.frameNStart = frameN  # exact frame index
                    momentary_not_alert_txt.tStart = t  # local t and not account for scr refresh
                    momentary_not_alert_txt.tStartRefresh = tThisFlipGlobal  # on global time
                    win.timeOnFlip(momentary_not_alert_txt, 'tStartRefresh')  # time at next scr refresh
                    # add timestamp to datafile
                    thisExp.timestampOnFlip(win, 'momentary_not_alert_txt.started')
                    # update status
                    momentary_not_alert_txt.status = STARTED
                    momentary_not_alert_txt.setAutoDraw(True)
                
                # if momentary_not_alert_txt is active this frame...
                if momentary_not_alert_txt.status == STARTED:
                    # update params
                    pass
                
                # *mouse_instruct_txt_1* updates
                
                # if mouse_instruct_txt_1 is starting this frame...
                if mouse_instruct_txt_1.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                    # keep track of start time/frame for later
                    mouse_instruct_txt_1.frameNStart = frameN  # exact frame index
                    mouse_instruct_txt_1.tStart = t  # local t and not account for scr refresh
                    mouse_instruct_txt_1.tStartRefresh = tThisFlipGlobal  # on global time
                    win.timeOnFlip(mouse_instruct_txt_1, 'tStartRefresh')  # time at next scr refresh
                    # add timestamp to datafile
                    thisExp.timestampOnFlip(win, 'mouse_instruct_txt_1.started')
                    # update status
                    mouse_instruct_txt_1.status = STARTED
                    mouse_instruct_txt_1.setAutoDraw(True)
                
                # if mouse_instruct_txt_1 is active this frame...
                if mouse_instruct_txt_1.status == STARTED:
                    # update params
                    pass
                
                # check for quit (typically the Esc key)
                if defaultKeyboard.getKeys(keyList=["escape"]):
                    thisExp.status = FINISHED
                if thisExp.status == FINISHED or endExpNow:
                    endExperiment(thisExp, win=win)
                    return
                # pause experiment here if requested
                if thisExp.status == PAUSED:
                    pauseExperiment(
                        thisExp=thisExp, 
                        win=win, 
                        timers=[routineTimer, globalClock], 
                        currentRoutine=momentary_arousal_rating,
                    )
                    # skip the frame we paused on
                    continue
                
                # has a Component requested the Routine to end?
                if not continueRoutine:
                    momentary_arousal_rating.forceEnded = routineForceEnded = True
                # has the Routine been forcibly ended?
                if momentary_arousal_rating.forceEnded or routineForceEnded:
                    break
                # has every Component finished?
                continueRoutine = False
                for thisComponent in momentary_arousal_rating.components:
                    if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                        continueRoutine = True
                        break  # at least one component has not yet finished
                
                # refresh the screen
                if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                    win.flip()
            
            # --- Ending Routine "momentary_arousal_rating" ---
            for thisComponent in momentary_arousal_rating.components:
                if hasattr(thisComponent, "setAutoDraw"):
                    thisComponent.setAutoDraw(False)
            # store stop times for momentary_arousal_rating
            momentary_arousal_rating.tStop = globalClock.getTime(format='float')
            momentary_arousal_rating.tStopRefresh = tThisFlipGlobal
            thisExp.addData('momentary_arousal_rating.stopped', momentary_arousal_rating.tStop)
            # Run 'End Routine' code from momentary_arousal_rating_code_B
            thisExp.addData('condition', condition)
            # store data for post_emotion_recovery_ratings (TrialHandler)
            post_emotion_recovery_ratings.addData('momentary_arousal_mouse.x', momentary_arousal_mouse.x)
            post_emotion_recovery_ratings.addData('momentary_arousal_mouse.y', momentary_arousal_mouse.y)
            post_emotion_recovery_ratings.addData('momentary_arousal_mouse.leftButton', momentary_arousal_mouse.leftButton)
            post_emotion_recovery_ratings.addData('momentary_arousal_mouse.midButton', momentary_arousal_mouse.midButton)
            post_emotion_recovery_ratings.addData('momentary_arousal_mouse.rightButton', momentary_arousal_mouse.rightButton)
            post_emotion_recovery_ratings.addData('momentary_arousal_mouse.time', momentary_arousal_mouse.time)
            post_emotion_recovery_ratings.addData('momentary_arousal_slider.response', momentary_arousal_slider.getRating())
            post_emotion_recovery_ratings.addData('momentary_arousal_slider.rt', momentary_arousal_slider.getRT())
            # the Routine "momentary_arousal_rating" was not non-slip safe, so reset the non-slip timer
            routineTimer.reset()
            
            # --- Prepare to start Routine "momentary_valence_rating_B" ---
            # create an object to store info about Routine momentary_valence_rating_B
            momentary_valence_rating_B = data.Routine(
                name='momentary_valence_rating_B',
                components=[momentary_valence_mouse_B, momentary_valence_question_txt_B, momentary_valence_slider_B, momentary_pleasant_txt_B, momentary_unpleasant_txt_B, mouse_instruct_txt_2],
            )
            momentary_valence_rating_B.status = NOT_STARTED
            continueRoutine = True
            # update component parameters for each repeat
            # Run 'Begin Routine' code from momentary_valence_rating_code_B
            momentary_valence_mouse_B.setVisible(True)
            timer = None
            
            condition = stim_condition
            
            # determine which slider will appear first
            if rating_order == 'valence_first':
                continueRoutine = False
            # setup some python lists for storing info about the momentary_valence_mouse_B
            momentary_valence_mouse_B.x = []
            momentary_valence_mouse_B.y = []
            momentary_valence_mouse_B.leftButton = []
            momentary_valence_mouse_B.midButton = []
            momentary_valence_mouse_B.rightButton = []
            momentary_valence_mouse_B.time = []
            gotValidClick = False  # until a click is received
            momentary_valence_slider_B.reset()
            momentary_valence_slider_B.setPos((0,0))
            momentary_pleasant_txt_B.setPos((0.5, -0.05))
            momentary_unpleasant_txt_B.setPos((-0.5, -0.05))
            # store start times for momentary_valence_rating_B
            momentary_valence_rating_B.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
            momentary_valence_rating_B.tStart = globalClock.getTime(format='float')
            momentary_valence_rating_B.status = STARTED
            thisExp.addData('momentary_valence_rating_B.started', momentary_valence_rating_B.tStart)
            momentary_valence_rating_B.maxDuration = None
            # keep track of which components have finished
            momentary_valence_rating_BComponents = momentary_valence_rating_B.components
            for thisComponent in momentary_valence_rating_B.components:
                thisComponent.tStart = None
                thisComponent.tStop = None
                thisComponent.tStartRefresh = None
                thisComponent.tStopRefresh = None
                if hasattr(thisComponent, 'status'):
                    thisComponent.status = NOT_STARTED
            # reset timers
            t = 0
            _timeToFirstFrame = win.getFutureFlipTime(clock="now")
            frameN = -1
            
            # --- Run Routine "momentary_valence_rating_B" ---
            thisExp.currentRoutine = momentary_valence_rating_B
            momentary_valence_rating_B.forceEnded = routineForceEnded = not continueRoutine
            while continueRoutine:
                # if trial has changed, end Routine now
                if hasattr(thisPost_emotion_recovery_rating, 'status') and thisPost_emotion_recovery_rating.status == STOPPING:
                    continueRoutine = False
                # get current time
                t = routineTimer.getTime()
                tThisFlip = win.getFutureFlipTime(clock=routineTimer)
                tThisFlipGlobal = win.getFutureFlipTime(clock=None)
                frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
                # update/draw components on each frame
                # Run 'Each Frame' code from momentary_valence_rating_code_B
                if momentary_valence_slider_B.getRating() is not None:
                
                    if timer is None:
                        timer = core.CountdownTimer(2)
                
                    if timer.getTime() < 0:
                        continueRoutine = False
                # *momentary_valence_mouse_B* updates
                
                # if momentary_valence_mouse_B is starting this frame...
                if momentary_valence_mouse_B.status == NOT_STARTED and t >= 0.0-frameTolerance:
                    # keep track of start time/frame for later
                    momentary_valence_mouse_B.frameNStart = frameN  # exact frame index
                    momentary_valence_mouse_B.tStart = t  # local t and not account for scr refresh
                    momentary_valence_mouse_B.tStartRefresh = tThisFlipGlobal  # on global time
                    win.timeOnFlip(momentary_valence_mouse_B, 'tStartRefresh')  # time at next scr refresh
                    # add timestamp to datafile
                    thisExp.addData('momentary_valence_mouse_B.started', t)
                    # update status
                    momentary_valence_mouse_B.status = STARTED
                    momentary_valence_mouse_B.mouseClock.reset()
                    prevButtonState = momentary_valence_mouse_B.getPressed()  # if button is down already this ISN'T a new click
                if momentary_valence_mouse_B.status == STARTED:  # only update if started and not finished!
                    buttons = momentary_valence_mouse_B.getPressed()
                    if buttons != prevButtonState:  # button state changed?
                        prevButtonState = buttons
                        if sum(buttons) > 0:  # state changed to a new click
                            pass
                            x, y = momentary_valence_mouse_B.getPos()
                            momentary_valence_mouse_B.x.append(float(x))
                            momentary_valence_mouse_B.y.append(float(y))
                            buttons = momentary_valence_mouse_B.getPressed()
                            momentary_valence_mouse_B.leftButton.append(buttons[0])
                            momentary_valence_mouse_B.midButton.append(buttons[1])
                            momentary_valence_mouse_B.rightButton.append(buttons[2])
                            momentary_valence_mouse_B.time.append(momentary_valence_mouse_B.mouseClock.getTime())
                
                # *momentary_valence_question_txt_B* updates
                
                # if momentary_valence_question_txt_B is starting this frame...
                if momentary_valence_question_txt_B.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                    # keep track of start time/frame for later
                    momentary_valence_question_txt_B.frameNStart = frameN  # exact frame index
                    momentary_valence_question_txt_B.tStart = t  # local t and not account for scr refresh
                    momentary_valence_question_txt_B.tStartRefresh = tThisFlipGlobal  # on global time
                    win.timeOnFlip(momentary_valence_question_txt_B, 'tStartRefresh')  # time at next scr refresh
                    # add timestamp to datafile
                    thisExp.timestampOnFlip(win, 'momentary_valence_question_txt_B.started')
                    # update status
                    momentary_valence_question_txt_B.status = STARTED
                    momentary_valence_question_txt_B.setAutoDraw(True)
                
                # if momentary_valence_question_txt_B is active this frame...
                if momentary_valence_question_txt_B.status == STARTED:
                    # update params
                    pass
                
                # *momentary_valence_slider_B* updates
                
                # if momentary_valence_slider_B is starting this frame...
                if momentary_valence_slider_B.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                    # keep track of start time/frame for later
                    momentary_valence_slider_B.frameNStart = frameN  # exact frame index
                    momentary_valence_slider_B.tStart = t  # local t and not account for scr refresh
                    momentary_valence_slider_B.tStartRefresh = tThisFlipGlobal  # on global time
                    win.timeOnFlip(momentary_valence_slider_B, 'tStartRefresh')  # time at next scr refresh
                    # add timestamp to datafile
                    thisExp.timestampOnFlip(win, 'momentary_valence_slider_B.started')
                    # update status
                    momentary_valence_slider_B.status = STARTED
                    momentary_valence_slider_B.setAutoDraw(True)
                
                # if momentary_valence_slider_B is active this frame...
                if momentary_valence_slider_B.status == STARTED:
                    # update params
                    pass
                
                # *momentary_pleasant_txt_B* updates
                
                # if momentary_pleasant_txt_B is starting this frame...
                if momentary_pleasant_txt_B.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                    # keep track of start time/frame for later
                    momentary_pleasant_txt_B.frameNStart = frameN  # exact frame index
                    momentary_pleasant_txt_B.tStart = t  # local t and not account for scr refresh
                    momentary_pleasant_txt_B.tStartRefresh = tThisFlipGlobal  # on global time
                    win.timeOnFlip(momentary_pleasant_txt_B, 'tStartRefresh')  # time at next scr refresh
                    # add timestamp to datafile
                    thisExp.timestampOnFlip(win, 'momentary_pleasant_txt_B.started')
                    # update status
                    momentary_pleasant_txt_B.status = STARTED
                    momentary_pleasant_txt_B.setAutoDraw(True)
                
                # if momentary_pleasant_txt_B is active this frame...
                if momentary_pleasant_txt_B.status == STARTED:
                    # update params
                    pass
                
                # *momentary_unpleasant_txt_B* updates
                
                # if momentary_unpleasant_txt_B is starting this frame...
                if momentary_unpleasant_txt_B.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                    # keep track of start time/frame for later
                    momentary_unpleasant_txt_B.frameNStart = frameN  # exact frame index
                    momentary_unpleasant_txt_B.tStart = t  # local t and not account for scr refresh
                    momentary_unpleasant_txt_B.tStartRefresh = tThisFlipGlobal  # on global time
                    win.timeOnFlip(momentary_unpleasant_txt_B, 'tStartRefresh')  # time at next scr refresh
                    # add timestamp to datafile
                    thisExp.timestampOnFlip(win, 'momentary_unpleasant_txt_B.started')
                    # update status
                    momentary_unpleasant_txt_B.status = STARTED
                    momentary_unpleasant_txt_B.setAutoDraw(True)
                
                # if momentary_unpleasant_txt_B is active this frame...
                if momentary_unpleasant_txt_B.status == STARTED:
                    # update params
                    pass
                
                # *mouse_instruct_txt_2* updates
                
                # if mouse_instruct_txt_2 is starting this frame...
                if mouse_instruct_txt_2.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                    # keep track of start time/frame for later
                    mouse_instruct_txt_2.frameNStart = frameN  # exact frame index
                    mouse_instruct_txt_2.tStart = t  # local t and not account for scr refresh
                    mouse_instruct_txt_2.tStartRefresh = tThisFlipGlobal  # on global time
                    win.timeOnFlip(mouse_instruct_txt_2, 'tStartRefresh')  # time at next scr refresh
                    # add timestamp to datafile
                    thisExp.timestampOnFlip(win, 'mouse_instruct_txt_2.started')
                    # update status
                    mouse_instruct_txt_2.status = STARTED
                    mouse_instruct_txt_2.setAutoDraw(True)
                
                # if mouse_instruct_txt_2 is active this frame...
                if mouse_instruct_txt_2.status == STARTED:
                    # update params
                    pass
                
                # check for quit (typically the Esc key)
                if defaultKeyboard.getKeys(keyList=["escape"]):
                    thisExp.status = FINISHED
                if thisExp.status == FINISHED or endExpNow:
                    endExperiment(thisExp, win=win)
                    return
                # pause experiment here if requested
                if thisExp.status == PAUSED:
                    pauseExperiment(
                        thisExp=thisExp, 
                        win=win, 
                        timers=[routineTimer, globalClock], 
                        currentRoutine=momentary_valence_rating_B,
                    )
                    # skip the frame we paused on
                    continue
                
                # has a Component requested the Routine to end?
                if not continueRoutine:
                    momentary_valence_rating_B.forceEnded = routineForceEnded = True
                # has the Routine been forcibly ended?
                if momentary_valence_rating_B.forceEnded or routineForceEnded:
                    break
                # has every Component finished?
                continueRoutine = False
                for thisComponent in momentary_valence_rating_B.components:
                    if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                        continueRoutine = True
                        break  # at least one component has not yet finished
                
                # refresh the screen
                if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                    win.flip()
            
            # --- Ending Routine "momentary_valence_rating_B" ---
            for thisComponent in momentary_valence_rating_B.components:
                if hasattr(thisComponent, "setAutoDraw"):
                    thisComponent.setAutoDraw(False)
            # store stop times for momentary_valence_rating_B
            momentary_valence_rating_B.tStop = globalClock.getTime(format='float')
            momentary_valence_rating_B.tStopRefresh = tThisFlipGlobal
            thisExp.addData('momentary_valence_rating_B.stopped', momentary_valence_rating_B.tStop)
            # Run 'End Routine' code from momentary_valence_rating_code_B
            momentary_valence_mouse_B.setVisible(False)
            
            thisExp.addData('condition', condition)
            # store data for post_emotion_recovery_ratings (TrialHandler)
            post_emotion_recovery_ratings.addData('momentary_valence_mouse_B.x', momentary_valence_mouse_B.x)
            post_emotion_recovery_ratings.addData('momentary_valence_mouse_B.y', momentary_valence_mouse_B.y)
            post_emotion_recovery_ratings.addData('momentary_valence_mouse_B.leftButton', momentary_valence_mouse_B.leftButton)
            post_emotion_recovery_ratings.addData('momentary_valence_mouse_B.midButton', momentary_valence_mouse_B.midButton)
            post_emotion_recovery_ratings.addData('momentary_valence_mouse_B.rightButton', momentary_valence_mouse_B.rightButton)
            post_emotion_recovery_ratings.addData('momentary_valence_mouse_B.time', momentary_valence_mouse_B.time)
            post_emotion_recovery_ratings.addData('momentary_valence_slider_B.response', momentary_valence_slider_B.getRating())
            post_emotion_recovery_ratings.addData('momentary_valence_slider_B.rt', momentary_valence_slider_B.getRT())
            # the Routine "momentary_valence_rating_B" was not non-slip safe, so reset the non-slip timer
            routineTimer.reset()
            # mark thisPost_emotion_recovery_rating as finished
            if hasattr(thisPost_emotion_recovery_rating, 'status'):
                thisPost_emotion_recovery_rating.status = FINISHED
            # if awaiting a pause, pause now
            if post_emotion_recovery_ratings.status == PAUSED:
                thisExp.status = PAUSED
                pauseExperiment(
                    thisExp=thisExp, 
                    win=win, 
                    timers=[globalClock], 
                )
                # once done pausing, restore running status
                post_emotion_recovery_ratings.status = STARTED
            thisExp.nextEntry()
            
        # completed 1.0 repeats of 'post_emotion_recovery_ratings'
        post_emotion_recovery_ratings.status = FINISHED
        
        if thisSession is not None:
            # if running in a Session with a Liaison client, send data up to now
            thisSession.sendExperimentData()
        # mark thisExperimental_condition as finished
        if hasattr(thisExperimental_condition, 'status'):
            thisExperimental_condition.status = FINISHED
        # if awaiting a pause, pause now
        if experimental_conditions.status == PAUSED:
            thisExp.status = PAUSED
            pauseExperiment(
                thisExp=thisExp, 
                win=win, 
                timers=[globalClock], 
            )
            # once done pausing, restore running status
            experimental_conditions.status = STARTED
        thisExp.nextEntry()
        
    # completed 2.0 repeats of 'experimental_conditions'
    experimental_conditions.status = FINISHED
    
    if thisSession is not None:
        # if running in a Session with a Liaison client, send data up to now
        thisSession.sendExperimentData()
    
    # --- Prepare to start Routine "stim_rating_instruct" ---
    # create an object to store info about Routine stim_rating_instruct
    stim_rating_instruct = data.Routine(
        name='stim_rating_instruct',
        components=[stim_rating_instruct_txt],
    )
    stim_rating_instruct.status = NOT_STARTED
    continueRoutine = True
    # update component parameters for each repeat
    # store start times for stim_rating_instruct
    stim_rating_instruct.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
    stim_rating_instruct.tStart = globalClock.getTime(format='float')
    stim_rating_instruct.status = STARTED
    thisExp.addData('stim_rating_instruct.started', stim_rating_instruct.tStart)
    stim_rating_instruct.maxDuration = None
    # keep track of which components have finished
    stim_rating_instructComponents = stim_rating_instruct.components
    for thisComponent in stim_rating_instruct.components:
        thisComponent.tStart = None
        thisComponent.tStop = None
        thisComponent.tStartRefresh = None
        thisComponent.tStopRefresh = None
        if hasattr(thisComponent, 'status'):
            thisComponent.status = NOT_STARTED
    # reset timers
    t = 0
    _timeToFirstFrame = win.getFutureFlipTime(clock="now")
    frameN = -1
    
    # --- Run Routine "stim_rating_instruct" ---
    thisExp.currentRoutine = stim_rating_instruct
    stim_rating_instruct.forceEnded = routineForceEnded = not continueRoutine
    while continueRoutine and routineTimer.getTime() < 10.0:
        # get current time
        t = routineTimer.getTime()
        tThisFlip = win.getFutureFlipTime(clock=routineTimer)
        tThisFlipGlobal = win.getFutureFlipTime(clock=None)
        frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
        # update/draw components on each frame
        
        # *stim_rating_instruct_txt* updates
        
        # if stim_rating_instruct_txt is starting this frame...
        if stim_rating_instruct_txt.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
            # keep track of start time/frame for later
            stim_rating_instruct_txt.frameNStart = frameN  # exact frame index
            stim_rating_instruct_txt.tStart = t  # local t and not account for scr refresh
            stim_rating_instruct_txt.tStartRefresh = tThisFlipGlobal  # on global time
            win.timeOnFlip(stim_rating_instruct_txt, 'tStartRefresh')  # time at next scr refresh
            # add timestamp to datafile
            thisExp.timestampOnFlip(win, 'stim_rating_instruct_txt.started')
            # update status
            stim_rating_instruct_txt.status = STARTED
            stim_rating_instruct_txt.setAutoDraw(True)
        
        # if stim_rating_instruct_txt is active this frame...
        if stim_rating_instruct_txt.status == STARTED:
            # update params
            pass
        
        # if stim_rating_instruct_txt is stopping this frame...
        if stim_rating_instruct_txt.status == STARTED:
            # is it time to stop? (based on global clock, using actual start)
            if tThisFlipGlobal > stim_rating_instruct_txt.tStartRefresh + 10-frameTolerance:
                # keep track of stop time/frame for later
                stim_rating_instruct_txt.tStop = t  # not accounting for scr refresh
                stim_rating_instruct_txt.tStopRefresh = tThisFlipGlobal  # on global time
                stim_rating_instruct_txt.frameNStop = frameN  # exact frame index
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'stim_rating_instruct_txt.stopped')
                # update status
                stim_rating_instruct_txt.status = FINISHED
                stim_rating_instruct_txt.setAutoDraw(False)
        
        # check for quit (typically the Esc key)
        if defaultKeyboard.getKeys(keyList=["escape"]):
            thisExp.status = FINISHED
        if thisExp.status == FINISHED or endExpNow:
            endExperiment(thisExp, win=win)
            return
        # pause experiment here if requested
        if thisExp.status == PAUSED:
            pauseExperiment(
                thisExp=thisExp, 
                win=win, 
                timers=[routineTimer, globalClock], 
                currentRoutine=stim_rating_instruct,
            )
            # skip the frame we paused on
            continue
        
        # has a Component requested the Routine to end?
        if not continueRoutine:
            stim_rating_instruct.forceEnded = routineForceEnded = True
        # has the Routine been forcibly ended?
        if stim_rating_instruct.forceEnded or routineForceEnded:
            break
        # has every Component finished?
        continueRoutine = False
        for thisComponent in stim_rating_instruct.components:
            if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                continueRoutine = True
                break  # at least one component has not yet finished
        
        # refresh the screen
        if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
            win.flip()
    
    # --- Ending Routine "stim_rating_instruct" ---
    for thisComponent in stim_rating_instruct.components:
        if hasattr(thisComponent, "setAutoDraw"):
            thisComponent.setAutoDraw(False)
    # store stop times for stim_rating_instruct
    stim_rating_instruct.tStop = globalClock.getTime(format='float')
    stim_rating_instruct.tStopRefresh = tThisFlipGlobal
    thisExp.addData('stim_rating_instruct.stopped', stim_rating_instruct.tStop)
    # using non-slip timing so subtract the expected duration of this Routine (unless ended on request)
    if stim_rating_instruct.maxDurationReached:
        routineTimer.addTime(-stim_rating_instruct.maxDuration)
    elif stim_rating_instruct.forceEnded:
        routineTimer.reset()
    else:
        routineTimer.addTime(-10.000000)
    thisExp.nextEntry()
    
    # set up handler to look after randomisation of conditions etc
    video_rating = data.TrialHandler2(
        name='video_rating',
        nReps=1.0, 
        method='random', 
        extraInfo=expInfo, 
        originPath=-1, 
        trialList=data.importConditions('rating_images.csv'), 
        seed=None, 
        isTrials=True, 
    )
    thisExp.addLoop(video_rating)  # add the loop to the experiment
    thisVideo_rating = video_rating.trialList[0]  # so we can initialise stimuli with some values
    # abbreviate parameter names if possible (e.g. rgb = thisVideo_rating.rgb)
    if thisVideo_rating != None:
        for paramName in thisVideo_rating:
            globals()[paramName] = thisVideo_rating[paramName]
    if thisSession is not None:
        # if running in a Session with a Liaison client, send data up to now
        thisSession.sendExperimentData()
    
    for thisVideo_rating in video_rating:
        video_rating.status = STARTED
        if hasattr(thisVideo_rating, 'status'):
            thisVideo_rating.status = STARTED
        currentLoop = video_rating
        thisExp.timestampOnFlip(win, 'thisRow.t', format=globalClock.format)
        if thisSession is not None:
            # if running in a Session with a Liaison client, send data up to now
            thisSession.sendExperimentData()
        # abbreviate parameter names if possible (e.g. rgb = thisVideo_rating.rgb)
        if thisVideo_rating != None:
            for paramName in thisVideo_rating:
                globals()[paramName] = thisVideo_rating[paramName]
        
        # --- Prepare to start Routine "stimuli_emo_rating" ---
        # create an object to store info about Routine stimuli_emo_rating
        stimuli_emo_rating = data.Routine(
            name='stimuli_emo_rating',
            components=[stim_arousal_mouse_2, stimuli_emo_question_txt, stimuli_emo_subquest_txt, intensitySlider, intensitySlider_txt_very_intense, intensitySlider_txt_not_intense, screenshot_image_arousal_2, emotionText, intensityQuestion],
        )
        stimuli_emo_rating.status = NOT_STARTED
        continueRoutine = True
        # update component parameters for each repeat
        # Run 'Begin Routine' code from stim_arousal_rating_code_2
        stim_arousal_mouse.setVisible(True)
        timer = None
        
        # set the path to the image shown so that it is identical to what was presented on the previous trial
        image_id = screenshot_path
        
        
        intensityQuestion.setAutoDraw(False)
        intensitySlider.setAutoDraw(False)
        intensitySlider_txt_very_intense.setAutoDraw(False)
        intensitySlider_txt_not_intense.setAutoDraw(False)
        # setup some python lists for storing info about the stim_arousal_mouse_2
        stim_arousal_mouse_2.x = []
        stim_arousal_mouse_2.y = []
        stim_arousal_mouse_2.leftButton = []
        stim_arousal_mouse_2.midButton = []
        stim_arousal_mouse_2.rightButton = []
        stim_arousal_mouse_2.time = []
        gotValidClick = False  # until a click is received
        intensitySlider.reset()
        intensitySlider.setPos((0, -0.35))
        screenshot_image_arousal_2.setImage(screenshot_path)
        emotionText.reset()
        # store start times for stimuli_emo_rating
        stimuli_emo_rating.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
        stimuli_emo_rating.tStart = globalClock.getTime(format='float')
        stimuli_emo_rating.status = STARTED
        thisExp.addData('stimuli_emo_rating.started', stimuli_emo_rating.tStart)
        stimuli_emo_rating.maxDuration = None
        # keep track of which components have finished
        stimuli_emo_ratingComponents = stimuli_emo_rating.components
        for thisComponent in stimuli_emo_rating.components:
            thisComponent.tStart = None
            thisComponent.tStop = None
            thisComponent.tStartRefresh = None
            thisComponent.tStopRefresh = None
            if hasattr(thisComponent, 'status'):
                thisComponent.status = NOT_STARTED
        # reset timers
        t = 0
        _timeToFirstFrame = win.getFutureFlipTime(clock="now")
        frameN = -1
        
        # --- Run Routine "stimuli_emo_rating" ---
        thisExp.currentRoutine = stimuli_emo_rating
        stimuli_emo_rating.forceEnded = routineForceEnded = not continueRoutine
        while continueRoutine:
            # if trial has changed, end Routine now
            if hasattr(thisVideo_rating, 'status') and thisVideo_rating.status == STOPPING:
                continueRoutine = False
            # get current time
            t = routineTimer.getTime()
            tThisFlip = win.getFutureFlipTime(clock=routineTimer)
            tThisFlipGlobal = win.getFutureFlipTime(clock=None)
            frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
            # update/draw components on each frame
            # Run 'Each Frame' code from stim_arousal_rating_code_2
            if len(emotionText.text.strip()) > 0:
                intensityQuestion.setAutoDraw(True)
                intensitySlider.setAutoDraw(True)
                intensitySlider_txt_very_intense.setAutoDraw(True)
            intensitySlider_txt_not_intense.setAutoDraw(True)
            
            if intensitySlider.getRating() is not None:
                if timer is None:
                    timer = core.CountdownTimer(2)
            
                if timer.getTime() < 0:
                    continueRoutine = False
            # *stim_arousal_mouse_2* updates
            
            # if stim_arousal_mouse_2 is starting this frame...
            if stim_arousal_mouse_2.status == NOT_STARTED and t >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                stim_arousal_mouse_2.frameNStart = frameN  # exact frame index
                stim_arousal_mouse_2.tStart = t  # local t and not account for scr refresh
                stim_arousal_mouse_2.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(stim_arousal_mouse_2, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.addData('stim_arousal_mouse_2.started', t)
                # update status
                stim_arousal_mouse_2.status = STARTED
                stim_arousal_mouse_2.mouseClock.reset()
                prevButtonState = stim_arousal_mouse_2.getPressed()  # if button is down already this ISN'T a new click
            if stim_arousal_mouse_2.status == STARTED:  # only update if started and not finished!
                buttons = stim_arousal_mouse_2.getPressed()
                if buttons != prevButtonState:  # button state changed?
                    prevButtonState = buttons
                    if sum(buttons) > 0:  # state changed to a new click
                        pass
                        x, y = stim_arousal_mouse_2.getPos()
                        stim_arousal_mouse_2.x.append(float(x))
                        stim_arousal_mouse_2.y.append(float(y))
                        buttons = stim_arousal_mouse_2.getPressed()
                        stim_arousal_mouse_2.leftButton.append(buttons[0])
                        stim_arousal_mouse_2.midButton.append(buttons[1])
                        stim_arousal_mouse_2.rightButton.append(buttons[2])
                        stim_arousal_mouse_2.time.append(stim_arousal_mouse_2.mouseClock.getTime())
            
            # *stimuli_emo_question_txt* updates
            
            # if stimuli_emo_question_txt is starting this frame...
            if stimuli_emo_question_txt.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                stimuli_emo_question_txt.frameNStart = frameN  # exact frame index
                stimuli_emo_question_txt.tStart = t  # local t and not account for scr refresh
                stimuli_emo_question_txt.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(stimuli_emo_question_txt, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'stimuli_emo_question_txt.started')
                # update status
                stimuli_emo_question_txt.status = STARTED
                stimuli_emo_question_txt.setAutoDraw(True)
            
            # if stimuli_emo_question_txt is active this frame...
            if stimuli_emo_question_txt.status == STARTED:
                # update params
                pass
            
            # *stimuli_emo_subquest_txt* updates
            
            # if stimuli_emo_subquest_txt is starting this frame...
            if stimuli_emo_subquest_txt.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                stimuli_emo_subquest_txt.frameNStart = frameN  # exact frame index
                stimuli_emo_subquest_txt.tStart = t  # local t and not account for scr refresh
                stimuli_emo_subquest_txt.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(stimuli_emo_subquest_txt, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'stimuli_emo_subquest_txt.started')
                # update status
                stimuli_emo_subquest_txt.status = STARTED
                stimuli_emo_subquest_txt.setAutoDraw(True)
            
            # if stimuli_emo_subquest_txt is active this frame...
            if stimuli_emo_subquest_txt.status == STARTED:
                # update params
                pass
            
            # *intensitySlider* updates
            
            # if intensitySlider is starting this frame...
            if intensitySlider.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                intensitySlider.frameNStart = frameN  # exact frame index
                intensitySlider.tStart = t  # local t and not account for scr refresh
                intensitySlider.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(intensitySlider, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'intensitySlider.started')
                # update status
                intensitySlider.status = STARTED
                intensitySlider.setAutoDraw(True)
            
            # if intensitySlider is active this frame...
            if intensitySlider.status == STARTED:
                # update params
                pass
            
            # *intensitySlider_txt_very_intense* updates
            
            # if intensitySlider_txt_very_intense is starting this frame...
            if intensitySlider_txt_very_intense.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                intensitySlider_txt_very_intense.frameNStart = frameN  # exact frame index
                intensitySlider_txt_very_intense.tStart = t  # local t and not account for scr refresh
                intensitySlider_txt_very_intense.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(intensitySlider_txt_very_intense, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'intensitySlider_txt_very_intense.started')
                # update status
                intensitySlider_txt_very_intense.status = STARTED
                intensitySlider_txt_very_intense.setAutoDraw(True)
            
            # if intensitySlider_txt_very_intense is active this frame...
            if intensitySlider_txt_very_intense.status == STARTED:
                # update params
                pass
            
            # *intensitySlider_txt_not_intense* updates
            
            # if intensitySlider_txt_not_intense is starting this frame...
            if intensitySlider_txt_not_intense.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                intensitySlider_txt_not_intense.frameNStart = frameN  # exact frame index
                intensitySlider_txt_not_intense.tStart = t  # local t and not account for scr refresh
                intensitySlider_txt_not_intense.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(intensitySlider_txt_not_intense, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'intensitySlider_txt_not_intense.started')
                # update status
                intensitySlider_txt_not_intense.status = STARTED
                intensitySlider_txt_not_intense.setAutoDraw(True)
            
            # if intensitySlider_txt_not_intense is active this frame...
            if intensitySlider_txt_not_intense.status == STARTED:
                # update params
                pass
            
            # *screenshot_image_arousal_2* updates
            
            # if screenshot_image_arousal_2 is starting this frame...
            if screenshot_image_arousal_2.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                screenshot_image_arousal_2.frameNStart = frameN  # exact frame index
                screenshot_image_arousal_2.tStart = t  # local t and not account for scr refresh
                screenshot_image_arousal_2.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(screenshot_image_arousal_2, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'screenshot_image_arousal_2.started')
                # update status
                screenshot_image_arousal_2.status = STARTED
                screenshot_image_arousal_2.setAutoDraw(True)
            
            # if screenshot_image_arousal_2 is active this frame...
            if screenshot_image_arousal_2.status == STARTED:
                # update params
                pass
            
            # *emotionText* updates
            
            # if emotionText is starting this frame...
            if emotionText.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                emotionText.frameNStart = frameN  # exact frame index
                emotionText.tStart = t  # local t and not account for scr refresh
                emotionText.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(emotionText, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'emotionText.started')
                # update status
                emotionText.status = STARTED
                emotionText.setAutoDraw(True)
            
            # if emotionText is active this frame...
            if emotionText.status == STARTED:
                # update params
                pass
            
            # *intensityQuestion* updates
            
            # if intensityQuestion is starting this frame...
            if intensityQuestion.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                intensityQuestion.frameNStart = frameN  # exact frame index
                intensityQuestion.tStart = t  # local t and not account for scr refresh
                intensityQuestion.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(intensityQuestion, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'intensityQuestion.started')
                # update status
                intensityQuestion.status = STARTED
                intensityQuestion.setAutoDraw(True)
            
            # if intensityQuestion is active this frame...
            if intensityQuestion.status == STARTED:
                # update params
                pass
            
            # check for quit (typically the Esc key)
            if defaultKeyboard.getKeys(keyList=["escape"]):
                thisExp.status = FINISHED
            if thisExp.status == FINISHED or endExpNow:
                endExperiment(thisExp, win=win)
                return
            # pause experiment here if requested
            if thisExp.status == PAUSED:
                pauseExperiment(
                    thisExp=thisExp, 
                    win=win, 
                    timers=[routineTimer, globalClock], 
                    currentRoutine=stimuli_emo_rating,
                )
                # skip the frame we paused on
                continue
            
            # has a Component requested the Routine to end?
            if not continueRoutine:
                stimuli_emo_rating.forceEnded = routineForceEnded = True
            # has the Routine been forcibly ended?
            if stimuli_emo_rating.forceEnded or routineForceEnded:
                break
            # has every Component finished?
            continueRoutine = False
            for thisComponent in stimuli_emo_rating.components:
                if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                    continueRoutine = True
                    break  # at least one component has not yet finished
            
            # refresh the screen
            if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                win.flip()
        
        # --- Ending Routine "stimuli_emo_rating" ---
        for thisComponent in stimuli_emo_rating.components:
            if hasattr(thisComponent, "setAutoDraw"):
                thisComponent.setAutoDraw(False)
        # store stop times for stimuli_emo_rating
        stimuli_emo_rating.tStop = globalClock.getTime(format='float')
        stimuli_emo_rating.tStopRefresh = tThisFlipGlobal
        thisExp.addData('stimuli_emo_rating.stopped', stimuli_emo_rating.tStop)
        # Run 'End Routine' code from stim_arousal_rating_code_2
        stim_arousal_mouse.setVisible(False)
        # store data for video_rating (TrialHandler)
        video_rating.addData('stim_arousal_mouse_2.x', stim_arousal_mouse_2.x)
        video_rating.addData('stim_arousal_mouse_2.y', stim_arousal_mouse_2.y)
        video_rating.addData('stim_arousal_mouse_2.leftButton', stim_arousal_mouse_2.leftButton)
        video_rating.addData('stim_arousal_mouse_2.midButton', stim_arousal_mouse_2.midButton)
        video_rating.addData('stim_arousal_mouse_2.rightButton', stim_arousal_mouse_2.rightButton)
        video_rating.addData('stim_arousal_mouse_2.time', stim_arousal_mouse_2.time)
        video_rating.addData('intensitySlider.response', intensitySlider.getRating())
        video_rating.addData('intensitySlider.rt', intensitySlider.getRT())
        video_rating.addData('emotionText.text',emotionText.text)
        # the Routine "stimuli_emo_rating" was not non-slip safe, so reset the non-slip timer
        routineTimer.reset()
        
        # --- Prepare to start Routine "stimuli_valence_rating_A" ---
        # create an object to store info about Routine stimuli_valence_rating_A
        stimuli_valence_rating_A = data.Routine(
            name='stimuli_valence_rating_A',
            components=[stim_valence_mouse_A, stimuli_valence_question_txt_A, stim_valence_slider_A, stim_pleasant_txt_A, stim_unpleasant_txt_A, screenshot_image_valence_A, mouse_instruct_txt_3],
        )
        stimuli_valence_rating_A.status = NOT_STARTED
        continueRoutine = True
        # update component parameters for each repeat
        # Run 'Begin Routine' code from stim_valence_rating_code_B
        stim_valence_mouse_A.setVisible(True)
        timer = None
        
        # set the path to the image shown so that it is identical to what was presented on the previous trial
        image_id = screenshot_path
        
        # Setup for counterbalancing
        stim_rating_pair_count += 1
        if stim_rating_pair_count % 2 == 1:
            stim_rating_order = stim_rating_start
        else:
            stim_rating_order = 'arousal_first' if stim_rating_start == 'valence_first' else 'valence_first'
        
        if stim_rating_order == 'arousal_first':
            continueRoutine = False
        # setup some python lists for storing info about the stim_valence_mouse_A
        stim_valence_mouse_A.x = []
        stim_valence_mouse_A.y = []
        stim_valence_mouse_A.leftButton = []
        stim_valence_mouse_A.midButton = []
        stim_valence_mouse_A.rightButton = []
        stim_valence_mouse_A.time = []
        gotValidClick = False  # until a click is received
        stim_valence_slider_A.reset()
        stim_valence_slider_A.setPos((0, -0.2))
        screenshot_image_valence_A.setImage(screenshot_path)
        # store start times for stimuli_valence_rating_A
        stimuli_valence_rating_A.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
        stimuli_valence_rating_A.tStart = globalClock.getTime(format='float')
        stimuli_valence_rating_A.status = STARTED
        thisExp.addData('stimuli_valence_rating_A.started', stimuli_valence_rating_A.tStart)
        stimuli_valence_rating_A.maxDuration = None
        # keep track of which components have finished
        stimuli_valence_rating_AComponents = stimuli_valence_rating_A.components
        for thisComponent in stimuli_valence_rating_A.components:
            thisComponent.tStart = None
            thisComponent.tStop = None
            thisComponent.tStartRefresh = None
            thisComponent.tStopRefresh = None
            if hasattr(thisComponent, 'status'):
                thisComponent.status = NOT_STARTED
        # reset timers
        t = 0
        _timeToFirstFrame = win.getFutureFlipTime(clock="now")
        frameN = -1
        
        # --- Run Routine "stimuli_valence_rating_A" ---
        thisExp.currentRoutine = stimuli_valence_rating_A
        stimuli_valence_rating_A.forceEnded = routineForceEnded = not continueRoutine
        while continueRoutine:
            # if trial has changed, end Routine now
            if hasattr(thisVideo_rating, 'status') and thisVideo_rating.status == STOPPING:
                continueRoutine = False
            # get current time
            t = routineTimer.getTime()
            tThisFlip = win.getFutureFlipTime(clock=routineTimer)
            tThisFlipGlobal = win.getFutureFlipTime(clock=None)
            frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
            # update/draw components on each frame
            # Run 'Each Frame' code from stim_valence_rating_code_B
            if stim_valence_slider_A.getRating() is not None:
                if timer is None:
                    timer = core.CountdownTimer(2)
            
                if timer.getTime() < 0:
                    continueRoutine = False
            # *stim_valence_mouse_A* updates
            
            # if stim_valence_mouse_A is starting this frame...
            if stim_valence_mouse_A.status == NOT_STARTED and t >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                stim_valence_mouse_A.frameNStart = frameN  # exact frame index
                stim_valence_mouse_A.tStart = t  # local t and not account for scr refresh
                stim_valence_mouse_A.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(stim_valence_mouse_A, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.addData('stim_valence_mouse_A.started', t)
                # update status
                stim_valence_mouse_A.status = STARTED
                stim_valence_mouse_A.mouseClock.reset()
                prevButtonState = stim_valence_mouse_A.getPressed()  # if button is down already this ISN'T a new click
            if stim_valence_mouse_A.status == STARTED:  # only update if started and not finished!
                buttons = stim_valence_mouse_A.getPressed()
                if buttons != prevButtonState:  # button state changed?
                    prevButtonState = buttons
                    if sum(buttons) > 0:  # state changed to a new click
                        pass
                        x, y = stim_valence_mouse_A.getPos()
                        stim_valence_mouse_A.x.append(float(x))
                        stim_valence_mouse_A.y.append(float(y))
                        buttons = stim_valence_mouse_A.getPressed()
                        stim_valence_mouse_A.leftButton.append(buttons[0])
                        stim_valence_mouse_A.midButton.append(buttons[1])
                        stim_valence_mouse_A.rightButton.append(buttons[2])
                        stim_valence_mouse_A.time.append(stim_valence_mouse_A.mouseClock.getTime())
            
            # *stimuli_valence_question_txt_A* updates
            
            # if stimuli_valence_question_txt_A is starting this frame...
            if stimuli_valence_question_txt_A.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                stimuli_valence_question_txt_A.frameNStart = frameN  # exact frame index
                stimuli_valence_question_txt_A.tStart = t  # local t and not account for scr refresh
                stimuli_valence_question_txt_A.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(stimuli_valence_question_txt_A, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'stimuli_valence_question_txt_A.started')
                # update status
                stimuli_valence_question_txt_A.status = STARTED
                stimuli_valence_question_txt_A.setAutoDraw(True)
            
            # if stimuli_valence_question_txt_A is active this frame...
            if stimuli_valence_question_txt_A.status == STARTED:
                # update params
                pass
            
            # *stim_valence_slider_A* updates
            
            # if stim_valence_slider_A is starting this frame...
            if stim_valence_slider_A.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                stim_valence_slider_A.frameNStart = frameN  # exact frame index
                stim_valence_slider_A.tStart = t  # local t and not account for scr refresh
                stim_valence_slider_A.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(stim_valence_slider_A, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'stim_valence_slider_A.started')
                # update status
                stim_valence_slider_A.status = STARTED
                stim_valence_slider_A.setAutoDraw(True)
            
            # if stim_valence_slider_A is active this frame...
            if stim_valence_slider_A.status == STARTED:
                # update params
                pass
            
            # *stim_pleasant_txt_A* updates
            
            # if stim_pleasant_txt_A is starting this frame...
            if stim_pleasant_txt_A.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                stim_pleasant_txt_A.frameNStart = frameN  # exact frame index
                stim_pleasant_txt_A.tStart = t  # local t and not account for scr refresh
                stim_pleasant_txt_A.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(stim_pleasant_txt_A, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'stim_pleasant_txt_A.started')
                # update status
                stim_pleasant_txt_A.status = STARTED
                stim_pleasant_txt_A.setAutoDraw(True)
            
            # if stim_pleasant_txt_A is active this frame...
            if stim_pleasant_txt_A.status == STARTED:
                # update params
                pass
            
            # *stim_unpleasant_txt_A* updates
            
            # if stim_unpleasant_txt_A is starting this frame...
            if stim_unpleasant_txt_A.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                stim_unpleasant_txt_A.frameNStart = frameN  # exact frame index
                stim_unpleasant_txt_A.tStart = t  # local t and not account for scr refresh
                stim_unpleasant_txt_A.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(stim_unpleasant_txt_A, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'stim_unpleasant_txt_A.started')
                # update status
                stim_unpleasant_txt_A.status = STARTED
                stim_unpleasant_txt_A.setAutoDraw(True)
            
            # if stim_unpleasant_txt_A is active this frame...
            if stim_unpleasant_txt_A.status == STARTED:
                # update params
                pass
            
            # *screenshot_image_valence_A* updates
            
            # if screenshot_image_valence_A is starting this frame...
            if screenshot_image_valence_A.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                screenshot_image_valence_A.frameNStart = frameN  # exact frame index
                screenshot_image_valence_A.tStart = t  # local t and not account for scr refresh
                screenshot_image_valence_A.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(screenshot_image_valence_A, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'screenshot_image_valence_A.started')
                # update status
                screenshot_image_valence_A.status = STARTED
                screenshot_image_valence_A.setAutoDraw(True)
            
            # if screenshot_image_valence_A is active this frame...
            if screenshot_image_valence_A.status == STARTED:
                # update params
                pass
            
            # *mouse_instruct_txt_3* updates
            
            # if mouse_instruct_txt_3 is starting this frame...
            if mouse_instruct_txt_3.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                mouse_instruct_txt_3.frameNStart = frameN  # exact frame index
                mouse_instruct_txt_3.tStart = t  # local t and not account for scr refresh
                mouse_instruct_txt_3.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(mouse_instruct_txt_3, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'mouse_instruct_txt_3.started')
                # update status
                mouse_instruct_txt_3.status = STARTED
                mouse_instruct_txt_3.setAutoDraw(True)
            
            # if mouse_instruct_txt_3 is active this frame...
            if mouse_instruct_txt_3.status == STARTED:
                # update params
                pass
            
            # check for quit (typically the Esc key)
            if defaultKeyboard.getKeys(keyList=["escape"]):
                thisExp.status = FINISHED
            if thisExp.status == FINISHED or endExpNow:
                endExperiment(thisExp, win=win)
                return
            # pause experiment here if requested
            if thisExp.status == PAUSED:
                pauseExperiment(
                    thisExp=thisExp, 
                    win=win, 
                    timers=[routineTimer, globalClock], 
                    currentRoutine=stimuli_valence_rating_A,
                )
                # skip the frame we paused on
                continue
            
            # has a Component requested the Routine to end?
            if not continueRoutine:
                stimuli_valence_rating_A.forceEnded = routineForceEnded = True
            # has the Routine been forcibly ended?
            if stimuli_valence_rating_A.forceEnded or routineForceEnded:
                break
            # has every Component finished?
            continueRoutine = False
            for thisComponent in stimuli_valence_rating_A.components:
                if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                    continueRoutine = True
                    break  # at least one component has not yet finished
            
            # refresh the screen
            if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                win.flip()
        
        # --- Ending Routine "stimuli_valence_rating_A" ---
        for thisComponent in stimuli_valence_rating_A.components:
            if hasattr(thisComponent, "setAutoDraw"):
                thisComponent.setAutoDraw(False)
        # store stop times for stimuli_valence_rating_A
        stimuli_valence_rating_A.tStop = globalClock.getTime(format='float')
        stimuli_valence_rating_A.tStopRefresh = tThisFlipGlobal
        thisExp.addData('stimuli_valence_rating_A.stopped', stimuli_valence_rating_A.tStop)
        # Run 'End Routine' code from stim_valence_rating_code_B
        stim_valence_mouse_A.setVisible(False)
        # store data for video_rating (TrialHandler)
        video_rating.addData('stim_valence_mouse_A.x', stim_valence_mouse_A.x)
        video_rating.addData('stim_valence_mouse_A.y', stim_valence_mouse_A.y)
        video_rating.addData('stim_valence_mouse_A.leftButton', stim_valence_mouse_A.leftButton)
        video_rating.addData('stim_valence_mouse_A.midButton', stim_valence_mouse_A.midButton)
        video_rating.addData('stim_valence_mouse_A.rightButton', stim_valence_mouse_A.rightButton)
        video_rating.addData('stim_valence_mouse_A.time', stim_valence_mouse_A.time)
        video_rating.addData('stim_valence_slider_A.response', stim_valence_slider_A.getRating())
        video_rating.addData('stim_valence_slider_A.rt', stim_valence_slider_A.getRT())
        # the Routine "stimuli_valence_rating_A" was not non-slip safe, so reset the non-slip timer
        routineTimer.reset()
        
        # --- Prepare to start Routine "stimuli_arousal_rating" ---
        # create an object to store info about Routine stimuli_arousal_rating
        stimuli_arousal_rating = data.Routine(
            name='stimuli_arousal_rating',
            components=[stim_arousal_mouse, stimuli_arousal_question_txt, stim_arousal_slider, stim_alert_txt, stim_not_alert_txt, screenshot_image_arousal, mouse_instruct_txt_4],
        )
        stimuli_arousal_rating.status = NOT_STARTED
        continueRoutine = True
        # update component parameters for each repeat
        # Run 'Begin Routine' code from stim_arousal_rating_code
        stim_arousal_mouse.setVisible(True)
        timer = None
        
        # set the path to the image shown so that it is identical to what was presented on the previous trial
        image_id = screenshot_path
        
        # setup some python lists for storing info about the stim_arousal_mouse
        stim_arousal_mouse.x = []
        stim_arousal_mouse.y = []
        stim_arousal_mouse.leftButton = []
        stim_arousal_mouse.midButton = []
        stim_arousal_mouse.rightButton = []
        stim_arousal_mouse.time = []
        gotValidClick = False  # until a click is received
        stim_arousal_slider.reset()
        stim_arousal_slider.setPos((0, -0.2))
        screenshot_image_arousal.setImage(screenshot_path)
        # store start times for stimuli_arousal_rating
        stimuli_arousal_rating.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
        stimuli_arousal_rating.tStart = globalClock.getTime(format='float')
        stimuli_arousal_rating.status = STARTED
        thisExp.addData('stimuli_arousal_rating.started', stimuli_arousal_rating.tStart)
        stimuli_arousal_rating.maxDuration = None
        # keep track of which components have finished
        stimuli_arousal_ratingComponents = stimuli_arousal_rating.components
        for thisComponent in stimuli_arousal_rating.components:
            thisComponent.tStart = None
            thisComponent.tStop = None
            thisComponent.tStartRefresh = None
            thisComponent.tStopRefresh = None
            if hasattr(thisComponent, 'status'):
                thisComponent.status = NOT_STARTED
        # reset timers
        t = 0
        _timeToFirstFrame = win.getFutureFlipTime(clock="now")
        frameN = -1
        
        # --- Run Routine "stimuli_arousal_rating" ---
        thisExp.currentRoutine = stimuli_arousal_rating
        stimuli_arousal_rating.forceEnded = routineForceEnded = not continueRoutine
        while continueRoutine:
            # if trial has changed, end Routine now
            if hasattr(thisVideo_rating, 'status') and thisVideo_rating.status == STOPPING:
                continueRoutine = False
            # get current time
            t = routineTimer.getTime()
            tThisFlip = win.getFutureFlipTime(clock=routineTimer)
            tThisFlipGlobal = win.getFutureFlipTime(clock=None)
            frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
            # update/draw components on each frame
            # Run 'Each Frame' code from stim_arousal_rating_code
            if stim_arousal_slider.getRating() is not None:
                if timer is None:
                    timer = core.CountdownTimer(2)
            
                if timer.getTime() < 0:
                    continueRoutine = False
            # *stim_arousal_mouse* updates
            
            # if stim_arousal_mouse is starting this frame...
            if stim_arousal_mouse.status == NOT_STARTED and t >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                stim_arousal_mouse.frameNStart = frameN  # exact frame index
                stim_arousal_mouse.tStart = t  # local t and not account for scr refresh
                stim_arousal_mouse.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(stim_arousal_mouse, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.addData('stim_arousal_mouse.started', t)
                # update status
                stim_arousal_mouse.status = STARTED
                stim_arousal_mouse.mouseClock.reset()
                prevButtonState = stim_arousal_mouse.getPressed()  # if button is down already this ISN'T a new click
            if stim_arousal_mouse.status == STARTED:  # only update if started and not finished!
                buttons = stim_arousal_mouse.getPressed()
                if buttons != prevButtonState:  # button state changed?
                    prevButtonState = buttons
                    if sum(buttons) > 0:  # state changed to a new click
                        pass
                        x, y = stim_arousal_mouse.getPos()
                        stim_arousal_mouse.x.append(float(x))
                        stim_arousal_mouse.y.append(float(y))
                        buttons = stim_arousal_mouse.getPressed()
                        stim_arousal_mouse.leftButton.append(buttons[0])
                        stim_arousal_mouse.midButton.append(buttons[1])
                        stim_arousal_mouse.rightButton.append(buttons[2])
                        stim_arousal_mouse.time.append(stim_arousal_mouse.mouseClock.getTime())
            
            # *stimuli_arousal_question_txt* updates
            
            # if stimuli_arousal_question_txt is starting this frame...
            if stimuli_arousal_question_txt.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                stimuli_arousal_question_txt.frameNStart = frameN  # exact frame index
                stimuli_arousal_question_txt.tStart = t  # local t and not account for scr refresh
                stimuli_arousal_question_txt.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(stimuli_arousal_question_txt, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'stimuli_arousal_question_txt.started')
                # update status
                stimuli_arousal_question_txt.status = STARTED
                stimuli_arousal_question_txt.setAutoDraw(True)
            
            # if stimuli_arousal_question_txt is active this frame...
            if stimuli_arousal_question_txt.status == STARTED:
                # update params
                pass
            
            # *stim_arousal_slider* updates
            
            # if stim_arousal_slider is starting this frame...
            if stim_arousal_slider.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                stim_arousal_slider.frameNStart = frameN  # exact frame index
                stim_arousal_slider.tStart = t  # local t and not account for scr refresh
                stim_arousal_slider.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(stim_arousal_slider, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'stim_arousal_slider.started')
                # update status
                stim_arousal_slider.status = STARTED
                stim_arousal_slider.setAutoDraw(True)
            
            # if stim_arousal_slider is active this frame...
            if stim_arousal_slider.status == STARTED:
                # update params
                pass
            
            # *stim_alert_txt* updates
            
            # if stim_alert_txt is starting this frame...
            if stim_alert_txt.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                stim_alert_txt.frameNStart = frameN  # exact frame index
                stim_alert_txt.tStart = t  # local t and not account for scr refresh
                stim_alert_txt.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(stim_alert_txt, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'stim_alert_txt.started')
                # update status
                stim_alert_txt.status = STARTED
                stim_alert_txt.setAutoDraw(True)
            
            # if stim_alert_txt is active this frame...
            if stim_alert_txt.status == STARTED:
                # update params
                pass
            
            # *stim_not_alert_txt* updates
            
            # if stim_not_alert_txt is starting this frame...
            if stim_not_alert_txt.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                stim_not_alert_txt.frameNStart = frameN  # exact frame index
                stim_not_alert_txt.tStart = t  # local t and not account for scr refresh
                stim_not_alert_txt.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(stim_not_alert_txt, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'stim_not_alert_txt.started')
                # update status
                stim_not_alert_txt.status = STARTED
                stim_not_alert_txt.setAutoDraw(True)
            
            # if stim_not_alert_txt is active this frame...
            if stim_not_alert_txt.status == STARTED:
                # update params
                pass
            
            # *screenshot_image_arousal* updates
            
            # if screenshot_image_arousal is starting this frame...
            if screenshot_image_arousal.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                screenshot_image_arousal.frameNStart = frameN  # exact frame index
                screenshot_image_arousal.tStart = t  # local t and not account for scr refresh
                screenshot_image_arousal.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(screenshot_image_arousal, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'screenshot_image_arousal.started')
                # update status
                screenshot_image_arousal.status = STARTED
                screenshot_image_arousal.setAutoDraw(True)
            
            # if screenshot_image_arousal is active this frame...
            if screenshot_image_arousal.status == STARTED:
                # update params
                pass
            
            # *mouse_instruct_txt_4* updates
            
            # if mouse_instruct_txt_4 is starting this frame...
            if mouse_instruct_txt_4.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                mouse_instruct_txt_4.frameNStart = frameN  # exact frame index
                mouse_instruct_txt_4.tStart = t  # local t and not account for scr refresh
                mouse_instruct_txt_4.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(mouse_instruct_txt_4, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'mouse_instruct_txt_4.started')
                # update status
                mouse_instruct_txt_4.status = STARTED
                mouse_instruct_txt_4.setAutoDraw(True)
            
            # if mouse_instruct_txt_4 is active this frame...
            if mouse_instruct_txt_4.status == STARTED:
                # update params
                pass
            
            # check for quit (typically the Esc key)
            if defaultKeyboard.getKeys(keyList=["escape"]):
                thisExp.status = FINISHED
            if thisExp.status == FINISHED or endExpNow:
                endExperiment(thisExp, win=win)
                return
            # pause experiment here if requested
            if thisExp.status == PAUSED:
                pauseExperiment(
                    thisExp=thisExp, 
                    win=win, 
                    timers=[routineTimer, globalClock], 
                    currentRoutine=stimuli_arousal_rating,
                )
                # skip the frame we paused on
                continue
            
            # has a Component requested the Routine to end?
            if not continueRoutine:
                stimuli_arousal_rating.forceEnded = routineForceEnded = True
            # has the Routine been forcibly ended?
            if stimuli_arousal_rating.forceEnded or routineForceEnded:
                break
            # has every Component finished?
            continueRoutine = False
            for thisComponent in stimuli_arousal_rating.components:
                if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                    continueRoutine = True
                    break  # at least one component has not yet finished
            
            # refresh the screen
            if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                win.flip()
        
        # --- Ending Routine "stimuli_arousal_rating" ---
        for thisComponent in stimuli_arousal_rating.components:
            if hasattr(thisComponent, "setAutoDraw"):
                thisComponent.setAutoDraw(False)
        # store stop times for stimuli_arousal_rating
        stimuli_arousal_rating.tStop = globalClock.getTime(format='float')
        stimuli_arousal_rating.tStopRefresh = tThisFlipGlobal
        thisExp.addData('stimuli_arousal_rating.stopped', stimuli_arousal_rating.tStop)
        # Run 'End Routine' code from stim_arousal_rating_code
        stim_arousal_mouse.setVisible(False)
        # store data for video_rating (TrialHandler)
        video_rating.addData('stim_arousal_mouse.x', stim_arousal_mouse.x)
        video_rating.addData('stim_arousal_mouse.y', stim_arousal_mouse.y)
        video_rating.addData('stim_arousal_mouse.leftButton', stim_arousal_mouse.leftButton)
        video_rating.addData('stim_arousal_mouse.midButton', stim_arousal_mouse.midButton)
        video_rating.addData('stim_arousal_mouse.rightButton', stim_arousal_mouse.rightButton)
        video_rating.addData('stim_arousal_mouse.time', stim_arousal_mouse.time)
        video_rating.addData('stim_arousal_slider.response', stim_arousal_slider.getRating())
        video_rating.addData('stim_arousal_slider.rt', stim_arousal_slider.getRT())
        # the Routine "stimuli_arousal_rating" was not non-slip safe, so reset the non-slip timer
        routineTimer.reset()
        
        # --- Prepare to start Routine "stimuli_valence_rating_B" ---
        # create an object to store info about Routine stimuli_valence_rating_B
        stimuli_valence_rating_B = data.Routine(
            name='stimuli_valence_rating_B',
            components=[stim_valence_mouse_B, stimuli_valence_question_txt_B, stim_valence_slider_B, stim_pleasant_txt_B, stim_unpleasant_txt_B, screenshot_image_valence_B, moust_instruct_txt_5],
        )
        stimuli_valence_rating_B.status = NOT_STARTED
        continueRoutine = True
        # update component parameters for each repeat
        # Run 'Begin Routine' code from stim_valence_rating_code_B_2
        stim_valence_mouse_B.setVisible(True)
        timer = None
        
        # Set the path to the image shown so that it is identical to what was presented on the previous trial
        image_id = screenshot_path
        
        # Skip if valence first
        if stim_rating_order == 'valence_first':
            continueRoutine = False
        # setup some python lists for storing info about the stim_valence_mouse_B
        stim_valence_mouse_B.x = []
        stim_valence_mouse_B.y = []
        stim_valence_mouse_B.leftButton = []
        stim_valence_mouse_B.midButton = []
        stim_valence_mouse_B.rightButton = []
        stim_valence_mouse_B.time = []
        gotValidClick = False  # until a click is received
        stim_valence_slider_B.reset()
        stim_valence_slider_B.setPos((0, -0.2))
        screenshot_image_valence_B.setImage(screenshot_path)
        # store start times for stimuli_valence_rating_B
        stimuli_valence_rating_B.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
        stimuli_valence_rating_B.tStart = globalClock.getTime(format='float')
        stimuli_valence_rating_B.status = STARTED
        thisExp.addData('stimuli_valence_rating_B.started', stimuli_valence_rating_B.tStart)
        stimuli_valence_rating_B.maxDuration = None
        # keep track of which components have finished
        stimuli_valence_rating_BComponents = stimuli_valence_rating_B.components
        for thisComponent in stimuli_valence_rating_B.components:
            thisComponent.tStart = None
            thisComponent.tStop = None
            thisComponent.tStartRefresh = None
            thisComponent.tStopRefresh = None
            if hasattr(thisComponent, 'status'):
                thisComponent.status = NOT_STARTED
        # reset timers
        t = 0
        _timeToFirstFrame = win.getFutureFlipTime(clock="now")
        frameN = -1
        
        # --- Run Routine "stimuli_valence_rating_B" ---
        thisExp.currentRoutine = stimuli_valence_rating_B
        stimuli_valence_rating_B.forceEnded = routineForceEnded = not continueRoutine
        while continueRoutine:
            # if trial has changed, end Routine now
            if hasattr(thisVideo_rating, 'status') and thisVideo_rating.status == STOPPING:
                continueRoutine = False
            # get current time
            t = routineTimer.getTime()
            tThisFlip = win.getFutureFlipTime(clock=routineTimer)
            tThisFlipGlobal = win.getFutureFlipTime(clock=None)
            frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
            # update/draw components on each frame
            # Run 'Each Frame' code from stim_valence_rating_code_B_2
            if stim_valence_slider_B.getRating() is not None:
                if timer is None:
                    timer = core.CountdownTimer(2)
            
                if timer.getTime() < 0:
                    continueRoutine = False
            # *stim_valence_mouse_B* updates
            
            # if stim_valence_mouse_B is starting this frame...
            if stim_valence_mouse_B.status == NOT_STARTED and t >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                stim_valence_mouse_B.frameNStart = frameN  # exact frame index
                stim_valence_mouse_B.tStart = t  # local t and not account for scr refresh
                stim_valence_mouse_B.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(stim_valence_mouse_B, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.addData('stim_valence_mouse_B.started', t)
                # update status
                stim_valence_mouse_B.status = STARTED
                stim_valence_mouse_B.mouseClock.reset()
                prevButtonState = stim_valence_mouse_B.getPressed()  # if button is down already this ISN'T a new click
            if stim_valence_mouse_B.status == STARTED:  # only update if started and not finished!
                buttons = stim_valence_mouse_B.getPressed()
                if buttons != prevButtonState:  # button state changed?
                    prevButtonState = buttons
                    if sum(buttons) > 0:  # state changed to a new click
                        pass
                        x, y = stim_valence_mouse_B.getPos()
                        stim_valence_mouse_B.x.append(float(x))
                        stim_valence_mouse_B.y.append(float(y))
                        buttons = stim_valence_mouse_B.getPressed()
                        stim_valence_mouse_B.leftButton.append(buttons[0])
                        stim_valence_mouse_B.midButton.append(buttons[1])
                        stim_valence_mouse_B.rightButton.append(buttons[2])
                        stim_valence_mouse_B.time.append(stim_valence_mouse_B.mouseClock.getTime())
            
            # *stimuli_valence_question_txt_B* updates
            
            # if stimuli_valence_question_txt_B is starting this frame...
            if stimuli_valence_question_txt_B.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                stimuli_valence_question_txt_B.frameNStart = frameN  # exact frame index
                stimuli_valence_question_txt_B.tStart = t  # local t and not account for scr refresh
                stimuli_valence_question_txt_B.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(stimuli_valence_question_txt_B, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'stimuli_valence_question_txt_B.started')
                # update status
                stimuli_valence_question_txt_B.status = STARTED
                stimuli_valence_question_txt_B.setAutoDraw(True)
            
            # if stimuli_valence_question_txt_B is active this frame...
            if stimuli_valence_question_txt_B.status == STARTED:
                # update params
                pass
            
            # *stim_valence_slider_B* updates
            
            # if stim_valence_slider_B is starting this frame...
            if stim_valence_slider_B.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                stim_valence_slider_B.frameNStart = frameN  # exact frame index
                stim_valence_slider_B.tStart = t  # local t and not account for scr refresh
                stim_valence_slider_B.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(stim_valence_slider_B, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'stim_valence_slider_B.started')
                # update status
                stim_valence_slider_B.status = STARTED
                stim_valence_slider_B.setAutoDraw(True)
            
            # if stim_valence_slider_B is active this frame...
            if stim_valence_slider_B.status == STARTED:
                # update params
                pass
            
            # *stim_pleasant_txt_B* updates
            
            # if stim_pleasant_txt_B is starting this frame...
            if stim_pleasant_txt_B.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                stim_pleasant_txt_B.frameNStart = frameN  # exact frame index
                stim_pleasant_txt_B.tStart = t  # local t and not account for scr refresh
                stim_pleasant_txt_B.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(stim_pleasant_txt_B, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'stim_pleasant_txt_B.started')
                # update status
                stim_pleasant_txt_B.status = STARTED
                stim_pleasant_txt_B.setAutoDraw(True)
            
            # if stim_pleasant_txt_B is active this frame...
            if stim_pleasant_txt_B.status == STARTED:
                # update params
                pass
            
            # *stim_unpleasant_txt_B* updates
            
            # if stim_unpleasant_txt_B is starting this frame...
            if stim_unpleasant_txt_B.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                stim_unpleasant_txt_B.frameNStart = frameN  # exact frame index
                stim_unpleasant_txt_B.tStart = t  # local t and not account for scr refresh
                stim_unpleasant_txt_B.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(stim_unpleasant_txt_B, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'stim_unpleasant_txt_B.started')
                # update status
                stim_unpleasant_txt_B.status = STARTED
                stim_unpleasant_txt_B.setAutoDraw(True)
            
            # if stim_unpleasant_txt_B is active this frame...
            if stim_unpleasant_txt_B.status == STARTED:
                # update params
                pass
            
            # *screenshot_image_valence_B* updates
            
            # if screenshot_image_valence_B is starting this frame...
            if screenshot_image_valence_B.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                screenshot_image_valence_B.frameNStart = frameN  # exact frame index
                screenshot_image_valence_B.tStart = t  # local t and not account for scr refresh
                screenshot_image_valence_B.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(screenshot_image_valence_B, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'screenshot_image_valence_B.started')
                # update status
                screenshot_image_valence_B.status = STARTED
                screenshot_image_valence_B.setAutoDraw(True)
            
            # if screenshot_image_valence_B is active this frame...
            if screenshot_image_valence_B.status == STARTED:
                # update params
                pass
            
            # *moust_instruct_txt_5* updates
            
            # if moust_instruct_txt_5 is starting this frame...
            if moust_instruct_txt_5.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                moust_instruct_txt_5.frameNStart = frameN  # exact frame index
                moust_instruct_txt_5.tStart = t  # local t and not account for scr refresh
                moust_instruct_txt_5.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(moust_instruct_txt_5, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'moust_instruct_txt_5.started')
                # update status
                moust_instruct_txt_5.status = STARTED
                moust_instruct_txt_5.setAutoDraw(True)
            
            # if moust_instruct_txt_5 is active this frame...
            if moust_instruct_txt_5.status == STARTED:
                # update params
                pass
            
            # check for quit (typically the Esc key)
            if defaultKeyboard.getKeys(keyList=["escape"]):
                thisExp.status = FINISHED
            if thisExp.status == FINISHED or endExpNow:
                endExperiment(thisExp, win=win)
                return
            # pause experiment here if requested
            if thisExp.status == PAUSED:
                pauseExperiment(
                    thisExp=thisExp, 
                    win=win, 
                    timers=[routineTimer, globalClock], 
                    currentRoutine=stimuli_valence_rating_B,
                )
                # skip the frame we paused on
                continue
            
            # has a Component requested the Routine to end?
            if not continueRoutine:
                stimuli_valence_rating_B.forceEnded = routineForceEnded = True
            # has the Routine been forcibly ended?
            if stimuli_valence_rating_B.forceEnded or routineForceEnded:
                break
            # has every Component finished?
            continueRoutine = False
            for thisComponent in stimuli_valence_rating_B.components:
                if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                    continueRoutine = True
                    break  # at least one component has not yet finished
            
            # refresh the screen
            if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                win.flip()
        
        # --- Ending Routine "stimuli_valence_rating_B" ---
        for thisComponent in stimuli_valence_rating_B.components:
            if hasattr(thisComponent, "setAutoDraw"):
                thisComponent.setAutoDraw(False)
        # store stop times for stimuli_valence_rating_B
        stimuli_valence_rating_B.tStop = globalClock.getTime(format='float')
        stimuli_valence_rating_B.tStopRefresh = tThisFlipGlobal
        thisExp.addData('stimuli_valence_rating_B.stopped', stimuli_valence_rating_B.tStop)
        # Run 'End Routine' code from stim_valence_rating_code_B_2
        stim_valence_mouse_B.setVisible(False)
        # store data for video_rating (TrialHandler)
        video_rating.addData('stim_valence_mouse_B.x', stim_valence_mouse_B.x)
        video_rating.addData('stim_valence_mouse_B.y', stim_valence_mouse_B.y)
        video_rating.addData('stim_valence_mouse_B.leftButton', stim_valence_mouse_B.leftButton)
        video_rating.addData('stim_valence_mouse_B.midButton', stim_valence_mouse_B.midButton)
        video_rating.addData('stim_valence_mouse_B.rightButton', stim_valence_mouse_B.rightButton)
        video_rating.addData('stim_valence_mouse_B.time', stim_valence_mouse_B.time)
        video_rating.addData('stim_valence_slider_B.response', stim_valence_slider_B.getRating())
        video_rating.addData('stim_valence_slider_B.rt', stim_valence_slider_B.getRT())
        # the Routine "stimuli_valence_rating_B" was not non-slip safe, so reset the non-slip timer
        routineTimer.reset()
        
        # --- Prepare to start Routine "approach_rating" ---
        # create an object to store info about Routine approach_rating
        approach_rating = data.Routine(
            name='approach_rating',
            components=[stim_approach_mouse, stim_approach_slider, stim_approach_question_txt, screenshot_image_approach, not_at_all_txt, approach_txt, moust_instruct_6_txt],
        )
        approach_rating.status = NOT_STARTED
        continueRoutine = True
        # update component parameters for each repeat
        # Run 'Begin Routine' code from approach_rating_code
        stim_approach_mouse.setVisible(True)
        timer = None
        
        # set the path to the image shown so that it is identical to what was presented on the previous trial
        image_id = screenshot_path
        
        # setup some python lists for storing info about the stim_approach_mouse
        stim_approach_mouse.x = []
        stim_approach_mouse.y = []
        stim_approach_mouse.leftButton = []
        stim_approach_mouse.midButton = []
        stim_approach_mouse.rightButton = []
        stim_approach_mouse.time = []
        gotValidClick = False  # until a click is received
        stim_approach_slider.reset()
        screenshot_image_approach.setImage(image_id)
        # store start times for approach_rating
        approach_rating.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
        approach_rating.tStart = globalClock.getTime(format='float')
        approach_rating.status = STARTED
        thisExp.addData('approach_rating.started', approach_rating.tStart)
        approach_rating.maxDuration = None
        # keep track of which components have finished
        approach_ratingComponents = approach_rating.components
        for thisComponent in approach_rating.components:
            thisComponent.tStart = None
            thisComponent.tStop = None
            thisComponent.tStartRefresh = None
            thisComponent.tStopRefresh = None
            if hasattr(thisComponent, 'status'):
                thisComponent.status = NOT_STARTED
        # reset timers
        t = 0
        _timeToFirstFrame = win.getFutureFlipTime(clock="now")
        frameN = -1
        
        # --- Run Routine "approach_rating" ---
        thisExp.currentRoutine = approach_rating
        approach_rating.forceEnded = routineForceEnded = not continueRoutine
        while continueRoutine:
            # if trial has changed, end Routine now
            if hasattr(thisVideo_rating, 'status') and thisVideo_rating.status == STOPPING:
                continueRoutine = False
            # get current time
            t = routineTimer.getTime()
            tThisFlip = win.getFutureFlipTime(clock=routineTimer)
            tThisFlipGlobal = win.getFutureFlipTime(clock=None)
            frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
            # update/draw components on each frame
            # Run 'Each Frame' code from approach_rating_code
            if stim_approach_slider.getRating() is not None:
            
                if timer is None:
                    timer = core.CountdownTimer(2)
            
                if timer.getTime() < 0:
                    continueRoutine = False
            # *stim_approach_mouse* updates
            
            # if stim_approach_mouse is starting this frame...
            if stim_approach_mouse.status == NOT_STARTED and t >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                stim_approach_mouse.frameNStart = frameN  # exact frame index
                stim_approach_mouse.tStart = t  # local t and not account for scr refresh
                stim_approach_mouse.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(stim_approach_mouse, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.addData('stim_approach_mouse.started', t)
                # update status
                stim_approach_mouse.status = STARTED
                stim_approach_mouse.mouseClock.reset()
                prevButtonState = stim_approach_mouse.getPressed()  # if button is down already this ISN'T a new click
            if stim_approach_mouse.status == STARTED:  # only update if started and not finished!
                buttons = stim_approach_mouse.getPressed()
                if buttons != prevButtonState:  # button state changed?
                    prevButtonState = buttons
                    if sum(buttons) > 0:  # state changed to a new click
                        pass
                        x, y = stim_approach_mouse.getPos()
                        stim_approach_mouse.x.append(float(x))
                        stim_approach_mouse.y.append(float(y))
                        buttons = stim_approach_mouse.getPressed()
                        stim_approach_mouse.leftButton.append(buttons[0])
                        stim_approach_mouse.midButton.append(buttons[1])
                        stim_approach_mouse.rightButton.append(buttons[2])
                        stim_approach_mouse.time.append(stim_approach_mouse.mouseClock.getTime())
            
            # *stim_approach_slider* updates
            
            # if stim_approach_slider is starting this frame...
            if stim_approach_slider.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                stim_approach_slider.frameNStart = frameN  # exact frame index
                stim_approach_slider.tStart = t  # local t and not account for scr refresh
                stim_approach_slider.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(stim_approach_slider, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'stim_approach_slider.started')
                # update status
                stim_approach_slider.status = STARTED
                stim_approach_slider.setAutoDraw(True)
            
            # if stim_approach_slider is active this frame...
            if stim_approach_slider.status == STARTED:
                # update params
                pass
            
            # *stim_approach_question_txt* updates
            
            # if stim_approach_question_txt is starting this frame...
            if stim_approach_question_txt.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                stim_approach_question_txt.frameNStart = frameN  # exact frame index
                stim_approach_question_txt.tStart = t  # local t and not account for scr refresh
                stim_approach_question_txt.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(stim_approach_question_txt, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'stim_approach_question_txt.started')
                # update status
                stim_approach_question_txt.status = STARTED
                stim_approach_question_txt.setAutoDraw(True)
            
            # if stim_approach_question_txt is active this frame...
            if stim_approach_question_txt.status == STARTED:
                # update params
                pass
            
            # *screenshot_image_approach* updates
            
            # if screenshot_image_approach is starting this frame...
            if screenshot_image_approach.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                screenshot_image_approach.frameNStart = frameN  # exact frame index
                screenshot_image_approach.tStart = t  # local t and not account for scr refresh
                screenshot_image_approach.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(screenshot_image_approach, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'screenshot_image_approach.started')
                # update status
                screenshot_image_approach.status = STARTED
                screenshot_image_approach.setAutoDraw(True)
            
            # if screenshot_image_approach is active this frame...
            if screenshot_image_approach.status == STARTED:
                # update params
                pass
            
            # *not_at_all_txt* updates
            
            # if not_at_all_txt is starting this frame...
            if not_at_all_txt.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                not_at_all_txt.frameNStart = frameN  # exact frame index
                not_at_all_txt.tStart = t  # local t and not account for scr refresh
                not_at_all_txt.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(not_at_all_txt, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'not_at_all_txt.started')
                # update status
                not_at_all_txt.status = STARTED
                not_at_all_txt.setAutoDraw(True)
            
            # if not_at_all_txt is active this frame...
            if not_at_all_txt.status == STARTED:
                # update params
                pass
            
            # *approach_txt* updates
            
            # if approach_txt is starting this frame...
            if approach_txt.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                approach_txt.frameNStart = frameN  # exact frame index
                approach_txt.tStart = t  # local t and not account for scr refresh
                approach_txt.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(approach_txt, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'approach_txt.started')
                # update status
                approach_txt.status = STARTED
                approach_txt.setAutoDraw(True)
            
            # if approach_txt is active this frame...
            if approach_txt.status == STARTED:
                # update params
                pass
            
            # *moust_instruct_6_txt* updates
            
            # if moust_instruct_6_txt is starting this frame...
            if moust_instruct_6_txt.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
                # keep track of start time/frame for later
                moust_instruct_6_txt.frameNStart = frameN  # exact frame index
                moust_instruct_6_txt.tStart = t  # local t and not account for scr refresh
                moust_instruct_6_txt.tStartRefresh = tThisFlipGlobal  # on global time
                win.timeOnFlip(moust_instruct_6_txt, 'tStartRefresh')  # time at next scr refresh
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'moust_instruct_6_txt.started')
                # update status
                moust_instruct_6_txt.status = STARTED
                moust_instruct_6_txt.setAutoDraw(True)
            
            # if moust_instruct_6_txt is active this frame...
            if moust_instruct_6_txt.status == STARTED:
                # update params
                pass
            
            # check for quit (typically the Esc key)
            if defaultKeyboard.getKeys(keyList=["escape"]):
                thisExp.status = FINISHED
            if thisExp.status == FINISHED or endExpNow:
                endExperiment(thisExp, win=win)
                return
            # pause experiment here if requested
            if thisExp.status == PAUSED:
                pauseExperiment(
                    thisExp=thisExp, 
                    win=win, 
                    timers=[routineTimer, globalClock], 
                    currentRoutine=approach_rating,
                )
                # skip the frame we paused on
                continue
            
            # has a Component requested the Routine to end?
            if not continueRoutine:
                approach_rating.forceEnded = routineForceEnded = True
            # has the Routine been forcibly ended?
            if approach_rating.forceEnded or routineForceEnded:
                break
            # has every Component finished?
            continueRoutine = False
            for thisComponent in approach_rating.components:
                if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                    continueRoutine = True
                    break  # at least one component has not yet finished
            
            # refresh the screen
            if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                win.flip()
        
        # --- Ending Routine "approach_rating" ---
        for thisComponent in approach_rating.components:
            if hasattr(thisComponent, "setAutoDraw"):
                thisComponent.setAutoDraw(False)
        # store stop times for approach_rating
        approach_rating.tStop = globalClock.getTime(format='float')
        approach_rating.tStopRefresh = tThisFlipGlobal
        thisExp.addData('approach_rating.stopped', approach_rating.tStop)
        # Run 'End Routine' code from approach_rating_code
        stim_approach_mouse.setVisible(False)
        # store data for video_rating (TrialHandler)
        video_rating.addData('stim_approach_mouse.x', stim_approach_mouse.x)
        video_rating.addData('stim_approach_mouse.y', stim_approach_mouse.y)
        video_rating.addData('stim_approach_mouse.leftButton', stim_approach_mouse.leftButton)
        video_rating.addData('stim_approach_mouse.midButton', stim_approach_mouse.midButton)
        video_rating.addData('stim_approach_mouse.rightButton', stim_approach_mouse.rightButton)
        video_rating.addData('stim_approach_mouse.time', stim_approach_mouse.time)
        video_rating.addData('stim_approach_slider.response', stim_approach_slider.getRating())
        video_rating.addData('stim_approach_slider.rt', stim_approach_slider.getRT())
        # the Routine "approach_rating" was not non-slip safe, so reset the non-slip timer
        routineTimer.reset()
        # mark thisVideo_rating as finished
        if hasattr(thisVideo_rating, 'status'):
            thisVideo_rating.status = FINISHED
        # if awaiting a pause, pause now
        if video_rating.status == PAUSED:
            thisExp.status = PAUSED
            pauseExperiment(
                thisExp=thisExp, 
                win=win, 
                timers=[globalClock], 
            )
            # once done pausing, restore running status
            video_rating.status = STARTED
        thisExp.nextEntry()
        
    # completed 1.0 repeats of 'video_rating'
    video_rating.status = FINISHED
    
    if thisSession is not None:
        # if running in a Session with a Liaison client, send data up to now
        thisSession.sendExperimentData()
    
    # --- Prepare to start Routine "end" ---
    # create an object to store info about Routine end
    end = data.Routine(
        name='end',
        components=[end_text],
    )
    end.status = NOT_STARTED
    continueRoutine = True
    # update component parameters for each repeat
    # store start times for end
    end.tStartRefresh = win.getFutureFlipTime(clock=globalClock)
    end.tStart = globalClock.getTime(format='float')
    end.status = STARTED
    thisExp.addData('end.started', end.tStart)
    end.maxDuration = None
    # keep track of which components have finished
    endComponents = end.components
    for thisComponent in end.components:
        thisComponent.tStart = None
        thisComponent.tStop = None
        thisComponent.tStartRefresh = None
        thisComponent.tStopRefresh = None
        if hasattr(thisComponent, 'status'):
            thisComponent.status = NOT_STARTED
    # reset timers
    t = 0
    _timeToFirstFrame = win.getFutureFlipTime(clock="now")
    frameN = -1
    
    # --- Run Routine "end" ---
    thisExp.currentRoutine = end
    end.forceEnded = routineForceEnded = not continueRoutine
    while continueRoutine and routineTimer.getTime() < 8.0:
        # get current time
        t = routineTimer.getTime()
        tThisFlip = win.getFutureFlipTime(clock=routineTimer)
        tThisFlipGlobal = win.getFutureFlipTime(clock=None)
        frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
        # update/draw components on each frame
        
        # *end_text* updates
        
        # if end_text is starting this frame...
        if end_text.status == NOT_STARTED and tThisFlip >= 0.0-frameTolerance:
            # keep track of start time/frame for later
            end_text.frameNStart = frameN  # exact frame index
            end_text.tStart = t  # local t and not account for scr refresh
            end_text.tStartRefresh = tThisFlipGlobal  # on global time
            win.timeOnFlip(end_text, 'tStartRefresh')  # time at next scr refresh
            # add timestamp to datafile
            thisExp.timestampOnFlip(win, 'end_text.started')
            # update status
            end_text.status = STARTED
            end_text.setAutoDraw(True)
        
        # if end_text is active this frame...
        if end_text.status == STARTED:
            # update params
            pass
        
        # if end_text is stopping this frame...
        if end_text.status == STARTED:
            # is it time to stop? (based on global clock, using actual start)
            if tThisFlipGlobal > end_text.tStartRefresh + 8-frameTolerance:
                # keep track of stop time/frame for later
                end_text.tStop = t  # not accounting for scr refresh
                end_text.tStopRefresh = tThisFlipGlobal  # on global time
                end_text.frameNStop = frameN  # exact frame index
                # add timestamp to datafile
                thisExp.timestampOnFlip(win, 'end_text.stopped')
                # update status
                end_text.status = FINISHED
                end_text.setAutoDraw(False)
        
        # check for quit (typically the Esc key)
        if defaultKeyboard.getKeys(keyList=["escape"]):
            thisExp.status = FINISHED
        if thisExp.status == FINISHED or endExpNow:
            endExperiment(thisExp, win=win)
            return
        # pause experiment here if requested
        if thisExp.status == PAUSED:
            pauseExperiment(
                thisExp=thisExp, 
                win=win, 
                timers=[routineTimer, globalClock], 
                currentRoutine=end,
            )
            # skip the frame we paused on
            continue
        
        # has a Component requested the Routine to end?
        if not continueRoutine:
            end.forceEnded = routineForceEnded = True
        # has the Routine been forcibly ended?
        if end.forceEnded or routineForceEnded:
            break
        # has every Component finished?
        continueRoutine = False
        for thisComponent in end.components:
            if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                continueRoutine = True
                break  # at least one component has not yet finished
        
        # refresh the screen
        if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
            win.flip()
    
    # --- Ending Routine "end" ---
    for thisComponent in end.components:
        if hasattr(thisComponent, "setAutoDraw"):
            thisComponent.setAutoDraw(False)
    # store stop times for end
    end.tStop = globalClock.getTime(format='float')
    end.tStopRefresh = tThisFlipGlobal
    thisExp.addData('end.stopped', end.tStop)
    # using non-slip timing so subtract the expected duration of this Routine (unless ended on request)
    if end.maxDurationReached:
        routineTimer.addTime(-end.maxDuration)
    elif end.forceEnded:
        routineTimer.reset()
    else:
        routineTimer.addTime(-8.000000)
    thisExp.nextEntry()
    # Run 'End Experiment' code from code
    #---
    # CAMERA SAVE
    #---
    recorder.stop()
    recorder.save_timestamps(f'{save_dir}/{participant_id}_frame_timestamps.csv')
    # Run 'End Experiment' code from webcam_code
    bio.write_clocksync(filename + '_clocksync.json', extra={
        "mono_reset":   core.monotonicClock.getLastResetTime(),  # raw monotonic base (→ PTB GetSecs)
        "global_reset": globalClock.getLastResetTime(),          # globalClock reset, same base (→ data-file .started)
    })
    bio.stop()
    
    # mark experiment as finished
    endExperiment(thisExp, win=win)


def saveData(thisExp):
    """
    Save data from this experiment
    
    Parameters
    ==========
    thisExp : psychopy.data.ExperimentHandler
        Handler object for this experiment, contains the data to save and information about 
        where to save it to.
    """
    filename = thisExp.dataFileName
    # these shouldn't be strictly necessary (should auto-save)
    thisExp.saveAsWideText(filename + '.csv', delim='auto')
    thisExp.saveAsPickle(filename)


def endExperiment(thisExp, win=None):
    """
    End this experiment, performing final shut down operations.
    
    This function does NOT close the window or end the Python process - use `quit` for this.
    
    Parameters
    ==========
    thisExp : psychopy.data.ExperimentHandler
        Handler object for this experiment, contains the data to save and information about 
        where to save it to.
    win : psychopy.visual.Window
        Window for this experiment.
    """
    # stop any playback components
    if thisExp.currentRoutine is not None:
        for comp in thisExp.currentRoutine.getPlaybackComponents():
            comp.stop()
    if win is not None:
        # remove autodraw from all current components
        win.clearAutoDraw()
        # Flip one final time so any remaining win.callOnFlip() 
        # and win.timeOnFlip() tasks get executed
        win.flip()
    # return console logger level to WARNING
    logging.console.setLevel(logging.WARNING)
    # mark experiment handler as finished
    thisExp.status = FINISHED
    # run any 'at exit' functions
    for fcn in runAtExit:
        fcn()
    logging.flush()


def quit(thisExp, win=None, thisSession=None):
    """
    Fully quit, closing the window and ending the Python process.
    
    Parameters
    ==========
    win : psychopy.visual.Window
        Window to close.
    thisSession : psychopy.session.Session or None
        Handle of the Session object this experiment is being run from, if any.
    """
    thisExp.abort()  # or data files will save again on exit
    # make sure everything is closed down
    if win is not None:
        # Flip one final time so any remaining win.callOnFlip() 
        # and win.timeOnFlip() tasks get executed before quitting
        win.flip()
        win.close()
    logging.flush()
    if thisSession is not None:
        thisSession.stop()
    # terminate Python process
    core.quit()


# if running this experiment as a script...
if __name__ == '__main__':
    # call all functions in order
    expInfo = showExpInfoDlg(expInfo=expInfo)
    thisExp = setupData(expInfo=expInfo)
    logFile = setupLogging(filename=thisExp.dataFileName)
    win = setupWindow(expInfo=expInfo)
    setupDevices(expInfo=expInfo, thisExp=thisExp, win=win)
    run(
        expInfo=expInfo, 
        thisExp=thisExp, 
        win=win,
        globalClock='float'
    )
    saveData(thisExp=thisExp)
    quit(thisExp=thisExp, win=win)
