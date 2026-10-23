% run_ledalab_batch.m
% ====================
% Ledalab batch CDA analysis for all participants, with the block event markers
% loaded, so Ledalab exports both the SCR list AND the event-related (ERA) results.
%
% Derived from pilot analysis of participant 001 (Ledalab v3.49):
%   CDA tau       : [2.069, 3.191]  (optimised Bateman function parameters)
%   smoothwin     : 0.2 s
%   tonicGridSize : 10
%
% Why events have to be added here
% --------------------------------
% Opening the BIOPAC exports directly ('open', 'biopacmat') brings in the signal only.
% With no events, Ledalab silently skips the ERA export: the 22 Oct 2026 run produced SCR
% lists but no _era.txt for anyone. Earlier ERA files came from adding events by hand in
% the GUI. So this script builds a Ledalab-format .mat for each participant - signal +
% block events from event_onsets/blocks/<id>_events_blocks_biopac_ledalab.txt - and runs
% the batch on those with 'open', 'leda'.
%
% The original files are never changed
% ------------------------------------
% The Ledalab-format files are built in a temporary folder and Ledalab runs there. The
% raw BIOPAC exports in RAW_DIR are only read. (The old version ran Ledalab in RAW_DIR,
% and Ledalab saved its results over the raw exports.)
%
% Sampling rate
% -------------
% The .mat files in RAW_DIR are BIOPAC exports at 2000 Hz (isi = 0.5 ms), so the
% downsample factor is computed from EXPECTED_INPUT_HZ / TARGET_HZ rather than
% hardcoded. 10 Hz is the target because it is what every existing result was produced
% at; SCRs rise over 1-3 s, so 10 Hz is far above Nyquist for the signal while keeping
% CDA deconvolution tractable. The preflight refuses input not at EXPECTED_INPUT_HZ.
%
% Pipeline
% --------
%   0. Pick the inputs: *.mat files in RAW_DIR (not batchmode_protocol.mat), for
%      participants whose EDA hasn't been extracted yet, i.e. OUT_DIR doesn't have BOTH a
%      non-empty {pid}*_era.txt and a non-empty {pid}*_scrlist.txt (IDs ignore case).
%      REDO_PIDS / REDO_ALL analyse participants again anyway; ONLY_PIDS limits the run
%      (e.g. to test one participant first).
%   1. Preflight: each input must be a raw BIOPAC export at EXPECTED_INPUT_HZ, and have a
%      BIOPAC events file whose onsets fall inside the recording. Participants that fail
%      are skipped and listed (a wrong sampling rate stops the run).
%   2. Build {pid}.mat in Ledalab format in a temporary folder:
%        fileinfo (version, date, log), data.conductance, data.time (0, dt, 2dt, ...),
%        data.timeoff, data.event(i).time / .nid / .name / .userdata
%   3. Run Ledalab batch CDA there ('open', 'leda'):
%        a. Downsample 2000 Hz -> 10 Hz (factor 200)
%        b. CDA with 4-round optimisation
%        c. Export ERA  : response window 0-180 s, threshold 0.05 µS -> text
%        d. Export SCR-list : threshold 0.05 µS -> text
%        e. Save QC overview images
%   4. Move the outputs to OUT_DIR (*_era.txt, *_scrlist.txt, *.tif/*.jpg, and each .mat
%      Ledalab saved its analysis into), delete the temporary folder, and check every
%      participant got an ERA file with one row per event.
%
% Output (in OUT_DIR)
% -------------------
%   {pid}.mat          - Ledalab .mat with events + analysis
%   {pid}_era.txt      - event-related activation (one row per block)
%   {pid}_scrlist.txt  - list of all detected SCRs
%   {pid}.tif          - decomposition QC (overview) image
%
% Usage
% -----
%   From the Matlab command window or as a batch job:
%     run('/path/to/run_ledalab_batch.m')
%   First time: set ONLY_PIDS = {'s1250'} (someone with an older ERA file) and REDO_PIDS
%   = {'s1250'}, and compare the new _era.txt with the old one before running everyone.

% ── CONFIGURATION ─────────────────────────────────────────────────────────────

LEDALAB_PATH = 'C:/Program Files/MATLAB/R2026a/ledalab-349/';
RAW_DIR      = 'C:/Users/carme/Box/Project_Biosignals_study_2/3_Data/ledalab/input/';   % raw BIOPAC exports (read only)
OUT_DIR      = 'C:/Users/carme/Box/Project_Biosignals_study_2/3_Data/ledalab/';
EVENTS_DIR   = 'C:/Users/carme/Box/Project_Biosignals_study_2/3_Data/event_onsets/blocks/';
% Event files: <id>_events_blocks_biopac_ledalab.txt (time, nid) from
% ledalab/01_create_ledalab_events_biopac.py, and the nid -> block name legend:
NID_MAP_FILE = 'nid_map_biopac_ledalab.txt';

% Sampling rate of the BIOPAC .mat exports in RAW_DIR, and the rate CDA runs at.
EXPECTED_INPUT_HZ = 2000;
TARGET_HZ         = 10;
DOWNSAMPLE_FACTOR = EXPECTED_INPUT_HZ / TARGET_HZ;   % 200

RESP_WIN_START = 0;
RESP_WIN_END   = 180;

% 0.05 µS threshold — standard in the literature.
% Affects CDA.nSCR, CDA.AmpSum, CDA.Latency, SCR-list — NOT CDA.SCR.
AMP_THRESHOLD  = 0.05;

% Participants to analyse again even though OUT_DIR already has their results
% (any case, e.g. {'k6294', 'S9686'}), or REDO_ALL = true for everyone. Old outputs
% are overwritten.
REDO_PIDS = {'r2433', 'r4755', 's9686'};   % still had ERA files from the old (GUI) method
REDO_ALL  = false;

% Run only these participants (any case); {} = everyone.
ONLY_PIDS = {};

% ── STEP 0: WHICH FILES TO ANALYSE ────────────────────────────────────────────

addpath(LEDALAB_PATH);
if ~exist(OUT_DIR, 'dir')
    mkdir(OUT_DIR);
    fprintf('Created output directory: %s\n', OUT_DIR);
end

all_files = dir(fullfile(RAW_DIR, '*.mat'));        % .mat only; everything else is ignored
all_files = all_files(~[all_files.isdir] & ~strcmpi({all_files.name}, 'batchmode_protocol.mat'));
if isempty(all_files)
    error('No .mat files found in RAW_DIR: %s', RAW_DIR);
end

redo = lower(strtrim(string(REDO_PIDS)));
only = lower(strtrim(string(ONLY_PIDS)));
todo = false(1, numel(all_files));
fprintf('Input .mat files in %s:\n', RAW_DIR);
for f = 1:numel(all_files)
    pid = pid_of(all_files(f).name);
    if ~isempty(only) && ~any(pid == only)
        continue                                     % not in ONLY_PIDS: not listed
    end
    done = has_results(OUT_DIR, pid);
    todo(f) = ~done || REDO_ALL || any(pid == redo);
    if ~todo(f)
        fprintf('  skip   %-35s (%s already extracted)\n', all_files(f).name, pid);
    elseif done
        fprintf('  REDO   %s\n', all_files(f).name);
    else
        fprintf('  new    %s\n', all_files(f).name);
    end
end
in_files = all_files(todo);

if isempty(in_files)
    fprintf('\nNothing to do: every participant selected already has results in %s.\n', OUT_DIR);
    fprintf('Use REDO_PIDS / REDO_ALL to analyse someone again.\n');
    return
end

% Two input files for one participant (e.g. K6294.mat and k6294.mat) can't be told
% apart once IDs ignore case: stop rather than analyse both.
pids = arrayfun(@(x) pid_of(x.name), in_files, 'UniformOutput', false);
[u, ~, k] = unique(pids);
dup = u(accumarray(k(:), 1) > 1);
if ~isempty(dup)
    error('Several input .mat files for the same participant (IDs ignore case): %s. Move the wrong one out of RAW_DIR.', ...
          strjoin(dup, ', '));
end

% ── STEP 1: PREFLIGHT ─────────────────────────────────────────────────────────

% Sampling rate: a file at another rate would be silently analysed at the wrong rate.
% A file without isi is not a raw BIOPAC export (e.g. a Ledalab output saved over it).
bad = {};
not_raw = false(1, numel(in_files));
for f = 1:numel(in_files)
    S = load_quiet(fullfile(RAW_DIR, in_files(f).name), {'isi', 'isi_units'});
    if ~isfield(S, 'isi')
        not_raw(f) = true;
        continue
    end
    hz = 1 / isi_seconds(S);
    if abs(hz - EXPECTED_INPUT_HZ) > 1
        bad{end+1} = sprintf('%s (%.1f Hz)', in_files(f).name, hz); %#ok<SAGROW>
    end
end
if ~isempty(bad)
    error(['Input files are not at %g Hz, so a downsample factor of %g would ' ...
           'not give %g Hz:\n  %s\nFix EXPECTED_INPUT_HZ or re-export these files.'], ...
           EXPECTED_INPUT_HZ, DOWNSAMPLE_FACTOR, TARGET_HZ, strjoin(bad, '\n  '));
end

% Events: the nid -> block name legend, and one events file per participant
nid_map = readtable(fullfile(EVENTS_DIR, NID_MAP_FILE), 'Delimiter', '\t', 'FileType', 'text', ...
                    'TextType', 'string');
ev_files = dir(fullfile(EVENTS_DIR, '*_events_blocks_biopac_ledalab.txt'));

% ── STEP 2: BUILD LEDALAB-FORMAT FILES (signal + events) IN A TEMPORARY FOLDER ─

STAGE_DIR = fullfile(tempdir, ['ledalab_batch_' char(datetime('now', 'Format', 'yyyyMMdd_HHmmss'))]);
mkdir(STAGE_DIR);

skipped = {};          % 'pid: reason'
% Files that aren't raw BIOPAC exports (no isi: e.g. a Ledalab output saved over the original)
% are skipped and listed; the rest of the run goes ahead.
for f = find(not_raw)
    skipped{end+1} = sprintf(['%s: %s is not a raw BIOPAC export (no isi) - probably a Ledalab output saved over ' ...
                              'the original; restore it (Box version history) or re-export it from AcqKnowledge'], ...
                             pid_of(in_files(f).name), in_files(f).name); %#ok<SAGROW>
end
in_files = in_files(~not_raw);
n_events = struct();   % pid -> number of events written (checked against the ERA file)
for f = 1:numel(in_files)
    pid = pid_of(in_files(f).name);
    ev_i = find(arrayfun(@(x) strcmp(pid_of(x.name), pid), ev_files), 1);
    if isempty(ev_i)
        skipped{end+1} = sprintf('%s: no %s_events_blocks_biopac_ledalab.txt in EVENTS_DIR (run ledalab/01_create_ledalab_events_biopac.py)', pid, pid); %#ok<SAGROW>
        continue
    end
    [ok, why, n_ev] = build_leda_file(fullfile(RAW_DIR, in_files(f).name), ...
                                      fullfile(EVENTS_DIR, ev_files(ev_i).name), nid_map, ...
                                      fullfile(STAGE_DIR, [pid '.mat']));
    if ~ok
        skipped{end+1} = sprintf('%s: %s', pid, why); %#ok<SAGROW>
        continue
    end
    n_events.(['p_' pid]) = n_ev;
    fprintf('  built  %s.mat  (%d events)\n', pid, n_ev);
end

staged = dir(fullfile(STAGE_DIR, '*.mat'));
if isempty(staged)
    rmdir(STAGE_DIR, 's');
    fprintf(2, '\nNo participant could be prepared:\n  %s\n', strjoin(skipped, '\n  '));
    return
end

fprintf('\nDownsampling %g Hz -> %g Hz (factor %g)\n', EXPECTED_INPUT_HZ, TARGET_HZ, DOWNSAMPLE_FACTOR);
fprintf('Starting Ledalab batch analysis on %d file(s) (temporary folder %s)\n', numel(staged), STAGE_DIR);
t_start = now;
orig_dir = pwd;   % Ledalab changes MATLAB's current folder to the one it analyses

% ── STEP 3: RUN LEDALAB ───────────────────────────────────────────────────────

try
    Ledalab([STAGE_DIR filesep],                       ...
        'open',           'leda',                          ...  % Ledalab-format files built above
        'downsample',     DOWNSAMPLE_FACTOR,               ...  % 2000 Hz -> 10 Hz
        'analyze',        'CDA',                           ...
        'optimize',       4,                               ...
        'export_era',     [RESP_WIN_START, RESP_WIN_END, AMP_THRESHOLD, 2], ...
        'export_scrlist', [AMP_THRESHOLD, 2],              ...
        'overview',       1)
catch err
    cd(orig_dir);
    fprintf(2, '\nLedalab failed. Its working folder is kept for inspection: %s\n', STAGE_DIR);
    rethrow(err);
end
cd(orig_dir);

% ── STEP 4: MOVE OUTPUTS TO OUT_DIR, THEN CHECK THEM ──────────────────────────

fprintf('\nMoving output files to: %s\n', OUT_DIR);
output_patterns = {'*_era.txt', '*_scrlist.txt', '*.jpg', '*.tif'};   % overview image is .tif in Ledalab 3.49
for p = 1:numel(output_patterns)
    files = dir(fullfile(STAGE_DIR, output_patterns{p}));
    for f = 1:numel(files)
        movefile(fullfile(STAGE_DIR, files(f).name), fullfile(OUT_DIR, files(f).name), 'f');
        fprintf('  Moved: %s\n', files(f).name);
    end
end
% .mat files Ledalab saved its analysis into go to OUT_DIR (not batchmode_protocol.mat)
files = dir(fullfile(STAGE_DIR, '*.mat'));
for f = 1:numel(files)
    if files(f).datenum >= t_start && ~strcmpi(files(f).name, 'batchmode_protocol.mat')
        movefile(fullfile(STAGE_DIR, files(f).name), fullfile(OUT_DIR, files(f).name), 'f');
        fprintf('  Moved: %s (Ledalab analysis)\n', files(f).name);
    end
end
try
    rmdir(STAGE_DIR, 's');
catch
    warning('Could not delete the temporary folder (a file in it may still be open): %s', STAGE_DIR);
end

% Every participant analysed should now have an ERA file with one row per event
problems = {};
for f = 1:numel(staged)
    pid = pid_of(staged(f).name);
    era = fullfile(OUT_DIR, [pid '_era.txt']);
    era_info = dir(era);
    if isempty(era_info) || era_info.bytes == 0
        problems{end+1} = sprintf('%s: no ERA file', pid); %#ok<SAGROW>
        continue
    end
    n_rows = height(readtable(era, 'Delimiter', '\t', 'FileType', 'text'));
    if n_rows ~= n_events.(['p_' pid])
        problems{end+1} = sprintf('%s: ERA has %d rows for %d events', pid, n_rows, n_events.(['p_' pid])); %#ok<SAGROW>
    end
    if ~has_results(OUT_DIR, pid)
        problems{end+1} = sprintf('%s: no SCR-list file', pid); %#ok<SAGROW>
    end
end

fprintf('\nDone. Analysed %d participant(s). Results in: %s\n', numel(staged), OUT_DIR);
if ~isempty(skipped)
    fprintf(2, 'Skipped (not analysed):\n  %s\n', strjoin(skipped, '\n  '));
end
if ~isempty(problems)
    warning('Check these outputs:\n  %s', strjoin(problems, '\n  '));
else
    fprintf('Every analysed participant has an ERA file with one row per block and an SCR list.\n');
end

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
% An empty (0-byte) file doesn't count: the export failed, so the participant is redone.
    tf = false;
    for i = 1:numel(files)
        if strcmp(pid_of(files(i).name), pid) && files(i).bytes > 0
            tf = true;
            return
        end
    end
end

function S = load_quiet(path, vars)
% load() only the variables in vars that the file contains (no "Variable not found" warnings)
    w = whos('-file', path);
    present = intersect(vars, {w.name});
    if isempty(present), S = struct(); else, S = load(path, present{:}); end
end

function dt = isi_seconds(S)
% BIOPAC exports the inter-sample interval (isi) in milliseconds.
    if isfield(S, 'isi_units') && contains(lower(char(S.isi_units)), 'ms')
        dt = double(S.isi) / 1000;
    else
        dt = double(S.isi);
    end
end

function [ok, why, n_ev] = build_leda_file(raw_path, ev_path, nid_map, out_path)
% Ledalab-format .mat (the layout Ledalab 3.49 saves: fileinfo + data) from a raw BIOPAC
% export plus the participant's block events.
    ok = false; why = ''; n_ev = 0;
    raw = load(raw_path);
    if ~isfield(raw, 'data')
        why = 'no data variable in the BIOPAC export'; return
    end
    sig = double(raw.data);
    if ~isvector(sig)
        % Several channels: use the one labelled as EDA
        labels = {};
        if isfield(raw, 'labels'), labels = cellstr(raw.labels); end
        k = find(contains(lower(labels), {'eda', 'gsr', 'skin', 'conductance'}), 1);
        if isempty(k) || numel(labels) ~= size(sig, 2)
            why = sprintf('%d channels in the export and none labelled EDA', size(sig, 2)); return
        end
        sig = sig(:, k);
    end
    dt = isi_seconds(raw);
    n  = numel(sig);

    ev = readtable(ev_path, 'Delimiter', '\t', 'FileType', 'text');
    if ~all(ismember({'time', 'nid'}, ev.Properties.VariableNames)) || height(ev) == 0
        why = 'events file has no time / nid rows'; return
    end
    dur = (n - 1) * dt;
    if any(ev.time < 0 | ev.time + 1 > dur)
        why = sprintf('event onsets (%.1f-%.1f s) outside the recording (0-%.1f s): wrong events file or untrimmed export?', ...
                      min(ev.time), max(ev.time), dur); return
    end

    data = struct();
    data.conductance = sig(:)';                % row vectors, as Ledalab saves them
    data.time        = (0:n-1) * dt;           % s from the start of the file, like the events
    data.timeoff     = 0;
    events = struct('time', {}, 'nid', {}, 'name', {}, 'userdata', {});
    for e = 1:height(ev)
        nm = nid_map.condition(nid_map.nid == ev.nid(e));
        if isempty(nm), nm = sprintf('event_%d', ev.nid(e)); else, nm = char(nm(1)); end
        events(e).time     = ev.time(e);
        events(e).nid      = ev.nid(e);
        events(e).name     = nm;
        events(e).userdata = [];
    end
    data.event = events;

    fileinfo = struct();
    fileinfo.version = 3.49;
    fileinfo.date    = clock;
    [~, rn, re] = fileparts(raw_path); [~, en, ee] = fileparts(ev_path);
    fileinfo.log = {sprintf('%s: built by run_ledalab_batch.m from %s and %s', ...
                    char(datetime('now', 'Format', 'HH:mm:ss')), [rn re], [en ee])};

    save(out_path, 'fileinfo', 'data', '-v7');
    ok = true; n_ev = numel(events);
end
