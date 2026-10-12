% config_template.m
% ==================
% Copy this file to config.m and fill in your machine's paths.
% config.m is gitignored — never commit it.
%
% All MATLAB scripts in analysis/pspm/ load this automatically.

% Root of the project data folder (the 3_Data folder in Box).
% All MATLAB scripts build their data paths relative to this.
% Expected subfolder structure:
%   SERVER_ROOT/
%     psychopy/            raw PsychoPy .csv files + cleaned output
%     raw_physiology/      raw .acq files (used across pipelines)
%     pspm/
%       preprocessed/      PsPM-imported .mat files
%       missing_epoch/     artefact epoch files
%       models/
%         blocks/          block-level GLM models
%         videos/          video-level (trial) GLM models
%     event_onsets/
%       blocks/            block-level onset .mat files (from Python scripts)
%       stimulus_videos/   video-level onset .mat files (from Python scripts)
%
% Example (Windows):
%   SERVER_ROOT = 'C:\Users\you\Box\Project_Biosignals_study_2\3_Data';
% Example (Mac):
%   SERVER_ROOT = '/Users/you/Library/CloudStorage/Box-Box/Project_Biosignals_study_2/3_Data';
SERVER_ROOT = '';

BLOCK_ONSETS_DIR = fullfile(SERVER_ROOT, 'event_onsets', 'blocks');
VIDEO_ONSETS_DIR = fullfile(SERVER_ROOT, 'event_onsets', 'stimulus_videos');

% Full path to the PsPM toolbox folder — the one that contains pspm.m.
%
% Example (Windows):  PSPM_PATH = 'C:\Users\you\Documents\MATLAB\PsPM';
% Example (Mac):      PSPM_PATH = '/Users/you/Documents/MATLAB/PsPM';
PSPM_PATH = '';
