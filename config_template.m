% config_template.m
% =================
% Copy this file to config.m at the repo root and fill in the paths.
% config.m is gitignored: never commit it.
% Same variables as config_template.py (plus PSPM_PATH at the end).
% All MATLAB scripts in analysis/pspm/ load this automatically.

% Example (Windows): SERVER_ROOT = 'C:/Users/you/Box/Project_Biosignals_study_2/3_Data';
% Example (Mac):     SERVER_ROOT = '/Users/you/Library/CloudStorage/Box-Box/Project_Biosignals_study_2/3_Data';
SERVER_ROOT = '';

%% Physiology
% The BIOPAC recordings live in three stages. Analyses run on the TRIMMED
% recordings (cut to the experimental protocol), because event onsets are
% measured from the start of the file and must match the data being analysed.
PHYSIOLOGY_ROOT           = fullfile(SERVER_ROOT, 'raw_physiology');
PHYSIOLOGY_SESSION_DIR    = fullfile(PHYSIOLOGY_ROOT, 'entire_session_duration');         % as recorded
PHYSIOLOGY_TRIMMED_DIR    = fullfile(PHYSIOLOGY_ROOT, 'experimental_protocol_duration');  % cut to protocol
PHYSIOLOGY_EXPORTS_DIR    = fullfile(PHYSIOLOGY_ROOT, 'exports');                         % .mat for Ledalab

% What analyses should use.
RAW_PHYSIOLOGY_DIR        = PHYSIOLOGY_TRIMMED_DIR;
PSYCHOPY_DATA_DIR         = fullfile(SERVER_ROOT, 'raw_psychopy');
RAW_QUESTIONNAIRE_DIR     = fullfile(SERVER_ROOT, 'raw_questionnaire');
COMBINED_DATA_DIR         = fullfile(SERVER_ROOT, 'clean_combined_data');
COMBINED_PSYCHO_DIR       = fullfile(COMBINED_DATA_DIR, 'psychopy');
COMBINED_QUEST_DIR        = fullfile(COMBINED_DATA_DIR, 'questionnaires');
COMBINED_PSYCHO_QUEST_DIR = fullfile(COMBINED_DATA_DIR, 'psychopy_questionnaire');
PROCESSED_PHYSIO_DIR      = fullfile(SERVER_ROOT, 'pspm', 'preprocessed');
BLOCK_ONSETS_DIR          = fullfile(SERVER_ROOT, 'event_onsets', 'blocks');
VIDEO_ONSETS_DIR          = fullfile(SERVER_ROOT, 'event_onsets', 'stimulus_videos');
FACEREADER_ONSETS_DIR     = fullfile(SERVER_ROOT, 'event_onsets', 'facereader_video');  % events in FaceReader AVI time
FACEREADER_RESULTS_DIR    = fullfile(SERVER_ROOT, 'facereader');  % FaceReader exports

%% Webcam (<id>_frames/, <id>_frame_timestamps.csv, <id>_facereader.avi)
WEBCAM_PNG_EXTERNAL_DIR   = '';  % e.g. 'D:/Biosignals2_png_data'; external hard drive: <id>_frames/ + <id>_frame_timestamps.csv
% Video working copies (1to1 / FaceReader AVIs + timestamps copies): the external hard drive.
VIDEO_EXTERNAL_DIR        = '';  % e.g. 'D:/Biosignals2_video'; external hard drive (not Box)
% WebcamBiometrics code (used by 002_run_webcam_biometrics.py)
WEBCAM_BIOMETRICS_REPO    = '';  % e.g. 'C:/Users/you/Documents/WebcamBiometrics'
% Webcam, older sessions recorded straight to AVI (<id>_frame_timestamps.csv, <id>_recording.avi)
VIDEO_BOX_DIR             = fullfile(SERVER_ROOT, 'video');   % Box
LEDALAB_RESULTS_DIR       = fullfile(SERVER_ROOT, 'ledalab');
% Ledalab input: EDA-only .mat files prepared for Ledalab
LEDALAB_INPUT_DIR         = fullfile(SERVER_ROOT, 'ledalab', 'input');

%% MATLAB only
% Full path to the PsPM toolbox folder: the one that contains pspm.m.
PSPM_PATH = '';  % e.g. 'C:/Users/you/Documents/MATLAB/PsPM'
