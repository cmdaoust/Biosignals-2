function batch_extract_kubios_hrv(mat_folder, output_csv)
% BATCH_EXTRACT_KUBIOS_HRV
%
% Reads all Kubios HRV .mat output files in a folder and consolidates all
% HRV metrics into a single long-format CSV.
%
% Output rows per participant:
%   - One row per protocol segment (5 segments, all metrics from Kubios)
%   - One 'whole_protocol' row recording the trimmed window boundaries
%     (marker 281 onset -> marker 340 offset) and beat count; HRV metric
%     columns are NaN because this window was not analyzed as a Kubios
%     segment. To get whole-protocol HRV metrics, define it as an
%     additional segment in Kubios before saving the .mat.
%
% Segment labels are derived from marker IDs (not Kubios-stored labels).
% Edit SEGMENT_MAP and PROTOCOL_MARKERS below to match your protocol.
%
% Participant ID = first 5 characters of the .acq filename in the .mat.
%
% Usage:
%   batch_extract_kubios_hrv()
%   batch_extract_kubios_hrv('C:\Data\mats')
%   batch_extract_kubios_hrv('C:\Data\mats', 'out.csv')
%
% Requires: MATLAB R2019b+ (v7.3 .mat support).
% -------------------------------------------------------------------------

    % =====================================================================
    % PROTOCOL CONFIGURATION  —  edit to match your study
    % =====================================================================

    % Segment definitions: {start_marker, end_marker, 'label'}
    SEGMENT_MAP = {
        281, 280, 'baseline';
        301, 290, 'negative_induction';
        311, 310, 'negative_recovery';
        331, 320, 'positive_induction';
        341, 340, 'positive_recovery';
    };

    % Whole-protocol trim: first and last markers of the experiment
    PROTOCOL_START_MARKER = 281;   % baseline onset
    PROTOCOL_END_MARKER   = 340;   % positive recovery offset

    % Segment-to-Kubios matching tolerance (seconds)
    TOL = 2.0;

    % ---- File pickers -------------------------------------------------------
    if nargin < 1 || isempty(mat_folder)
        mat_folder = uigetdir(pwd, 'Select folder containing Kubios .mat files');
        if isequal(mat_folder, 0), return; end
    end
    if nargin < 2 || isempty(output_csv)
        default_name = fullfile(mat_folder, 'HRV_results_all.csv');
        [f, p] = uiputfile('*.csv', 'Save consolidated CSV as', default_name);
        if isequal(f, 0), return; end
        output_csv = fullfile(p, f);
    end

    % ---- Discover .mat files ------------------------------------------------
    files = dir(fullfile(mat_folder, '*.mat'));
    if isempty(files)
        error('No .mat files found in: %s', mat_folder);
    end
    fprintf('Found %d .mat file(s) in: %s\n\n', length(files), mat_folder);

    all_rows = {};

    for fi = 1:length(files)
        mat_path = fullfile(mat_folder, files(fi).name);
        fprintf('[%d/%d] %s\n', fi, length(files), files(fi).name);

        try
            S   = load(mat_path);
            Res = S.Res;

            % --- Participant ID ----------------------------------------------
            acq_fname = decode_char(Res.f_name);
            [~, acq_base] = fileparts(acq_fname);
            participant_id = acq_base(1 : min(5, length(acq_base)));

            % --- Markers -----------------------------------------------------
            stim_type    = Res.CNT.CntEve.StimType(:);
            stim_time    = Res.CNT.CntEve.StimTime(:);
            kubios_times = Res.HRV.Param.Segments;   % (2 x N): start/stop in seconds

            % =================================================================
            % PART 1: per-segment rows (all metrics from Kubios)
            % =================================================================
            n_segs = size(SEGMENT_MAP, 1);

            for si = 1:n_segs
                start_id = SEGMENT_MAP{si, 1};
                end_id   = SEGMENT_MAP{si, 2};
                label    = SEGMENT_MAP{si, 3};

                t_start_vec = stim_time(stim_type == start_id);
                t_end_vec   = stim_time(stim_type == end_id);

                if isempty(t_start_vec) || isempty(t_end_vec)
                    fprintf('  WARNING: markers %d->%d not found for "%s" — skipping\n', ...
                            start_id, end_id, label);
                    continue;
                end

                t_start = t_start_vec(1);
                t_end   = t_end_vec(1);

                [min_diff, ki] = min(abs(kubios_times(1,:) - t_start));
                if min_diff > TOL
                    fprintf('  WARNING: no Kubios segment within %.1fs of %.2fs for "%s" — skipping\n', ...
                            TOL, t_start, label);
                    continue;
                end

                row = build_kubios_row(participant_id, si, label, t_start, t_end, ki, Res);
                all_rows{end+1} = row; %#ok<AGROW>
                fprintf('  + %-22s  [%s - %s]\n', label, sec2str(t_start), sec2str(t_end));
            end

            % =================================================================
            % PART 2: whole_protocol row — timing and beat count only
            %   HRV metrics are NaN (not a Kubios-analyzed segment).
            %   To get metrics here, define this window as a segment in
            %   Kubios before saving the .mat.
            % =================================================================
            t_ps_vec = stim_time(stim_type == PROTOCOL_START_MARKER);
            t_pe_vec = stim_time(stim_type == PROTOCOL_END_MARKER);

            if isempty(t_ps_vec) || isempty(t_pe_vec)
                fprintf('  WARNING: protocol trim markers not found — skipping whole_protocol row\n');
            else
                t_ps = t_ps_vec(1);
                t_pe = t_pe_vec(1);

                % Count beats in the protocol window from the corrected RR series
                T_RR_full  = Res.HRV.Data.T_RR(:);
                RR_full    = Res.HRV.Data.RR(:);
                beat_times = T_RR_full(2:end);   % T_RR has one extra leading ref point
                n_beats    = sum(beat_times >= t_ps & beat_times <= t_pe);

                prow = build_protocol_row(participant_id, t_ps, t_pe, n_beats);
                all_rows{end+1} = prow; %#ok<AGROW>
                fprintf('  + %-22s  [%s - %s]  (%d beats)\n', ...
                        'whole_protocol', sec2str(t_ps), sec2str(t_pe), n_beats);
            end

        catch ME
            fprintf('  ERROR: %s\n  %s (line %d)\n', ME.message, ...
                    ME.stack(1).file, ME.stack(1).line);
        end

        fprintf('\n');
    end

    % ---- Write CSV ----------------------------------------------------------
    if isempty(all_rows)
        error('No data extracted from any file.');
    end

    T = struct2table(vertcat(all_rows{:}));
    writetable(T, output_csv);
    fprintf('Done. %d rows written to:\n  %s\n', height(T), output_csv);
