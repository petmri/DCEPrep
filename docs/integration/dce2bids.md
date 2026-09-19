# dce2bids Integration

[dce2bids](https://github.com/petmri/dce2bids) is the petmri group's DICOM-to-BIDS conversion tool for DCE-MRI studies. It is the **recommended** way to convert raw DICOM data into the BIDS layout DCEPrep expects. It is more automated, but has less control than the bundled `sort_dicom.py` script for new studies.

---

## Why dce2bids

Every scanner and protocol labels its series and parameters a little differently. Instead of maintaining a hand-edited series-matching config per site (as `sort_dicom.py` requires), dce2bids uses a coding agent (Claude Code, Codex, VS Code with Copilot, or Cursor) to work out the correct settings **once per scanner/protocol**, following the rules and validation steps defined in the tool's `SKILL.md`. After that one-time, AI-assisted setup, converting each new participant on that scanner/protocol is a single command — no AI needed.

Only the series DCEPrep needs are converted: the dynamic **DCE** series, the **VFA** flip-angle scans, and one **structural** scan (usually a T1 MPRAGE). Everything else in the session is left out.

---

## Integration with DCEPrep

dce2bids is a standalone tool that produces a BIDS dataset. DCEPrep itself only consumes BIDS-organized data — it does not call dce2bids directly, so any BIDS dataset produced by dce2bids that matches the [required file patterns](../getting-started/bids-setup.md#required-files-per-subjectsession) will work.

---

## How-To

- For an overview of the dce2bids workflow, see [DICOM to BIDS Conversion](../how-to/dicom-to-bids.md) 
- For complete installation and usage instructions, see the [dce2bids GitHub page](https://github.com/petmri/dce2bids)

---

## Related Pages

- [DICOM to BIDS Conversion](../how-to/dicom-to-bids.md) — walkthrough covering both dce2bids and the legacy `sort_dicom.py` path
- [BIDS Data Setup](../getting-started/bids-setup.md)
- [dce2bids on GitHub](https://github.com/petmri/dce2bids)
