% run_all_pspm.m
%
% Master script: runs the full PsPM SCR pipeline in order.
%
%   Step 1 — x03_preprocess_scr.m   Import raw ACQ + missing epoch detection
%   Step 2 — x04_run_sf.m           Fit SF models (auc, scl, mp, dcm)
%   Step 3 — x05_sf_export_stats.m  Export SF model statistics to TSV
%
% SKIP_EXISTING controls:
%   Set each flag below to true  → skip participants who already have output files.
%   Set each flag below to false → reprocess everyone regardless.
%
% Each script also works as a standalone: when run directly (not from here),
% it falls back to its own default SKIP_EXISTING value.
%
% Run from within MATLAB with PsPM initialised (run pspm first).
% Alternatively, set RUN_PSPM_INIT = true below to initialise PsPM here.

% ── Per-script SKIP_EXISTING toggles ─────────────────────────────────────────
SKIP_X03 = false;   % Preprocessing  — false = re-import all participants
SKIP_X04 = false;    % SF models       — false  = re-fit models
SKIP_X05 = false;    % Stats export    — false  = re-fit already-exported stats

% ── Optional: initialise PsPM from here ──────────────────────────────────────
% Set to true if you are not running pspm; before executing this script.
RUN_PSPM_INIT = false;

if RUN_PSPM_INIT
    REPO_ROOT   = fileparts(fileparts(fileparts(mfilename('fullpath'))));
    config_path = fullfile(REPO_ROOT, 'config.m');
    if ~isfile(config_path)
        error('config.m not found at:\n  %s', config_path);
    end
    run(config_path);
    addpath(PSPM_PATH);
    pspm;
end

% ── Script paths ──────────────────────────────────────────────────────────────
SCRIPT_DIR = fileparts(mfilename('fullpath'));

% ── Step 1: Preprocessing ─────────────────────────────────────────────────────
fprintf('\n%s\n', repmat('=', 1, 60));
fprintf('STEP 1: Preprocessing (x03_preprocess_scr)\n');
fprintf('%s\n', repmat('=', 1, 60));
SKIP_EXISTING = SKIP_X03;
run(fullfile(SCRIPT_DIR, 'x03_preprocess_scr.m'));
clear SKIP_EXISTING

% ── Step 2: SF models ─────────────────────────────────────────────────────────
fprintf('\n%s\n', repmat('=', 1, 60));
fprintf('STEP 2: SF models (x04_run_sf)\n');
fprintf('%s\n', repmat('=', 1, 60));
SKIP_EXISTING = SKIP_X04;
run(fullfile(SCRIPT_DIR, 'x04_run_sf.m'));
clear SKIP_EXISTING

% ── Step 3: Export stats ──────────────────────────────────────────────────────
fprintf('\n%s\n', repmat('=', 1, 60));
fprintf('STEP 3: Export SF stats (x05_sf_export_stats)\n');
fprintf('%s\n', repmat('=', 1, 60));
SKIP_EXISTING = SKIP_X05;
run(fullfile(SCRIPT_DIR, 'x05_sf_export_stats.m'));
clear SKIP_EXISTING

% ── Done ──────────────────────────────────────────────────────────────────────
fprintf('\n%s\n', repmat('=', 1, 60));
fprintf('Pipeline complete.\n');
fprintf('%s\n', repmat('=', 1, 60));
