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
%   0. Pick the inputs: only *.mat files in RAW_DIR, and only participants whose
%      EDA has not been extracted yet, i.e. OUT_DIR has no {pid}_*era.txt AND
%      {pid}_*scrlist.txt (participant IDs ignore case). Put an ID in REDO_PIDS to
%      analyse that participant again.
%   1. Copy those .mat files into a temporary folder and run Ledalab batch CDA there,
%      so Ledalab only ever sees the files to analyse (no other file types, nobody
%      already done). The originals in RAW_DIR are left untouched.
%        a. Downsample 2000 Hz → 10 Hz (factor 200)
%        b. CDA with 4-round optimisation
%        c. Export ERA  : response window 0–180 s, threshold 0.05 µS → text
%        d. Export SCR-list : threshold 0.05 µS → text
%        e. Save QC overview images
%   2. Move the outputs from the temporary folder to OUT_DIR:
%        *_era.txt, *_scrlist.txt, *.jpg, and each .mat that Ledalab saved its
%        analysis into. Then delete the temporary folder.
%
% Output (in OUT_DIR)
% -------------------
%   {pid}_eda.mat          — Ledalab .mat with analysis embedded (if Ledalab saved one)
%   {pid}_eda_era.txt      — event-related activation (one row per event)
%   {pid}_eda_scrlist.txt  — list of all detected SCRs
%   *.jpg                  — decomposition QC image
%
% Usage
% -----
%   From the Matlab command window or as a batch job:
%     run('/path/to/run_ledalab_batch.m')

% ── CONFIGURATION ─────────────────────────────────────────────────────────────

LEDALAB_PATH = 'C:/Program Files/MATLAB/R2026a/ledalab-349/';
RAW_DIR      = 'C:/Users/carme/Box/Project_Biosignals_study_2/3_Data/ledalab/input/';
OUT_DIR      = 'C:/Users/carme/Box/Project_Biosignals_study_2/3_Data/ledalab/';

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

% Participants to analyse again even though OUT_DIR already has their results
% (any case, e.g. {'k6294', 'S9686'}). Their old outputs are overwritten.
REDO_PIDS      = {};

% ── STEP 0: WHICH FILES TO ANALYSE ────────────────────────────────────────────

addpath(LEDALAB_PATH);
if ~exist(OUT_DIR, 'dir')
    mkdir(OUT_DIR);
    fprintf('Created output directory: %s\n', OUT_DIR);
end

all_files = dir(fullfile(RAW_DIR, '*.mat'));        % .mat only; everything else is ignored
all_files = all_files(~[all_files.isdir]);
if isempty(all_files)
    error('No .mat files found in RAW_DIR: %s', RAW_DIR);
end

redo = lower(strtrim(string(REDO_PIDS)));
todo = false(1, numel(all_files));
fprintf('Input .mat files in %s:\n', RAW_DIR);
for f = 1:numel(all_files)
    pid = pid_of(all_files(f).name);
    done = has_results(OUT_DIR, pid);
    todo(f) = ~done || any(pid == redo);
    if ~todo(f)
        fprintf('  skip   %-35s (%s already extracted)\n', all_files(f).name, pid);
    elseif done
        fprintf('  REDO   %-35s (in REDO_PIDS)\n', all_files(f).name);
    else
        fprintf('  new    %s\n', all_files(f).name);
    end
end
in_files = all_files(todo);

if isempty(in_files)
    fprintf('\nNothing to do: every participant in RAW_DIR already has results in %s.\n', OUT_DIR);
    fprintf('Add IDs to REDO_PIDS to analyse someone again.\n');
    return
end

% Two input files for one participant (e.g. K6294_eda.mat and k6294_eda.mat) can't be
% told apart once IDs ignore case: stop rather than analyse both.
pids = arrayfun(@(x) pid_of(x.name), in_files, 'UniformOutput', false);
[u, ~, k] = unique(pids);
dup = u(accumarray(k(:), 1) > 1);
if ~isempty(dup)
    error('Several input .mat files for the same participant (IDs ignore case): %s. Move the wrong one out of RAW_DIR.', ...
          strjoin(dup, ', '));
end

% ── Preflight: every input must be at EXPECTED_INPUT_HZ ───────────────────────
% A file at another rate would be silently analysed at the wrong sampling rate,
% which is exactly how the old hardcoded factor of 5 went unnoticed.
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

