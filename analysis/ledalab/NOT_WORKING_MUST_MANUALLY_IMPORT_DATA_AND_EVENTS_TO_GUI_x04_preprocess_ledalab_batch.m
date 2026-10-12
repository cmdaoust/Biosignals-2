% x02_preprocess_ledalab_batch.m
% ==============================
% Convert raw Biopac .mat exports to Ledalab-format .mat files,
% injecting block event markers from the events .txt files.
%
% Run this script BEFORE x03_run_ledalab_batch.m.
%
% Input file naming convention:
%   Raw EDA  : {RAW_DIR}\{pid}.mat
%   Events   : {EVENTS_DIR}\{pid}_events_blocks_biopac_ledalab.txt
%
% Raw .mat structure (Biopac export):
%   data       — EDA signal vector (µS), sampled at 2000 Hz (isi = 0.5 ms)
%   isi        — inter-sample interval in ms (0.5 → 2000 Hz)
%   isi_units  — 'ms'
%   units      — 'microsiemens'
%
% Events .txt structure (tab-delimited, 5 rows):
%   time   — block onset in seconds (relative to recording start)
%   nid    — numeric block ID (1–5)
%
% NID → block name mapping:
%   1 = baseline
%   2 = negative_induction
%   3 = negative_recovery
%   4 = positive_induction
%   5 = positive_recovery
%
% Pipeline
% --------
%   1. Load raw .mat
%   2. Downsample 2000 Hz → 50 Hz (factor 40) using resample()
%        — resample() applies an anti-aliasing FIR filter before decimating
%   3. Read block onsets from matching events .txt
%   4. Build Ledalab data structure with embedded event markers
%   5. Save to OUT_DIR as {pid}.mat (Ledalab native format)
%
% Output
% ------
%   {OUT_DIR}\{pid}.mat  — Ledalab-format .mat, ready for x03_run_ledalab_batch.m

% ── CONFIGURATION ─────────────────────────────────────────────────────────────

RAW_DIR    = 'C:\Users\carme\Box\Project_Biosignals_study_2\3_Data\ledalab\input\';
EVENTS_DIR = 'C:\Users\carme\Box\Project_Biosignals_study_2\3_Data\event_onsets\blocks\';
OUT_DIR    = 'C:\Users\carme\Box\Project_Biosignals_study_2\3_Data\ledalab\preprocessed\';

SR_RAW     = 2000;   % Hz — raw Biopac sampling rate (isi = 0.5 ms)
SR_TARGET  =   50;   % Hz — target rate for Ledalab (CDA optimised tau from pilot)
DS_FACTOR  =   40;   % SR_RAW / SR_TARGET

% Block names indexed by nid (1–5)
BLOCK_NAMES = {'baseline', 'negative_induction', 'negative_recovery', ...
               'positive_induction', 'positive_recovery'};

% ── VALIDATE PATHS ────────────────────────────────────────────────────────────

assert(isfolder(RAW_DIR),    'RAW_DIR not found:\n  %s', RAW_DIR);
assert(isfolder(EVENTS_DIR), 'EVENTS_DIR not found:\n  %s', EVENTS_DIR);
assert(isfolder(OUT_DIR),    'OUT_DIR not found:\n  %s', OUT_DIR);

% ── PROCESS FILES ─────────────────────────────────────────────────────────────

raw_files = dir(fullfile(RAW_DIR, '*.mat'));

if isempty(raw_files)
    error('No .mat files found in RAW_DIR:\n  %s', RAW_DIR);
end

fprintf('Found %d file(s) to process.\n\n', numel(raw_files));

for i = 1:numel(raw_files)

    pid      = raw_files(i).name(1:end-4);  % strip .mat → participant ID
    raw_path = fullfile(RAW_DIR, raw_files(i).name);
    evt_path = fullfile(EVENTS_DIR, [pid '_events_blocks_biopac_ledalab.txt']);
    out_path = fullfile(OUT_DIR, [pid '.mat']);

    fprintf('[%d/%d] %s\n', i, numel(raw_files), pid);

    % ── Check events file exists ───────────────────────────────────────────
    if ~isfile(evt_path)
        warning('  Events file not found, skipping:\n    %s', evt_path);
        continue
    end

    % ── Load raw EDA ───────────────────────────────────────────────────────
    raw = load(raw_path);

    % Verify sampling rate matches expectation
    sr_actual = round(1000 / raw.isi);  % isi is in ms
    if sr_actual ~= SR_RAW
        warning('  Unexpected sampling rate %d Hz (expected %d Hz). Adjusting DS_FACTOR.', ...
            sr_actual, SR_RAW);
        ds = sr_actual / SR_TARGET;
    else
        ds = DS_FACTOR;
    end

    % ── Downsample ─────────────────────────────────────────────────────────
    signal_ds = resample(double(raw.data), 1, ds);
    n_samples  = numel(signal_ds);
    time_vec   = (0:n_samples-1)' / SR_TARGET;   % seconds

    fprintf('  Downsampled: %d → %d samples  (%.1f → %.1f s)\n', ...
        numel(raw.data), n_samples, numel(raw.data)/SR_RAW, time_vec(end));

    % ── Load events ────────────────────────────────────────────────────────
    evt_table = readtable(evt_path, 'Delimiter', '\t', 'FileType', 'text');
    n_events  = height(evt_table);

    fprintf('  Events: %d block onset(s)\n', n_events);

    % ── Build Ledalab data structure ───────────────────────────────────────
    % conductance
    data.conductance.data                  = signal_ds;
    data.conductance.session.starttime     = '00:00:00';
    data.conductance.session.sr            = SR_TARGET;

    % time
    data.time.data = time_vec;

    % events
    for e = 1:n_events
        t   = evt_table.time(e);
        nid = evt_table.nid(e);

        if nid >= 1 && nid <= numel(BLOCK_NAMES)
            bname = BLOCK_NAMES{nid};
        else
            bname = sprintf('event_%d', nid);
            warning('  nid %d out of range — labelled "%s"', nid, bname);
        end

        data.event(e).time     = t;
        data.event(e).nid      = nid;
        data.event(e).name     = bname;
        data.event(e).userdata = [];
    end

    % ── Save ───────────────────────────────────────────────────────────────
    save(out_path, 'data', '-v7');
    fprintf('  Saved → %s\n\n', out_path);

end

fprintf('Done. Run x03_run_ledalab_batch.m to proceed with CDA analysis.\n');
