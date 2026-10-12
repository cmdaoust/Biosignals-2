# Follow-up notes

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
