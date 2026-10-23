# Follow-up notes

## TO DO: get Ledalab's ERA export from the batch run (added 23 Oct 2026)

**Issue:** `ledalab/run_ledalab_batch.m` asks Ledalab for an ERA export, but the batch run
imports the BIOPAC .mat with `'open', 'biopacmat'`, which brings in the signal only - no
events. With no events Ledalab silently skips the ERA export, so the 22 Oct run wrote SCR
lists for everyone but no `_era.txt` (the four existing ERA files - r2433, r4755, s1250,
s9686 - are from earlier runs where events were added by hand in the GUI). The run also
saved Ledalab's results over the raw BIOPAC exports in `ledalab/input/` (old in-place
behaviour), so those files can't be re-run as `biopacmat`.

**Current plan (23 Oct):** regenerate the Ledalab outputs, with events, from the older
versions of the input files restored from Box version history. 05 and `07_interim_summary.Rmd`
both read the ERA files (07 reads `ledalab/<id>_era.txt` directly, no R.matlab). A workaround
that computed the ERA measures in R from the saved .mat decomposition (via R.matlab) was tried
and dropped; it matched the existing ERA files within ~5% (SCR, tonic) and ~10% (nSCR).

**To fix in the Ledalab pipeline:**
1. Re-export the raw BIOPAC EDA .mat files into `ledalab/input/` (the current ones there are
   Ledalab output, not raw exports).
2. Add the block events before the batch run: e.g. a MATLAB step that builds a Ledalab-format
   .mat (`data.conductance`, `data.time`, `data.timeoff`, `data.event` with time/nid/name)
   from each raw export + its `_events_blocks_biopac_ledalab.txt`, then run the batch with
   `'open', 'leda'`. Check the format against a GUI-made file that has events first.
3. Check every participant has a non-empty `_era.txt` with 5 events, then re-knit 05 and 07.

**Also check:** r2433 and o8244 got very short CDA time constants in the 22 Oct run
(tau = 0.34/0.73 s and 0.24/0.60 s, vs ~0.5-1 / 1.3-2 s for the others). r2433's positive
recovery block now gives a phasic driver ~6x larger and a tonic level ~1.4 uS lower than its
earlier ERA file - the decomposition may be absorbing tonic changes. Inspect those two fits.

**ID mismatch:** the Ledalab and event files use G9788; the QC dashboard / PsychoPy use
C9788. Rename whichever is wrong.

---

## DCM threshold for SF analysis (ask Liat to ask Bach)

**Issue:** The DCM SF model was returning implausibly low values (~0.45) for 3-minute
epochs with many clearly visible SCRs. The threshold was initially set to 0.1 µS
(too high — set arbitrarily). Changed to 0.05 µS based on typical PsPM usage.

**Question for Bach:** What is the correct/recommended amplitude threshold for
SF-DCM with data from the BN-PPGED-R in µS units? Typical literature values
appear to be 0.01–0.05 µS.

---

## PsPM transfer function for BN-PPGED-R (ask Liat to ask Bach)

**Issue:** PsPM's `acq_python` import reads raw uncalibrated voltage values from the
.acq file rather than the calibrated µS values that AcqKnowledge/bioread display.
With `scr_transfer.none`, the imported signal is −0.008 to +0.0003 V instead of the
expected 11–17 µS.

**Current workaround** (`x03_preprocess_scr.m`): derived transfer function from
participant 001's known raw vs. calibrated range:

| Parameter       | Value  |
|-----------------|--------|
| transfer_const  | 0.001531 |
| offset          | −0.026   |
| resistor        | 0        |
| recsys          | conductance |

PsPM's formula is **scr = (raw − offset) / transfer_const** (divides, does not multiply).
- raw range from PsPM import: −0.0082 to +0.0003 V
- calibrated range from AcqKnowledge/bioread: 11.6 to 17.2 µS
- transfer_const = raw_range / µS_range = 0.0085 / 5.55 = 0.001531
- offset = raw value at 0 µS ≈ −0.026 V (back-calculated)

**Questions for Bach:**
1. What are the correct transfer function parameters for the BN-PPGED-R in PsPM?
2. Why does `acq_python` import return raw voltage instead of calibrated µS when
   bioread's `ch.data` already applies the AcqKnowledge calibration?
3. Is there an official supported way to import BIOPAC BN-PPGED-R data into PsPM
   so that units are correctly set to µS without manually specifying the calibration?
