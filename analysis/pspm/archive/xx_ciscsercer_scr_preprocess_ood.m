%-----------------------------------------------------------------------
% pspm PsPM - Unknown
% cfg_basicio BasicIO - Unknown
%-----------------------------------------------------------------------
matlabbatch{1}.pspm{1}.prep{1}.import.datatype.acqmat.datafile = {'/research/cisc2/projects/sdl_emotioncontrol/Biosignals2/raw_physiology/carmen_pilot_mat.mat'};
matlabbatch{1}.pspm{1}.prep{1}.import.datatype.acqmat.importtype{1}.scr.chan_nr.chan_nr_spec = 2;
matlabbatch{1}.pspm{1}.prep{1}.import.datatype.acqmat.importtype{1}.scr.scr_transfer.none = true;
matlabbatch{1}.pspm{1}.prep{1}.import.overwrite = 2;
matlabbatch{2}.pspm{1}.data_preprocessing{1}.pp_scr.datafile(1) = cfg_dep('Import: Output File', substruct('.','val', '{}',{1}, '.','val', '{}',{1}, '.','val', '{}',{1}), substruct('()',{':'}));
matlabbatch{2}.pspm{1}.data_preprocessing{1}.pp_scr.chan.chan_def = 0;
matlabbatch{2}.pspm{1}.data_preprocessing{1}.pp_scr.outputtype.output.file = '001_missing_epoch';
matlabbatch{2}.pspm{1}.data_preprocessing{1}.pp_scr.outputtype.output.dir = {'/research/cisc2/projects/sdl_emotioncontrol/Biosignals2/raw_physiology'};
matlabbatch{2}.pspm{1}.data_preprocessing{1}.pp_scr.outputtype.output.overwrite = 2;
matlabbatch{2}.pspm{1}.data_preprocessing{1}.pp_scr.options.min = 0.05;
matlabbatch{2}.pspm{1}.data_preprocessing{1}.pp_scr.options.max = 60;
matlabbatch{2}.pspm{1}.data_preprocessing{1}.pp_scr.options.slope = 10;
matlabbatch{2}.pspm{1}.data_preprocessing{1}.pp_scr.options.deflection_threshold = 0.1;
matlabbatch{2}.pspm{1}.data_preprocessing{1}.pp_scr.options.data_island_threshold = 0;
matlabbatch{2}.pspm{1}.data_preprocessing{1}.pp_scr.options.expand_epochs = 0.5;
matlabbatch{2}.pspm{1}.data_preprocessing{1}.pp_scr.options.clipping_detection.clipping_step_size = 2;
matlabbatch{2}.pspm{1}.data_preprocessing{1}.pp_scr.options.clipping_detection.clipping_threshold = 0.1;
