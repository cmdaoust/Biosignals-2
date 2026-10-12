% x05_sf_export_stats.m
%
% Exports SF model statistics for all participants and all methods.
% For each model file in MODEL_DIR, exports parameter estimates to a
% tab-delimited text file in STATS_DIR.
%
% Methods exported: auc, scl, mp, dcm
%
% Run from within MATLAB with PsPM initialised (run pspm first).
% Run order: after x04_run_sf.m

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
    SKIP_EXISTING = true;
end

METHODS = {'auc', 'scl', 'mp', 'dcm'};

% ── Paths ─────────────────────────────────────────────────────────────────────
MODEL_DIR = fullfile(SERVER_ROOT, 'pspm', 'models');
STATS_DIR = fullfile(SERVER_ROOT, 'pspm', 'outputs');

if ~exist(STATS_DIR, 'dir')
    mkdir(STATS_DIR);
end

% ── Loop over methods ─────────────────────────────────────────────────────────
for m = 1:numel(METHODS)
    method = METHODS{m};

    fprintf('\n=== Method: %s ===\n', method);

    model_files = dir(fullfile(MODEL_DIR, ['*_sf_' method '_model.mat']));

    if isempty(model_files)
        fprintf('  No %s model files found — skipping.\n', method);
        continue
    end

    participant_ids = cellfun(@(f) regexp(f, '^(\d+)_sf_', 'tokens', 'once'), ...
        {model_files.name}, 'UniformOutput', false);
    participant_ids = [participant_ids{:}];

    fprintf('  Found %d participant(s): %s\n', numel(participant_ids), strjoin(participant_ids, ', '));

    for i = 1:numel(participant_ids)
        id = participant_ids{i};

        model_file  = fullfile(MODEL_DIR, [id '_sf_' method '_model.mat']);
        output_name = [id '_' method '_model_statistics'];
        output_file = fullfile(STATS_DIR, [output_name '.txt']);

        if SKIP_EXISTING && isfile(output_file)
            fprintf('  Skipping sub-%s %s (already exists).\n', id, method);
            continue
        end

        fprintf('  Exporting sub-%s %s ...\n', id, method);

        matlabbatch{1}.pspm{1}.first_level{1}.export.datafile                        = {model_file};
        matlabbatch{1}.pspm{1}.first_level{1}.export.datatype                        = 'param';
        matlabbatch{1}.pspm{1}.first_level{1}.export.exclude_missing                 = false;
        matlabbatch{1}.pspm{1}.first_level{1}.export.target.output.file              = output_name;
        matlabbatch{1}.pspm{1}.first_level{1}.export.target.output.dir               = {STATS_DIR};
        matlabbatch{1}.pspm{1}.first_level{1}.export.target.output.overwrite         = 2;
        matlabbatch{1}.pspm{1}.first_level{1}.export.delim.tab                       = '\t';

        try
            cfg_util('run', matlabbatch);
            fprintf('  Done: %s\n', output_name);
        catch ME
            warning('  Error exporting %s for sub-%s:\n  %s', method, id, ME.message);
        end

        clear matlabbatch
    end
end

fprintf('\n=== SF export complete ===\n');
fprintf('Stats saved to: %s\n', STATS_DIR);
