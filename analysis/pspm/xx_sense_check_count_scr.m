% xx_sense_check_count_scr.m
%
% Sense-check script: counts SCR peaks per epoch using simple peak detection
% on the preprocessed SCR signal.
%
% NOT for final analysis — use PsPM SF models (x04/x05) for that.
% Use this to verify that SF model outputs are in the expected ballpark,
% and to sanity-check epoch windows and signal quality.
%
% Does NOT require PsPM to be initialised — loads .mat files directly.
%
% Peak detection parameters (adjust as needed):
%   MIN_AMPLITUDE  — minimum peak prominence in µS (height above surrounding
%                    trough). Prominence is preferable to absolute height
%                    because it is baseline-independent.
%   MIN_DISTANCE   — minimum time between peaks in seconds. SCR rise time is
%                    typically 1–4 s; 1 s prevents double-counting one response.
%
% OUTPUT: sense_check_scr_counts.csv  (in pspm/outputs/)
%   columns: participant_id, epoch_num, onset, offset, scr_count
%
% Run order: after x03_preprocess_scr.m

% ── Load config ───────────────────────────────────────────────────────────────
REPO_ROOT = fileparts(fileparts(fileparts(mfilename('fullpath'))));

config_path = fullfile(REPO_ROOT, 'config.m');
if ~isfile(config_path)
    error('config.m not found at:\n  %s\nCopy config_template.m to config.m and fill in your paths.', config_path);
end
run(config_path);

if isempty(SERVER_ROOT)
    error('SERVER_ROOT is empty in config.m.');
end

% ── Settings ──────────────────────────────────────────────────────────────────
MIN_AMPLITUDE = 0.02;   % µS  — minimum peak prominence
MIN_DISTANCE  = 1.0;    % s   — minimum inter-peak interval

% ── Paths ─────────────────────────────────────────────────────────────────────
PREPROCESSED_DIR = fullfile(SERVER_ROOT, 'pspm', 'preprocessed');
EPOCHS_DIR       = fullfile(SERVER_ROOT, 'event_onsets', 'blocks');
OUTPUT_DIR       = fullfile(SERVER_ROOT, 'pspm', 'outputs');
OUTPUT_FILE      = fullfile(OUTPUT_DIR, 'sense_check_scr_counts.csv');

if ~isfolder(OUTPUT_DIR)
    mkdir(OUTPUT_DIR);
end

% ── Participant IDs ───────────────────────────────────────────────────────────
preprocessed_files = dir(fullfile(PREPROCESSED_DIR, 'pspm_*_physiology.mat'));

if isempty(preprocessed_files)
    error('No preprocessed files found in:\n  %s\nRun x03_preprocess_scr.m first.', PREPROCESSED_DIR);
end

participant_ids = cellfun(@(f) regexp(f, '(?<=pspm_)\d+', 'match', 'once'), ...
    {preprocessed_files.name}, 'UniformOutput', false);

fprintf('Found %d participants: %s\n', numel(participant_ids), strjoin(participant_ids, ', '));
fprintf('MIN_AMPLITUDE = %.3f µS,  MIN_DISTANCE = %.1f s\n\n', MIN_AMPLITUDE, MIN_DISTANCE);

% ── Output file ───────────────────────────────────────────────────────────────
fid = fopen(OUTPUT_FILE, 'w');
fprintf(fid, 'participant_id,epoch_num,onset,offset,scr_count\n');

% ── Loop over participants ────────────────────────────────────────────────────
for i = 1:numel(participant_ids)
    id = participant_ids{i};
    fprintf('=== Processing sub-%s ===\n', id);

    data_file   = fullfile(PREPROCESSED_DIR, ['pspm_' id '_physiology.mat']);
    epochs_file = fullfile(EPOCHS_DIR, [id '_epochs_conditions_psychopy.mat']);

    if ~isfile(data_file)
        warning('Preprocessed file not found, skipping sub-%s:\n  %s', id, data_file);
        continue
    end
    if ~isfile(epochs_file)
        warning('Epochs file not found, skipping sub-%s:\n  %s', id, epochs_file);
        continue
    end

    % ── Load SCR signal ───────────────────────────────────────────────────────
    pspm_struct = load(data_file);

    scr_chan = [];
    for c = 1:numel(pspm_struct.data)
        if strcmpi(pspm_struct.data{c}.header.chantype, 'scr')
            scr_chan = c;
            break
        end
    end

    if isempty(scr_chan)
        warning('No SCR channel found in preprocessed file for sub-%s', id);
        continue
    end

    signal      = pspm_struct.data{scr_chan}.data;
    sr          = pspm_struct.data{scr_chan}.header.sr;
    min_samples = round(MIN_DISTANCE * sr);

    fprintf('  SCR channel %d | sr=%.1f Hz | %d samples (%.1f s)\n', ...
        scr_chan, sr, numel(signal), numel(signal)/sr);

    % ── Load epochs ───────────────────────────────────────────────────────────
    epochs_struct = load(epochs_file);
    epochs        = epochs_struct.epochs;   % N×2 [onset, offset] in seconds

    fprintf('  %d epochs\n', size(epochs, 1));

    % ── Count peaks per epoch ─────────────────────────────────────────────────
    for e = 1:size(epochs, 1)
        onset  = epochs(e, 1);
        offset = epochs(e, 2);

        start_samp = max(1,             round(onset  * sr) + 1);
        end_samp   = min(numel(signal), round(offset * sr));

        if start_samp >= end_samp
            warning('  Epoch %d: invalid sample range (onset=%.2f, offset=%.2f) — skipping', ...
                e, onset, offset);
            fprintf(fid, '%s,%d,%.4f,%.4f,NA\n', id, e, onset, offset);
            continue
        end

        segment = signal(start_samp:end_samp);

        [~, ~, ~, prominences] = findpeaks(segment, ...
            'MinPeakProminence', MIN_AMPLITUDE, ...
            'MinPeakDistance',   min_samples);

        scr_count = numel(prominences);

        fprintf('  Epoch %2d  (%.1f – %.1f s)  →  %d peaks\n', e, onset, offset, scr_count);
        fprintf(fid, '%s,%d,%.4f,%.4f,%d\n', id, e, onset, offset, scr_count);
    end

    fprintf('\n');
end

fclose(fid);

fprintf('=== Done ===\n');
fprintf('Output: %s\n', OUTPUT_FILE);
