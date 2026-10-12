% run_ledalab_batch.m
% ====================
% Ledalab batch CDA analysis for all participants.
%
% Derived from pilot analysis of participant 001 (Ledalab v3.49):
%   CDA tau       : [2.069, 3.191]  (optimised Bateman function parameters)
%   smoothwin     : 0.2 s
%   tonicGridSize : 10
%
% Sampling rate
% -------------
% The .mat files in RAW_DIR are BIOPAC exports at 2000 Hz (isi = 0.5 ms), so the
% downsample factor is computed from EXPECTED_INPUT_HZ / TARGET_HZ rather than
% hardcoded. It previously read 5, which assumed a separate 2000 -> 50 Hz
% pre-processing pass that is not part of this pipeline; run against 2000 Hz
% input that silently produced 400 Hz instead of 10 Hz.
%
% 10 Hz is the target because it is what every existing result was produced at,
% and because EDA carries no meaningful energy near that limit — SCRs rise over
% 1-3 s, so 10 Hz is far above Nyquist for the signal while keeping CDA
% deconvolution tractable. The preflight below refuses to run on input that is
% not at EXPECTED_INPUT_HZ.
%
% Pipeline
% --------
%   1. Run Ledalab batch CDA on RAW_DIR (files processed in-place):
%        a. Downsample 2000 Hz → 10 Hz (factor 200)
%        b. CDA with 4-round optimisation
%        c. Export ERA  : response window 0–180 s, threshold 0.05 µS → text
%        d. Export SCR-list : threshold 0.05 µS → text
%        e. Save QC overview images
%   2. Move all generated output files from RAW_DIR to OUT_DIR:
%        *_era.txt, *_scrlist.txt, *.jpg, *.mat (analysis-embedded)
%
% Output (moved to OUT_DIR after analysis)
% ----------------------------------------
%   {pid}_eda.mat   — Ledalab .mat with analysis embedded
%   {pid}_era.txt          — event-related activation (one row per event)
%   {pid}_scrlist.txt      — list of all detected SCRs
%   {pid}_overview.jpg     — decomposition QC image
%
% Usage
% -----
%   From the Matlab command window or as a batch job:
%     run('/path/to/run_ledalab_batch.m')

% ── CONFIGURATION ─────────────────────────────────────────────────────────────

LEDALAB_PATH = '/its/home/cm909/matlab_toolboxes/ledalab/';
RAW_DIR      = '/its/research/cisc2/projects/sdl_emotioncontrol/Biosignals2/data/ledalab/input/';
OUT_DIR      = '/its/research/cisc2/projects/sdl_emotioncontrol/Biosignals2/data/ledalab/';

% Sampling rate of the BIOPAC .mat exports in RAW_DIR, and the rate CDA runs at.
% The factor is derived, not hardcoded, so the two can never drift apart.
EXPECTED_INPUT_HZ = 2000;
TARGET_HZ         = 10;
DOWNSAMPLE_FACTOR = EXPECTED_INPUT_HZ / TARGET_HZ;   % 200

RESP_WIN_START = 0;
RESP_WIN_END   = 180;

% 0.05 µS threshold — standard in the literature.
% Affects CDA.nSCR, CDA.AmpSum, CDA.Latency, SCR-list — NOT CDA.SCR.
AMP_THRESHOLD  = 0.05;

% File format of raw physiology files.
% 'biopacmat' = MATLAB export from BioPac (most likely)
% 'leda'      = already-saved Ledalab .mat files
OPEN_FORMAT    = 'biopacmat';

% ── STEP 1: RUN LEDALAB BATCH ─────────────────────────────────────────────────

addpath(LEDALAB_PATH);

% ── Preflight: every input must be at EXPECTED_INPUT_HZ ───────────────────────
% A file at another rate would be silently analysed at the wrong sampling rate,
% which is exactly how the old hardcoded factor of 5 went unnoticed.
in_files = dir(fullfile(RAW_DIR, '*.mat'));
if isempty(in_files)
    error('No .mat files found in RAW_DIR: %s', RAW_DIR);
end

bad = {};
for f = 1:numel(in_files)
    S = load(fullfile(RAW_DIR, in_files(f).name), 'isi', 'isi_units');
    if ~isfield(S, 'isi')
        bad{end+1} = sprintf('%s (no isi field — not a BIOPAC export?)', in_files(f).name); %#ok<SAGROW>
        continue
    end
    % isi is the inter-sample interval; BIOPAC exports it in milliseconds.
    if isfield(S, 'isi_units') && contains(lower(char(S.isi_units)), 'ms')
        hz = 1000 / S.isi;
    else
        hz = 1 / S.isi;
    end
    if abs(hz - EXPECTED_INPUT_HZ) > 1
        bad{end+1} = sprintf('%s (%.1f Hz)', in_files(f).name, hz); %#ok<SAGROW>
    end
end

if ~isempty(bad)
    error(['Input files are not at %g Hz, so a downsample factor of %g would ' ...
           'not give %g Hz:\n  %s\nFix EXPECTED_INPUT_HZ or re-export these files.'], ...
           EXPECTED_INPUT_HZ, DOWNSAMPLE_FACTOR, TARGET_HZ, strjoin(bad, '\n  '));
end

fprintf('Preflight OK: %d input file(s) at %g Hz.\n', numel(in_files), EXPECTED_INPUT_HZ);
fprintf('Downsampling %g Hz -> %g Hz (factor %g)\n', ...
        EXPECTED_INPUT_HZ, TARGET_HZ, DOWNSAMPLE_FACTOR);
fprintf('Starting Ledalab batch analysis on: %s\n', RAW_DIR);

Ledalab(RAW_DIR,                                       ...
    'open',           OPEN_FORMAT,                     ...
    'downsample',     DOWNSAMPLE_FACTOR,               ...  % 2000 Hz → 10 Hz
    'analyze',        'CDA',                           ...
    'optimize',       4,                               ...
    'export_era',     [RESP_WIN_START, RESP_WIN_END, AMP_THRESHOLD, 2], ...
    'export_scrlist', [AMP_THRESHOLD, 2],              ...
    'overview',       1)

% ── STEP 2: MOVE OUTPUTS TO OUT_DIR ───────────────────────────────────────────

if ~exist(OUT_DIR, 'dir')
    mkdir(OUT_DIR);
    fprintf('Created output directory: %s\n', OUT_DIR);
end

output_patterns = {'*_era.txt', '*_scrlist.txt', '*.jpg'};

fprintf('\nMoving output files to: %s\n', OUT_DIR);
for p = 1:numel(output_patterns)
    files = dir(fullfile(RAW_DIR, output_patterns{p}));
    for f = 1:numel(files)
        src = fullfile(RAW_DIR, files(f).name);
        dst = fullfile(OUT_DIR, files(f).name);
        movefile(src, dst);
        fprintf('  Moved: %s\n', files(f).name);
    end
end

fprintf('\nDone. Results in: %s\n', OUT_DIR);
