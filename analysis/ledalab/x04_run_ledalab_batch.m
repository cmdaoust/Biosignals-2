% run_ledalab_batch.m
% ====================
% Ledalab batch CDA analysis for all participants.
%
% Derived from pilot analysis of participant 001 (Ledalab v3.49):
%   Sampling rate : 50 Hz
%   CDA tau       : [2.069, 3.191]  (optimised Bateman function parameters)
%   smoothwin     : 0.2 s
%   tonicGridSize : 10
%
% Pipeline
% --------
%   1. Open all Ledalab .mat files in DATA_DIR
%   2. Downsample 50 Hz → 10 Hz (factor 5)
%        — 10 Hz is sufficient for SCR; reduces CDA computation time ~25×
%   3. Run CDA with 4-round optimisation
%   4. Export ERA  : response window 0–177 s, threshold 0.01 µS → text file
%        — 177 s = floor of shortest block duration across all participants
%          and conditions (negative_induction min = 177.4 s; all other
%          blocks are exactly 180 s except positive_induction ~185–186 s)
%        — A single fixed window is used for all events; 177 s fits every
%          block without clipping. The tail of positive_induction blocks
%          (~8 s) is not captured — acceptable given CDA.SCR is the
%          primary outcome and responses typically peak well within 177 s.
%        — Use CDA.SCR (mean phasic driver) as primary outcome measure
%        — CDA.nSCR / CDA.AmpSum are threshold-dependent; interpret cautiously
%   5. Export SCR-list : threshold 0.05 µS → text file
%   6. Save decomposition overview image per participant (for QC)
%
% Output
% ------
%   All files are saved back into DATA_DIR alongside the .mat files:
%     {pid}_era.txt        — event-related activation (one row per event)
%     {pid}_scrlist.txt    — list of all detected SCRs
%     {pid}_overview.jpg   — decomposition QC image
%
% Usage
% -----
%   1. Open Matlab and cd to the Ledalab installation directory
%   2. Edit DATA_DIR below to match your local Box path
%   3. Run:  run('/path/to/run_ledalab_batch.m')
%      or open the file and press Run in the Matlab editor

% ── CONFIGURATION ─────────────────────────────────────────────────────────────

DATA_DIR = 'C:\Users\carme\Box\Project_Biosignals_study_2\3_Data\ledalab\preprocessed\';

% Response window for ERA export [start_s  end_s] relative to event onset.
% 177 s = conservative floor across all block types and participants.
% See block duration summary (from Kubios_Samples.csv, n=6):
%   baseline          : 180 s (fixed)
%   negative_induction: 177.4–178.3 s  ← shortest; sets the ceiling
%   negative_recovery : 180 s (fixed)
%   positive_induction: 185.4–186.5 s  (tail ~8 s not captured)
%   positive_recovery : 180 s (fixed)
RESP_WIN_START = 0;
RESP_WIN_END   = 177;

% Amplitude threshold (µS) for SCR detection.
% 0.0 = Ledalab default (permissive); 0.05 = more conservative, common in literature.
% Affects CDA.nSCR, CDA.AmpSum, CDA.Latency, and the SCR-list — NOT CDA.SCR.
AMP_THRESHOLD = 0.05;

% ── RUN BATCH ─────────────────────────────────────────────────────────────────

Ledalab(DATA_DIR,                                      ...
    'open',           'leda',                           ...  % generic .mat files (preprocessed by x02)
    'downsample',     5,                               ...  % 50 Hz → 10 Hz
    'analyze',        'CDA',                           ...
    'optimize',       4,                               ...  % 4 optimisation rounds
    'export_era',     [RESP_WIN_START, RESP_WIN_END, AMP_THRESHOLD, 2], ...  % filetype 2 = text
    'export_scrlist', [AMP_THRESHOLD, 2],              ...  % filetype 2 = text
    'overview',       1)                                    % save QC images