fprintf('\nPreflight OK: %d file(s) to analyse at %g Hz.\n', numel(in_files), EXPECTED_INPUT_HZ);
fprintf('Downsampling %g Hz -> %g Hz (factor %g)\n', ...
        EXPECTED_INPUT_HZ, TARGET_HZ, DOWNSAMPLE_FACTOR);

% ── STEP 1: RUN LEDALAB BATCH ON A COPY OF THE FILES TO ANALYSE ───────────────
% Ledalab's batch mode processes every file in the folder it is given, so it gets a
% temporary folder holding only these .mat files.

STAGE_DIR = fullfile(tempdir, ['ledalab_batch_' char(datetime('now', 'Format', 'yyyyMMdd_HHmmss'))]);
mkdir(STAGE_DIR);
for f = 1:numel(in_files)
    copyfile(fullfile(RAW_DIR, in_files(f).name), fullfile(STAGE_DIR, in_files(f).name));
end
t_start = now;

fprintf('Starting Ledalab batch analysis on %d file(s) (temporary copy in %s)\n', numel(in_files), STAGE_DIR);
try
    Ledalab([STAGE_DIR filesep],                       ...
        'open',           OPEN_FORMAT,                     ...
        'downsample',     DOWNSAMPLE_FACTOR,               ...  % 2000 Hz → 10 Hz
        'analyze',        'CDA',                           ...
        'optimize',       4,                               ...
        'export_era',     [RESP_WIN_START, RESP_WIN_END, AMP_THRESHOLD, 2], ...
        'export_scrlist', [AMP_THRESHOLD, 2],              ...
        'overview',       1)
catch err
    fprintf(2, '\nLedalab failed. Its working copy is kept for inspection: %s\n', STAGE_DIR);
    rethrow(err);
end

% ── STEP 2: MOVE OUTPUTS TO OUT_DIR ───────────────────────────────────────────

fprintf('\nMoving output files to: %s\n', OUT_DIR);
output_patterns = {'*_era.txt', '*_scrlist.txt', '*.jpg'};
for p = 1:numel(output_patterns)
    files = dir(fullfile(STAGE_DIR, output_patterns{p}));
    for f = 1:numel(files)
        movefile(fullfile(STAGE_DIR, files(f).name), fullfile(OUT_DIR, files(f).name), 'f');
        fprintf('  Moved: %s\n', files(f).name);
    end
end
% .mat files Ledalab saved its analysis into (changed since the copy) go to OUT_DIR;
% unchanged copies are just discarded (the original is still in RAW_DIR).
files = dir(fullfile(STAGE_DIR, '*.mat'));
for f = 1:numel(files)
    if files(f).datenum >= t_start
        movefile(fullfile(STAGE_DIR, files(f).name), fullfile(OUT_DIR, files(f).name), 'f');
        fprintf('  Moved: %s (Ledalab analysis)\n', files(f).name);
    end
end
rmdir(STAGE_DIR, 's');

% Did every participant get both result files?
missing = {};
for f = 1:numel(in_files)
    pid = pid_of(in_files(f).name);
    if ~has_results(OUT_DIR, pid)
        missing{end+1} = in_files(f).name; %#ok<SAGROW>
    end
end
if ~isempty(missing)
    warning('No ERA and/or SCR-list output for: %s', strjoin(missing, ', '));
end

fprintf('\nDone. Analysed %d file(s), skipped %d already extracted. Results in: %s\n', ...
        numel(in_files), numel(all_files) - numel(in_files), OUT_DIR);

% ── HELPERS ───────────────────────────────────────────────────────────────────

function pid = pid_of(name)
% Participant ID = file name up to the first "_", lower case (IDs ignore case).
    [~, base] = fileparts(name);
    pid = lower(strtrim(extractBefore([base '_'], '_')));
end

function tf = has_results(folder, pid)
% TRUE if folder already has both an ERA and an SCR-list file for this participant.
    tf = any_for(dir(fullfile(folder, '*_era.txt')), pid) && ...
         any_for(dir(fullfile(folder, '*_scrlist.txt')), pid);
end

function tf = any_for(files, pid)
    tf = false;
    for i = 1:numel(files)
        if strcmp(pid_of(files(i).name), pid)
            tf = true;
            return
        end
    end
end