end


% =========================================================================
% Build one row from Kubios-stored segment metrics (Kubios index ki)
% =========================================================================
function row = build_kubios_row(pid, seg_num, label, t_start, t_end, ki, Res)
    row = struct();
    row.participant_id  = {pid};
    row.segment_number  = seg_num;
    row.segment_label   = {label};
    row.onset_offset    = {sprintf('%s - %s', sec2str(t_start), sec2str(t_end))};
    row.seg_start_s     = t_start;
    row.seg_stop_s      = t_end;

    % Data quality
    row.beats_total         = sv(Res.HRV.Data.BeatsTotal{ki});
    row.beats_corrected     = sv(Res.HRV.Data.BeatsCorrected{ki});
    row.beats_corrected_prc = sv(Res.HRV.Data.BeatsCorrectedPrc{ki});
    row.effective_data_s    = sv(Res.HRV.Data.EffectiveDataSec{ki});
    row.effective_data_prc  = sv(Res.HRV.Data.EffectiveDataPrc{ki});

    % Time domain
    stat = Res.HRV.Statistics;
    row.mean_RR_ms    = sv(stat.mean_RR{ki})  * 1000;
    row.std_RR_ms     = sv(stat.std_RR{ki})   * 1000;
    row.mean_HR_bpm   = sv(stat.mean_HR{ki});
    row.std_HR_bpm    = sv(stat.std_HR{ki});
    row.min_HR_bpm    = sv(stat.min_HR{ki});
    row.max_HR_bpm    = sv(stat.max_HR{ki});
    row.RMSSD_ms      = sv(stat.RMSSD{ki})    * 1000;
    row.NNxx          = sv(stat.NNxx{ki});
    row.pNNxx_prc     = sv(stat.pNNxx{ki});
    row.HRV_tri_index = sv(stat.HRV_tri_ind{ki});
    row.TINN_ms       = sv(stat.TINN{ki})     * 1000;
    row.SDANN_ms      = sv(stat.SDANN{ki});
    row.SDNN_index_ms = sv(stat.SDNN_index{ki});
    row.stress_index  = sv(stat.SI{ki});

    % Frequency: AR
    ar = Res.HRV.Frequency.AR{ki};
    row.VLF_peak_AR_Hz    = sv(ar.VLF_peak);
    row.LF_peak_AR_Hz     = sv(ar.LF_peak);
    row.HF_peak_AR_Hz     = sv(ar.HF_peak);
    row.VLF_power_AR_ms2  = sv(ar.VLF_power);
    row.LF_power_AR_ms2   = sv(ar.LF_power);
    row.HF_power_AR_ms2   = sv(ar.HF_power);
    row.VLF_power_AR_log  = sv(ar.logVLF_power);
    row.LF_power_AR_log   = sv(ar.logLF_power);
    row.HF_power_AR_log   = sv(ar.logHF_power);
    row.VLF_power_AR_prc  = sv(ar.VLF_power_prc);
    row.LF_power_AR_prc   = sv(ar.LF_power_prc);
    row.HF_power_AR_prc   = sv(ar.HF_power_prc);
    row.LF_power_AR_nu    = sv(ar.LF_power_nu);
    row.HF_power_AR_nu    = sv(ar.HF_power_nu);
    row.tot_power_AR_ms2  = sv(ar.tot_power);
    row.LF_HF_ratio_AR    = sv(ar.LF_HF_power);

    % Frequency: Welch (FFT)
    w = Res.HRV.Frequency.Welch{ki};
    row.VLF_peak_FFT_Hz    = sv(w.VLF_peak);
    row.LF_peak_FFT_Hz     = sv(w.LF_peak);
    row.HF_peak_FFT_Hz     = sv(w.HF_peak);
    row.VLF_power_FFT_ms2  = sv(w.VLF_power);
    row.LF_power_FFT_ms2   = sv(w.LF_power);
    row.HF_power_FFT_ms2   = sv(w.HF_power);
    row.VLF_power_FFT_log  = sv(w.logVLF_power);
    row.LF_power_FFT_log   = sv(w.logLF_power);
    row.HF_power_FFT_log   = sv(w.logHF_power);
    row.VLF_power_FFT_prc  = sv(w.VLF_power_prc);
    row.LF_power_FFT_prc   = sv(w.LF_power_prc);
    row.HF_power_FFT_prc   = sv(w.HF_power_prc);
    row.LF_power_FFT_nu    = sv(w.LF_power_nu);
    row.HF_power_FFT_nu    = sv(w.HF_power_nu);
    row.tot_power_FFT_ms2  = sv(w.tot_power);
    row.LF_HF_ratio_FFT    = sv(w.LF_HF_power);

    % Non-linear
    nl = Res.HRV.NonLinear;
    row.SD1_ms        = sv(nl.Poincare_SD1{ki})    * 1000;
    row.SD2_ms        = sv(nl.Poincare_SD2{ki})    * 1000;
    row.SD2_SD1_ratio = sv(nl.Poincare_SD2_SD1{ki});
    row.ApEn          = sv(nl.ApEn{ki});
    row.SampEn        = sv(nl.SampEn{ki});

    dfa = nl.DFA{ki};
    row.DFA_alpha1 = sv(dfa.alpha1);
    row.DFA_alpha2 = sv(dfa.alpha2);

    rpa = nl.RPA{ki};
    row.RPA_REC    = sv(rpa.REC);
    row.RPA_DET    = sv(rpa.DET);
    row.RPA_Lmean  = sv(rpa.Lmean);
    row.RPA_Lmax   = sv(rpa.Lmax);
    row.RPA_ShanEn = sv(rpa.ShanEn);

    mse = nl.MSE{ki};
    for mi = 1:20
        if mi <= length(mse)
            row.(sprintf('MSE_%d', mi)) = double(mse(mi));
        else
            row.(sprintf('MSE_%d', mi)) = NaN;
        end
    end

    % Summary
    row.PNS_index = sv(Res.HRV.Summary.PNS{ki}.index);
    row.SNS_index = sv(Res.HRV.Summary.SNS{ki}.index);
