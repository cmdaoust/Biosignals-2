% x03_preprocess_scr.m
%
% Loops PsPM SCR preprocessing over all participants.
% For each participant, runs two steps as a single batch:
%   1. Import: reads AcqKnowledge-exported .mat file, extracts SCR from
%              channel 2. Uses acqmat import (not acq_python) with no
%              transfer function — the .mat export already contains
%              calibrated µS values.
%   2. Missing epoch detection: identifies artefact epochs and saves
%      a missing epoch file for use in the GLM.
% After each participant is processed, the imported .mat file is moved
% from raw_physiology/ to pspm/preprocessed/ immediately.
%
% INPUT FILES: {id}_physiology.mat  (exported from AcqKnowledge as MATLAB)
%
% Run from within MATLAB with PsPM initialised (run pspm first).
% Run order: 01 — before x04_run_sf.m

% ── Load config ───────────────────────────────────────────────────────────────
REPO_ROOT = fileparts(fileparts(fileparts(mfilename('fullpath'))));

config_path = fullfile(REPO_ROOT, 'config.m');
if ~isfile(config_path)
    error('config.m not found at:\n  %s\nCopy config_template.m to config.m and fill in your paths.', config_path);
end
run(config_path);

if isempty(SERVER_ROOT)
    error('SERVER_ROOT is empty in config.m. Fill in the path to the project root on this machine.');
end

% ── Initialise PsPM ───────────────────────────────────────────────────────────
addpath(PSPM_PATH);
pspm;

% ── Settings ──────────────────────────────────────────────────────────────────
% When called from run_all_pspm.m, the parent script sets SKIP_EXISTING;
% the default here is used only when the script is run standalone.
if ~exist('SKIP_EXISTING', 'var')
    SKIP_EXISTING = false;
end

% ── Paths ─────────────────────────────────────────────────────────────────────
RAW_DIR          = fullfile(SERVER_ROOT, 'raw_physiology');
PREPROCESSED_DIR = fullfile(SERVER_ROOT, 'pspm', 'preprocessed');
EPOCH_DIR        = fullfile(SERVER_ROOT, 'pspm', 'missing epoch');

% ── Participant IDs ───────────────────────────────────────────────────────────
% Looks for AcqKnowledge .mat exports: {id}_physiology.mat
% These must be exported from AcqKnowledge (File > Save As > MATLAB).
% Excludes pspm_* files (PsPM output) by matching only files whose name
% starts with digits.
mat_files = dir(fullfile(RAW_DIR, '*_physiology.mat'));
mat_files = mat_files(~strncmp({mat_files.name}, 'pspm_', 5));

if isempty(mat_files)
    error('No *_physiology.mat files found in:\n  %s\nExport .mat files from AcqKnowledge (File > Save As > MATLAB).', RAW_DIR);
end

participant_ids = cellfun(@(f) regexp(f, '^\d+', 'match', 'once'), ...
    {mat_files.name}, 'UniformOutput', false);

fprintf('Found %d participants: %s\n', numel(participant_ids), ...
    strjoin(participant_ids, ', '));

% ── Loop ──────────────────────────────────────────────────────────────────────
for i = 1:numel(participant_ids)
    id = participant_ids{i};

    fprintf('\n=== Processing sub-%s ===\n', id);

    mat_file = fullfile(RAW_DIR, [id '_physiology.mat']);

    if ~isfile(mat_file)
        warning('MAT file not found, skipping sub-%s:\n  %s', id, mat_file);
        continue
    end

    % ── Skip if output already exists ─────────────────────────────────────────
    imported_file = fullfile(PREPROCESSED_DIR, ['pspm_' id '_physiology.mat']);
    epoch_file    = fullfile(EPOCH_DIR, [id '_missing_epoch.mat']);

    if SKIP_EXISTING && isfile(imported_file) && isfile(epoch_file)
        fprintf('Skipping sub-%s (output files already exist).\n', id);
        continue
    end

    % ── Batch 1: Import ───────────────────────────────────────────────────────
    % acqmat reads AcqKnowledge .mat exports; data is already in µS so
    % scr_transfer.none passes it through without conversion.
    matlabbatch{1}.pspm{1}.prep{1}.import.datatype.acqmat.datafile                          = {mat_file};
    matlabbatch{1}.pspm{1}.prep{1}.import.datatype.acqmat.importtype{1}.scr.chan_nr.chan_nr_spec = 2;
    matlabbatch{1}.pspm{1}.prep{1}.import.datatype.acqmat.importtype{1}.scr.scr_transfer.none   = true;
    matlabbatch{1}.pspm{1}.prep{1}.import.overwrite                                         = 2;

    % ── Batch 2: Missing epoch detection ─────────────────────────────────────
    matlabbatch{2}.pspm{1}.data_preprocessing{1}.pp_scr.datafile(1) = ...
        cfg_dep('Import: Output File', ...
            substruct('.','val', '{}',{1}, '.','val', '{}',{1}, '.','val', '{}',{1}), ...
            substruct('()',{':'}));
    matlabbatch{2}.pspm{1}.data_preprocessing{1}.pp_scr.chan.chan_def                                        = 0;
    matlabbatch{2}.pspm{1}.data_preprocessing{1}.pp_scr.outputtype.output.file                              = [id '_missing_epoch'];
    matlabbatch{2}.pspm{1}.data_preprocessing{1}.pp_scr.outputtype.output.dir                               = {EPOCH_DIR};
    matlabbatch{2}.pspm{1}.data_preprocessing{1}.pp_scr.outputtype.output.overwrite                         = 2;
    matlabbatch{2}.pspm{1}.data_preprocessing{1}.pp_scr.options.min                                         = 0.05;
    matlabbatch{2}.pspm{1}.data_preprocessing{1}.pp_scr.options.max                                         = 60;
    matlabbatch{2}.pspm{1}.data_preprocessing{1}.pp_scr.options.slope                                       = 10;
    matlabbatch{2}.pspm{1}.data_preprocessing{1}.pp_scr.options.deflection_threshold                        = 0.1;
    matlabbatch{2}.pspm{1}.data_preprocessing{1}.pp_scr.options.data_island_threshold                       = 0;
    matlabbatch{2}.pspm{1}.data_preprocessing{1}.pp_scr.options.expand_epochs                               = 0.5;
    matlabbatch{2}.pspm{1}.data_preprocessing{1}.pp_scr.options.clipping_detection.clipping_step_size       = 2;
    matlabbatch{2}.pspm{1}.data_preprocessing{1}.pp_scr.options.clipping_detection.clipping_threshold       = 0.1;

    % ── Run both steps together so cfg_dep resolves correctly ─────────────────
    try
        cfg_util('run', matlabbatch);
        fprintf('Done: sub-%s\n', id);
    catch ME
        warning('Error processing sub-%s:\n  %s', id, ME.message);
        clear matlabbatch
        continue
    end

    % ── Move imported file to preprocessed directory ──────────────────────────
    % PsPM saves the imported .mat next to the raw input file; move it now
    % so it is in the right place before the SF models run.
    src_file = fullfile(RAW_DIR, ['pspm_' id '_physiology.mat']);
    if isfile(src_file)
        try
            movefile(src_file, imported_file);
            fprintf('Moved: pspm_%s_physiology.mat → preprocessed dir\n', id);
        catch ME
            warning('Could not move file for sub-%s:\n  %s', id, ME.message);
        end
    else
        warning('Imported file not found for sub-%s:\n  %s', id, src_file);
    end

    clear matlabbatch
end

fprintf('\n=== Preprocessing complete ===\n');
