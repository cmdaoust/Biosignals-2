% config_template_hpc.m
% ======================
% HPC (CISC2 cluster) version of config.m.
% Copy this file to config.m on the HPC and fill in PSPM_PATH.
% config.m is gitignored — never commit it.
%
% All MATLAB scripts in analysis/pspm/ load this automatically.

% Root of the project data folder on the HPC.
% The GitHub repo is cloned directly into Biosignals2/; data lives in
% Biosignals2/data/ with the same subfolder structure as the Box 3_Data folder
% (raw_physiology/, pspm/, event_onsets/, etc.).
SERVER_ROOT = '/mnt/research/cisc2/projects/sdl_emotioncontrol/Biosignals2/data';

BLOCK_ONSETS_DIR = fullfile(SERVER_ROOT, 'event_onsets', 'blocks');
VIDEO_ONSETS_DIR = fullfile(SERVER_ROOT, 'event_onsets', 'stimulus_videos');

% Full path to the PsPM toolbox folder — the one that contains pspm.m.
% Fill this in once you know where PsPM is installed on the cluster.
% Example: PSPM_PATH = '/mnt/research/cisc2/tools/PsPM';
PSPM_PATH = '';