end


% =========================================================================
% Build whole_protocol boundary row — timing only, all HRV metrics NaN
% =========================================================================
function row = build_protocol_row(pid, t_start, t_end, n_beats)
    row = struct();
    row.participant_id  = {pid};
    row.segment_number  = 0;
    row.segment_label   = {'whole_protocol'};
    row.onset_offset    = {sprintf('%s - %s', sec2str(t_start), sec2str(t_end))};
    row.seg_start_s     = t_start;
    row.seg_stop_s      = t_end;

    % Beat count from corrected RR series (count only, not an HRV metric)
    row.beats_total         = n_beats;
    row.beats_corrected     = NaN;
    row.beats_corrected_prc = NaN;
    row.effective_data_s    = t_end - t_start;
    row.effective_data_prc  = NaN;

    % All HRV metrics NaN — this window was not analyzed as a Kubios segment.
    % Define it as a segment in Kubios to populate these fields.
    nan_fields = { ...
        'mean_RR_ms','std_RR_ms','mean_HR_bpm','std_HR_bpm','min_HR_bpm','max_HR_bpm', ...
        'RMSSD_ms','NNxx','pNNxx_prc','HRV_tri_index','TINN_ms','SDANN_ms', ...
        'SDNN_index_ms','stress_index', ...
        'VLF_peak_AR_Hz','LF_peak_AR_Hz','HF_peak_AR_Hz', ...
        'VLF_power_AR_ms2','LF_power_AR_ms2','HF_power_AR_ms2', ...
        'VLF_power_AR_log','LF_power_AR_log','HF_power_AR_log', ...
        'VLF_power_AR_prc','LF_power_AR_prc','HF_power_AR_prc', ...
        'LF_power_AR_nu','HF_power_AR_nu','tot_power_AR_ms2','LF_HF_ratio_AR', ...
        'VLF_peak_FFT_Hz','LF_peak_FFT_Hz','HF_peak_FFT_Hz', ...
        'VLF_power_FFT_ms2','LF_power_FFT_ms2','HF_power_FFT_ms2', ...
        'VLF_power_FFT_log','LF_power_FFT_log','HF_power_FFT_log', ...
        'VLF_power_FFT_prc','LF_power_FFT_prc','HF_power_FFT_prc', ...
        'LF_power_FFT_nu','HF_power_FFT_nu','tot_power_FFT_ms2','LF_HF_ratio_FFT', ...
        'SD1_ms','SD2_ms','SD2_SD1_ratio','ApEn','SampEn', ...
        'DFA_alpha1','DFA_alpha2', ...
        'RPA_REC','RPA_DET','RPA_Lmean','RPA_Lmax','RPA_ShanEn', ...
        'PNS_index','SNS_index'};
    for k = 1:length(nan_fields)
        row.(nan_fields{k}) = NaN;
    end
    for mi = 1:20
        row.(sprintf('MSE_%d', mi)) = NaN;
    end
end


% =========================================================================
% Helper: safe scalar — NaN for empty or all-NaN input
% =========================================================================
function val = sv(x)
    if isempty(x)
        val = NaN; return;
    end
    x = double(x(:));
    x = x(~isnan(x));
    val = x(1);  % first valid value
    if isempty(x), val = NaN; end
end


% =========================================================================
% Helper: decode uint16 char array stored by Kubios
% =========================================================================
function s = decode_char(arr)
    arr = double(arr(:))';
    s   = char(arr(arr > 0));
end


% =========================================================================
% Helper: format seconds as HH:MM:SS
% =========================================================================
function s = sec2str(sec)
    h     = floor(sec / 3600);
    m     = floor(mod(sec, 3600) / 60);
    s_val = round(mod(sec, 60));
    s     = sprintf('%02d:%02d:%02d', h, m, s_val);
end
